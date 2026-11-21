from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models import Admin
from app.extensions import limiter

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/admin/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    """Admin login endpoint."""
    if session.get("admin_id"):
        return redirect(url_for("dashboard.overview"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json() or {}
            username = data.get("username", "").strip()
            password = data.get("password", "")
        else:
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

        if not username or not password:
            msg = "Username and password are required."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("login.html"), 400

        admin = Admin.query.filter_by(username=username).first()
        if admin and admin.check_password(password):
            session.clear()
            session["admin_id"] = admin.id
            session["admin_username"] = admin.username
            session.permanent = True

            next_url = request.args.get("next") or url_for("dashboard.overview")
            if request.is_json:
                return jsonify({"success": True, "redirect": next_url}), 200
            return redirect(next_url)

        msg = "Invalid username or password."
        if request.is_json:
            return jsonify({"error": msg}), 401
        flash(msg, "danger")
        return render_template("login.html"), 401

    return render_template("login.html")


@auth_bp.route("/admin/logout", methods=["GET", "POST"])
def logout():
    """Admin logout endpoint."""
    session.clear()
    if request.is_json:
        return jsonify({"success": True, "message": "Logged out successfully."})
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
