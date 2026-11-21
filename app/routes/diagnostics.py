import ipaddress
import json
from flask import Blueprint, render_template, request, jsonify
from app.utils.security import login_required
from app.models import db, VisitorRecord
from app.services.provider_comparator import compare_all_providers
from app.services.confidence import is_city_centre_fallback, evaluate_confidence

diagnostics_bp = Blueprint("diagnostics", __name__)

@diagnostics_bp.route("/admin/diagnostics", methods=["GET"])
@login_required
def diagnostics_page():
    """Admin diagnostic interface for side-by-side provider comparison."""
    # Retrieve recent unique consented visitor IPs for quick selection
    recent_records = VisitorRecord.query.order_by(
        VisitorRecord.consent_timestamp.desc()
    ).limit(30).all()

    recent_ips = []
    seen = set()
    for r in recent_records:
        if r.ip_address not in seen:
            seen.add(r.ip_address)
            loc_label = f"{r.city}, {r.country}" if r.city and r.country else r.country or "Unknown location"
            recent_ips.append({
                "ip": r.ip_address,
                "label": f"{r.ip_address} ({loc_label})",
                "record_id": r.id,
            })

    return render_template("diagnostics.html", active_page="diagnostics", recent_ips=recent_ips)


@diagnostics_bp.route("/api/diagnostics/compare", methods=["GET"])
@login_required
def compare_ip():
    """
    Run multi-provider geolocation diagnostic on an IP address.
    Protected endpoint accessible only by authenticated administrators.
    """
    ip = request.args.get("ip", "").strip()
    if not ip:
        return jsonify({"error": "IP address parameter is required."}), 400

    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return jsonify({"error": "Invalid IPv4 or IPv6 address format."}), 400

    # Execute multi-provider comparison
    comparison = compare_all_providers(ip)
    providers = comparison.get("providers", [])

    # Identify primary coordinates for centroid check
    primary = next((p for p in providers if p.get("success") and p.get("latitude") is not None), None)
    lat = primary.get("latitude") if primary else None
    lon = primary.get("longitude") if primary else None
    city = primary.get("city") if primary else None

    # Detect city-centre fallback
    is_centroid, centroid_reason = is_city_centre_fallback(
        lat=lat,
        lon=lon,
        city=city,
        db_session=db.session,
        current_ip=ip
    )

    # Evaluate confidence rating
    confidence_level, confidence_reasons = evaluate_confidence(
        providers_results=providers,
        is_city_centre=is_centroid,
        city_centre_reason=centroid_reason
    )

    disclaimer = "IP-based location is an estimate and does not represent the exact physical location of the visitor."

    return jsonify({
        "success": True,
        "ip_address": ip,
        "providers": providers,
        "total_providers_queried": comparison.get("total_providers_queried", 0),
        "successful_providers": comparison.get("successful_providers", 0),
        "max_variance_km": comparison.get("max_variance_km", 0.0),
        "pairwise_variances": comparison.get("pairwise_variances", []),
        "is_city_centre": is_centroid,
        "city_centre_reason": centroid_reason,
        "confidence": confidence_level,
        "confidence_reasons": confidence_reasons,
        "disclaimer": disclaimer,
    })


@diagnostics_bp.route("/api/diagnostics/records/<int:record_id>", methods=["GET"])
@login_required
def get_record_comparison(record_id: int):
    """Retrieve stored multi-provider comparison data for an existing visitor record."""
    record = db.get_or_404(VisitorRecord, record_id)
    stored_data = {}
    if record.provider_comparison:
        try:
            stored_data = json.loads(record.provider_comparison)
        except Exception:
            pass

    return jsonify({
        "record_id": record.id,
        "ip_address": record.ip_address,
        "stored_comparison": stored_data,
        "confidence": record.confidence,
        "is_city_centre": record.is_city_centre,
        "accuracy_radius": record.accuracy_radius,
        "disclaimer": "IP-based location is an estimate and does not represent the exact physical location of the visitor.",
    })
