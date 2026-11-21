import os
import sys
import pytest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from config import TestConfig
from app.models import db, Admin, TrackingLink, VisitorRecord

@pytest.fixture
def app():
    """Create test application instance with TestConfig."""
    from app.services.geolocation import _geo_cache
    _geo_cache.clear()

    app = create_app(TestConfig)
    
    with app.app_context():
        # Ensure fresh database tables for each test
        db.create_all()
        # Ensure test admin has the expected password
        admin = Admin.query.filter_by(username="admin").first()
        if not admin:
            admin = Admin(username="admin")
            db.session.add(admin)
        admin.set_password("AdminSecurePass123!")
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()
        _geo_cache.clear()


@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """Logged in admin client fixture."""
    with client.session_transaction() as sess:
        admin = Admin.query.filter_by(username="admin").first()
        sess["admin_id"] = admin.id
        sess["admin_username"] = admin.username
    return client


@pytest.fixture
def sample_link(app):
    """Sample active tracking link."""
    with app.app_context():
        link = TrackingLink(name="Test Campaign", token="test_token_123", is_active=True)
        db.session.add(link)
        db.session.commit()
        # Refresh to ensure id is loaded
        db.session.refresh(link)
        return link
