from __future__ import annotations

import re

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")


def normalize_phone(value: str) -> str:
    """Normalize a phone number to E.164 (+14805551234), the form Twilio sends.

    Bare 10-digit numbers, and 11-digit ones starting with 1, are taken as US.
    """
    raw = (value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if not raw.startswith("+"):
        if len(digits) == 10:
            digits = "1" + digits
        elif not (len(digits) == 11 and digits.startswith("1")):
            raise ValueError("Enter a full phone number, e.g. +1 480 555 1234")
    number = "+" + digits
    if not _E164_RE.match(number):
        raise ValueError("Enter a full phone number, e.g. +1 480 555 1234")
    return number
