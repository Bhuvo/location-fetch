import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import func, distinct
from app.models import db, TrackingLink, VisitorRecord

def get_overview_metrics() -> Dict[str, Any]:
    """Retrieve top-level KPI metrics computed from actual database records."""
    total_links = db.session.query(func.count(TrackingLink.id)).scalar() or 0
    total_consents = db.session.query(func.count(VisitorRecord.id)).scalar() or 0
    unique_ips = db.session.query(func.count(distinct(VisitorRecord.ip_address))).scalar() or 0
    
    # Non-null and non-empty countries
    countries_detected = db.session.query(
        func.count(distinct(VisitorRecord.country))
    ).filter(
        VisitorRecord.country.isnot(None), 
        VisitorRecord.country != ""
    ).scalar() or 0

    # Non-null and non-empty cities
    cities_detected = db.session.query(
        func.count(distinct(VisitorRecord.city))
    ).filter(
        VisitorRecord.city.isnot(None), 
        VisitorRecord.city != ""
    ).scalar() or 0

    return {
        "total_tracking_links": total_links,
        "total_consent_events": total_consents,
        "unique_ip_addresses": unique_ips,
        "countries_detected": countries_detected,
        "cities_detected": cities_detected,
    }


def get_timeline(days: int = 14) -> Dict[str, Any]:
    """Get consent events grouped by date over the past N days."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days - 1)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Initialize all dates in range with 0 count
    timeline_dict: Dict[str, int] = {}
    for i in range(days):
        day_str = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        timeline_dict[day_str] = 0

    records = db.session.query(
        func.date(VisitorRecord.consent_timestamp).label("date_label"),
        func.count(VisitorRecord.id).label("count")
    ).filter(
        VisitorRecord.consent_timestamp >= start_date
    ).group_by(
        "date_label"
    ).all()

    for r in records:
        key = str(r.date_label)
        if key in timeline_dict:
            timeline_dict[key] = r.count

    return {
        "labels": list(timeline_dict.keys()),
        "data": list(timeline_dict.values()),
    }


def get_country_breakdown(limit: int = 10) -> List[Dict[str, Any]]:
    """Return top countries by consented visitor count."""
    total = db.session.query(func.count(VisitorRecord.id)).scalar() or 0
    if total == 0:
        return []

    results = db.session.query(
        VisitorRecord.country,
        VisitorRecord.country_code,
        func.count(VisitorRecord.id).label("count")
    ).filter(
        VisitorRecord.country.isnot(None),
        VisitorRecord.country != ""
    ).group_by(
        VisitorRecord.country,
        VisitorRecord.country_code
    ).order_by(
        func.count(VisitorRecord.id).desc()
    ).limit(limit).all()

    breakdown = []
    for r in results:
        count = r.count
        pct = round((count / total) * 100, 1) if total > 0 else 0
        breakdown.append({
            "country": r.country,
            "country_code": r.country_code or "N/A",
            "count": count,
            "percentage": pct,
        })
    return breakdown


def get_browser_breakdown(limit: int = 6) -> List[Dict[str, Any]]:
    """Return browser distribution for chart rendering."""
    results = db.session.query(
        VisitorRecord.browser,
        func.count(VisitorRecord.id).label("count")
    ).filter(
        VisitorRecord.browser.isnot(None)
    ).group_by(
        VisitorRecord.browser
    ).order_by(
        func.count(VisitorRecord.id).desc()
    ).limit(limit).all()

    return [{"browser": r.browser or "Unknown", "count": r.count} for r in results]


def get_os_breakdown(limit: int = 6) -> List[Dict[str, Any]]:
    """Return operating system distribution for chart rendering."""
    results = db.session.query(
        VisitorRecord.operating_system,
        func.count(VisitorRecord.id).label("count")
    ).filter(
        VisitorRecord.operating_system.isnot(None)
    ).group_by(
        VisitorRecord.operating_system
    ).order_by(
        func.count(VisitorRecord.id).desc()
    ).limit(limit).all()

    return [{"os": r.operating_system or "Unknown", "count": r.count} for r in results]


def get_map_points(link_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve approximate coordinates for Leaflet map markers.
    Excludes records with missing coordinates.
    """
    query = VisitorRecord.query.filter(
        VisitorRecord.latitude.isnot(None),
        VisitorRecord.longitude.isnot(None)
    )

    if link_id:
        query = query.filter(VisitorRecord.tracking_link_id == link_id)

    records = query.order_by(VisitorRecord.consent_timestamp.desc()).limit(500).all()

    points = []
    for r in records:
        points.append({
            "id": r.id,
            "lat": r.latitude,
            "lon": r.longitude,
            "city": r.city or "Unknown City",
            "region": r.region or "Unknown Region",
            "country": r.country or "Unknown Country",
            "isp": r.isp or "Unknown ISP",
            "link_name": r.tracking_link.name if r.tracking_link else "Unknown Link",
            "timestamp": r.consent_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if r.consent_timestamp else "",
        })
    return points


def export_records_csv(
    city: Optional[str] = None,
    country: Optional[str] = None,
    link_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """Generate CSV string for visitor records matching filters."""
    query = VisitorRecord.query.join(TrackingLink, VisitorRecord.tracking_link_id == TrackingLink.id)

    if city:
        query = query.filter(VisitorRecord.city.ilike(f"%{city.strip()}%"))
    if country:
        query = query.filter(VisitorRecord.country.ilike(f"%{country.strip()}%"))
    if link_id:
        query = query.filter(VisitorRecord.tracking_link_id == link_id)
    if start_date:
        try:
            sd = datetime.strptime(start_date.strip(), "%Y-%m-%d")
            query = query.filter(VisitorRecord.consent_timestamp >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date.strip(), "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(VisitorRecord.consent_timestamp < ed)
        except ValueError:
            pass

    records = query.order_by(VisitorRecord.consent_timestamp.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID",
        "Timestamp (UTC)",
        "Tracking Link Name",
        "Tracking Link Token",
        "Public IP",
        "Country",
        "Country Code",
        "Region",
        "City",
        "Postal Code",
        "Latitude (Approx)",
        "Longitude (Approx)",
        "Confidence",
        "Accuracy Radius (km)",
        "City-Centre Centroid",
        "Timezone",
        "ISP",
        "Organization",
        "ASN",
        "Browser",
        "Operating System",
    ])

    for r in records:
        writer.writerow([
            r.id,
            r.consent_timestamp.strftime("%Y-%m-%d %H:%M:%S") if r.consent_timestamp else "",
            r.tracking_link.name if r.tracking_link else "",
            r.tracking_link.token if r.tracking_link else "",
            r.ip_address,
            r.country or "Not available",
            r.country_code or "N/A",
            r.region or "Not available",
            r.city or "Not available",
            r.postal_code or "Not available",
            r.latitude if r.latitude is not None else "Not available",
            r.longitude if r.longitude is not None else "Not available",
            r.confidence or "UNKNOWN",
            r.accuracy_radius if r.accuracy_radius is not None else "Not available",
            "YES" if r.is_city_centre else "NO",
            r.timezone or "Not available",
            r.isp or "Not available",
            r.organization or "Not available",
            r.asn or "Not available",
            r.browser or "Unknown",
            r.operating_system or "Unknown",
        ])

    return output.getvalue()


def purge_retention(retention_days: int) -> int:
    """Delete records older than retention_days. If <= 0, no records are deleted."""
    if retention_days <= 0:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted_count = db.session.query(VisitorRecord).filter(
        VisitorRecord.consent_timestamp < cutoff
    ).delete(synchronize_session=False)

    db.session.commit()
    return deleted_count
