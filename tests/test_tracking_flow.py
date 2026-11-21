from unittest.mock import patch
from app.models import TrackingLink, VisitorRecord, db

@patch("app.routes.tracking.lookup_ip_geolocation")
def test_view_tracking_page_active(mock_geo, client, sample_link, app):
    """Test visiting active tracking URL immediately fetches IP and approximate location."""
    mock_geo.return_value = {
        "ip_address": "81.2.69.142",
        "country": "United Kingdom",
        "country_code": "GB",
        "region": "England",
        "city": "London",
        "postal_code": "SW1A",
        "latitude": 51.5014,
        "longitude": -0.1419,
        "timezone": "Europe/London",
        "isp": "Virgin Media",
        "organization": "Virgin Media",
        "asn": "AS5089",
        "provider": "ipinfo",
        "success": True,
    }

    resp = client.get(
        f"/track/{sample_link.token}",
        environ_base={"REMOTE_ADDR": "81.2.69.142"}
    )
    assert resp.status_code == 200
    assert b"Location Fetched Successfully" in resp.data
    assert b"81.2.69.142" in resp.data
    assert b"London" in resp.data

    with app.app_context():
        record = VisitorRecord.query.filter_by(ip_address="81.2.69.142").first()
        assert record is not None
        assert record.city == "London"


def test_view_tracking_page_not_found(client):
    """Test visiting non-existent token yields 404."""
    resp = client.get("/track/invalid_non_existent_token_123")
    assert resp.status_code == 404
    assert b"Tracking Link Not Found" in resp.data


def test_view_tracking_page_disabled(client, sample_link, app):
    """Test visiting deactivated tracking link yields 403."""
    with app.app_context():
        link = db.session.get(TrackingLink, sample_link.id)
        link.is_active = False
        db.session.commit()

    resp = client.get(f"/track/{sample_link.token}")
    assert resp.status_code == 403
    assert b"Tracking Link Inactive" in resp.data


@patch("app.routes.tracking.lookup_ip_geolocation")
def test_consent_flow_records_data(mock_geo, client, sample_link, app):
    """Test consenting records visitor IP and approximate location."""
    mock_geo.return_value = {
        "ip_address": "198.51.100.42",
        "country": "United Kingdom",
        "country_code": "GB",
        "region": "England",
        "city": "London",
        "postal_code": "EC1A",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "timezone": "Europe/London",
        "isp": "British Telecom",
        "organization": "BT Group",
        "asn": "AS2856",
        "provider": "ipinfo",
        "success": True
    }

    resp = client.post(
        f"/api/track/{sample_link.token}/consent",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        environ_base={"REMOTE_ADDR": "198.51.100.42"}
    )
    assert resp.status_code == 200
    assert resp.json["success"] is True
    assert resp.json["approximate_location"]["city"] == "London"
    assert resp.json["approximate_location"]["country"] == "United Kingdom"

    with app.app_context():
        record = VisitorRecord.query.filter_by(ip_address="198.51.100.42").first()
        assert record is not None
        assert record.city == "London"
        assert record.country == "United Kingdom"
        assert record.country_code == "GB"
        assert record.latitude == 51.5074
        assert record.longitude == -0.1278
        assert record.postal_code == "EC1A"
        assert record.isp == "British Telecom"
        assert "Windows" in record.operating_system


def test_decline_flow_does_not_store_data(client, sample_link, app):
    """Test declining does NOT save any record or IP."""
    initial_count = 0
    with app.app_context():
        initial_count = VisitorRecord.query.count()

    resp = client.post(
        f"/api/track/{sample_link.token}/decline",
        environ_base={"REMOTE_ADDR": "203.0.113.88"}
    )
    assert resp.status_code == 200
    assert resp.json["status"] == "declined"
    assert "No IP address or location information has been collected" in resp.json["message"]

    with app.app_context():
        final_count = VisitorRecord.query.count()
        assert final_count == initial_count
        assert VisitorRecord.query.filter_by(ip_address="203.0.113.88").first() is None
