"""Token usage accumulator for voice pipeline sessions."""

from __future__ import annotations

import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

try:
    from pipecat.frames.frames import MetricsFrame
    from pipecat.metrics.metrics import LLMUsageMetricsData
except ImportError:  # pragma: no cover
    MetricsFrame = None
    LLMUsageMetricsData = None

# Gemini 2.0 Flash pricing (per 1M tokens)
# https://ai.google.dev/pricing
_INPUT_PRICE_PER_M = Decimal("0.10")   # $0.10 per 1M input tokens
_OUTPUT_PRICE_PER_M = Decimal("0.40")  # $0.40 per 1M output tokens
_PER_M = Decimal("1000000")

# Gemini Flash Lite pricing (used by ConversationMonitor)
_MONITOR_INPUT_PRICE_PER_M = Decimal("0.075")   # $0.075 per 1M input tokens
_MONITOR_OUTPUT_PRICE_PER_M = Decimal("0.30")    # $0.30 per 1M output tokens


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Estimate LLM cost based on Gemini Flash pricing."""
    input_cost = Decimal(prompt_tokens) * _INPUT_PRICE_PER_M / _PER_M
    output_cost = Decimal(completion_tokens) * _OUTPUT_PRICE_PER_M / _PER_M
    return (input_cost + output_cost).quantize(Decimal("0.000001"))


def estimate_monitor_cost(prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Estimate LLM cost based on Gemini Flash Lite pricing (monitor model)."""
    input_cost = Decimal(prompt_tokens) * _MONITOR_INPUT_PRICE_PER_M / _PER_M
    output_cost = Decimal(completion_tokens) * _MONITOR_OUTPUT_PRICE_PER_M / _PER_M
    return (input_cost + output_cost).quantize(Decimal("0.000001"))


class UsageAccumulator:
    """Accumulates LLM token usage by intercepting MetricsFrames pushed by the LLM."""

    def __init__(self):
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost(self) -> Decimal:
        return estimate_cost(self.prompt_tokens, self.completion_tokens)

    def add_tokens(self, prompt: int, completion: int) -> None:
        """Add token counts from an LLM call."""
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        logger.info(
            "LLM usage: +%d/%d tokens (cumulative: %d/%d)",
            prompt, completion,
            self.prompt_tokens, self.completion_tokens,
        )
