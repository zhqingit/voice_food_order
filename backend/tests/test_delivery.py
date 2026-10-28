import pytest

from app.models.store import Store
from app.services import delivery_service
from app.services.delivery_service import _GeocodeHit, _is_precise
from app.voice.tool_router import _spell_out

# Store in Chandler, AZ with a 10-mile radius.
STORE = Store(
    name="Test Kitchen", city="Chandler", state="Arizona", country="US",
    latitude=33.3049657, longitude=-111.8418054, delivery_radius_km=10 * delivery_service.KM_PER_MILE,
)

# Shaped after real Google responses for these inputs.
FAKE_GEOCODER = {
    # Bare street with no city → country centroid.
    "5777 east mayo boulevard": _GeocodeHit(38.79, -106.53, "United States", False),
    # Store city appended → a different street that happens to be nearby.
    "5777 east mayo boulevard, chandler, arizona": _GeocodeHit(33.2108, -111.8436, "5777 East Dr, Sun Lakes, AZ 85248, USA", False),
    # Street matched, house number not → centre of the road.
    "577 east mayo boulevard, phoenix": _GeocodeHit(33.667, -111.968, "E Mayo Blvd, Phoenix, AZ, USA", False),
    "5777 e mayo blvd, phoenix, az 85054": _GeocodeHit(33.6585, -111.9548, "5777 E Mayo Blvd, Phoenix, AZ 85054, USA", True),
    "540 n mamas way, chandler, az": _GeocodeHit(33.3123, -111.7982, "540 N Mammoth Way, Chandler, AZ 85225, USA", True),
}


@pytest.fixture(autouse=True)
def fake_geocoder(monkeypatch):
    monkeypatch.setattr(delivery_service, "_geocode_cached", lambda address, *args: FAKE_GEOCODER.get(address))


@pytest.mark.parametrize(
    "result,precise",
    [
        ({"geometry": {"location_type": "ROOFTOP"}, "types": ["premise", "street_address"]}, True),
        ({"geometry": {"location_type": "RANGE_INTERPOLATED"}, "types": ["street_address"]}, True),
        ({"geometry": {"location_type": "RANGE_INTERPOLATED"}, "types": ["street_address"], "partial_match": True}, False),
        ({"geometry": {"location_type": "GEOMETRIC_CENTER"}, "types": ["route"]}, False),
        ({"geometry": {"location_type": "APPROXIMATE"}, "types": ["country", "political"]}, False),
    ],
)
def test_only_full_street_address_matches_are_precise(result, precise):
    assert _is_precise(result) is precise


@pytest.mark.parametrize(
    "address", ["5777 East Mayo Boulevard", "577 East Mayo Boulevard, Phoenix", "unknown place"]
)
def test_vague_or_partial_matches_are_rejected(address):
    check = delivery_service.is_within_delivery_range(STORE, address)
    assert (check.in_range, check.reason) == (False, delivery_service.REASON_GEOCODE_FAILED)


def test_precise_address_outside_radius_is_out_of_range():
    check = delivery_service.is_within_delivery_range(STORE, "5777 E Mayo Blvd, Phoenix, AZ 85054")
    assert check.reason == delivery_service.REASON_OUT_OF_RANGE
    assert delivery_service.km_to_miles(check.distance_km) > 20


def test_in_range_returns_googles_spelling():
    check = delivery_service.is_within_delivery_range(STORE, "540 N Mamas Way, Chandler, AZ")
    assert check.in_range
    assert check.formatted_address == "540 N Mammoth Way, Chandler, AZ 85225"


@pytest.mark.parametrize(
    "text,spoken",
    [
        ("540 N Mammoth Way, Chandler, AZ 85225", "540 North M, A, M, M, O, T, H Way, Chandler"),
        ("12 W 5th St, Tempe, AZ", "12 West 5th Street, Tempe"),
        ("140 N Arizona Ave #104, Chandler", "140 North A, R, I, Z, O, N, A Avenue #104, Chandler"),
        ("Alan", "A, L, A, N"),
    ],
)
def test_read_back_spells_names_letter_by_letter(text, spoken):
    assert _spell_out(text) == spoken
