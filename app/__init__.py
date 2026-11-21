import os
from datetime import datetime, timezone
from flask import Flask, redirect, url_for, session
from sqlalchemy import event
from sqlalchemy.engine import Engine
from config import Config
from app.extensions import db, csrf, limiter
from app.models import Admin

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable SQLite foreign key support."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception:
        pass

def create_app(config_class=Config):
    """Application factory for IPTrace."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.tracking import tracking_bp
    from app.routes.links import links_bp
    from app.routes.visitors import visitors_bp
    from app.routes.analytics import analytics_bp
    from app.routes.settings import settings_bp
    from app.routes.diagnostics import diagnostics_bp

    # Exempt public visitor tracking endpoints from CSRF
    csrf.exempt(tracking_bp)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(tracking_bp)
    app.register_blueprint(links_bp)
    app.register_blueprint(visitors_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(diagnostics_bp)

    # Root route redirects to dashboard
    @app.route("/")
    def index():
        if session.get("admin_id"):
            return redirect(url_for("dashboard.overview"))
        return redirect(url_for("auth.login"))

    # Context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.now(timezone.utc).year,
            "admin_username": session.get("admin_username"),
        }

    # Reverse proxy support in serverless / cloud deployments
    if any(os.getenv(k) for k in ("VERCEL", "VERCEL_ENV", "AWS_LAMBDA_FUNCTION_NAME")):
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
            app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
        except Exception:
            pass

    # Ensure database is safely initialized on startup
    with app.app_context():
        try:
            db.create_all()
            _migrate_database(app)
            _seed_initial_admin(app)
        except Exception as e:
            app.logger.warning(f"Initial DB bootstrap warning: {e}")

    # Ensure tables exist on cold-start worker invocations
    @app.before_request
    def ensure_database_ready():
        if not getattr(app, "_db_initialized", False):
            try:
                db.create_all()
                _migrate_database(app)
                _seed_initial_admin(app)
                app._db_initialized = True
            except Exception as e:
                app.logger.warning(f"On-demand DB check warning: {e}")

    return app


def _migrate_database(app):
    """Ensure new columns exist in existing SQLite databases."""
    from sqlalchemy import text
    try:
        with db.engine.connect() as conn:
            res = conn.execute(text("PRAGMA table_info(visitor_records)")).fetchall()
            existing_cols = [r[1] for r in res]
            if existing_cols:
                if "accuracy_radius" not in existing_cols:
                    conn.execute(text("ALTER TABLE visitor_records ADD COLUMN accuracy_radius FLOAT"))
                if "confidence" not in existing_cols:
                    conn.execute(text("ALTER TABLE visitor_records ADD COLUMN confidence VARCHAR(20) DEFAULT 'UNKNOWN'"))
                if "is_city_centre" not in existing_cols:
                    conn.execute(text("ALTER TABLE visitor_records ADD COLUMN is_city_centre BOOLEAN DEFAULT 0"))
                if "provider" not in existing_cols:
                    conn.execute(text("ALTER TABLE visitor_records ADD COLUMN provider VARCHAR(50)"))
                if "provider_comparison" not in existing_cols:
                    conn.execute(text("ALTER TABLE visitor_records ADD COLUMN provider_comparison TEXT"))
                conn.commit()
    except Exception as e:
        app.logger.warning(f"Database column check: {e}")


def _seed_initial_admin(app):
    """Ensure at least one administrator account exists in the database."""
    try:
        if not Admin.query.first():
            default_username = app.config.get("ADMIN_USERNAME", "admin")
            default_password = app.config.get("ADMIN_PASSWORD", "AdminSecurePass123!")
            
            admin = Admin(username=default_username)
            admin.set_password(default_password)
            db.session.add(admin)
            db.session.commit()
            app.logger.info(f"Initialized default administrator account: '{default_username}'")
    except Exception as e:
        app.logger.error(f"Error seeding initial admin: {e}")
