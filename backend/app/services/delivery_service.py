"""Delivery-range helpers: geocoding + haversine + range check.

Used by the voice tool router and the user-portal pre-check endpoint to
decide whether a customer's delivery address falls inside a store's
configured delivery radius.

Distance is straight-line (haversine). Geocoding is delegated to the Google
Geocoding API and cached in-process. The same `GOOGLE_API_KEY` /
`GEMINI_API_KEY` that drives the voice pipeline powers geocoding too.
"""
from __future__ import annotations

import json
import logging
import math
import os
import threading
from functools import lru_cache
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.models.store import Store

log = logging.getLogger(__name__)


# ── Reason codes returned to callers ─────────────────────────────────────
# Stable strings — voice flow / frontend may switch on them.
REASON_OK = "ok"
REASON_OUT_OF_RANGE = "out_of_range"
REASON_GEOCODE_FAILED = "geocode_failed"
REASON_STORE_NO_LOCATION = "store_no_location"
REASON_STORE_NO_RADIUS = "store_no_radius"
REASON_EMPTY_ADDRESS = "empty_address"


_GEOCODE_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"
_HTTP_TIMEOUT_SECONDS = 10.0

# Default bias radius around the store when geocoding a customer address.
# Soft bias only — Google can still return matches outside the box if no good
# in-box hit exists.
_DEFAULT_BIAS_KM = 20.0


