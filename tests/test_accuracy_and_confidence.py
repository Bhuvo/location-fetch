from unittest.mock import patch, MagicMock
from app.services.confidence import is_city_centre_fallback, evaluate_confidence, haversine_distance_km
from app.services.provider_comparator import compare_all_providers
from app.services.geolocation import lookup_ip_geolocation
from app.models import db, VisitorRecord

def test_missing_coordinates_returns_unknown_confidence():
    """When coordinates are missing from all providers, confidence is UNKNOWN."""
    empty_providers = [
        {"provider": "ipinfo", "success": False, "latitude": None, "longitude": None},
        {"provider": "ip-api", "success": False, "latitude": None, "longitude": None},
    ]
    conf, reasons = evaluate_confidence(empty_providers, is_city_centre=False)
    assert conf == "UNKNOWN"
    assert any("No coordinates returned" in r for r in reasons)


def test_generic_city_centre_coordinates_chennai_detected(app):
    """
    Test that coordinates matching known municipal centroids
    (e.g. Chennai 13.0878, 80.2785) are flagged as city-center fallbacks
    and assigned LOW confidence.
    """
    with app.app_context():
        # Chennai canonical centroid
        is_centroid, reason = is_city_centre_fallback(
            lat=13.0878, 
            lon=80.2785, 
            city="Chennai"
        )
        assert is_centroid is True
        assert "Chennai" in reason

        # Confidence evaluation must be LOW for generic centroids
        provider_results = [{
            "provider": "ipinfo",
            "success": True,
            "latitude": 13.0878,
            "longitude": 80.2785,
            "city": "Chennai",
            "country": "India"
        }]
        conf, reasons = evaluate_confidence(provider_results, is_city_centre=True, city_centre_reason=reason)
        assert conf == "LOW"
        assert any("Chennai" in r or "city-center" in r.lower() for r in reasons)


def test_database_shared_coordinates_flagged_as_city_centre(sample_link, app):
    """When multiple distinct IPs share identical coordinates, flag as repeated ISP centroid."""
    with app.app_context():
        # Seed an existing record with coordinates (45.5017, -73.5673)
        rec = VisitorRecord(
            tracking_link_id=sample_link.id,
            ip_address="198.51.100.10",
            latitude=45.5017,
            longitude=-73.5673,
            city="Montreal",
            country="Canada"
        )
        db.session.add(rec)
        db.session.commit()

        # Another IP tests the exact same coordinates
        is_centroid, reason = is_city_centre_fallback(
            lat=45.5017,
            lon=-73.5673,
            city="Montreal",
            db_session=db.session,
            current_ip="198.51.100.20"
        )
        assert is_centroid is True
        assert "distinct IP" in reason


def test_provider_disagreement_flagged_low_confidence():
    """
    When providers disagree significantly on coordinates/cities,
    mark as LOW confidence.
    """
    providers = [
        {
            "provider": "ipinfo",
            "success": True,
            "city": "London",
            "country": "United Kingdom",
            "latitude": 51.5074,
            "longitude": -0.1278
        },
        {
            "provider": "ip-api",
            "success": True,
            "city": "Manchester",
            "country": "United Kingdom",
            "latitude": 53.4808,
            "longitude": -2.2426
        }
    ]
    # Distance between London and Manchester is ~260 km
    conf, reasons = evaluate_confidence(providers, is_city_centre=False)
    assert conf == "LOW"
    assert any("disagree" in r.lower() or "variance" in r.lower() for r in reasons)


def test_provider_agreement_high_confidence():
    """
    When providers strongly agree on city and close coordinates with postal code,
    mark as HIGH confidence.
    """
    providers = [
        {
            "provider": "ipinfo",
            "success": True,
            "city": "Cambridge",
            "country": "United Kingdom",
            "postal_code": "CB2 1TN",
            "latitude": 52.2053,
            "longitude": 0.1218,
            "accuracy_radius": 15
        },
        {
            "provider": "ip-api",
            "success": True,
            "city": "Cambridge",
            "country": "United Kingdom",
            "postal_code": "CB2 1TN",
            "latitude": 52.2045,
            "longitude": 0.1205,
            "accuracy_radius": 20
        }
    ]
    conf, reasons = evaluate_confidence(providers, is_city_centre=False)
    assert conf == "HIGH"
    assert any("consensus" in r.lower() or "agree" in r.lower() for r in reasons)


