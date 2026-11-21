from flask import Blueprint, render_template, redirect, url_for
from app.utils.security import login_required
from app.models import TrackingLink, VisitorRecord

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/admin")

@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def overview():
    """Admin Dashboard Overview view."""
    return render_template("dashboard.html", active_page="overview")

@dashboard_bp.route("/links")
@login_required
def links():
    """Tracking Links Management view."""
    return render_template("links.html", active_page="links")

@dashboard_bp.route("/visitors")
@login_required
def visitors():
    """Visitor Records Search & Filter view."""
    all_links = TrackingLink.query.order_by(TrackingLink.name.asc()).all()
    return render_template("visitors.html", active_page="visitors", links=all_links)

@dashboard_bp.route("/analytics")
@login_required
def analytics():
    """Location Analytics & Leaflet Map view."""
    all_links = TrackingLink.query.order_by(TrackingLink.name.asc()).all()
    return render_template("analytics.html", active_page="analytics", links=all_links)

@dashboard_bp.route("/settings")
@login_required
def settings():
    """System Settings & Data Retention view."""
    return render_template("settings.html", active_page="settings")
