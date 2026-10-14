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

_PER_M = Decimal("1000000")

# Gemini Live prices per 1M tokens, split by modality. Live sessions mix text
# (system prompt + menu, re-billed every turn) and audio, priced very
# differently. Sources:
#   https://ai.google.dev/gemini-api/docs/pricing
#   https://cloud.google.com/vertex-ai/generative-ai/pricing
_LIVE_PRICES_2_5 = {  # Gemini 2.5 Flash Live / native audio
    "input": {"TEXT": Decimal("0.50"), "AUDIO": Decimal("3.00")},
    "output": {"TEXT": Decimal("2.00"), "AUDIO": Decimal("12.00")},
}
_LIVE_PRICES_3 = {  # Gemini 3.x Flash Live
    "input": {"TEXT": Decimal("0.75"), "AUDIO": Decimal("3.00")},
    "output": {"TEXT": Decimal("4.50"), "AUDIO": Decimal("12.00")},
}

# Gemini 2.5 Flash text pricing (ConversationMonitor model).
_MONITOR_INPUT_PRICE_PER_M = Decimal("0.30")
_MONITOR_OUTPUT_PRICE_PER_M = Decimal("2.50")


def live_prices_for_model(model: str) -> dict[str, dict[str, Decimal]]:
    return _LIVE_PRICES_2_5 if "2.5" in model else _LIVE_PRICES_3


def _modality_key(modality: object) -> str:
    # Image/video share the audio price row; anything unknown is priced as
    # audio too, so the estimate errs high rather than low.
    name = str(getattr(modality, "value", modality) or "").upper()
    return "TEXT" if name == "TEXT" else "AUDIO"


def _split_by_modality(total: int, details: list | None) -> dict[str, int]:
    counts = {"TEXT": 0, "AUDIO": 0}
    for d in details or []:
        counts[_modality_key(d.modality)] += d.token_count or 0
    # Tokens the server didn't break down are priced as audio (upper bound).
    counts["AUDIO"] += max(total - sum(counts.values()), 0)
    return counts


def estimate_monitor_cost(prompt_tokens: int, completion_tokens: int) -> Decimal:
    """Estimate LLM cost based on Gemini 2.5 Flash pricing (monitor model)."""
    input_cost = Decimal(prompt_tokens) * _MONITOR_INPUT_PRICE_PER_M / _PER_M
    output_cost = Decimal(completion_tokens) * _MONITOR_OUTPUT_PRICE_PER_M / _PER_M
    return (input_cost + output_cost).quantize(Decimal("0.000001"))


class UsageAccumulator:
    """Accumulates Gemini Live token usage per modality for one voice session."""

    def __init__(self, model: str = ""):
        self.model = model
        self.input_tokens: dict[str, int] = {"TEXT": 0, "AUDIO": 0}
        self.output_tokens: dict[str, int] = {"TEXT": 0, "AUDIO": 0}

    @property
    def prompt_tokens(self) -> int:
        return sum(self.input_tokens.values())

    @property
    def completion_tokens(self) -> int:
        return sum(self.output_tokens.values())

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def cost(self) -> Decimal:
        prices = live_prices_for_model(self.model)
        total = sum(
            Decimal(self.input_tokens[k]) * prices["input"][k] + Decimal(self.output_tokens[k]) * prices["output"][k]
            for k in ("TEXT", "AUDIO")
        )
        return (total / _PER_M).quantize(Decimal("0.000001"))

    def add_usage_metadata(self, usage: object) -> None:
        """Add one turn's google.genai UsageMetadata (from a Live server message)."""
        inputs = _split_by_modality(usage.prompt_token_count or 0, usage.prompt_tokens_details)
        outputs = _split_by_modality(usage.response_token_count or 0, usage.response_tokens_details)
        for k in ("TEXT", "AUDIO"):
            self.input_tokens[k] += inputs[k]
            self.output_tokens[k] += outputs[k]
        logger.info(
            "LLM usage: +in %s +out %s (cumulative in %s out %s)",
            inputs, outputs, self.input_tokens, self.output_tokens,
        )