@patch("app.services.provider_comparator.query_ipinfo_provider")
@patch("app.services.provider_comparator.query_ip_api_provider")
@patch("app.services.provider_comparator.query_maxmind_or_ipapi_provider")
def test_coordinates_never_averaged(mock_maxmind, mock_ipapi, mock_ipinfo, app):
    """
    CRITICAL RULE TEST: Never average coordinates from different providers.
    The primary coordinates stored in SQLite must exactly match one provider's
    actual coordinates, never a synthetic midpoint!
    """
    mock_ipinfo.return_value = {
        "provider": "ipinfo",
        "display_name": "IPinfo",
        "success": True,
        "latitude": 51.5000,
        "longitude": -0.1000,
        "city": "London",
        "country": "United Kingdom"
    }
    mock_ipapi.return_value = {
        "provider": "ip-api",
        "display_name": "ip-api",
        "success": True,
        "latitude": 51.5200,
        "longitude": -0.1400,
        "city": "London",
        "country": "United Kingdom"
    }
    mock_maxmind.return_value = {
        "provider": "maxmind",
        "display_name": "MaxMind GeoIP2",
        "success": False,
        "error": "Not configured"
    }

    with app.app_context():
        res = lookup_ip_geolocation("81.2.69.142")
        # Midpoint would have been 51.5100, -0.1200
        # The result MUST match primary provider (51.5000, -0.1000), NEVER the average!
        assert res["latitude"] == 51.5000
        assert res["longitude"] == -0.1000
        assert res["latitude"] != 51.5100
        assert res["longitude"] != -0.1200


@patch("app.services.provider_comparator.query_ipinfo_provider")
@patch("app.services.provider_comparator.query_ip_api_provider")
@patch("app.services.provider_comparator.query_maxmind_or_ipapi_provider")
def test_api_failure_handled_gracefully(mock_maxmind, mock_ipapi, mock_ipinfo, app):
    """
    When primary provider IPinfo fails, ip-api succeeds gracefully.
    When all providers fail, returns UNKNOWN confidence without crashing.
    """
    # IPinfo fails, ip-api succeeds
    mock_ipinfo.return_value = {"provider": "ipinfo", "success": False, "error": "HTTP 500"}
    mock_ipapi.return_value = {
        "provider": "ip-api",
        "display_name": "ip-api",
        "success": True,
        "latitude": 48.8566,
        "longitude": 2.3522,
        "city": "Paris",
        "country": "France"
    }
    mock_maxmind.return_value = {"provider": "maxmind", "success": False, "error": "Timeout"}

    with app.app_context():
        res = lookup_ip_geolocation("194.25.0.1")
        assert res["success"] is True
        assert res["provider"] == "ip-api"
        assert res["latitude"] == 48.8566

    # Total failure case
    mock_ipapi.return_value = {"provider": "ip-api", "success": False, "error": "Timeout"}
    with app.app_context():
        res_total = lookup_ip_geolocation("194.25.0.2")
        assert res_total["success"] is False
        assert res_total["confidence"] == "UNKNOWN"
        assert res_total["latitude"] is None


def test_diagnostics_unauthorized(client):
    """Unauthorized diagnostic request must be rejected."""
    resp = client.get("/api/diagnostics/compare?ip=8.8.8.8")
    assert resp.status_code == 401


def test_diagnostics_authorized_with_disclaimer(auth_client):
    """Authorized admin request succeeds and contains mandatory accuracy disclaimer."""
    resp = auth_client.get("/api/diagnostics/compare?ip=8.8.8.8")
    assert resp.status_code == 200
    data = resp.json
    assert data["success"] is True
    assert data["ip_address"] == "8.8.8.8"
    assert "providers" in data
    assert "confidence" in data
    assert data["disclaimer"] == "IP-based location is an estimate and does not represent the exact physical location of the visitor."
