import io
from pathlib import Path

import pytest
from PIL import Image

UPLOADS = Path(__file__).resolve().parent.parent / "uploads" / "logos"


@pytest.fixture()
def store_auth(store_client):
    r = store_client.post(
        "/store/auth/signup",
        json={"email": "owner@example.com", "password": "password123", "name": "Test Kitchen"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _png_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), "orange").save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.parametrize(
    "filename,content_type,body",
    [
        ("logo.svg", "image/svg+xml", b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
        ("logo.html", "image/png", b"<script>alert(1)</script>"),
        ("logo.png", "image/png", b"not really a png"),
    ],
)
def test_logo_upload_rejects_non_raster_files(store_client, store_auth, filename, content_type, body):
    r = store_client.post(
        "/store/me/logo", files={"file": (filename, body, content_type)}, headers=store_auth
    )
    assert r.status_code == 400, r.text
    assert r.json()["code"] == "invalid_file_type"


def test_logo_upload_names_file_from_decoded_format(store_client, store_auth):
    # Client claims .html; server decodes a PNG and stores it as .png.
    r = store_client.post(
        "/store/me/logo",
        files={"file": ("evil.html", _png_bytes(), "text/html")},
        headers=store_auth,
    )
    assert r.status_code == 200, r.text
    logo_url = r.json()["logo_url"]
    try:
        assert logo_url.endswith(".png")
        assert (UPLOADS / Path(logo_url).name).is_file()
    finally:
        (UPLOADS / Path(logo_url).name).unlink(missing_ok=True)
