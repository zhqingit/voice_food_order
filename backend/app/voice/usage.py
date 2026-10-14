"""Token usage accumulator for voice pipeline sessions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from pipecat.frames.frames import MetricsFrame
    from pipecat.metrics.metrics import LLMUsageMetricsData
except ImportError:  # pragma: no cover
    MetricsFrame = None
    LLMUsageMetricsData = None

_PER_M = Decimal("1000000")


@dataclass(frozen=True)
class LivePricing:
    """Per-1M-token prices for a Gemini Live (native audio) model."""

    text_input: Decimal
    audio_input: Decimal
    text_output: Decimal
    audio_output: Decimal


# Live API pricing, per 1M tokens.
# https://ai.google.dev/gemini-api/docs/pricing
# https://cloud.google.com/vertex-ai/generative-ai/pricing
#
# Audio costs 6x text on input and 6x (Vertex) / 2.7x (API) on output, and a
# voice session is almost entirely audio — so pricing everything at the text
# rate understates the true cost by roughly an order of magnitude.
_PRICING_VERTEX_2_5 = LivePricing(  # google/gemini-live-2.5-flash-native-audio
    text_input=Decimal("0.50"),
    audio_input=Decimal("3.00"),
    text_output=Decimal("2.00"),
    audio_output=Decimal("12.00"),
)
_PRICING_API_3_1 = LivePricing(  # gemini-3.1-flash-live-preview
    text_input=Decimal("0.75"),
    audio_input=Decimal("3.00"),
    text_output=Decimal("4.50"),
    audio_output=Decimal("12.00"),
)

# ConversationMonitor runs settings.voice_monitor_model (gemini-2.5-flash),
# which is text-only.
_MONITOR_INPUT_PRICE_PER_M = Decimal("0.30")
_MONITOR_OUTPUT_PRICE_PER_M = Decimal("2.50")


def live_pricing() -> LivePricing:
    """Pricing for whichever Live model the pipeline is configured to run."""
    return _PRICING_VERTEX_2_5 if settings.voice_use_vertex else _PRICING_API_3_1


def estimate_cost(
    prompt_tokens: int,
    completion_tokens: int,
    input_audio_tokens: int = 0,
    output_audio_tokens: int = 0,
) -> Decimal:
    """Estimate Gemini Live cost, pricing audio and text tokens separately.

    Gemini reports audio tokens as a *subset* of the prompt/completion totals,
    so the text portion is the remainder. The subtraction is clamped at zero in
    case a turn ever reports an audio count above its own total.
    """
    pricing = live_pricing()
    text_input_tokens = max(prompt_tokens - input_audio_tokens, 0)
    text_output_tokens = max(completion_tokens - output_audio_tokens, 0)
    total = (
        Decimal(text_input_tokens) * pricing.text_input
        + Decimal(input_audio_tokens) * pricing.audio_input
        + Decimal(text_output_tokens) * pricing.text_output
        + Decimal(output_audio_tokens) * pricing.audio_output
    ) / _PER_M
    return total.quantize(Decimal("0.000001"))


def estimate_monitor_cost(prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Estimate LLM cost for the ConversationMonitor's text-only calls."""
    input_cost = Decimal(prompt_tokens) * _MONITOR_INPUT_PRICE_PER_M / _PER_M
    output_cost = Decimal(completion_tokens) * _MONITOR_OUTPUT_PRICE_PER_M / _PER_M
    return (input_cost + output_cost).quantize(Decimal("0.000001"))


class UsageAccumulator:
    """Accumulates LLM token usage by intercepting MetricsFrames pushed by the LLM."""

    def __init__(self):
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        # Audio subsets of the two counts above — tracked separately for
        # pricing, not added to the totals.
        self.input_audio_tokens: int = 0
        self.output_audio_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost(self) -> Decimal:
        return estimate_cost(
            self.prompt_tokens,
            self.completion_tokens,
            self.input_audio_tokens,
            self.output_audio_tokens,
        )

    def add_tokens(
        self,
        prompt: int,
        completion: int,
        input_audio: int = 0,
        output_audio: int = 0,
    ) -> None:
        """Add token counts from an LLM call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.input_audio_tokens += input_audio
        self.output_audio_tokens += output_audio
        logger.info(
            "LLM usage: +%d/%d tokens (audio %d/%d) (cumulative: %d/%d, audio %d/%d)",
            prompt, completion, input_audio, output_audio,
            self.prompt_tokens, self.completion_tokens,
            self.input_audio_tokens, self.output_audio_tokens,
        )
