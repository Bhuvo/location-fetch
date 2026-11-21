from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, Response
from app.models import db, TrackingLink, VisitorRecord
from app.utils.security import login_required
from app.services.analytics import export_records_csv

visitors_bp = Blueprint("visitors_api", __name__, url_prefix="/api/visitors")

@visitors_bp.route("", methods=["GET"])
@login_required
def get_visitors():
    """Retrieve filtered, searchable, and paginated visitor records."""
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 15, type=int), 100)
    
    city = request.args.get("city", "").strip()
    country = request.args.get("country", "").strip()
    link_id = request.args.get("link_id", type=int)
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    query = VisitorRecord.query

    if city:
        query = query.filter(VisitorRecord.city.ilike(f"%{city}%"))
    if country:
        query = query.filter(VisitorRecord.country.ilike(f"%{country}%"))
    if link_id:
        query = query.filter(VisitorRecord.tracking_link_id == link_id)
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(VisitorRecord.consent_timestamp >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(VisitorRecord.consent_timestamp < ed)
        except ValueError:
            pass

    pagination = query.order_by(VisitorRecord.consent_timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    records = [r.to_dict() for r in pagination.items]

    return jsonify({
        "records": records,
        "page": pagination.page,
        "pages": pagination.pages,
        "per_page": pagination.per_page,
        "total": pagination.total,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
    })


@visitors_bp.route("/<int:record_id>", methods=["GET"])
@login_required
def get_visitor(record_id: int):
    """Retrieve full details of an individual visitor record."""
    record = db.get_or_404(VisitorRecord, record_id)
    return jsonify(record.to_dict())


@visitors_bp.route("/<int:record_id>", methods=["DELETE"])
@login_required
def delete_visitor(record_id: int):
    """Delete an individual visitor record."""
    record = db.get_or_404(VisitorRecord, record_id)
    db.session.delete(record)
    db.session.commit()
    return jsonify({"success": True, "message": f"Record #{record_id} deleted successfully."})


@visitors_bp.route("/export", methods=["GET"])
@login_required
def export_visitors_csv():
    """Export filtered visitor records to CSV file."""
    city = request.args.get("city", "").strip() or None
    country = request.args.get("country", "").strip() or None
    link_id = request.args.get("link_id", type=int) or None
    start_date = request.args.get("start_date", "").strip() or None
    end_date = request.args.get("end_date", "").strip() or None

    csv_data = export_records_csv(
        city=city,
        country=country,
        link_id=link_id,
        start_date=start_date,
        end_date=end_date
    )

    filename = f"iptrace_visitors_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
