from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Callable

from app.voice.config import GoogleVoiceConfig, VoiceRuntimeConfig

if TYPE_CHECKING:
    from app.voice.monitor import ConversationMonitor

try:
    from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
    from pipecat.frames.frames import LLMRunFrame
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
    LLMRunFrame = None
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

    # Register transcript event handlers.
    @user_agg.event_handler("on_user_turn_stopped")
    async def _on_user_turn(agg: Any, strategy: Any, message: UserTurnStoppedMessage) -> None:
        if monitor is not None:
            monitor.record_user(message.content)
        if on_transcript is not None:
            await on_transcript("user", message.content)

    @assistant_agg.event_handler("on_assistant_turn_stopped")
    async def _on_assistant_turn(agg: Any, message: AssistantTurnStoppedMessage) -> None:
        if monitor is not None:
            monitor.record_assistant(message.content)
        if on_transcript is not None:
            await on_transcript("assistant", message.content)

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(task: PipelineTask, frame: Any):
        # Context is already set via the aggregator pair; just trigger the LLM run.
        await task.queue_frames([LLMRunFrame()])

    return task
