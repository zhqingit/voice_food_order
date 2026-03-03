from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.voice.config import GoogleVoiceConfig, VoiceRuntimeConfig

try:
    from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
    from pipecat.frames.frames import LLMContextFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.services.google.gemini_live.llm import GeminiLiveLLMService
except ImportError:  # pragma: no cover - optional dependency
    AdapterType = None
    ToolsSchema = None
    LLMContextFrame = None
    Pipeline = None
    PipelineParams = None
    PipelineTask = None
    LLMContext = None
    GeminiLiveLLMService = None


def create_voice_pipeline_task(
    *,
    transport: Any,
    runtime: VoiceRuntimeConfig,
    google_config: GoogleVoiceConfig,
    system_prompt: str,
    tool_schema: Any,
    tool_handlers: dict[str, Callable[[Any], Awaitable[Any]]] | None = None,
    enable_metrics: bool = True,
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

    # TODO: Re-enable tools once Gemini Live API 1008 bug with tool calls is fixed.
    # See: https://discuss.ai.google.dev/t/gemini-live-api-random-websocket-closures-after-sendtoolresponse/109319
    # tools = ToolsSchema(standard_tools=[], custom_tools={AdapterType.GEMINI: tool_schema})

    llm = GeminiLiveLLMService(
        api_key=google_config.api_key,
        model=runtime.llm_model,
        system_instruction=system_prompt,
        #tools=tools,  # Disabled: causes 1008 crashes
        voice_id="Puck",
    )

    # if tool_handlers:
    #     for name, handler in tool_handlers.items():
    #         llm.register_function(name, handler)

    # Gemini Live processes audio natively — pipe audio directly to LLM.
    # No LLMContextAggregatorPair or local VAD needed.
    pipeline = Pipeline([
        transport.input(),
        llm,
        transport.output(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=enable_metrics,
            enable_usage_metrics=enable_metrics,
        ),
    )

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(task: PipelineTask, frame: Any):
        # Send initial context to trigger a greeting.
        # LLMContextFrame → _handle_context() → _create_initial_response()
        # which correctly handles the case where the Gemini session isn't
        # ready yet (sets _run_llm_when_session_ready = True).
        context = LLMContext(
            messages=[{"role": "user", "content": "Greet me and ask what I want to order."}],
        )
        await task.queue_frames([LLMContextFrame(context=context)])

    return task
