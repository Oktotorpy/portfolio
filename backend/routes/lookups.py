from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

bp = Blueprint("lookups", __name__, url_prefix="/api/lookups")

ALLOWED_TABLES = {"countries", "skills", "work_types", "proficiencies"}


@bp.route("", methods=["GET"])
def get_lookups():
    db = get_db()
    result = {}
    for table in ALLOWED_TABLES:
        rows = db.execute(f"SELECT id, name FROM {table} ORDER BY name").fetchall()
        result[table] = [dict(r) for r in rows]
    db.close()
    return jsonify(result)


@bp.route("/<table_name>", methods=["POST"])
@require_auth
def add_lookup(table_name):
    if table_name not in ALLOWED_TABLES:
        return jsonify({"error": "Invalid table"}), 400

    data = request.get_json()
    if not data or not data.get("name", "").strip():
        return jsonify({"error": "name is required"}), 400

    name = data["name"].strip()
    db = get_db()

    existing = db.execute(f"SELECT id FROM {table_name} WHERE name = ?", (name,)).fetchone()
    if existing:
        db.close()
        return jsonify({"error": f"'{name}' already exists"}), 409

    cursor = db.execute(f"INSERT INTO {table_name} (name) VALUES (?)", (name,))
    db.commit()
    new_id = cursor.lastrowid
    db.close()
    return jsonify({"id": new_id, "name": name}), 201


@bp.route("/<table_name>/<int:item_id>", methods=["PUT"])
@require_auth
def update_lookup(table_name, item_id):
    if table_name not in ALLOWED_TABLES:
        return jsonify({"error": "Invalid table"}), 400

    data = request.get_json()
    if not data or not data.get("name", "").strip():
        return jsonify({"error": "name is required"}), 400

    name = data["name"].strip()
    db = get_db()

    existing = db.execute(f"SELECT id FROM {table_name} WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Item not found"}), 404

    duplicate = db.execute(f"SELECT id FROM {table_name} WHERE name = ? AND id != ?", (name, item_id)).fetchone()
    if duplicate:
        db.close()
        return jsonify({"error": f"'{name}' already exists"}), 409

    db.execute(f"UPDATE {table_name} SET name = ? WHERE id = ?", (name, item_id))
    db.commit()
    db.close()
    return jsonify({"id": item_id, "name": name})


@bp.route("/<table_name>/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_lookup(table_name, item_id):
    if table_name not in ALLOWED_TABLES:
        return jsonify({"error": "Invalid table"}), 400

    db = get_db()
    existing = db.execute(f"SELECT id FROM {table_name} WHERE id = ?", (item_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Item not found"}), 404

    try:
        db.execute(f"DELETE FROM {table_name} WHERE id = ?", (item_id,))
        db.commit()
    except Exception:
        db.close()
        return jsonify({"error": "Cannot delete: item is in use"}), 409

    db.close()
    return jsonify({"ok": True})
