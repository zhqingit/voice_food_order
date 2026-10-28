from decimal import Decimal

import pytest

from app.core.config import settings
from app.voice.usage import UsageAccumulator, estimate_cost, estimate_monitor_cost


@pytest.mark.parametrize(
    "use_vertex,expected",
    [
        # 0.5M text in $0.50 + 0.5M audio in $3.00 + 1M audio out $12.00
        (True, Decimal("13.750000")),
        # 0.5M text in $0.75 + 0.5M audio in $3.00 + 1M audio out $12.00
        (False, Decimal("13.875000")),
    ],
)
def test_live_cost_prices_audio_and_text_separately(monkeypatch, use_vertex, expected):
    monkeypatch.setattr(settings, "voice_use_vertex", use_vertex)
    assert estimate_cost(1_000_000, 1_000_000, input_audio_tokens=500_000, output_audio_tokens=1_000_000) == expected


def test_audio_count_above_total_is_clamped(monkeypatch):
    monkeypatch.setattr(settings, "voice_use_vertex", True)
    # Text remainder would be negative; it must count as zero, not a credit.
    assert estimate_cost(100, 0, input_audio_tokens=1_000_000) == Decimal("3.000000")


def test_accumulator_sums_turns(monkeypatch):
    monkeypatch.setattr(settings, "voice_use_vertex", True)
    usage = UsageAccumulator()
    usage.add_tokens(600_000, 400_000, input_audio=500_000, output_audio=400_000)
    usage.add_tokens(400_000, 600_000, input_audio=500_000, output_audio=600_000)

    assert (usage.prompt_tokens, usage.completion_tokens, usage.total_tokens) == (1_000_000, 1_000_000, 2_000_000)
    assert (usage.input_audio_tokens, usage.output_audio_tokens) == (1_000_000, 1_000_000)
    assert usage.cost == Decimal("15.000000")  # $3.00 audio in + $12.00 audio out


def test_monitor_uses_text_prices():
    assert estimate_monitor_cost(1_000_000, 1_000_000) == Decimal("2.800000")
