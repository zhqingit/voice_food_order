import pytest
from pydantic import ValidationError

from app.core.config import Settings

_GOOD = "s" * 40


def _settings(**overrides):
    values = {"jwt_secret": _GOOD, "refresh_token_pepper": _GOOD, **overrides}
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("field", ["jwt_secret", "refresh_token_pepper"])
@pytest.mark.parametrize("value", ["change-me", "change-me-too", "short-but-not-placeholder"])
def test_weak_secrets_are_rejected(field, value):
    with pytest.raises(ValidationError):
        _settings(**{field: value})


def test_wildcard_cors_is_rejected():
    with pytest.raises(ValidationError):
        _settings(cors_origins="https://voxeats.rest-oai.com, *")


def test_explicit_cors_origins_are_parsed():
    s = _settings(cors_origins="https://a.example, https://b.example ,")
    assert s.cors_origin_list == ["https://a.example", "https://b.example"]
    assert _settings().cors_origin_list == []
