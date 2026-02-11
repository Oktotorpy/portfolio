from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

bp = Blueprint("projects", __name__, url_prefix="/api/projects")

PROJECT_COLS = "id, name, role_id, description, date_of_creation, link, weight_id, content_type, content_value"


def _row_to_project(db, row):
    project = dict(row)

    # Skills
    skills = db.execute(
        """SELECT s.id, s.name FROM skills s
           JOIN project_skills ps ON ps.skill_id = s.id
           WHERE ps.project_id = ?""",
        (project["id"],),
    ).fetchall()
    project["skills"] = [dict(s) for s in skills]

    # Work types
    work_types = db.execute(
        """SELECT wt.id, wt.name FROM work_types wt
           JOIN project_work_types pwt ON pwt.work_type_id = wt.id
           WHERE pwt.project_id = ?""",
        (project["id"],),
    ).fetchall()
    project["work_types"] = [dict(wt) for wt in work_types]

    # Tools
    tools = db.execute(
        """SELECT t.id, t.name FROM tools t
           JOIN project_tools pt ON pt.tool_id = t.id
           WHERE pt.project_id = ?""",
        (project["id"],),
    ).fetchall()
    project["tools"] = [dict(t) for t in tools]

    # Weight
    if project.get("weight_id"):
        weight = db.execute("SELECT id, name FROM weights WHERE id = ?", (project["weight_id"],)).fetchone()
        project["weight"] = dict(weight) if weight else None
    else:
        project["weight"] = None

    # Media (multi)
    media = db.execute(
        "SELECT id, media_type, media_value, sort_order FROM project_media WHERE project_id = ? ORDER BY sort_order",
        (project["id"],),
    ).fetchall()
    project["media"] = [dict(m) for m in media]

    return project


def _sync_skills(db, project_id, skill_ids):
    db.execute("DELETE FROM project_skills WHERE project_id = ?", (project_id,))
    for sid in skill_ids:
        db.execute("INSERT INTO project_skills (project_id, skill_id) VALUES (?, ?)", (project_id, sid))


def _sync_work_types(db, project_id, work_type_ids):
    db.execute("DELETE FROM project_work_types WHERE project_id = ?", (project_id,))
    for wtid in work_type_ids:
        db.execute("INSERT INTO project_work_types (project_id, work_type_id) VALUES (?, ?)", (project_id, wtid))


def _sync_tools(db, project_id, tool_ids):
    db.execute("DELETE FROM project_tools WHERE project_id = ?", (project_id,))
    for tid in tool_ids:
        db.execute("INSERT INTO project_tools (project_id, tool_id) VALUES (?, ?)", (project_id, tid))


def _sync_media(db, project_id, media_items):
    db.execute("DELETE FROM project_media WHERE project_id = ?", (project_id,))
    for i, item in enumerate(media_items):
        media_type = item.get("media_type")
        media_value = item.get("media_value")
        if media_type and media_value:
            db.execute(
                "INSERT INTO project_media (project_id, media_type, media_value, sort_order) VALUES (?, ?, ?, ?)",
                (project_id, media_type, media_value, i),
            )


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

    db = get_db()
    cursor = db.execute(
        """INSERT INTO projects (name, role_id, description, date_of_creation, link, weight_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data["name"], data["role_id"], data.get("description", ""),
         data.get("date_of_creation"), data.get("link"),
         data.get("weight_id")),
    )
    project_id = cursor.lastrowid
    _sync_skills(db, project_id, data.get("skill_ids", []))
    _sync_work_types(db, project_id, data.get("work_type_ids", []))
    _sync_tools(db, project_id, data.get("tool_ids", []))
    _sync_media(db, project_id, data.get("media", []))
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

    db = get_db()
    existing = db.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Project not found"}), 404

    updates, values = [], []
    for field in ["name", "role_id", "description", "date_of_creation", "link", "weight_id"]:
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
    if "tool_ids" in data:
        _sync_tools(db, project_id, data["tool_ids"])
    if "media" in data:
        _sync_media(db, project_id, data["media"])

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
