from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable

logger = logging.getLogger(__name__)

from app.core.config import settings
from app.voice.config import GoogleVoiceConfig, VoiceRuntimeConfig
from app.voice.usage import UsageAccumulator

if TYPE_CHECKING:
    from app.voice.monitor import ConversationMonitor

try:
    from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
    from pipecat.frames.frames import (
        FunctionCallCancelFrame,
        LLMMessagesAppendFrame,
        LLMRunFrame,
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
    AdapterType = None
    ToolsSchema = None
    FunctionCallCancelFrame = None
    LLMMessagesAppendFrame = None
    LLMRunFrame = None
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
    monitor: "ConversationMonitor | None" = None,
    usage: UsageAccumulator | None = None,
    enable_metrics: bool = True,
    voice_id: str = "Puck",
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

    # Hook into the LLM's internal metrics object to capture token usage.
    # We patch _metrics.start_llm_usage_metrics because the Gemini Live
    # service calls self.start_llm_usage_metrics() which delegates to
    # self._metrics.start_llm_usage_metrics() — patching at the _metrics
    # level reliably intercepts all token reports.
    if usage is not None:
        _metrics = llm._metrics
        _orig_metrics_llm_usage = _metrics.start_llm_usage_metrics

        async def _patched_metrics_llm_usage(tokens: Any) -> Any:
            usage.add_tokens(tokens.prompt_tokens, tokens.completion_tokens)
            return await _orig_metrics_llm_usage(tokens)

        _metrics.start_llm_usage_metrics = _patched_metrics_llm_usage

    # Create context with greeting message for the aggregator pair.
    context = LLMContext(
        messages=[{"role": "user", "content": "Greet me and ask what I want to order."}],
    )

    # Use context aggregators for transcript capture + interruption handling.
    # - TranscriptionUserTurnStartStrategy: detect user speech from Gemini
    #   Live's transcription frames (no local VAD needed).
    # - FunctionCallUserMuteStrategy: suppress interruptions while tool calls
    #   are in flight, preventing the "second item not added" bug.
    user_agg, assistant_agg = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            user_turn_strategies=UserTurnStrategies(
                start=[TranscriptionUserTurnStartStrategy()],
            ),
            user_mute_strategies=[FunctionCallUserMuteStrategy()],
        ),
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
            await self.push_frame(frame, direction)

    cancel_observer = _FunctionCallCancelObserver()

    pipeline = Pipeline([
        transport.input(),
        user_agg,
        llm,
        cancel_observer,
        transport.output(),
        assistant_agg,
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=enable_metrics,
            enable_usage_metrics=enable_metrics,
        ),
    )

    # Attach monitor to the pipeline task so it can inject corrections.
    if monitor is not None:
        monitor.attach(task)

    # ── Silence nudge: if user doesn't speak within 5s after bot finishes, ──
    # ── prompt the LLM to follow up. ──────────────────────────────────────
    SILENCE_TIMEOUT = settings.voice_silence_nudge_seconds
    _nudge_timer: asyncio.Task[None] | None = None

    async def _nudge_after_silence() -> None:
        await asyncio.sleep(SILENCE_TIMEOUT)
        logger.info("Silence nudge: user silent for %.1fs, prompting bot follow-up", SILENCE_TIMEOUT)
        # Push directly to the LLM processor, bypassing transport/aggregator
        # which may not forward LLMMessagesAppendFrame.
        frame = LLMMessagesAppendFrame(
            messages=[{"role": "user", "content": "(The customer has been silent for a few seconds. Briefly ask if they need anything else.)"}],
        )
        await llm.process_frame(frame, FrameDirection.DOWNSTREAM)

    def _cancel_nudge() -> None:
        nonlocal _nudge_timer
        if _nudge_timer is not None and not _nudge_timer.done():
            _nudge_timer.cancel()
        _nudge_timer = None

    def _start_nudge() -> None:
        nonlocal _nudge_timer
        _cancel_nudge()
        _nudge_timer = asyncio.create_task(_nudge_after_silence())

    # Notify client of interruptions so it can clear its audio buffer.
    @user_agg.event_handler("on_user_turn_started")
    async def _on_user_turn_started(agg: Any, strategy: Any) -> None:
        logger.debug("User turn started (barge-in detected)")
        _cancel_nudge()
        if on_interruption is not None:
            await on_interruption()

    # Register transcript event handlers.
    @user_agg.event_handler("on_user_turn_stopped")
    async def _on_user_turn(agg: Any, strategy: Any, message: UserTurnStoppedMessage) -> None:
        logger.debug("User turn stopped, cancelling silence nudge timer")
        _cancel_nudge()
        if monitor is not None:
            monitor.record_user(message.content)
        if on_transcript is not None:
            await on_transcript("user", message.content)

    @assistant_agg.event_handler("on_assistant_turn_stopped")
    async def _on_assistant_turn(agg: Any, message: AssistantTurnStoppedMessage) -> None:
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
                await task.queue_frames([
                    LLMMessagesAppendFrame(
                        messages=[{
                            "role": "user",
                            "content": "(system: your previous tool call was interrupted. Check the current order state and respond briefly to the customer.)",
                        }],
                    ),
                    LLMRunFrame(),
                ])
            except Exception:
                logger.warning("Recovery: failed to push nudge frames", exc_info=True)

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(task: PipelineTask, frame: Any):
        nonlocal _recovery_task
        _recovery_task = asyncio.create_task(_recovery_loop())
        # Context is already set via the aggregator pair; just trigger the LLM run.
        await task.queue_frames([LLMRunFrame()])

    @task.event_handler("on_pipeline_stopped")
    async def on_pipeline_stopped(task: PipelineTask, frame: Any):
        _cancel_nudge()
        if _recovery_task is not None and not _recovery_task.done():
            _recovery_task.cancel()

    return task
