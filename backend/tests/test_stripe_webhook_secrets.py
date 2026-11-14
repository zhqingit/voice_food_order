import hashlib
import hmac
import json
import time

import pytest

from app.core.config import settings
from app.core.errors import AppError
from app.services import payment_service

PLATFORM_SECRET = "whsec_platform"
CONNECT_SECRET = "whsec_connect"


def _signed(secret: str) -> tuple[bytes, str]:
    payload = json.dumps({"id": "evt_1", "object": "event", "type": "account.updated", "data": {"object": {}}}).encode()
    ts = int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return payload, f"t={ts},v1={sig}"


@pytest.fixture(autouse=True)
def two_secrets(monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", f"{PLATFORM_SECRET}, {CONNECT_SECRET}")


@pytest.mark.parametrize("secret", [PLATFORM_SECRET, CONNECT_SECRET])
def test_either_endpoint_secret_is_accepted(secret):
    event = payment_service.verify_webhook(*_signed(secret))

    assert event["type"] == "account.updated"


def test_unknown_secret_is_rejected():
    with pytest.raises(AppError) as exc:
        payment_service.verify_webhook(*_signed("whsec_other"))

    assert exc.value.code == "invalid_webhook"
