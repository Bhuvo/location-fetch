from app.models import TrackingLink, VisitorRecord, db

def test_create_tracking_link(auth_client, app):
    """Test generating a tracking link with random token."""
    resp = auth_client.post("/api/links", json={"name": "Social Media Launch"})
    assert resp.status_code == 201
    data = resp.json
    assert data["success"] is True
    assert data["link"]["name"] == "Social Media Launch"
    token = data["link"]["token"]
    assert len(token) >= 12
    assert f"/track/{token}" in data["link"]["tracking_url"]

    with app.app_context():
        link_db = TrackingLink.query.filter_by(token=token).first()
        assert link_db is not None
        assert link_db.is_active is True


def test_create_link_missing_name(auth_client):
    """Test creating a link without name fails with 400."""
    resp = auth_client.post("/api/links", json={"name": ""})
    assert resp.status_code == 400
    assert "Link name is required" in resp.json["error"]


def test_get_links_list(auth_client, sample_link):
    """Test retrieving list of tracking links."""
    resp = auth_client.get("/api/links")
    assert resp.status_code == 200
    links = resp.json["links"]
    assert len(links) >= 1
    assert any(l["token"] == sample_link.token for l in links)


def test_patch_link_status(auth_client, sample_link, app):
    """Test toggling link active status."""
    resp = auth_client.patch(f"/api/links/{sample_link.id}", json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json["link"]["is_active"] is False

    with app.app_context():
        link = db.session.get(TrackingLink, sample_link.id)
        assert link.is_active is False


def test_delete_link_and_cascade(auth_client, sample_link, app):
    """Test deleting tracking link cascades to visitor records."""
    with app.app_context():
        record = VisitorRecord(
            tracking_link_id=sample_link.id,
            ip_address="8.8.8.8",
            city="Mountain View",
            country="United States"
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    resp = auth_client.delete(f"/api/links/{sample_link.id}")
    assert resp.status_code == 200
    assert resp.json["success"] is True

    with app.app_context():
        assert db.session.get(TrackingLink, sample_link.id) is None
        assert db.session.get(VisitorRecord, record_id) is None
