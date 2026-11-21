from app.models import Admin

def test_admin_login_success(client):
    """Test successful admin login with valid credentials."""
    resp = client.post("/admin/login", data={
        "username": "admin",
        "password": "AdminSecurePass123!"
    }, follow_redirects=False)
    assert resp.status_code == 302
    assert "/admin" in resp.headers["Location"]

    # Verify session cookie was set
    with client.session_transaction() as sess:
        assert sess.get("admin_id") is not None
        assert sess.get("admin_username") == "admin"


def test_admin_login_invalid_password(client):
    """Test failed admin login with incorrect password."""
    resp = client.post("/admin/login", data={
        "username": "admin",
        "password": "WrongPassword!"
    })
    assert resp.status_code == 401
    assert b"Invalid username or password" in resp.data

    with client.session_transaction() as sess:
        assert sess.get("admin_id") is None


def test_admin_login_json(client):
    """Test JSON payload login."""
    resp = client.post("/admin/login", json={
        "username": "admin",
        "password": "AdminSecurePass123!"
    })
    assert resp.status_code == 200
    assert resp.json.get("success") is True


def test_admin_logout(auth_client):
    """Test admin logout clears session."""
    resp = auth_client.get("/admin/logout", follow_redirects=False)
    assert resp.status_code == 302

    with auth_client.session_transaction() as sess:
        assert sess.get("admin_id") is None


def test_unauthorized_dashboard_access(client):
    """Unauthenticated access to dashboard views redirects to login."""
    resp = client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/admin/login" in resp.headers["Location"]


def test_unauthorized_api_access(client):
    """Unauthenticated access to protected API endpoints returns 401."""
    resp = client.get("/api/links")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json.get("error", "")

    resp = client.get("/api/visitors")
    assert resp.status_code == 401

    resp = client.get("/api/analytics/overview")
    assert resp.status_code == 401
