import os
import secrets
import tempfile
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _determine_instance_dir() -> str:
    """
    Safely determine a writable instance directory for SQLite and runtime files.
    Serverless platforms (Vercel, AWS Lambda) mount the code as read-only (/var/task),
    leaving only /tmp writable.
    """
    # 1. Check known serverless environment indicators
    serverless_flags = (
        "VERCEL",
        "VERCEL_ENV",
        "AWS_LAMBDA_FUNCTION_NAME",
        "LAMBDA_TASK_ROOT",
        "NOW_REGION",
    )
    if any(os.getenv(flag) for flag in serverless_flags):
        return "/tmp"

    # 2. Check if the code path is inside an AWS Lambda / Vercel container
    if "/var/task" in BASE_DIR or "/var/runtime" in BASE_DIR:
        return "/tmp"

    # 3. Otherwise try creating local instance directory with graceful fallback
    target = os.path.join(BASE_DIR, "instance")
    try:
        os.makedirs(target, exist_ok=True)
        # Verify write permission
        test_file = os.path.join(target, ".write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return target
    except (OSError, PermissionError):
        # Fallback to system temp folder (/tmp on Linux/Vercel)
        return tempfile.gettempdir()


class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    
    # Safe writable directory for SQLite
    INSTANCE_DIR = _determine_instance_dir()
    default_db_path = os.path.join(INSTANCE_DIR, "iptrace.db")

    # Format SQLite URI properly for Linux/Unix (sqlite:////tmp/iptrace.db)
    if default_db_path.startswith("/"):
        _default_sqlite_uri = f"sqlite:////{default_db_path.lstrip('/')}"
    else:
        _default_sqlite_uri = f"sqlite:///{default_db_path}"

    # Handle postgres:// vs postgresql:// compatibility if external DB is configured
    _raw_db_url = os.getenv("DATABASE_URL")
    if _raw_db_url and _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = _raw_db_url or _default_sqlite_uri
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
