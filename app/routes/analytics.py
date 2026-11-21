from flask import Blueprint, request, jsonify
from app.utils.security import login_required
from app.services.analytics import (
    get_overview_metrics,
    get_timeline,
    get_country_breakdown,
    get_browser_breakdown,
    get_os_breakdown,
    get_map_points
)

analytics_bp = Blueprint("analytics_api", __name__, url_prefix="/api/analytics")

@analytics_bp.route("/overview", methods=["GET"])
@login_required
def overview():
    """Retrieve top-level KPI metrics."""
    metrics = get_overview_metrics()
    return jsonify(metrics)


@analytics_bp.route("/timeline", methods=["GET"])
@login_required
def timeline():
    """Retrieve visitor events timeline for Chart.js."""
    days = request.args.get("days", 14, type=int)
    days = min(max(days, 3), 90)
    data = get_timeline(days=days)
    return jsonify(data)


@analytics_bp.route("/countries", methods=["GET"])
@login_required
def countries():
    """Retrieve country distribution breakdown."""
    limit = request.args.get("limit", 10, type=int)
    data = get_country_breakdown(limit=limit)
    return jsonify({"countries": data})


@analytics_bp.route("/map", methods=["GET"])
@login_required
def map_points():
    """Retrieve approximate coordinates for Leaflet map markers."""
    link_id = request.args.get("link_id", type=int)
    points = get_map_points(link_id=link_id)
    return jsonify({"points": points, "total": len(points)})


@analytics_bp.route("/browsers", methods=["GET"])
@login_required
def browsers():
    """Retrieve browser distribution breakdown."""
    data = get_browser_breakdown()
    return jsonify({"browsers": data})


@analytics_bp.route("/os", methods=["GET"])
@login_required
def operating_systems():
    """Retrieve operating system distribution breakdown."""
    data = get_os_breakdown()
    return jsonify({"os": data})
