from datetime import datetime, timedelta, timezone
from app.models import db, TrackingLink, VisitorRecord
from app.services.analytics import purge_retention

def _create_sample_records(app, link_id):
    """Helper to seed sample visitor records."""
    records = [
        VisitorRecord(
            tracking_link_id=link_id,
            ip_address="198.51.100.1",
            country="France",
            country_code="FR",
            region="Île-de-France",
            city="Paris",
            latitude=48.8566,
            longitude=2.3522,
            browser="Chrome 122",
            operating_system="Windows 11",
            consent_timestamp=datetime.now(timezone.utc) - timedelta(days=2)
        ),
        VisitorRecord(
            tracking_link_id=link_id,
            ip_address="198.51.100.2",
            country="Germany",
            country_code="DE",
            region="Berlin",
            city="Berlin",
            latitude=52.5200,
            longitude=13.4050,
            browser="Firefox 123",
            operating_system="Linux",
            consent_timestamp=datetime.now(timezone.utc) - timedelta(days=100) # Old record
        ),
    ]
    with app.app_context():
        for r in records:
            db.session.add(r)
        db.session.commit()


def test_get_visitors_and_filters(auth_client, sample_link, app):
    """Test searching and filtering visitor records."""
    _create_sample_records(app, sample_link.id)

    # 1. Fetch all
    resp = auth_client.get("/api/visitors")
    assert resp.status_code == 200
    assert resp.json["total"] == 2

    # 2. Filter by City
    resp_city = auth_client.get("/api/visitors?city=Paris")
    assert resp_city.status_code == 200
    assert resp_city.json["total"] == 1
    assert resp_city.json["records"][0]["city"] == "Paris"

    # 3. Filter by Country
    resp_country = auth_client.get("/api/visitors?country=Germany")
    assert resp_country.status_code == 200
    assert resp_country.json["total"] == 1
    assert resp_country.json["records"][0]["city"] == "Berlin"


def test_get_and_delete_visitor_record(auth_client, sample_link, app):
    """Test retrieving detail and deleting an individual record."""
    _create_sample_records(app, sample_link.id)

    record_id = None
    with app.app_context():
        rec = VisitorRecord.query.filter_by(city="Paris").first()
        record_id = rec.id

    # Get single
    resp = auth_client.get(f"/api/visitors/{record_id}")
    assert resp.status_code == 200
    assert resp.json["city"] == "Paris"

    # Delete single
    del_resp = auth_client.delete(f"/api/visitors/{record_id}")
    assert del_resp.status_code == 200
    assert del_resp.json["success"] is True

    with app.app_context():
        assert db.session.get(VisitorRecord, record_id) is None


def test_csv_export(auth_client, sample_link, app):
    """Test exporting visitor records to CSV."""
    _create_sample_records(app, sample_link.id)

    resp = auth_client.get("/api/visitors/export")
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert "attachment; filename=" in resp.headers["Content-Disposition"]
    
    csv_text = resp.data.decode("utf-8")
    assert "Public IP" in csv_text
    assert "Paris" in csv_text
    assert "198.51.100.1" in csv_text


def test_analytics_endpoints(auth_client, sample_link, app):
    """Test analytics overview, timeline, countries, and map points."""
    _create_sample_records(app, sample_link.id)

    # Overview
    resp_overview = auth_client.get("/api/analytics/overview")
    assert resp_overview.status_code == 200
    data = resp_overview.json
    assert data["total_tracking_links"] >= 1
    assert data["total_consent_events"] == 2
    assert data["unique_ip_addresses"] == 2
    assert data["countries_detected"] == 2
    assert data["cities_detected"] == 2

    # Map Points
    resp_map = auth_client.get("/api/analytics/map")
    assert resp_map.status_code == 200
    points = resp_map.json["points"]
    assert len(points) == 2
    assert any(p["city"] == "Paris" for p in points)


def test_retention_purge(auth_client, sample_link, app):
    """Test retention purge deletes records older than threshold."""
    _create_sample_records(app, sample_link.id)

    with app.app_context():
        assert VisitorRecord.query.count() == 2
        # Purge records older than 90 days (should purge the 100-day-old Berlin record)
        deleted = purge_retention(90)
        assert deleted == 1
        assert VisitorRecord.query.count() == 1
        # The 2-day-old Paris record must remain
        assert VisitorRecord.query.filter_by(city="Paris").first() is not None
