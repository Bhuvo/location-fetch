from flask import Blueprint, request, jsonify, current_app
from app.utils.security import login_required
from app.models import SystemSetting
from app.services.analytics import purge_retention

settings_bp = Blueprint("settings_api", __name__, url_prefix="/api/settings")

@settings_bp.route("", methods=["GET"])
@login_required
def get_settings():
    """Retrieve current system configuration and retention status."""
    default_retention = current_app.config.get("DATA_RETENTION_DAYS", 90)
    current_retention = SystemSetting.get_setting("data_retention_days", str(default_retention))

    return jsonify({
        "data_retention_days": int(current_retention),
        "use_proxy_headers": current_app.config.get("USE_PROXY_HEADERS", False),
        "trusted_proxies": current_app.config.get("TRUSTED_PROXIES", []),
        "fallback_provider": current_app.config.get("FALLBACK_GEO_PROVIDER", "ip-api"),
        "has_ipinfo_token": bool(current_app.config.get("IPINFO_API_TOKEN")),
        "dev_resolve_server_ip": current_app.config.get("DEV_RESOLVE_SERVER_PUBLIC_IP", False),
    })


@settings_bp.route("/retention", methods=["POST"])
@login_required
def update_retention():
    """Update data retention threshold in days."""
    data = request.get_json() or {}
    days = data.get("days")

    if days is None:
        return jsonify({"error": "Retention days field is required."}), 400

    try:
        days_int = int(days)
        if days_int < 0 or days_int > 3650:
            return jsonify({"error": "Retention days must be between 0 and 3650."}), 400
    except ValueError:
        return jsonify({"error": "Retention days must be a valid integer."}), 400

    SystemSetting.set_setting("data_retention_days", str(days_int))
    return jsonify({
        "success": True, 
        "data_retention_days": days_int,
        "message": f"Data retention policy updated to {days_int} days."
    })


@settings_bp.route("/purge", methods=["POST"])
@login_required
def trigger_purge():
    """Manually trigger data retention cleanup for expired records."""
    data = request.get_json() or {}
    days = data.get("days")

    if days is not None:
        try:
            retention_days = int(days)
        except ValueError:
            return jsonify({"error": "Invalid days parameter."}), 400
    else:
        default_retention = current_app.config.get("DATA_RETENTION_DAYS", 90)
        retention_days = int(SystemSetting.get_setting("data_retention_days", str(default_retention)))

    if retention_days <= 0:
        return jsonify({
            "success": True, 
            "deleted_count": 0, 
            "message": "Retention policy is set to keep data indefinitely (0 days). No records were purged."
        })

    deleted = purge_retention(retention_days)
    return jsonify({
        "success": True,
        "deleted_count": deleted,
        "message": f"Successfully purged {deleted} records older than {retention_days} days."
    })
