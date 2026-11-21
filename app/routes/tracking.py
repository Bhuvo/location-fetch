import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, request, jsonify, abort
from app.models import db, TrackingLink, VisitorRecord
from app.services.ip_resolver import get_client_ip, parse_user_agent
from app.services.geolocation import lookup_ip_geolocation
from app.extensions import limiter

logger = logging.getLogger(__name__)

tracking_bp = Blueprint("tracking", __name__)

@tracking_bp.route("/track/<token>", methods=["GET"])
def view_tracking_page(token: str):
    """
    Public tracking endpoint.
    Immediately identifies visitor IP and retrieves approximate location upon URL hit.
    """
    clean_token = token.strip()
    link = TrackingLink.query.filter_by(token=clean_token).first()
    if not link:
        return render_template(
            "tracking.html", 
            error_title="Tracking Link Not Found",
            error_message="The tracking link you followed does not exist or has been removed."
        ), 404

    if not link.is_active:
        return render_template(
            "tracking.html",
            error_title="Tracking Link Inactive",
            error_message="This analytics tracking link is currently deactivated by the administrator."
        ), 403

    # Immediately resolve visitor IP and user agent upon hitting the URL
    client_ip = get_client_ip(request)
    ua_header = request.headers.get("User-Agent", "")
    browser, operating_system = parse_user_agent(ua_header)

    # Check for recent duplicate from same IP on same link within 1 minute
    recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=1)
    recent_duplicate = VisitorRecord.query.filter(
        VisitorRecord.tracking_link_id == link.id,
        VisitorRecord.ip_address == client_ip,
        VisitorRecord.consent_timestamp >= recent_cutoff
    ).first()

    if recent_duplicate:
        record = recent_duplicate
        is_new = False
    else:
        # Perform geolocation lookup immediately
        geo_data = lookup_ip_geolocation(client_ip)
        now = datetime.now(timezone.utc)

        record = VisitorRecord(
            tracking_link_id=link.id,
            ip_address=client_ip,
            country=geo_data.get("country"),
            country_code=geo_data.get("country_code"),
            region=geo_data.get("region"),
            city=geo_data.get("city"),
            postal_code=geo_data.get("postal_code"),
            latitude=geo_data.get("latitude"),
            longitude=geo_data.get("longitude"),
            timezone=geo_data.get("timezone"),
            isp=geo_data.get("isp"),
            organization=geo_data.get("organization"),
            asn=geo_data.get("asn"),
            accuracy_radius=geo_data.get("accuracy_radius"),
            confidence=geo_data.get("confidence", "UNKNOWN"),
            is_city_centre=geo_data.get("is_city_centre", False),
            provider=geo_data.get("provider"),
            provider_comparison=geo_data.get("provider_comparison"),
            browser=browser,
            operating_system=operating_system,
            consent_timestamp=now,
            created_at=now,
        )
        db.session.add(record)
        db.session.commit()
        is_new = True

        logger.info(f"Auto-fetched location for link '{link.name}' from IP {client_ip} ({geo_data.get('city')}, {geo_data.get('country')})")

    loc_parts = [record.city, record.region, record.country]
    location_str = ", ".join([p for p in loc_parts if p and p != "Not available"]) or "Location recorded (IP Level)"

    return render_template(
        "tracking.html", 
        link=link, 
        record=record, 
        location_str=location_str, 
        is_new=is_new
    )


@tracking_bp.route("/api/track/<token>/consent", methods=["POST"])
@limiter.limit("30 per minute")
def submit_consent(token: str):
    """API endpoint to record visitor tracking request."""
    clean_token = token.strip()
    link = TrackingLink.query.filter_by(token=clean_token).first()
    if not link:
        return jsonify({"error": "Invalid or expired tracking token."}), 404

    if not link.is_active:
        return jsonify({"error": "Tracking link is deactivated."}), 403

    client_ip = get_client_ip(request)

    recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=2)
    recent_duplicate = VisitorRecord.query.filter(
        VisitorRecord.tracking_link_id == link.id,
        VisitorRecord.ip_address == client_ip,
        VisitorRecord.consent_timestamp >= recent_cutoff
    ).first()

    if recent_duplicate:
        return jsonify({
            "success": True,
            "status": "already_recorded",
            "message": "Your visit was already recently recorded.",
            "approximate_location": {
                "city": recent_duplicate.city or "Not available",
                "country": recent_duplicate.country or "Not available",
            }
        }), 200

    ua_header = request.headers.get("User-Agent", "")
    browser, operating_system = parse_user_agent(ua_header)

    geo_data = lookup_ip_geolocation(client_ip)
    now = datetime.now(timezone.utc)
    record = VisitorRecord(
        tracking_link_id=link.id,
        ip_address=client_ip,
        country=geo_data.get("country"),
        country_code=geo_data.get("country_code"),
        region=geo_data.get("region"),
        city=geo_data.get("city"),
        postal_code=geo_data.get("postal_code"),
        latitude=geo_data.get("latitude"),
        longitude=geo_data.get("longitude"),
        timezone=geo_data.get("timezone"),
        isp=geo_data.get("isp"),
        organization=geo_data.get("organization"),
        asn=geo_data.get("asn"),
        accuracy_radius=geo_data.get("accuracy_radius"),
        confidence=geo_data.get("confidence", "UNKNOWN"),
        is_city_centre=geo_data.get("is_city_centre", False),
        provider=geo_data.get("provider"),
        provider_comparison=geo_data.get("provider_comparison"),
        browser=browser,
        operating_system=operating_system,
        consent_timestamp=now,
        created_at=now,
    )

    db.session.add(record)
    db.session.commit()

    return jsonify({
        "success": True,
        "status": "consented",
        "message": "Location fetched and recorded for analytics.",
        "approximate_location": {
            "city": geo_data.get("city") or "Not available",
            "country": geo_data.get("country") or "Not available",
        }
    }), 200


@tracking_bp.route("/api/track/<token>/decline", methods=["POST"])
@limiter.limit("30 per minute")
def submit_decline(token: str):
    """Handle visitor decline request."""
    clean_token = token.strip()
    link = TrackingLink.query.filter_by(token=clean_token).first()
    if not link:
        return jsonify({"error": "Invalid or expired tracking token."}), 404

    return jsonify({
        "success": True,
        "status": "declined",
        "message": "You have declined the request. No IP address or location information has been collected or stored."
    }), 200
