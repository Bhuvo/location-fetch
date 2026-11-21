import secrets
from flask import Blueprint, request, jsonify, url_for
from app.models import db, TrackingLink
from app.utils.security import login_required

links_bp = Blueprint("links_api", __name__, url_prefix="/api/links")

@links_bp.route("", methods=["GET"])
@login_required
def get_links():
    """List all tracking links sorted by newest first."""
    links = TrackingLink.query.order_by(TrackingLink.created_at.desc()).all()
    results = []
    base_url = request.host_url.rstrip("/")
    for link in links:
        link_dict = link.to_dict()
        link_dict["tracking_url"] = f"{base_url}/track/{link.token}"
        results.append(link_dict)
    return jsonify({"links": results})


@links_bp.route("", methods=["POST"])
@login_required
def create_link():
    """Create a new tracking link with cryptographically random token."""
    data = request.get_json() or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Link name is required."}), 400

    if len(name) > 120:
        return jsonify({"error": "Link name must be 120 characters or fewer."}), 400

    # Generate a cryptographically random unique URL-safe token
    for _ in range(5):
        token = secrets.token_urlsafe(12)
        if not TrackingLink.query.filter_by(token=token).first():
            break
    else:
        return jsonify({"error": "Failed to generate unique token, please try again."}), 500

    new_link = TrackingLink(name=name, token=token, is_active=True)
    db.session.add(new_link)
    db.session.commit()

    base_url = request.host_url.rstrip("/")
    link_dict = new_link.to_dict()
    link_dict["tracking_url"] = f"{base_url}/track/{new_link.token}"

    return jsonify({"success": True, "link": link_dict}), 201


@links_bp.route("/<int:link_id>", methods=["GET"])
@login_required
def get_link(link_id: int):
    """Retrieve details for a single tracking link."""
    link = db.get_or_404(TrackingLink, link_id)
    base_url = request.host_url.rstrip("/")
    link_dict = link.to_dict()
    link_dict["tracking_url"] = f"{base_url}/track/{link.token}"
    return jsonify(link_dict)


@links_bp.route("/<int:link_id>", methods=["PATCH"])
@login_required
def update_link(link_id: int):
    """Update tracking link active state or name."""
    link = db.get_or_404(TrackingLink, link_id)
    data = request.get_json() or {}

    if "is_active" in data:
        link.is_active = bool(data["is_active"])

    if "name" in data:
        name = str(data["name"]).strip()
        if name:
            link.name = name[:120]

    db.session.commit()

    base_url = request.host_url.rstrip("/")
    link_dict = link.to_dict()
    link_dict["tracking_url"] = f"{base_url}/track/{link.token}"

    return jsonify({"success": True, "link": link_dict})


@links_bp.route("/<int:link_id>", methods=["DELETE"])
@login_required
def delete_link(link_id: int):
    """Delete tracking link and cascade delete associated records."""
    link = db.get_or_404(TrackingLink, link_id)
    db.session.delete(link)
    db.session.commit()
    return jsonify({"success": True, "message": f"Tracking link '{link.name}' deleted successfully."})
