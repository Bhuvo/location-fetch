from app import create_app
from config import TestConfig
from app.models import db, TrackingLink

class RateLimitTestConfig(TestConfig):
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URI = "memory://"

def test_public_endpoint_rate_limiting():
    """Verify rate limiter blocks excessive requests returning 429."""
    app = create_app(RateLimitTestConfig)
    
    with app.app_context():
        link = TrackingLink(name="Rate Limit Test Link", token="rl_token_123", is_active=True)
        db.session.add(link)
        db.session.commit()

        client = app.test_client()

        # Decline endpoint has a limit of 30 per minute
        # We issue rapid requests until rate limited or up to 35
        got_429 = False
        for _ in range(35):
            resp = client.post(f"/api/track/rl_token_123/decline")
            if resp.status_code == 429:
                got_429 = True
                break

        assert got_429 is True
