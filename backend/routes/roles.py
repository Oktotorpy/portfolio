from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

bp = Blueprint("roles", __name__, url_prefix="/api/roles")

ROLE_COLS = "id, name, job_id, department, description, accolades, date_start, date_end"


def _row_to_role(db, row):
    role = dict(row)
    profs = db.execute(
        """SELECT p.id, p.name FROM proficiencies p
           JOIN role_proficiencies rp ON rp.proficiency_id = p.id
           WHERE rp.role_id = ?""",
        (role["id"],),
    ).fetchall()
    role["proficiencies"] = [dict(p) for p in profs]
    return role


def _sync_proficiencies(db, role_id, proficiency_ids):
    db.execute("DELETE FROM role_proficiencies WHERE role_id = ?", (role_id,))
    for pid in proficiency_ids:
        db.execute("INSERT INTO role_proficiencies (role_id, proficiency_id) VALUES (?, ?)", (role_id, pid))


@bp.route("", methods=["GET"])
def list_roles():
    db = get_db()
    job_id = request.args.get("job_id", type=int)
    if job_id is not None:
        rows = db.execute(f"SELECT {ROLE_COLS} FROM roles WHERE job_id = ? ORDER BY date_start DESC", (job_id,)).fetchall()
    else:
        rows = db.execute(f"SELECT {ROLE_COLS} FROM roles ORDER BY date_start DESC").fetchall()
    result = [_row_to_role(db, r) for r in rows]
    db.close()
    return jsonify(result)


@bp.route("/<int:role_id>", methods=["GET"])
def get_role(role_id):
    db = get_db()
    row = db.execute(f"SELECT {ROLE_COLS} FROM roles WHERE id = ?", (role_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Role not found"}), 404
    result = _row_to_role(db, row)
    db.close()
    return jsonify(result)


@bp.route("", methods=["POST"])
@require_auth
def create_role():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("job_id"):
        return jsonify({"error": "name and job_id are required"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO roles (name, job_id, department, description, accolades, date_start, date_end) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (data["name"], data["job_id"], data.get("department", ""), data.get("description", ""), data.get("accolades", ""),
         data.get("date_start"), data.get("date_end")),
    )
    role_id = cursor.lastrowid
    _sync_proficiencies(db, role_id, data.get("proficiency_ids", []))
    db.commit()
    row = db.execute(f"SELECT {ROLE_COLS} FROM roles WHERE id = ?", (role_id,)).fetchone()
    result = _row_to_role(db, row)
    db.close()
    return jsonify(result), 201


@bp.route("/<int:role_id>", methods=["PUT"])
@require_auth
def update_role(role_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM roles WHERE id = ?", (role_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Role not found"}), 404

    updates, values = [], []
    for field in ["name", "job_id", "department", "description", "accolades", "date_start", "date_end"]:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(role_id)
        db.execute(f"UPDATE roles SET {', '.join(updates)} WHERE id = ?", values)

    if "proficiency_ids" in data:
        _sync_proficiencies(db, role_id, data["proficiency_ids"])

    db.commit()
    row = db.execute(f"SELECT {ROLE_COLS} FROM roles WHERE id = ?", (role_id,)).fetchone()
    result = _row_to_role(db, row)
    db.close()
    return jsonify(result)


@bp.route("/<int:role_id>", methods=["DELETE"])
@require_auth
def delete_role(role_id):
    db = get_db()
    existing = db.execute("SELECT id FROM roles WHERE id = ?", (role_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Role not found"}), 404
    db.execute("DELETE FROM roles WHERE id = ?", (role_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})
