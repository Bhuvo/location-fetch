import os
import secrets
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    
    # SQLite Database
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(INSTANCE_DIR, 'iptrace.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "yes")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Initial Admin Credentials
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "AdminSecurePass123!")

    # Geolocation Settings
    IPINFO_API_TOKEN = os.getenv("IPINFO_API_TOKEN", "")
    IP_API_KEY = os.getenv("IP_API_KEY", "")
    MAXMIND_ACCOUNT_ID = os.getenv("MAXMIND_ACCOUNT_ID", "")
    MAXMIND_LICENSE_KEY = os.getenv("MAXMIND_LICENSE_KEY", "")
    FALLBACK_GEO_PROVIDER = os.getenv("FALLBACK_GEO_PROVIDER", "ip-api")  # ip-api, ipapi.co
    GEO_CACHE_TTL_SECONDS = int(os.getenv("GEO_CACHE_TTL_SECONDS", "3600"))

    # Trusted Proxy & Security Settings
    # If False, X-Forwarded-For is strictly ignored and request.remote_addr is used.
    USE_PROXY_HEADERS = os.getenv("USE_PROXY_HEADERS", "False").lower() in ("true", "1", "yes")
    # Comma-separated list of trusted proxy IPs, e.g. "127.0.0.1,10.0.0.1"
    TRUSTED_PROXIES = [
        ip.strip() 
        for ip in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") 
        if ip.strip()
    ]

    # Rate Limiting
    RATELIMIT_ENABLED = os.getenv("RATELIMIT_ENABLED", "True").lower() in ("true", "1", "yes")
    RATELIMIT_DEFAULT = "120 per hour"
    RATELIMIT_STORAGE_URI = "memory://"

    # Data Retention (in days, 0 = keep indefinitely)
    DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "90"))

    # Development helper: if True and client IP is private/loopback,
    # allows dev simulation / public IP detection for testing on localhost
    DEV_RESOLVE_SERVER_PUBLIC_IP = os.getenv("DEV_RESOLVE_SERVER_PUBLIC_IP", "False").lower() in ("true", "1", "yes")


class TestConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SECRET_KEY = "test-secret-key-for-testing-only"
    DEV_RESOLVE_SERVER_PUBLIC_IP = False
