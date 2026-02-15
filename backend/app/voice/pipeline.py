from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

from app.voice.config import GoogleVoiceConfig, VoiceRuntimeConfig

try:
    from pipecat.adapters.schemas.tools_schema import AdapterType, ToolsSchema
    from pipecat.frames.frames import LLMMessagesAppendFrame, LLMRunFrame
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.task import PipelineParams, PipelineTask
    from pipecat.processors.aggregators.llm_context import LLMContext
    from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
    from pipecat.processors.filters.stt_mute_filter import STTMuteConfig, STTMuteFilter, STTMuteStrategy
    from pipecat.services.google.llm import GoogleLLMService
    from pipecat.services.google.stt import GoogleSTTService
    from pipecat.services.google.tts import GoogleTTSService
except ImportError:  # pragma: no cover - optional dependency during Phase 2.1
    AdapterType = None
    ToolsSchema = None
    LLMMessagesAppendFrame = None
    LLMRunFrame = None
    Pipeline = None
    PipelineParams = None
    PipelineTask = None
    LLMContext = None
    LLMContextAggregatorPair = None
    STTMuteConfig = None
    STTMuteFilter = None
    STTMuteStrategy = None
    GoogleLLMService = None
    GoogleSTTService = None
    GoogleTTSService = None


class ConversationLogger:
    def __init__(self, *, label: str = "") -> None:
        self._label = label.strip()

    async def process(self, frame: Any, direction: Any, push: Callable[[Any, Any], Awaitable[None]]) -> None:
        text = getattr(frame, "text", "")
        if isinstance(text, str) and text.strip():
            prefix = f"{self._label}: " if self._label else ""
            print(f"{prefix}{text.strip()}")
        await push(frame, direction)


class LLMRateLimiter:
    def __init__(self, *, max_requests_per_minute: float) -> None:
        if max_requests_per_minute <= 0:
            raise ValueError("max_requests_per_minute must be > 0")
        self._interval_secs = 60.0 / float(max_requests_per_minute)
        self._next_allowed_time = 0.0

    async def process(self, frame: Any, direction: Any, push: Callable[[Any, Any], Awaitable[None]]) -> None:
        is_llm_run = frame.__class__.__name__ == "LLMRunFrame"
        if is_llm_run and str(direction).lower().endswith("downstream"):
            now = time.monotonic()
            sleep_for = self._next_allowed_time - now
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            self._next_allowed_time = max(self._next_allowed_time, time.monotonic()) + self._interval_secs
        await push(frame, direction)


def create_voice_pipeline_task(
    *,
    transport: Any,
    runtime: VoiceRuntimeConfig,
    google_config: GoogleVoiceConfig,
    system_prompt: str,
    tool_schema: Any,
    tool_handlers: dict[str, Callable[[Any], Awaitable[Any]]] | None = None,
    max_rpm: float = 5.0,
    enable_metrics: bool = True,
) -> Any:
    """
    Build a pipecat PipelineTask for a single voice session.

    Providers are selected via `runtime`; only Google providers are wired in Phase 2.1.
    """

    if runtime.stt_provider != "google" or runtime.tts_provider != "google" or runtime.llm_provider != "google":
        raise NotImplementedError("Only Google STT/TTS/LLM providers are wired in Phase 2.1")

    if not google_config.api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY/GEMINI_API_KEY for LLM")
    if not google_config.credentials_path:
        raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS for STT/TTS")

    if Pipeline is None:
        raise RuntimeError("pipecat is required for voice pipeline")

    stt = GoogleSTTService(credentials_path=google_config.credentials_path)
    tts = GoogleTTSService(credentials_path=google_config.credentials_path)
    llm = GoogleLLMService(api_key=google_config.api_key, model=runtime.llm_model)

    if tool_handlers:
        for name, handler in tool_handlers.items():
            llm.register_function(name, handler)

    tools = ToolsSchema(standard_tools=[], custom_tools={AdapterType.GEMINI: tool_schema})
    context = LLMContext(messages=[{"role": "system", "content": system_prompt}], tools=tools)
    context_aggregators = LLMContextAggregatorPair(context)

    stt_mute = STTMuteFilter(config=STTMuteConfig(strategies={STTMuteStrategy.ALWAYS}))
    #rate_limiter = LLMRateLimiter(max_requests_per_minute=max_rpm)

    processors = [
        transport.input(),
        stt,
        stt_mute,
        context_aggregators.user(),
        #rate_limiter,
        llm,
        tts,
        context_aggregators.assistant(),
        transport.output(),
    ]

    pipeline = Pipeline(processors)

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=False,
            enable_metrics=enable_metrics,
            enable_usage_metrics=enable_metrics,
        ),
    )

    @task.event_handler("on_pipeline_started")
    async def on_pipeline_started(task: PipelineTask, frame: Any):
        await task.queue_frames([
            LLMMessagesAppendFrame(messages=[{
                "role": "user",
                "content": "Greet me and ask what I want to order.",
            }]),
            LLMRunFrame(),
        ])

    return task
