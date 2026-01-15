from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.schemas.common import Audience, PrincipalType


def test_password_hashing_roundtrip():
    pw = "correct horse battery staple"
    ph = hash_password(pw)
    assert verify_password(pw, ph)
    assert not verify_password("wrong", ph)


def test_access_token_roundtrip():
    token = create_access_token(subject="user-123", role=PrincipalType.user, audience=Audience.mobile, ttl_minutes=1)
    decoded = decode_access_token(token)
    assert decoded.subject == "user-123"
    assert decoded.role == PrincipalType.user
    assert decoded.audience == Audience.mobile


def test_refresh_token_hash_is_stable():
    rt = generate_refresh_token()
    h1 = hash_refresh_token(rt)
    h2 = hash_refresh_token(rt)
    assert h1 == h2
    assert len(h1) == 64
