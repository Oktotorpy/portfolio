from flask import Blueprint, request, jsonify
from database import get_db
from auth import require_auth

bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

JOB_COLS = "id, name, logo, website, description, date_start, date_end, color"


def _row_to_job(db, row):
    job = dict(row)
    countries = db.execute(
        """SELECT c.id, c.name FROM countries c
           JOIN job_countries jc ON jc.country_id = c.id
           WHERE jc.job_id = ?""",
        (job["id"],),
    ).fetchall()
    job["countries"] = [dict(c) for c in countries]
    return job


def _sync_countries(db, job_id, country_ids):
    db.execute("DELETE FROM job_countries WHERE job_id = ?", (job_id,))
    for cid in country_ids:
        db.execute("INSERT INTO job_countries (job_id, country_id) VALUES (?, ?)", (job_id, cid))


@bp.route("", methods=["GET"])
def list_jobs():
    db = get_db()
    rows = db.execute(f"SELECT {JOB_COLS} FROM jobs ORDER BY date_start DESC").fetchall()
    result = [_row_to_job(db, r) for r in rows]
    db.close()
    return jsonify(result)


@bp.route("/<int:job_id>", methods=["GET"])
def get_job(job_id):
    db = get_db()
    row = db.execute(f"SELECT {JOB_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        db.close()
        return jsonify({"error": "Job not found"}), 404
    result = _row_to_job(db, row)
    db.close()
    return jsonify(result)


@bp.route("", methods=["POST"])
@require_auth
def create_job():
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "Name is required"}), 400

    db = get_db()
    cursor = db.execute(
        "INSERT INTO jobs (name, website, description, date_start, date_end, color) VALUES (?, ?, ?, ?, ?, ?)",
        (data["name"], data.get("website"), data.get("description", ""),
         data.get("date_start"), data.get("date_end"), data.get("color", "#3a3d48")),
    )
    job_id = cursor.lastrowid
    _sync_countries(db, job_id, data.get("country_ids", []))
    db.commit()
    row = db.execute(f"SELECT {JOB_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
    result = _row_to_job(db, row)
    db.close()
    return jsonify(result), 201


@bp.route("/<int:job_id>", methods=["PUT"])
@require_auth
def update_job(job_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Job not found"}), 404

    updates, values = [], []
    for field in ["name", "website", "description", "date_start", "date_end", "color"]:
        if field in data:
            updates.append(f"{field} = ?")
            values.append(data[field])

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(job_id)
        db.execute(f"UPDATE jobs SET {', '.join(updates)} WHERE id = ?", values)

    if "country_ids" in data:
        _sync_countries(db, job_id, data["country_ids"])

    db.commit()
    row = db.execute(f"SELECT {JOB_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
    result = _row_to_job(db, row)
    db.close()
    return jsonify(result)


@bp.route("/<int:job_id>", methods=["DELETE"])
@require_auth
def delete_job(job_id):
    db = get_db()
    existing = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Job not found"}), 404
    db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@bp.route("/<int:job_id>/logo", methods=["PUT"])
@require_auth
def update_logo(job_id):
    """Update a job's logo path (set after uploading via /api/uploads)."""
    data = request.get_json()
    if not data or "logo" not in data:
        return jsonify({"error": "logo path required"}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not existing:
        db.close()
        return jsonify({"error": "Job not found"}), 404

    db.execute("UPDATE jobs SET logo = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (data["logo"], job_id))
    db.commit()
    row = db.execute(f"SELECT {JOB_COLS} FROM jobs WHERE id = ?", (job_id,)).fetchone()
    result = _row_to_job(db, row)
    db.close()
    return jsonify(result)
