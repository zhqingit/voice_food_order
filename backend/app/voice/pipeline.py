from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Awaitable, Callable

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.voice.config import GoogleVoiceConfig, VoiceRuntimeConfig
from app.voice.usage import UsageAccumulator

if TYPE_CHECKING:
    from app.voice.monitor import ConversationMonitor

try:
    import numpy as np
    from pipecat.adapters.llm.schemas.tools_schema import AdapterType, ToolsSchema
    from pipecat.frames.frames import (
        BotStartedSpeakingFrame,
        BotStoppedSpeakingFrame,
        FunctionCallCancelFrame,
        InputAudioRawFrame,
        InputDTMFFrame,
        InputTextRawFrame,
        LLMRunFrame,
        TranscriptionFrame,
    )
    from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        AssistantTurnStoppedMessage,
        LLMContextAggregatorPair,
        LLMUserAggregatorParams,
        UserTurnStoppedMessage,
    )
    from pipecat.turns.user_mute import FunctionCallUserMuteStrategy
    from pipecat.turns.user_start import TranscriptionUserTurnStartStrategy
    from pipecat.turns.user_turn_strategies import UserTurnStrategies
    from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService, GeminiVADParams
    from pipecat.services.google.gemini_live.vertex.llm import GeminiLiveVertexLLMService
    from google.genai.types import StartSensitivity, EndSensitivity
except ImportError:  # pragma: no cover - optional dependency
    np = None
    AdapterType = None
    ToolsSchema = None
    BotStartedSpeakingFrame = None
    BotStoppedSpeakingFrame = None
    FunctionCallCancelFrame = None
    InputAudioRawFrame = None
    InputDTMFFrame = None
    InputTextRawFrame = None
    LLMRunFrame = None
    TranscriptionFrame = None
    FrameDirection = None
    FrameProcessor = object  # type: ignore[assignment,misc]
    Pipeline = None
    PipelineParams = None
    PipelineTask = None
    LLMContext = None
    LLMContextAggregatorPair = None
    LLMUserAggregatorParams = None
    AssistantTurnStoppedMessage = None
    UserTurnStoppedMessage = None
    FunctionCallUserMuteStrategy = None
    TranscriptionUserTurnStartStrategy = None
    UserTurnStrategies = None
    GeminiLiveLLMService = None
    GeminiLiveVertexLLMService = None
    GeminiVADParams = None
    StartSensitivity = None
    EndSensitivity = None


