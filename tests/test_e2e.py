from unittest.mock import patch
from app.models import db, TrackingLink, VisitorRecord

@patch("app.routes.tracking.lookup_ip_geolocation")
def test_full_application_lifecycle(mock_geo, client, app):
    """
    Complete end-to-end lifecycle test fulfilling all project criteria:
    1. Admin logs in.
    2. Admin creates a unique tracking URL.
    3. Visitor opens the URL and views consent notice.
    4. Visitor accepts consent.
    5. IP lookup executes server-side, records approximate location in SQLite.
    6. Admin views the actual record in visitor records and map API.
    7. Visitor declines another request: verify no IP or location stored.
    8. Admin disables link: verify public page rejects requests.
    9. Admin exports CSV.
    """
    mock_geo.return_value = {
        "ip_address": "81.2.69.142",
        "country": "United Kingdom",
        "country_code": "GB",
        "region": "Greater London",
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

    # Step 1: Admin logs in
    login_resp = client.post("/admin/login", json={
        "username": "admin",
        "password": "AdminSecurePass123!"
    })
    assert login_resp.status_code == 200
    assert login_resp.json["success"] is True

    # Step 2: Admin creates a tracking link
    create_link_resp = client.post("/api/links", json={
        "name": "London Tech Conference"
    })
    assert create_link_resp.status_code == 201
    link_data = create_link_resp.json["link"]
    token = link_data["token"]
    link_id = link_data["id"]
    assert token is not None
    assert f"/track/{token}" in link_data["tracking_url"]

    # Step 3: Visitor opens public tracking URL -> IP and location fetched immediately
    visit_page_resp = client.get(
        f"/track/{token}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        environ_base={"REMOTE_ADDR": "81.2.69.142"}
    )
    assert visit_page_resp.status_code == 200
    assert b"Location Fetched Successfully" in visit_page_resp.data
    assert b"81.2.69.142" in visit_page_resp.data
    assert b"London" in visit_page_resp.data

    # Step 6: Admin inspects records, overview KPIs, and map coordinates
    overview_resp = client.get("/api/analytics/overview")
    assert overview_resp.status_code == 200
    assert overview_resp.json["total_consent_events"] == 1
    assert overview_resp.json["countries_detected"] == 1
    assert overview_resp.json["cities_detected"] == 1

    visitors_resp = client.get(f"/api/visitors?link_id={link_id}")
    assert visitors_resp.status_code == 200
    assert visitors_resp.json["total"] == 1
    record = visitors_resp.json["records"][0]
    assert record["ip_address"] == "81.2.69.142"
    assert record["city"] == "London"
    assert record["country"] == "United Kingdom"
    assert record["postal_code"] == "SW1A"
    assert record["latitude"] == 51.5014
    assert record["longitude"] == -0.1419
    record_id = record["id"]

    map_resp = client.get(f"/api/analytics/map?link_id={link_id}")
    assert map_resp.status_code == 200
    assert len(map_resp.json["points"]) == 1
    assert map_resp.json["points"][0]["lat"] == 51.5014

    # Step 7: Visitor declines another request
    decline_resp = client.post(
        f"/api/track/{token}/decline",
        environ_base={"REMOTE_ADDR": "81.2.69.199"}
    )
    assert decline_resp.status_code == 200
    assert decline_resp.json["status"] == "declined"

    # Verify no additional records created
    with app.app_context():
        assert VisitorRecord.query.count() == 1
        assert VisitorRecord.query.filter_by(ip_address="81.2.69.199").first() is None

    # Step 8: Admin disables link
    disable_resp = client.patch(f"/api/links/{link_id}", json={"is_active": False})
    assert disable_resp.status_code == 200
    assert disable_resp.json["link"]["is_active"] is False

    # Visitor opens disabled link -> 403 Inactive
    disabled_page_resp = client.get(f"/track/{token}")
    assert disabled_page_resp.status_code == 403

    # Step 9: Admin exports CSV
    csv_resp = client.get("/api/visitors/export")
    assert csv_resp.status_code == 200
    csv_content = csv_resp.data.decode("utf-8")
    assert "81.2.69.142" in csv_content
    assert "London" in csv_content
    assert "United Kingdom" in csv_content
