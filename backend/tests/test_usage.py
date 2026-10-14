from decimal import Decimal

from google.genai.types import MediaModality, ModalityTokenCount, UsageMetadata

from app.voice.usage import UsageAccumulator, estimate_monitor_cost


def _meta(prompt, response, prompt_details=None, response_details=None):
    return UsageMetadata(
        prompt_token_count=prompt,
        response_token_count=response,
        prompt_tokens_details=prompt_details,
        response_tokens_details=response_details,
    )


def test_live_cost_is_priced_per_modality():
    usage = UsageAccumulator(model="google/gemini-live-2.5-flash-native-audio")
    usage.add_usage_metadata(
        _meta(
            1_500_000,
            1_000_000,
            prompt_details=[
                ModalityTokenCount(modality=MediaModality.TEXT, token_count=1_000_000),
                ModalityTokenCount(modality=MediaModality.AUDIO, token_count=500_000),
            ],
            response_details=[ModalityTokenCount(modality=MediaModality.AUDIO, token_count=1_000_000)],
        )
    )
    # 1M text in $0.50 + 0.5M audio in $1.50 + 1M audio out $12.00
    assert usage.cost == Decimal("14.000000")
    assert (usage.prompt_tokens, usage.completion_tokens) == (1_500_000, 1_000_000)


def test_missing_breakdown_is_priced_as_audio():
    usage = UsageAccumulator(model="gemini-3.1-flash-live-preview")
    usage.add_usage_metadata(_meta(1_000_000, 1_000_000))
    assert usage.cost == Decimal("15.000000")  # $3.00 audio in + $12.00 audio out


def test_monitor_uses_2_5_flash_prices():
    assert estimate_monitor_cost(1_000_000, 1_000_000) == Decimal("2.800000")
