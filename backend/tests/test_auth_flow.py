def _auth_header(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


def test_signup_me_refresh_reuse_and_logout_current(user_client):
    # signup
    r = user_client.post("/user/auth/signup", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    data = r.json()

    access1 = data["access_token"]
    refresh1 = data["refresh_token"]
    session_id = data["session_id"]

    # me
    r = user_client.get("/user/me", headers=_auth_header(access1))
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "a@example.com"

    # refresh -> rotate
    r = user_client.post("/user/auth/refresh", json={"session_id": session_id, "refresh_token": refresh1})
    assert r.status_code == 200, r.text
    data2 = r.json()
    refresh2 = data2["refresh_token"]
    assert refresh2 != refresh1

    # reuse old refresh token should revoke session
    r = user_client.post("/user/auth/refresh", json={"session_id": session_id, "refresh_token": refresh1})
    assert r.status_code == 401
    body = r.json()
    assert body["code"] in {"refresh_reuse", "invalid_refresh"}

    # new refresh token should now also fail due to session revoked
    r = user_client.post("/user/auth/refresh", json={"session_id": session_id, "refresh_token": refresh2})
    assert r.status_code == 401

    # logout current (idempotent)
    r = user_client.post(
        "/user/auth/logout",
        json={"scope": "current", "session_id": session_id},
        headers=_auth_header(access1),
    )
    assert r.status_code == 200


def test_logout_all_revokes_all_sessions(user_client):
    # signup creates session A
    r = user_client.post("/user/auth/signup", json={"email": "b@example.com", "password": "password123"})
    assert r.status_code == 200
    a = r.json()

    # login creates session B
    r = user_client.post("/user/auth/login", json={"email": "b@example.com", "password": "password123"})
    assert r.status_code == 200
    b = r.json()

    access = b["access_token"]

    # logout all
    r = user_client.post("/user/auth/logout", json={"scope": "all"}, headers=_auth_header(access))
    assert r.status_code == 200

    # both refresh should fail
    r = user_client.post(
        "/user/auth/refresh",
        json={"session_id": a["session_id"], "refresh_token": a["refresh_token"]},
    )
    assert r.status_code == 401

    r = user_client.post(
        "/user/auth/refresh",
        json={"session_id": b["session_id"], "refresh_token": b["refresh_token"]},
    )
    assert r.status_code == 401
