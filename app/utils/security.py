from functools import wraps
from flask import session, request, redirect, url_for, jsonify

def login_required(f):
    """Decorator to protect admin routes and API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_id = session.get("admin_id")
        if not admin_id:
            # Check if request is an API call or expects JSON
            if (
                request.path.startswith("/api/") or 
                request.is_json or 
                request.headers.get("Accept") == "application/json"
            ):
                return jsonify({"error": "Unauthorized. Administrator session required."}), 401
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function