def _rms(pcm16: bytes) -> float:
    """Root-mean-square level of a 16-bit PCM chunk (0–32768)."""
    samples = np.frombuffer(pcm16[: len(pcm16) // 2 * 2], dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0


def create_voice_pipeline_task(
    *,
    transport: Any,
    runtime: VoiceRuntimeConfig,
    google_config: GoogleVoiceConfig,
    system_prompt: str,
    tool_schema: Any,
    tool_handlers: dict[str, Callable[[Any], Awaitable[Any]]] | None = None,
    on_transcript: Callable[[str, str], Awaitable[None]] | None = None,
    on_interruption: Callable[[], Awaitable[None]] | None = None,
    on_bot_started_speaking: Callable[[], None] | None = None,
    on_bot_stopped_speaking: Callable[[], None] | None = None,
    on_customer_said: Callable[[str], None] | None = None,
    monitor: "ConversationMonitor | None" = None,
    usage: UsageAccumulator | None = None,
    enable_metrics: bool = True,
    voice_id: str = "Puck",
    greeting: str = "Greet me and ask what I want to order.",
    on_dtmf: Callable[[str], None] | None = None,
) -> Any:
    """
    Build a pipecat PipelineTask for a single voice session.

    Uses Gemini Live API for native audio-in/out (no separate STT/TTS services).
    Gemini Live handles VAD, turn-taking, and audio processing internally —
    no local aggregators or VAD are needed.
    Only a GEMINI_API_KEY is required.
    """

    if Pipeline is None:
        raise RuntimeError("pipecat is required for voice pipeline")

    tools = ToolsSchema(standard_tools=[], custom_tools={AdapterType.GEMINI: tool_schema})

    # Shared VAD tuning — same on both surfaces. LOW start sensitivity reduces
    # false triggers from kitchen/street noise; HIGH end sensitivity keeps us
    # from cutting off mid-sentence; 700ms silence is a good responsiveness vs.
    # natural-pause balance.
    vad_params = GeminiVADParams(
        start_sensitivity=StartSensitivity.START_SENSITIVITY_LOW,
        end_sensitivity=EndSensitivity.END_SENSITIVITY_HIGH,
        silence_duration_ms=700,
        prefix_padding_ms=300,
    )

    if settings.voice_use_vertex:
        project = settings.google_cloud_project.strip()
        if not project:
            raise RuntimeError("VOICE_USE_VERTEX is true but GOOGLE_CLOUD_PROJECT is empty")
        location = settings.google_cloud_location.strip() or "us-central1"
        logger.info(
            "Voice LLM: Vertex %s @ %s/%s",
            settings.voice_llm_model_vertex,
            project,
            location,
        )
        # Credentials resolve via ADC (attached service account on GCE, or
        # ~/.config/gcloud on dev machines mounted into the container).
        llm = GeminiLiveVertexLLMService(
            project_id=project,
            location=location,
            system_instruction=system_prompt,
            tools=tools,
            settings=GeminiLiveVertexLLMService.Settings(
                model=settings.voice_llm_model_vertex,
                voice=voice_id,
                vad=vad_params,
            ),
        )
    else:
        if not google_config.api_key:
            raise RuntimeError("Missing GOOGLE_API_KEY/GEMINI_API_KEY for Gemini Live (API surface)")
        logger.info("Voice LLM: Gemini API %s", runtime.llm_model)
        llm = GeminiLiveLLMService(
            api_key=google_config.api_key,
            system_instruction=system_prompt,
            tools=tools,
            settings=GeminiLiveLLMService.Settings(
                model=runtime.llm_model,
                voice=voice_id,
                vad=vad_params,
            ),
        )

    if tool_handlers:
        for name, handler in tool_handlers.items():
            llm.register_function(name, handler)

    # Interruptions must not cancel tool calls. Gemini Live sends the customer's
    # transcription, which pipecat treats as an interruption, at the same moment
    # as the tool call it led to, so the call would be cancelled as it starts
    # and the model told CANCELLED. Our tools finish quickly either way.
    async def _keep_tool_calls_running(_frame: Any) -> None:
        return

    llm._handle_interruptions = _keep_tool_calls_running

    # Hook into the LLM's internal metrics object to capture token usage.
    # We patch _metrics.start_llm_usage_metrics because the Gemini Live
    # service calls self.start_llm_usage_metrics() which delegates to
    # self._metrics.start_llm_usage_metrics() — patching at the _metrics
    # level reliably intercepts all token reports.
    #
    # Audio tokens are reported as a *subset* of prompt/completion totals and
    # are billed at a much higher rate, so they must be carried through
    # separately or session cost comes out far too low.
    if usage is not None:
        _metrics = llm._metrics
        _orig_metrics_llm_usage = _metrics.start_llm_usage_metrics

        async def _patched_metrics_llm_usage(tokens: Any) -> Any:
            usage.add_tokens(
                tokens.prompt_tokens,
                tokens.completion_tokens,
                tokens.input_audio_tokens or 0,
                tokens.output_audio_tokens or 0,
            )
            return await _orig_metrics_llm_usage(tokens)

        _metrics.start_llm_usage_metrics = _patched_metrics_llm_usage

    # Create context with greeting message for the aggregator pair.
    context = LLMContext(
        messages=[{"role": "user", "content": greeting}],
    )

    # Use context aggregators for transcript capture + interruption handling.
    # - TranscriptionUserTurnStartStrategy: detect user speech from Gemini
    #   Live's transcription frames (no local VAD needed).
    # - FunctionCallUserMuteStrategy: suppress interruptions while tool calls
    #   are in flight, preventing the "second item not added" bug.
    #
    # realtime_service_mode is opted out of explicitly. Gemini Live advertises
    # itself as a realtime service, which would auto-enable the mode — and that
    # drops TranscriptionUserTurnStartStrategy on the grounds that the service
    # drives turn-taking itself. But Gemini Live emits no turn-start/-end
    # frames, and our websocket transport carries no local VAD, so nothing
    # would be left to start a user turn: on_user_turn_started would stop
    # firing and the client would never be told to flush its audio buffer on
    # barge-in. Realtime mode also stops populating UserTurnStoppedMessage
    # .content, which our transcript handler reads.
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                start=[TranscriptionUserTurnStartStrategy()],
            ),
            user_mute_strategies=[FunctionCallUserMuteStrategy()],
        ),
        realtime_service_mode=False,
    )

    # Observe FunctionCallCancelFrame so we can recover when pipecat cancels a
    # tool call mid-flight (happens when a user utterance races with Gemini's
    # tool-call dispatch). Without recovery Gemini sits silent, waiting for a
    # tool result that will never arrive.
    cancel_events: asyncio.Queue[str] = asyncio.Queue()

    class _FunctionCallCancelObserver(FrameProcessor):
        async def process_frame(self, frame: Any, direction: Any) -> None:
            await super().process_frame(frame, direction)
            if FunctionCallCancelFrame is not None and isinstance(frame, FunctionCallCancelFrame):
                try:
                    cancel_events.put_nowait(getattr(frame, "tool_call_id", "") or "unknown")
                except Exception:
                    pass
            # The output transport emits these as the bot's audio starts and
            # finishes playing (sent both ways; only the upstream copy passes
            # here). They also feed the checkout name and approval gates.
            if BotStartedSpeakingFrame is not None and isinstance(frame, BotStartedSpeakingFrame):
                _on_bot_started_speaking()
                if on_bot_started_speaking is not None:
                    on_bot_started_speaking()
            elif BotStoppedSpeakingFrame is not None and isinstance(frame, BotStoppedSpeakingFrame):
                _on_bot_stopped_speaking()
                if on_bot_stopped_speaking is not None:
                    on_bot_stopped_speaking()
            await self.push_frame(frame, direction)

    cancel_observer = _FunctionCallCancelObserver()

    # Gemini Live only sends the user's transcription once they finish
    # speaking, so turn events can't tell the silence nudge that the customer
    # is mid-sentence (e.g. spelling a long address). Track mic level instead.
    last_voice_at = 0.0

    class _UserVoiceDetector(FrameProcessor):
        async def process_frame(self, frame: Any, direction: Any) -> None:
            nonlocal last_voice_at
            await super().process_frame(frame, direction)
            if isinstance(frame, InputAudioRawFrame) and _rms(frame.audio) >= settings.voice_speech_rms_threshold:
                last_voice_at = time.monotonic()
            elif on_dtmf is not None and isinstance(frame, InputDTMFFrame):
                on_dtmf(str(frame.button.value))  # phone keypad (Twilio)
            await self.push_frame(frame, direction)

    # Sits right next to the LLM: the customer's words feed the checkout approval
    # gate as soon as Gemini reports them, ahead of the aggregator's turn events.
    class _CustomerTranscriptTap(FrameProcessor):
        async def process_frame(self, frame: Any, direction: Any) -> None:
            await super().process_frame(frame, direction)
            if on_customer_said is not None and isinstance(frame, TranscriptionFrame) and frame.text:
                on_customer_said(frame.text)
            await self.push_frame(frame, direction)

    pipeline = Pipeline([
        transport.input(),
        _UserVoiceDetector(),
        user_agg,
        _CustomerTranscriptTap(),
        llm,
        cancel_observer,
        transport.output(),
        assistant_agg,
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            # No allow_interruptions: the field was removed in pipecat 1.x and
            # is silently discarded. Interruptions are governed by the user
            # turn/mute strategies on the aggregator pair above.
            enable_metrics=enable_metrics,
            enable_usage_metrics=enable_metrics,
        ),
    )

    # Attach monitor to the pipeline task so it can inject corrections.
    if monitor is not None:
        monitor.attach(task)

    # ── Silence nudge: if user stays quiet after the bot finishes speaking, ─
    # ── prompt the LLM to follow up. ──────────────────────────────────────
    SILENCE_TIMEOUT = settings.voice_silence_nudge_seconds
    MAX_NUDGES = settings.voice_silence_max_nudges
    _nudge_timer: asyncio.Task[None] | None = None
    _nudges_sent = 0
    _bot_speaking = False

    async def _send_system_note(text: str) -> None:
        # Sent as realtime text straight to the LLM processor: Gemini 3 answers
        # this, whereas an LLMMessagesAppendFrame only adds to its context.
        await llm.process_frame(InputTextRawFrame(text=text), FrameDirection.DOWNSTREAM)

    async def _nudge_after_silence() -> None:
        nonlocal _nudges_sent
        # Count silence from the later of the bot finishing and the customer's
        # last audible audio, so talking keeps pushing the nudge back.
        started = time.monotonic()
        while (wait := max(started, last_voice_at) + SILENCE_TIMEOUT - time.monotonic()) > 0:
            await asyncio.sleep(wait)
        _nudges_sent += 1
        logger.info("Silence nudge: user silent for %.1fs, prompting bot follow-up", SILENCE_TIMEOUT)
        await _send_system_note(
            "(System note, not from the customer: the customer has been quiet. Say out loud, in one short natural sentence, a question asking whether they need anything else. Never read this note aloud.)"
        )

    def _cancel_nudge() -> None:
        nonlocal _nudge_timer
        if _nudge_timer is not None and not _nudge_timer.done():
            _nudge_timer.cancel()
        _nudge_timer = None

    def _start_nudge() -> None:
        nonlocal _nudge_timer
        _cancel_nudge()
        if _nudges_sent >= MAX_NUDGES:
            logger.info("Silence nudge: %d sent with no reply, waiting for idle timeout", _nudges_sent)
            return
        _nudge_timer = asyncio.create_task(_nudge_after_silence())

    def _reset_nudges() -> None:
        nonlocal _nudges_sent
        _nudges_sent = 0
        _cancel_nudge()

    # A turn can stop before its audio plays (a tool call ends the turn, then
    # the reply comes), so the silence clock only runs while the bot is quiet.
    def _on_bot_started_speaking() -> None:
        nonlocal _bot_speaking
        _bot_speaking = True
        _cancel_nudge()

    def _on_bot_stopped_speaking() -> None:
        nonlocal _bot_speaking
        _bot_speaking = False
        _start_nudge()

    # Notify client of interruptions so it can clear its audio buffer.
    @user_agg.event_handler("on_user_turn_started")
    async def _on_user_turn_started(agg: Any, strategy: Any) -> None:
        logger.debug("User turn started (barge-in detected)")
        _reset_nudges()
        if on_interruption is not None:
            await on_interruption()

    # Register transcript event handlers.
    @user_agg.event_handler("on_user_turn_stopped")
    async def _on_user_turn(agg: Any, strategy: Any, message: UserTurnStoppedMessage) -> None:
        logger.debug("User turn stopped, cancelling silence nudge timer")
        _reset_nudges()
        if monitor is not None:
            monitor.record_user(message.content)
        if on_transcript is not None:
            await on_transcript("user", message.content)

    @assistant_agg.event_handler("on_assistant_turn_stopped")
    async def _on_assistant_turn(agg: Any, message: AssistantTurnStoppedMessage) -> None:
        if not _bot_speaking:
            logger.debug("Assistant turn stopped, starting %ss silence nudge timer", SILENCE_TIMEOUT)
            _start_nudge()
        if monitor is not None:
            monitor.record_assistant(message.content)
        if on_transcript is not None:
            await on_transcript("assistant", message.content)

    # ── Recovery loop: drain cancel events and unstick Gemini ─────────────
    # When a function call is cancelled mid-flight, Gemini's internal state is
    # "awaiting tool result" — it won't speak. Our shielded handler still
    # commits the DB write, so the order state is correct; we just need to
    # prod Gemini so it re-reads context and responds to the customer.
    _recovery_task: asyncio.Task[None] | None = None

    async def _recovery_loop() -> None:
        while True:
            tool_call_id = await cancel_events.get()
            # Small settle so pipecat finishes its cancel bookkeeping before
            # we push a new frame.
            await asyncio.sleep(0.3)
            logger.info(
                "Recovery: function call %s cancelled mid-flight; nudging Gemini to resume",
                tool_call_id,
            )
            try:
                await _send_system_note(
                    "(System note, not from the customer: your previous tool call was interrupted. Check the current order state and respond briefly to the customer. Never read this note aloud.)"
                )
            except Exception:
                logger.warning("Recovery: failed to push nudge frames", exc_info=True)

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(task: PipelineTask, frame: Any):
        nonlocal _recovery_task
        _recovery_task = asyncio.create_task(_recovery_loop())
        # Context is already set via the aggregator pair; just trigger the LLM run.
        await task.queue_frames([LLMRunFrame()])

    @task.event_handler("on_pipeline_finished")
    async def on_pipeline_finished(task: PipelineTask, frame: Any):
        _cancel_nudge()
        if _recovery_task is not None and not _recovery_task.done():
            _recovery_task.cancel()

    return task
