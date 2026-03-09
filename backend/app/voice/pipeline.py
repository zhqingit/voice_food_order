from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable

logger = logging.getLogger(__name__)

from app.voice.config import GoogleVoiceConfig, VoiceRuntimeConfig

if TYPE_CHECKING:
    from app.voice.monitor import ConversationMonitor

try:
    from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
    from pipecat.frames.frames import LLMMessagesAppendFrame, LLMRunFrame
    from pipecat.processors.frame_processor import FrameDirection
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import (
        AssistantTurnStoppedMessage,
        LLMContextAggregatorPair,
        UserTurnStoppedMessage,
    )
    from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
except ImportError:  # pragma: no cover - optional dependency
    AdapterType = None
    ToolsSchema = None
    LLMMessagesAppendFrame = None
    LLMRunFrame = None
    FrameDirection = None
    Pipeline = None
    PipelineParams = None
    PipelineTask = None
    LLMContext = None
    LLMContextAggregatorPair = None
    AssistantTurnStoppedMessage = None
    UserTurnStoppedMessage = None
    GeminiLiveLLMService = None


def create_voice_pipeline_task(
    *,
    transport: Any,
    runtime: VoiceRuntimeConfig,
    google_config: GoogleVoiceConfig,
    system_prompt: str,
    tool_schema: Any,
    tool_handlers: dict[str, Callable[[Any], Awaitable[Any]]] | None = None,
    on_transcript: Callable[[str, str], Awaitable[None]] | None = None,
    monitor: "ConversationMonitor | None" = None,
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

    if not google_config.api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY/GEMINI_API_KEY for Gemini Live")

    if Pipeline is None:
        raise RuntimeError("pipecat is required for voice pipeline")

    tools = ToolsSchema(standard_tools=[], custom_tools={AdapterType.GEMINI: tool_schema})

    llm = GeminiLiveLLMService(
        api_key=google_config.api_key,
        model=runtime.llm_model,
        system_instruction=system_prompt,
        tools=tools,
        voice_id=voice_id,
    )

    if tool_handlers:
        for name, handler in tool_handlers.items():
            llm.register_function(name, handler)

    # Create context with greeting message for the aggregator pair.
    context = LLMContext(
        messages=[{"role": "user", "content": "Greet me and ask what I want to order."}],
    )

    # Use context aggregators for transcript capture.
    # Do NOT add a local VAD — Gemini Live handles VAD and turn-taking
    # internally.  Adding SileroVAD causes transcription events to trigger
    # spurious interruptions that cancel pending tool calls.
    user_agg, assistant_agg = LLMContextAggregatorPair(context)

    pipeline = Pipeline([
        transport.input(),
        user_agg,
        llm,
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
    SILENCE_TIMEOUT = 5.0
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

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(task: PipelineTask, frame: Any):
        # Context is already set via the aggregator pair; just trigger the LLM run.
        await task.queue_frames([LLMRunFrame()])

    @task.event_handler("on_pipeline_stopped")
    async def on_pipeline_stopped(task: PipelineTask, frame: Any):
        _cancel_nudge()

    return task
