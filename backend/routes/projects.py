from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

bp = Blueprint("projects", __name__, url_prefix="/api/projects")

PROJECT_COLS = "id, name, role_id, description, date_of_creation, link, content_type, content_value"


def _row_to_project(db, row):
    project = dict(row)
    skills = db.execute(
        """SELECT s.id, s.name FROM skills s
           JOIN project_skills ps ON ps.skill_id = s.id
           WHERE ps.project_id = ?""",
        (project["id"],),
    ).fetchall()
    project["skills"] = [dict(s) for s in skills]

    work_types = db.execute(
        """SELECT wt.id, wt.name FROM work_types wt
           JOIN project_work_types pwt ON pwt.work_type_id = wt.id
           WHERE pwt.project_id = ?""",
        (project["id"],),
    ).fetchall()
    project["work_types"] = [dict(wt) for wt in work_types]
    return project


def _sync_skills(db, project_id, skill_ids):
    db.execute("DELETE FROM project_skills WHERE project_id = ?", (project_id,))
    for sid in skill_ids:
        db.execute("INSERT INTO project_skills (project_id, skill_id) VALUES (?, ?)", (project_id, sid))


def _sync_work_types(db, project_id, work_type_ids):
    db.execute("DELETE FROM project_work_types WHERE project_id = ?", (project_id,))
    for wtid in work_type_ids:
        db.execute("INSERT INTO project_work_types (project_id, work_type_id) VALUES (?, ?)", (project_id, wtid))


@bp.route("", methods=["GET"])
def list_projects():
    db = get_db()
    role_id = request.args.get("role_id", type=int)
    if role_id is not None:
        rows = db.execute(
            f"SELECT {PROJECT_COLS} FROM projects WHERE role_id = ? ORDER BY date_of_creation DESC",
            (role_id,),
        ).fetchall()
    else:
        rows = db.execute(f"SELECT {PROJECT_COLS} FROM projects ORDER BY date_of_creation DESC").fetchall()
    result = [_row_to_project(db, r) for r in rows]
    db.close()
    return jsonify(result)


@bp.route("/<int:project_id>", methods=["GET"])
def get_project(project_id):
    db = get_db()
    row = db.execute(f"SELECT {PROJECT_COLS} FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Project not found"}), 404
    result = _row_to_project(db, row)
    db.close()
    return jsonify(result)


@bp.route("", methods=["POST"])
@require_auth
def create_project():
    data = request.get_json()
    if not data or not data.get("name") or not data.get("role_id"):
        return jsonify({"error": "name and role_id are required"}), 400

    # Validate content_type if provided
    content_type = data.get("content_type")
    if content_type and content_type not in ("image", "video", "youtube"):
        return jsonify({"error": "content_type must be image, video, or youtube"}), 400

    db = get_db()
    cursor = db.execute(
        """INSERT INTO projects (name, role_id, description, date_of_creation, link, content_type, content_value)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (data["name"], data["role_id"], data.get("description", ""),
         data.get("date_of_creation"), data.get("link"),
         content_type, data.get("content_value")),
    )
    project_id = cursor.lastrowid
    _sync_skills(db, project_id, data.get("skill_ids", []))
    _sync_work_types(db, project_id, data.get("work_type_ids", []))
    db.commit()
    row = db.execute(f"SELECT {PROJECT_COLS} FROM projects WHERE id = ?", (project_id,)).fetchone()
    result = _row_to_project(db, row)
    db.close()
    return jsonify(result), 201


@bp.route("/<int:project_id>", methods=["PUT"])
@require_auth
def update_project(project_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    content_type = data.get("content_type")
    if content_type and content_type not in ("image", "video", "youtube"):
        return jsonify({"error": "content_type must be image, video, or youtube"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Project not found"}), 404

    updates, values = [], []
    for field in ["name", "role_id", "description", "date_of_creation", "link", "content_type", "content_value"]:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(project_id)
        db.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", values)

    if "skill_ids" in data:
        _sync_skills(db, project_id, data["skill_ids"])
    if "work_type_ids" in data:
        _sync_work_types(db, project_id, data["work_type_ids"])

    db.commit()
    row = db.execute(f"SELECT {PROJECT_COLS} FROM projects WHERE id = ?", (project_id,)).fetchone()
    result = _row_to_project(db, row)
    db.close()
    return jsonify(result)


@bp.route("/<int:project_id>", methods=["DELETE"])
@require_auth
def delete_project(project_id):
    db = get_db()
    existing = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Project not found"}), 404
    db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})
