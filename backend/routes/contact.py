from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

bp = Blueprint("contact", __name__, url_prefix="/api/contact")


@bp.route("", methods=["GET"])
def get_contact():
    db = get_db()
    row = db.execute("SELECT name, email, linkedin FROM contact WHERE id = 1").fetchone()
    db.close()
    return jsonify(dict(row))


@bp.route("", methods=["PUT"])
@require_auth
def update_contact():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    db = get_db()
    db.execute(
        "UPDATE contact SET name = ?, email = ?, linkedin = ? WHERE id = 1",
        (data.get("name", ""), data.get("email", ""), data.get("linkedin", "")),
    )
    db.commit()
    row = db.execute("SELECT name, email, linkedin FROM contact WHERE id = 1").fetchone()
    db.close()
    return jsonify(dict(row))
