import json
import os

from flask import Blueprint, request, jsonify, Response

from database import get_db
from auth import require_auth

# Public read endpoints + auth-gated config/admin endpoints.
bp = Blueprint("election", __name__, url_prefix="/api/election")

# Manual-mode JSON lives in a file (CMS-editable, also scriptable via SSH).
ELECTION_JSON_FILE = os.environ.get("ELECTION_JSON_FILE", "/opt/portfolio/data/election.json")

CONFIG_FIELDS = ("source_mode", "api_url", "api_proxy", "api_headers", "api_timeout")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _validate_parties(data):
    """Loose shape check: a non-empty list of party objects with vote fields."""
    if not isinstance(data, list) or not data:
        raise ValueError("payload must be a non-empty JSON array")
    for i, party in enumerate(data):
        if not isinstance(party, dict):
            raise ValueError(f"party[{i}] is not an object")
        if "votes" not in party and "percent" not in party:
            raise ValueError(f"party[{i}] missing 'votes'/'percent'")
    return data


def _get_config(db):
    row = db.execute(
        "SELECT source_mode, api_url, api_proxy, api_headers, api_timeout, updated_at "
        "FROM election_config WHERE id = 1"
    ).fetchone()
    return dict(row) if row else None


def _read_manual_file():
    """Return the manual JSON array from disk, or None if missing/invalid."""
    try:
        with open(ELECTION_JSON_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) and data else None
    except (OSError, json.JSONDecodeError):
        return None