def _api_key() -> str:
    return (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()


# Common long-form country names → ISO 3166-1 alpha-2. Free-form column means
# we have to map. Unknown values fall through to None and the country filter is
# silently skipped (coord bias is the stronger signal anyway).
_COUNTRY_NAME_TO_ISO2 = {
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "america": "US",
    "canada": "CA",
    "mexico": "MX",
    "united kingdom": "GB",
    "uk": "GB",
    "great britain": "GB",
    "china": "CN",
    "australia": "AU",
}


def _normalize_country_code(value: str | None) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    if len(v) == 2 and v.isalpha():
        return v.upper()
    return _COUNTRY_NAME_TO_ISO2.get(v.lower())


def _compute_bbox(
    lat: float, lng: float, km: float = _DEFAULT_BIAS_KM
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return ((sw_lat, sw_lng), (ne_lat, ne_lng)) for a square bbox around (lat, lng).

    1 degree latitude ≈ 111 km; longitude scales by cos(lat). We clamp the
    latitude factor to avoid a degenerate box near the poles (no real store
    will hit this, but keeps the math safe)."""
    lat_delta = km / 111.0
    cos_lat = math.cos(math.radians(max(-85.0, min(85.0, lat))))
    lng_delta = km / (111.0 * max(cos_lat, 0.01))
    return ((lat - lat_delta, lng - lng_delta), (lat + lat_delta, lng + lng_delta))


# ── Haversine ────────────────────────────────────────────────────────────

_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two (lat, lng) points in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


# ── Geocoding ────────────────────────────────────────────────────────────

_geocode_lock = threading.Lock()


def _normalize_address(address: str) -> str:
    return " ".join((address or "").split()).lower()


@lru_cache(maxsize=2048)
def _geocode_cached(
    normalized_address: str,
    near_lat_rounded: float | None,
    near_lng_rounded: float | None,
    country_code: str | None,
    api_key_marker: str,
) -> tuple[float, float] | None:
    """Internal cached call. `api_key_marker` is included so a key rotation
    invalidates the cache; the actual key is read fresh from env inside."""
    del api_key_marker  # only used to key the cache
    key = _api_key()
    if not key:
        log.warning("delivery_service.geocode: no GOOGLE_API_KEY/GEMINI_API_KEY configured")
        return None
    if not normalized_address:
        return None

    params: dict[str, str] = {"address": normalized_address, "key": key}
    if near_lat_rounded is not None and near_lng_rounded is not None:
        (sw_lat, sw_lng), (ne_lat, ne_lng) = _compute_bbox(near_lat_rounded, near_lng_rounded)
        params["bounds"] = f"{sw_lat},{sw_lng}|{ne_lat},{ne_lng}"
    if country_code:
        params["components"] = f"country:{country_code}"

    url = f"{_GEOCODE_ENDPOINT}?{urlencode(params)}"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
        data = json.loads(raw)
    except (URLError, ValueError, TimeoutError) as exc:
        log.warning("delivery_service.geocode HTTP error: %s", exc)
        return None

    status = data.get("status")
    if status != "OK":
        # ZERO_RESULTS is expected for bad addresses; other statuses are unusual.
        if status not in ("ZERO_RESULTS",):
            log.warning("delivery_service.geocode status=%s error=%s", status, data.get("error_message"))
        return None

    results = data.get("results") or []
    if not results:
        return None
    loc = (results[0].get("geometry") or {}).get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    if lat is None or lng is None:
        return None
    return (float(lat), float(lng))


def geocode_address(
    address: str,
    *,
    near_lat: float | None = None,
    near_lng: float | None = None,
    country: str | None = None,
) -> tuple[float, float] | None:
    """Convert a free-text address to (lat, lng), or None if it can't be resolved.

    Optional bias args make the resolver prefer matches near the store and in
    the store's country. If a biased lookup finds nothing, we fall back to one
    unbiased call so customers ordering across a regional boundary (or stores
    with miscategorized country values) still resolve.

    Results are cached in-process; cache key includes bias params.
    """
    normalized = _normalize_address(address)
    if not normalized:
        return None
    # Use a short api-key fingerprint so the cache invalidates on key rotation
    # without leaking the full key into the cache key (it's still local memory,
    # but principle of least exposure).
    key = _api_key()
    marker = (key[-4:] if key else "")
    # Round bias coords so trivially-different lat/lngs share cache slots
    # (~110 m at the equator at 3 decimals).
    lat_round = round(near_lat, 3) if near_lat is not None else None
    lng_round = round(near_lng, 3) if near_lng is not None else None
    country_code = _normalize_country_code(country)

    with _geocode_lock:
        result = _geocode_cached(normalized, lat_round, lng_round, country_code, marker)
        if result is None and (lat_round is not None or country_code is not None):
            # Safety net: bias is soft, but if Google returned nothing inside our
            # filter we retry without it before giving up.
            result = _geocode_cached(normalized, None, None, None, marker)
        return result


# ── Range check ──────────────────────────────────────────────────────────


def _maybe_complete_with_locality(addr: str, store: Store) -> str | None:
    """If the customer's address looks like it omits city/state, return a
    completed version with the store's locality appended. Returns None when
    no completion is safe or useful.

    Customers calling a local store routinely say "123 Main St" with no city.
    Without context, Google's geocoder can resolve that to a far-away Main St.
    """
    addr_l = addr.lower()
    # If the customer's address contains a comma, they're following the
    # `street, city, state` convention and have already specified a locality
    # (even if it's a neighboring town). Don't second-guess them.
    if "," in addr:
        return None
    # Belt-and-suspenders: if the customer named the store's city or state
    # without a comma, still trust them.
    if store.city and store.city.strip().lower() in addr_l:
        return None
    if store.state and store.state.strip().lower() in addr_l:
        return None

    parts: list[str] = [addr.strip()]
    if store.city and store.city.strip():
        parts.append(store.city.strip())
    if store.state and store.state.strip():
        parts.append(store.state.strip())
    if len(parts) == 1:
        return None
    return ", ".join(parts)


def is_within_delivery_range(
    store: Store, customer_address: str
) -> tuple[bool, float | None, str]:
    """Check whether `customer_address` is within `store.delivery_radius_km`.

    Returns (in_range, distance_km, reason_code). On any policy or lookup
    failure, in_range is False and reason_code explains why.

    If the customer's address omits the city/state, this falls back to
    re-geocoding with the store's locality appended and keeps whichever
    attempt resolves closer to the store.
    """
    addr = (customer_address or "").strip()
    if not addr:
        return (False, None, REASON_EMPTY_ADDRESS)

    if store.latitude is None or store.longitude is None:
        return (False, None, REASON_STORE_NO_LOCATION)

    radius = store.delivery_radius_km
    if radius is None or radius <= 0:
        return (False, None, REASON_STORE_NO_RADIUS)

    coords = geocode_address(
        addr,
        near_lat=store.latitude,
        near_lng=store.longitude,
        country=store.country,
    )
    distance: float | None = None
    if coords is not None:
        distance = haversine_km(store.latitude, store.longitude, coords[0], coords[1])

    # If we have no result, or the result is outside the radius, try once more
    # with the store's city/state appended (when the customer didn't already
    # name them). This catches the "123 Main St" case where the customer
    # implicitly means the local Main St.
    if coords is None or (distance is not None and distance > float(radius)):
        completed = _maybe_complete_with_locality(addr, store)
        if completed is not None:
            coords2 = geocode_address(
                completed,
                near_lat=store.latitude,
                near_lng=store.longitude,
                country=store.country,
            )
            if coords2 is not None:
                distance2 = haversine_km(
                    store.latitude, store.longitude, coords2[0], coords2[1]
                )
                if distance is None or distance2 < distance:
                    coords = coords2
                    distance = distance2

    if coords is None or distance is None:
        return (False, None, REASON_GEOCODE_FAILED)

    in_range = distance <= float(radius)
    return (in_range, distance, REASON_OK if in_range else REASON_OUT_OF_RANGE)
