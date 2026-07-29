# Delivery Range Check — Implementation Plan

Restrict delivery orders to addresses within a configurable radius of the store. Customer-supplied address (typed or selected) is geocoded server-side; distance is calculated locally; out-of-range orders are rejected.

**Scope decision:** customer GPS coordinates are NOT used as the delivery address. Addresses come from text input only — geocoded server-side.

## Current state

- `stores` has `address_line1/2`, `allow_delivery`, `allow_pickup`. No lat/lng, no delivery radius.
- `orders` has `fulfillment_type` (`pickup` | `delivery`) and `delivery_address` (free text).
- Voice flow has `set_fulfillment(type, delivery_address)` in `backend/app/voice/tool_router.py:501` — only checks the address is non-empty when delivery.
- User-portal (Flutter) presumably has an address field for non-voice delivery orders.

Gap: two free-text addresses (store + customer) need to become coordinates, get measured, and gated by a max distance.

## Design — three pieces

### 1. Store-side: capture location + radius (one-time per store)

Add to `stores` table:
- `latitude: Float | None`
- `longitude: Float | None`
- `delivery_radius_km: Float | None` (e.g. 5.0)

When the store manager saves their address in the store-portal Profile page:
- Geocode it server-side once (Google Geocoding API → lat/lng) and persist the coords.
- Add a **Delivery radius (km)** input next to the "Allow delivery" toggle.
- Re-geocode whenever address fields change. Keep prior coords if a re-geocode fails (don't wipe them).

### 2. Distance check helper

New module `backend/app/services/delivery_service.py`:

```python
def geocode_address(address: str) -> tuple[float, float] | None: ...
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float: ...
def is_within_delivery_range(store, customer_address: str) -> tuple[bool, float | None, str]: ...
    # returns (in_range, distance_km, reason_code)
```

**Haversine** = pure math, zero cost, runs locally. Straight-line distance.

**Geocoding** = Google Geocoding API (reuses existing `GOOGLE_API_KEY`). ~$5/1000 requests, covered by Google's $200/month free credit at expected volume.

**Caching**:
- In-memory LRU on the address string for the API process — fine for v1.
- Promote to a `geocode_cache` table if volume grows (key: normalized address, value: lat/lng + cached_at).

**Why haversine, not Google Distance Matrix:**
- Haversine is free and instant; Distance Matrix costs per call and adds latency.
- Haversine is straight-line, undercounts actual driving distance — compensate by setting radius slightly tighter than the desired drive radius (or storing the user's intended drive-distance and dividing by ~1.2 for a rough straight-line equivalent).
- If precise drive-time gating is needed later, swap the helper without changing call sites.

### 3. Enforcement — server is the source of truth, client gives early feedback

**Server-side (must enforce):**
- In `set_fulfillment` (voice tool router) and the analogous user-portal endpoint, after the customer provides `delivery_address`, call `is_within_delivery_range`. If out of range, return a structured failure (see voice contract below) — do NOT set the address.
- Also gate at order submit/checkout (`tool_router.checkout` path) as a final safeguard — addresses can be edited between selection and checkout.

**Client-side (UX hint):**
- User-portal: when the customer types/picks an address, call `POST /user/delivery/check-range` and show "Out of range — pickup only?" *before* they fill the cart.
- Same endpoint can be reused by the store-portal preview tools.

## Voice-flow contract

The `set_fulfillment` tool should return one of:

```json
{ "ok": true, "fulfillment_type": "delivery", "delivery_address": "...", "distance_km": 2.4 }
{ "ok": false, "reason": "out_of_range", "distance_km": 8.2, "max_km": 5.0,
  "message": "That address is about 8 km away — we only deliver within 5 km." }
{ "ok": false, "reason": "geocode_failed",
  "message": "I couldn't locate that address — could you say it again or include a postcode?" }
{ "ok": false, "reason": "store_no_location",
  "message": "Sorry, this store hasn't set up delivery yet." }
```

Update `backend/app/voice/tools.py` description for `set_fulfillment` so Gemini knows the address may be rejected and the bot must ask for an alternate address or offer pickup. Structured `reason` codes let the LLM phrase a natural response without us hardcoding strings.

## Edge cases & policy

| Case | Behavior |
|---|---|
| Store has no lat/lng set | Fail closed for delivery (`reason: "store_no_location"`). Silent acceptance would hide config bugs. |
| Store has no `delivery_radius_km` set | Same — fail closed. Manager must set a radius before delivery is allowed. |
| Geocoding returns no result | `reason: "geocode_failed"`, prompt customer to clarify (postcode, city). |
| Geocoding returns multiple matches | Take Google's first match (ranked by confidence). For user-portal we can surface alternatives in a dropdown later. |
| Geocoder is down / errors | Fail closed for new orders. Don't quietly let through. Log with a clear marker for monitoring. |
| Customer edits address after set_fulfillment | Re-run the check at checkout — `set_fulfillment` is not enough on its own. |
| `allow_delivery = false` on store | Existing behavior wins — never reach the range check. |

## Dependencies

- Google Geocoding API — same `GOOGLE_API_KEY` already used for voice services. No new credentials.
- No new Python packages (use `httpx`, already in the project).
- Alembic migration for 3 new columns + a one-time backfill script to geocode existing stores' addresses.

## Implementation steps (smallest useful slice first)

1. **Migration** — add `latitude`, `longitude`, `delivery_radius_km` to `stores`. Alembic autogenerate, no data loss.
2. **`delivery_service.py`** — `geocode_address`, `haversine_km`, `is_within_delivery_range`. Unit tests with mocked geocoder.
3. **Store-portal Profile** — add "Delivery radius (km)" input. On save, backend geocodes address and stores coords.
4. **Backfill** — small one-off script to geocode existing stores with addresses (`python -m app.scripts.backfill_store_coords` or similar).
5. **Voice integration** — wire range check into `set_fulfillment` and `checkout` in `tool_router.py`. Update tool description in `tools.py`.
6. **User-portal pre-check endpoint** — `POST /user/delivery/check-range` returning `{in_range, distance_km, max_km, reason}`. Wire into Flutter address screen.
7. **End-to-end test** — voice path with an out-of-range address, ensure bot offers pickup; user-portal path with same.

## Open questions

- **Units**: km or miles? Affects manager input UI and bot phrasing. Default: km.
- **Per-store vs global radius**: per-store is assumed (column on `stores`). Add an org-level default later only if needed.
- **User-portal address source**: typed free text, saved-address list, or Google Places autocomplete? Determines whether geocoding happens on type or on submit. Server-side geocoding works regardless.
- **Driving-distance upgrade path**: keep haversine indefinitely, or design to swap in Google Distance Matrix later? The helper signature already abstracts this — concrete need can drive the change.

## Out of scope (for this iteration)

- Customer GPS as authoritative delivery location (explicitly excluded).
- Multi-store / closest-store routing.
- Driving-time vs straight-line distance.
- Delivery fee calculation based on distance.
- Zone-shaped delivery areas (e.g. polygons, postcode lists).