def _latest_api_snapshot(db):
    row = db.execute(
        "SELECT payload FROM election_snapshots WHERE source = 'api' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return json.loads(row["payload"]) if row else None


# --------------------------------------------------------------------------- #
# public read endpoints
# --------------------------------------------------------------------------- #
@bp.route("/published", methods=["GET"])
def published():
    """The currently published parties array, chosen by source_mode.

    manual -> the manual file; api -> the latest 'api' snapshot. Empty array if
    the selected source has no data yet (the frontend supplies a placeholder).
    """
    db = get_db()
    cfg = _get_config(db)
    mode = (cfg or {}).get("source_mode", "manual")
    parties = _latest_api_snapshot(db) if mode == "api" else _read_manual_file()
    db.close()
    return jsonify(parties or [])


@bp.route("/latest", methods=["GET"])
def latest():
    """Newest stored snapshot as the bare parties array (any source). 404 if none."""
    db = get_db()
    row = db.execute(
        "SELECT payload, fetched_at, source FROM election_snapshots ORDER BY id DESC LIMIT 1"
    ).fetchone()
    db.close()
    if row is None:
        return jsonify({"error": "no election data yet"}), 404
    resp = Response(row["payload"], mimetype="application/json")
    resp.headers["X-Election-Fetched-At"] = row["fetched_at"]
    resp.headers["X-Election-Source"] = row["source"]
    return resp


@bp.route("/history", methods=["GET"])
def history():
    """Snapshot metadata, newest first (no payloads). Optional ?limit=N (max 1000)."""
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 1000)
    except ValueError:
        limit = 100
    db = get_db()
    rows = db.execute(
        "SELECT id, fetched_at, source, content_hash, http_status "
        "FROM election_snapshots ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@bp.route("/history/<int:snapshot_id>", methods=["GET"])
def history_item(snapshot_id):
    db = get_db()
    row = db.execute(
        "SELECT id, fetched_at, source, content_hash, http_status, payload "
        "FROM election_snapshots WHERE id = ?",
        (snapshot_id,),
    ).fetchone()
    db.close()
    if row is None:
        return jsonify({"error": "snapshot not found"}), 404
    out = dict(row)
    out["data"] = json.loads(out.pop("payload"))
    return jsonify(out)


# --------------------------------------------------------------------------- #
# admin: data-source config
# --------------------------------------------------------------------------- #
@bp.route("/config", methods=["GET"])
@require_auth
def get_config():
    db = get_db()
    cfg = _get_config(db)
    db.close()
    if cfg is None:
        return jsonify({"error": "config not initialised"}), 500
    return jsonify(cfg)


@bp.route("/config", methods=["PUT"])
@require_auth
def update_config():
    data = request.get_json() or {}

    mode = data.get("source_mode")
    if mode is not None and mode not in ("manual", "api"):
        return jsonify({"error": "source_mode must be 'manual' or 'api'"}), 400

    # api_headers must be a JSON object (or empty)
    headers = data.get("api_headers")
    if headers:
        try:
            parsed = json.loads(headers) if isinstance(headers, str) else headers
            if not isinstance(parsed, dict):
                raise ValueError
            headers = json.dumps(parsed)
        except (ValueError, TypeError):
            return jsonify({"error": "api_headers must be a JSON object"}), 400
    else:
        headers = ""

    timeout = data.get("api_timeout", 30)
    try:
        timeout = max(1, min(int(timeout), 300))
    except (ValueError, TypeError):
        return jsonify({"error": "api_timeout must be an integer (seconds)"}), 400

    from datetime import datetime, timezone

    db = get_db()
    db.execute(
        "UPDATE election_config SET source_mode = ?, api_url = ?, api_proxy = ?, "
        "api_headers = ?, api_timeout = ?, updated_at = ? WHERE id = 1",
        (
            mode if mode is not None else _get_config(db)["source_mode"],
            (data.get("api_url") or "").strip(),
            (data.get("api_proxy") or "").strip(),
            headers,
            timeout,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    db.commit()
    cfg = _get_config(db)
    db.close()
    return jsonify(cfg)


# --------------------------------------------------------------------------- #
# admin: manual JSON editor (writes the file used in manual mode)
# --------------------------------------------------------------------------- #
@bp.route("/manual", methods=["GET"])
@require_auth
def get_manual():
    return jsonify(_read_manual_file() or [])


@bp.route("/manual", methods=["PUT"])
@require_auth
def put_manual():
    body = request.get_json(silent=True)
    parties = body.get("data") if isinstance(body, dict) else body
    try:
        _validate_parties(parties)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    try:
        os.makedirs(os.path.dirname(ELECTION_JSON_FILE), exist_ok=True)
        with open(ELECTION_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(parties, f, ensure_ascii=False, indent=4)
    except OSError as e:
        return jsonify({"error": f"could not write file: {e}"}), 500

    return jsonify({"ok": True, "count": len(parties), "path": ELECTION_JSON_FILE})


# --------------------------------------------------------------------------- #
# admin: test the upstream API + proxy without saving/storing
# --------------------------------------------------------------------------- #
@bp.route("/test", methods=["POST"])
@require_auth
def test_connection():
    data = request.get_json() or {}

    # use posted values if present, else fall back to stored config
    db = get_db()
    cfg = _get_config(db) or {}
    db.close()

    url = (data.get("api_url") or cfg.get("api_url") or "").strip()
    proxy = (data.get("api_proxy") or cfg.get("api_proxy") or "").strip()
    raw_headers = data.get("api_headers", cfg.get("api_headers", "")) or ""
    try:
        timeout = max(1, min(int(data.get("api_timeout", cfg.get("api_timeout", 30))), 300))
    except (ValueError, TypeError):
        timeout = 30

    if not url:
        return jsonify({"ok": False, "error": "no api_url to test"}), 400

    try:
        headers = json.loads(raw_headers) if isinstance(raw_headers, str) and raw_headers else (raw_headers or None)
    except json.JSONDecodeError:
        return jsonify({"ok": False, "error": "api_headers is not valid JSON"}), 400

    try:
        import requests

        proxies = {"http": proxy, "https": proxy} if proxy else None
        resp = requests.get(url, proxies=proxies, headers=headers or None, timeout=timeout)
    except Exception as e:  # noqa: BLE001 — surface any client/proxy error to the admin
        return jsonify({"ok": False, "error": f"{type(e).__name__}: {e}", "via": proxy or "direct"})

    out = {"ok": resp.status_code == 200, "status": resp.status_code, "via": proxy or "direct"}
    try:
        parsed = resp.json()
        out["count"] = len(parsed) if isinstance(parsed, list) else None
        out["sample"] = parsed[:2] if isinstance(parsed, list) else parsed
    except ValueError:
        out["ok"] = False
        out["error"] = "response was not JSON"
        out["sample"] = resp.text[:300]
    return jsonify(out)
