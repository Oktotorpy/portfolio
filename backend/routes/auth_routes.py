from flask import Blueprint, request, jsonify, make_response
from auth import (
    ADMIN_USERNAME, ADMIN_PASSWORD_HASH,
    verify_password, create_session, delete_session,
    SESSION_COOKIE_NAME, active_sessions,
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password required"}), 400

    if data["username"] != ADMIN_USERNAME or not verify_password(data["password"], ADMIN_PASSWORD_HASH):
        return jsonify({"error": "Invalid credentials"}), 401

    session_id = create_session()
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie(
        SESSION_COOKIE_NAME,
        session_id,
        httponly=True,
        samesite="Lax",
        secure=False,
        max_age=60 * 60 * 24 * 7,  # 7 days
    )
    return resp


@bp.route("/logout", methods=["POST"])
def logout():
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if session_id:
        delete_session(session_id)
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie(SESSION_COOKIE_NAME)
    return resp


@bp.route("/me", methods=["GET"])
def me():
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    authenticated = bool(session_id and session_id in active_sessions)
    return jsonify({"authenticated": authenticated})
