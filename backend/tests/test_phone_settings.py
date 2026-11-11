import pytest

from app.core.phone import normalize_phone
from app.core.security import create_access_token, hash_password
from app.models.admin import Admin
from app.schemas.common import Audience, PrincipalType


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("+16232943370", "+16232943370"),
        ("(623) 294-3370", "+16232943370"),
        ("1 623 294 3370", "+16232943370"),
        ("+44 20 7946 0958", "+442079460958"),
    ],
)
def test_normalize_phone(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize("raw", ["294-3370", "abc", "+0123", "0623 294 3370 99"])
def test_normalize_phone_rejects_partial_numbers(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def _signup(store_client, email):
    r = store_client.post("/store/auth/signup", json={"email": email, "password": "password123", "name": "Kitchen"})
    assert r.status_code == 200, r.text
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    store_id = store_client.get("/store/me", headers=headers).json()["id"]
    return store_id, headers


@pytest.fixture()
def admin_auth(session_factory):
    with session_factory() as db:
        admin = Admin(email="admin@example.com", password_hash=hash_password("password123"))
        db.add(admin)
        db.commit()
        token = create_access_token(subject=str(admin.id), role=PrincipalType.admin, audience=Audience.admin)
    return {"Authorization": f"Bearer {token}"}


def _assign(admin_client, admin_auth, store_id, number):
    return admin_client.patch(f"/admin/stores/{store_id}", json={"phone_ai_number": number}, headers=admin_auth)


def test_store_cannot_enable_phone_ordering_without_a_number(store_client):
    _, headers = _signup(store_client, "a@example.com")

    r = store_client.patch("/store/me", json={"phone_ai_enabled": True}, headers=headers)

    assert r.status_code == 409 and r.json()["code"] == "phone_ai_number_missing"


def test_store_cannot_assign_its_own_ai_number(store_client):
    _, headers = _signup(store_client, "a@example.com")

    r = store_client.patch("/store/me", json={"phone_ai_number": "+16232943370"}, headers=headers)

    assert r.status_code == 200
    assert r.json()["phone_ai_number"] is None


def test_admin_assigns_number_and_store_turns_phone_ordering_on(store_client, admin_client, admin_auth):
    store_id, headers = _signup(store_client, "a@example.com")

    r = _assign(admin_client, admin_auth, store_id, "(623) 294-3370")
    assert r.status_code == 200, r.text
    assert r.json()["phone_ai_number"] == "+16232943370"

    r = store_client.patch(
        "/store/me", json={"phone_ai_enabled": True, "phone_staff_number": "480-555-0100"}, headers=headers
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["phone_ai_enabled"], body["phone_staff_number"]) == (True, "+14805550100")

    # Unassigning the number turns phone ordering off.
    r = _assign(admin_client, admin_auth, store_id, None)
    assert (r.json()["phone_ai_number"], r.json()["phone_ai_enabled"]) == (None, False)


def test_staff_number_must_differ_from_ai_number(store_client, admin_client, admin_auth):
    store_id, headers = _signup(store_client, "a@example.com")
    assert _assign(admin_client, admin_auth, store_id, "+16232943370").status_code == 200

    r = store_client.patch("/store/me", json={"phone_staff_number": "623-294-3370"}, headers=headers)

    assert r.status_code == 400 and r.json()["code"] == "phone_staff_number_invalid"


def test_ai_number_belongs_to_one_store(store_client, admin_client, admin_auth):
    first, _ = _signup(store_client, "a@example.com")
    second, _ = _signup(store_client, "b@example.com")
    assert _assign(admin_client, admin_auth, first, "+16232943370").status_code == 200

    r = _assign(admin_client, admin_auth, second, "623 294 3370")

    assert r.status_code == 409 and r.json()["code"] == "phone_number_taken"


def test_bad_number_is_rejected(store_client, admin_client, admin_auth):
    store_id, headers = _signup(store_client, "a@example.com")

    assert _assign(admin_client, admin_auth, store_id, "294-3370").status_code == 422
    assert store_client.patch("/store/me", json={"phone_staff_number": "12345"}, headers=headers).status_code == 422
