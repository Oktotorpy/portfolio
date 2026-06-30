"""CineVote API — group movie-night voting at /cinevote.

Auth (register/login/logout/me) + TMDb search + events/picks/watched/voting/
results + CMS admin endpoints.

Lifecycle of an event: picking -> voting -> [runoff] -> concluded.
- The LIVE event is the earliest-dated event that isn't concluded.
- One pick per user; a movie can only appear once per event.
- One vote per user per round; you can't vote your own pick.
- Points: 2 if the voter hasn't watched the movie, 1 if they have (frozen at cast).
- Voting auto-concludes once every picker has voted. A tie triggers one runoff
  round among the tied movies; a tie after that falls back to the earliest pick.
"""

import os
import sqlite3
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, make_response, g

from database import get_db
from auth import require_auth  # single-admin CMS auth
import cinevote_auth as cv

bp = Blueprint("cinevote", __name__, url_prefix="/api/cinevote")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_IMG = "https://image.tmdb.org/t/p/w500"
COOKIE_MAX_AGE = 60 * 60 * 24 * 180  # 180 days


def _now():
    return datetime.now(timezone.utc).isoformat()


def _set_cookie(resp, token):
    secure = os.environ.get("CV_COOKIE_SECURE", "1") != "0"
    resp.set_cookie(cv.CV_COOKIE, token, httponly=True, samesite="Lax",
                    secure=secure, max_age=COOKIE_MAX_AGE, path="/")
    return resp


# --------------------------------------------------------------------------- #
# auth
# --------------------------------------------------------------------------- #
@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not (2 <= len(username) <= 32):
        return jsonify({"error": "Username must be 2–32 characters"}), 400
    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    try:
        uid = cv.create_user(username, password)
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already taken"}), 409
    return _set_cookie(make_response(jsonify({"id": uid, "username": username})), cv.create_session(uid))


@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = (data.get("username") or "").strip()
    uid = cv.authenticate(username, data.get("password") or "")
    if not uid:
        return jsonify({"error": "Invalid username or password"}), 401
    return _set_cookie(make_response(jsonify({"id": uid, "username": username})), cv.create_session(uid))


@bp.route("/logout", methods=["POST"])
def logout():
    token = request.cookies.get(cv.CV_COOKIE)
    if token:
        cv.delete_session(token)
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie(cv.CV_COOKIE, path="/")
    return resp


@bp.route("/me", methods=["GET"])
def me():
    return jsonify(cv.current_user())


# --------------------------------------------------------------------------- #
# TMDb
# --------------------------------------------------------------------------- #
@bp.route("/search", methods=["GET"])
@cv.require_user
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify([])
    if not TMDB_API_KEY:
        return jsonify({"error": "Movie search is not configured (TMDB_API_KEY)"}), 503
    import requests
    try:
        r = requests.get("https://api.themoviedb.org/3/search/movie",
                         params={"api_key": TMDB_API_KEY, "query": q, "include_adult": "false"},
                         timeout=10)
        results = r.json().get("results", [])
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": f"search failed: {e}"}), 502
    out = []
    for m in results:
        if not m.get("poster_path"):
            continue
        out.append({"tmdb_id": m["id"],
                    "title": m.get("title") or m.get("original_title") or "",
                    "year": (m.get("release_date") or "")[:4],
                    "poster_url": TMDB_IMG + m["poster_path"]})
        if len(out) >= 18:
            break
    return jsonify(out)


def _tmdb_imdb_id(tmdb_id):
    if not TMDB_API_KEY:
        return None
    import requests
    try:
        r = requests.get(f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}/external_ids",
                         params={"api_key": TMDB_API_KEY}, timeout=10)
        return r.json().get("imdb_id") or None
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# event helpers
# --------------------------------------------------------------------------- #
def _live_event(db):
    """Earliest-dated event that isn't concluded, or None."""
    return db.execute(
        "SELECT * FROM cinevote_events WHERE status != 'concluded' "
        "ORDER BY event_date ASC, id ASC LIMIT 1"
    ).fetchone()


def _participants(db, event_id):
    """User ids that have a pick in the event (the voters)."""
    return [r["user_id"] for r in db.execute(
        "SELECT user_id FROM cinevote_picks WHERE event_id = ?", (event_id,)).fetchall()]


def _round1_tally(db, event_id):
    rows = db.execute(
        "SELECT pick_id, SUM(points) pts FROM cinevote_votes "
        "WHERE event_id = ? AND round = 1 GROUP BY pick_id", (event_id,)).fetchall()
    return {r["pick_id"]: r["pts"] for r in rows}


def _runoff_contention(db, event_id):
    """Pick ids tied for the lead in round 1 (the runoff candidates)."""
    scores = _round1_tally(db, event_id)
    if not scores:
        return []
    top = max(scores.values())
    return [pid for pid, p in scores.items() if p == top]


def _pick_owner(db, pick_id):
    r = db.execute("SELECT user_id FROM cinevote_picks WHERE id = ?", (pick_id,)).fetchone()
    return r["user_id"] if r else None


def _max_votes(db, event_id, voter_id, rnd):
    """How many votes a voter casts this round: 2 in the main round (capped by the
    number of non-own movies), 1 in the runoff."""
    if rnd == 1:
        non_own = db.execute(
            "SELECT COUNT(*) c FROM cinevote_picks WHERE event_id = ? AND user_id != ?",
            (event_id, voter_id)).fetchone()["c"]
        return min(2, non_own)
    return 1 if any(_pick_owner(db, pid) != voter_id for pid in _runoff_contention(db, event_id)) else 0


def _vote_count(db, event_id, voter_id, rnd):
    return db.execute(
        "SELECT COUNT(*) c FROM cinevote_votes WHERE event_id = ? AND voter_id = ? AND round = ?",
        (event_id, voter_id, rnd)).fetchone()["c"]


def _maybe_advance(db, event_id):
    """After a vote: if everyone used all their votes this round, conclude or runoff."""
    ev = db.execute("SELECT * FROM cinevote_events WHERE id = ?", (event_id,)).fetchone()
    if not ev or ev["status"] not in ("voting", "runoff"):
        return
    rnd = 1 if ev["status"] == "voting" else 2
    participants = _participants(db, event_id)
    if not participants:
        return
    for uid in participants:
        if _vote_count(db, event_id, uid, rnd) < _max_votes(db, event_id, uid, rnd):
            return  # someone still has votes to cast

    if rnd == 1:
        contention = list(_round1_tally(db, event_id).items())
        scores = {pid: pts for pid, pts in contention}
    else:
        # runoff: tally round-2 votes over the tied picks
        rows = db.execute(
            "SELECT pick_id, SUM(points) pts FROM cinevote_votes "
            "WHERE event_id = ? AND round = 2 GROUP BY pick_id", (event_id,)).fetchall()
        scores = {r["pick_id"]: r["pts"] for r in rows}

    if not scores:
        return
    top = max(scores.values())
    winners = [pid for pid, p in scores.items() if p == top]

    if len(winners) == 1:
        _conclude(db, event_id, winners[0])
    elif rnd == 1:
        db.execute("UPDATE cinevote_events SET status = 'runoff' WHERE id = ?", (event_id,))
        db.commit()
    else:
        # still tied after runoff -> earliest-created pick among the tied wins
        row = db.execute(
            "SELECT id FROM cinevote_picks WHERE id IN ({}) "
            "ORDER BY created_at ASC, id ASC LIMIT 1".format(",".join("?" * len(winners))),
            winners).fetchone()
        _conclude(db, event_id, row["id"] if row else winners[0])


def _conclude(db, event_id, winner_pick_id):
    db.execute("UPDATE cinevote_events SET status = 'concluded', winner_pick_id = ? WHERE id = ?",
               (winner_pick_id, event_id))
    db.commit()


def _serialize_event(db, ev, user_id):
    """Full state of an event for the frontend, scoped to the given user."""
    eid = ev["id"]
    status = ev["status"]
    concluded = status == "concluded"
    rnd = 2 if status == "runoff" else 1
    runoff_ids = _runoff_contention(db, eid) if status in ("runoff", "concluded") else []

    picks = db.execute(
        "SELECT p.*, u.username AS owner_name FROM cinevote_picks p "
        "JOIN cinevote_users u ON u.id = p.user_id WHERE p.event_id = ? "
        "ORDER BY p.created_at ASC, p.id ASC", (eid,)).fetchall()

    watched_ids = set()
    my_vote_pick_ids = []
    my_vote_max = 0
    if user_id:
        watched_ids = {r["pick_id"] for r in db.execute(
            "SELECT pick_id FROM cinevote_watched WHERE user_id = ?", (user_id,)).fetchall()}
        my_vote_pick_ids = [r["pick_id"] for r in db.execute(
            "SELECT pick_id FROM cinevote_votes WHERE event_id = ? AND voter_id = ? AND round = ?",
            (eid, user_id, rnd)).fetchall()]
        if status in ("voting", "runoff"):
            my_vote_max = _max_votes(db, eid, user_id, rnd)

    scores = _round1_tally(db, eid) if concluded else {}

    pick_list = []
    my_pick_id = None
    for p in picks:
        is_mine = bool(user_id) and p["user_id"] == user_id
        if is_mine:
            my_pick_id = p["id"]
        pick_list.append({
            "id": p["id"], "tmdb_id": p["tmdb_id"], "imdb_id": p["imdb_id"],
            "title": p["title"], "year": p["year"], "poster_url": p["poster_url"],
            "owner_id": p["user_id"], "owner_name": p["owner_name"], "is_mine": is_mine,
            "watched_by_me": p["id"] in watched_ids,
            "in_runoff": p["id"] in runoff_ids,
            "points": scores.get(p["id"], 0) if concluded else None,
        })

    # participants + (during voting) who has finished casting their votes
    voting = status in ("voting", "runoff")
    participants = db.execute(
        "SELECT p.user_id, u.username FROM cinevote_picks p "
        "JOIN cinevote_users u ON u.id = p.user_id WHERE p.event_id = ? "
        "ORDER BY p.created_at ASC", (eid,)).fetchall()
    part_list = []
    for r in participants:
        done = False
        if voting:
            done = _vote_count(db, eid, r["user_id"], rnd) >= _max_votes(db, eid, r["user_id"], rnd)
        part_list.append({"user_id": r["user_id"], "username": r["username"], "has_voted": done})

    results = None
    if concluded:
        ranking = sorted(pick_list, key=lambda x: (-(x["points"] or 0), x["id"]))
        results = {
            "winner_pick_id": ev["winner_pick_id"],
            "had_runoff": len(runoff_ids) > 1,
            "ranking": [{"pick_id": x["id"], "title": x["title"], "points": x["points"]} for x in ranking],
        }

    return {
        "event": {"id": eid, "name": ev["name"], "event_date": ev["event_date"], "status": status},
        "phase": status,
        "picks": pick_list,
        "participants": part_list,
        "my_pick_id": my_pick_id,
        "my_vote_pick_ids": my_vote_pick_ids,
        "my_vote_max": my_vote_max,
        "can_pick": status == "picking" and user_id is not None and my_pick_id is None,
        "runoff_pick_ids": runoff_ids if status == "runoff" else [],
        "results": results,
    }


# --------------------------------------------------------------------------- #
# event (live) + actions
# --------------------------------------------------------------------------- #
@bp.route("/event", methods=["GET"])
def event():
    db = get_db()
    ev = _live_event(db)
    if not ev:
        db.close()
        return jsonify({"event": None})
    u = cv.current_user()
    out = _serialize_event(db, ev, u["id"] if u else None)
    db.close()
    return jsonify(out)


@bp.route("/pick", methods=["POST"])
@cv.require_user
def add_pick():
    data = request.get_json() or {}
    tmdb_id = data.get("tmdb_id")
    title = (data.get("title") or "").strip()
    if not tmdb_id or not title:
        return jsonify({"error": "tmdb_id and title required"}), 400
    db = get_db()
    ev = _live_event(db)
    if not ev or ev["status"] != "picking":
        db.close()
        return jsonify({"error": "Picking is closed"}), 409
    imdb_id = _tmdb_imdb_id(tmdb_id)
    try:
        db.execute(
            "INSERT INTO cinevote_picks (event_id, user_id, tmdb_id, imdb_id, title, year, poster_url, created_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ev["id"], g.cv_user["id"], tmdb_id, imdb_id, title,
             (data.get("year") or ""), (data.get("poster_url") or ""), _now()))
        db.commit()
    except sqlite3.IntegrityError:
        db.close()
        return jsonify({"error": "You already picked, or that movie is already in the event"}), 409
    out = _serialize_event(db, _live_event(db), g.cv_user["id"])
    db.close()
    return jsonify(out)


@bp.route("/pick", methods=["DELETE"])
@cv.require_user
def delete_pick():
    db = get_db()
    ev = _live_event(db)
    if not ev or ev["status"] != "picking":
        db.close()
        return jsonify({"error": "Picking is closed"}), 409
    db.execute("DELETE FROM cinevote_picks WHERE event_id = ? AND user_id = ?", (ev["id"], g.cv_user["id"]))
    db.commit()
    out = _serialize_event(db, _live_event(db), g.cv_user["id"])
    db.close()
    return jsonify(out)


@bp.route("/watched", methods=["POST"])
@cv.require_user
def toggle_watched():
    data = request.get_json() or {}
    pick_id = data.get("pick_id")
    if not pick_id:
        return jsonify({"error": "pick_id required"}), 400
    db = get_db()
    exists = db.execute("SELECT 1 FROM cinevote_watched WHERE user_id = ? AND pick_id = ?",
                        (g.cv_user["id"], pick_id)).fetchone()
    if exists:
        db.execute("DELETE FROM cinevote_watched WHERE user_id = ? AND pick_id = ?", (g.cv_user["id"], pick_id))
    else:
        db.execute("INSERT INTO cinevote_watched (user_id, pick_id) VALUES (?, ?)", (g.cv_user["id"], pick_id))
    db.commit()
    out = _serialize_event(db, _live_event(db), g.cv_user["id"])
    db.close()
    return jsonify(out)


@bp.route("/vote", methods=["POST"])
@cv.require_user
def vote():
    data = request.get_json() or {}
    pick_id = data.get("pick_id")
    if not pick_id:
        return jsonify({"error": "pick_id required"}), 400
    uid = g.cv_user["id"]
    db = get_db()
    ev = _live_event(db)
    if not ev or ev["status"] not in ("voting", "runoff"):
        db.close()
        return jsonify({"error": "Voting is not open"}), 409
    rnd = 2 if ev["status"] == "runoff" else 1

    pick = db.execute("SELECT * FROM cinevote_picks WHERE id = ? AND event_id = ?", (pick_id, ev["id"])).fetchone()
    if not pick:
        db.close()
        return jsonify({"error": "No such pick"}), 404
    if pick["user_id"] == uid:
        db.close()
        return jsonify({"error": "You can't vote for your own pick"}), 400
    if rnd == 2 and pick_id not in _runoff_contention(db, ev["id"]):
        db.close()
        return jsonify({"error": "That movie isn't in the runoff"}), 400

    watched = db.execute("SELECT 1 FROM cinevote_watched WHERE user_id = ? AND pick_id = ?",
                         (uid, pick_id)).fetchone()
    points = 1 if watched else 2  # unseen = 2, seen = 1

    if rnd == 2:
        # runoff: single vote — replace any existing
        db.execute("DELETE FROM cinevote_votes WHERE event_id = ? AND voter_id = ? AND round = 2", (ev["id"], uid))
        db.execute("INSERT INTO cinevote_votes (event_id, voter_id, pick_id, points, round, created_at) "
                   "VALUES (?,?,?,?,2,?)", (ev["id"], uid, pick_id, points, _now()))
    else:
        # main round: toggle, up to 2 distinct movies
        existing = db.execute(
            "SELECT 1 FROM cinevote_votes WHERE event_id = ? AND voter_id = ? AND pick_id = ? AND round = 1",
            (ev["id"], uid, pick_id)).fetchone()
        if existing:
            db.execute("DELETE FROM cinevote_votes WHERE event_id = ? AND voter_id = ? AND pick_id = ? AND round = 1",
                       (ev["id"], uid, pick_id))
        else:
            if _vote_count(db, ev["id"], uid, 1) >= _max_votes(db, ev["id"], uid, 1):
                db.close()
                return jsonify({"error": "You've picked your 2 movies — deselect one to change"}), 400
            db.execute("INSERT INTO cinevote_votes (event_id, voter_id, pick_id, points, round, created_at) "
                       "VALUES (?,?,?,?,1,?)", (ev["id"], uid, pick_id, points, _now()))
    db.commit()

    _maybe_advance(db, ev["id"])
    out = _serialize_event(db, db.execute("SELECT * FROM cinevote_events WHERE id = ?", (ev["id"],)).fetchone(), uid)
    db.close()
    return jsonify(out)


@bp.route("/start-voting", methods=["POST"])
@cv.require_user
def user_start_voting():
    """Live-page 'All movies picked' — any logged-in user opens voting."""
    db = get_db()
    ev = _live_event(db)
    if not ev or ev["status"] != "picking":
        db.close()
        return jsonify({"error": "Not in the picking phase"}), 409
    n = db.execute("SELECT COUNT(*) c FROM cinevote_picks WHERE event_id = ?", (ev["id"],)).fetchone()["c"]
    if n < 2:
        db.close()
        return jsonify({"error": "Need at least 2 picks to start voting"}), 409
    db.execute("UPDATE cinevote_events SET status = 'voting' WHERE id = ?", (ev["id"],))
    db.commit()
    out = _serialize_event(db, _live_event(db), g.cv_user["id"])
    db.close()
    return jsonify(out)


@bp.route("/revert", methods=["POST"])
@cv.require_user
def user_revert():
    """Revert voting -> picking (e.g. a latecomer wants in). Keeps picks AND votes."""
    db = get_db()
    ev = _live_event(db)
    if not ev or ev["status"] != "voting":
        db.close()
        return jsonify({"error": "Can only revert during voting"}), 409
    db.execute("UPDATE cinevote_events SET status = 'picking' WHERE id = ?", (ev["id"],))
    db.commit()
    out = _serialize_event(db, _live_event(db), g.cv_user["id"])
    db.close()
    return jsonify(out)


@bp.route("/history", methods=["GET"])
def history():
    """Concluded events with their winner + ranking (public)."""
    db = get_db()
    evs = db.execute("SELECT * FROM cinevote_events WHERE status = 'concluded' "
                     "ORDER BY event_date DESC, id DESC LIMIT 50").fetchall()
    out = []
    for ev in evs:
        s = _serialize_event(db, ev, None)
        out.append({"event": s["event"], "results": s["results"],
                    "picks": [{"title": p["title"], "year": p["year"], "owner_name": p["owner_name"],
                               "points": p["points"], "poster_url": p["poster_url"], "imdb_id": p["imdb_id"],
                               "is_winner": p["id"] == ev["winner_pick_id"]} for p in s["picks"]]})
    db.close()
    return jsonify(out)


# --------------------------------------------------------------------------- #
# CMS admin (single-admin require_auth)
# --------------------------------------------------------------------------- #
@bp.route("/admin/events", methods=["GET"])
@require_auth
def admin_list_events():
    db = get_db()
    evs = db.execute("SELECT * FROM cinevote_events ORDER BY event_date ASC, id ASC").fetchall()
    live = _live_event(db)
    live_id = live["id"] if live else None
    out = []
    for ev in evs:
        npicks = db.execute("SELECT COUNT(*) c FROM cinevote_picks WHERE event_id = ?", (ev["id"],)).fetchone()["c"]
        out.append({"id": ev["id"], "name": ev["name"], "event_date": ev["event_date"],
                    "status": ev["status"], "picks": npicks, "is_live": ev["id"] == live_id})
    db.close()
    return jsonify(out)


@bp.route("/admin/events", methods=["POST"])
@require_auth
def admin_create_event():
    data = request.get_json() or {}
    event_date = (data.get("event_date") or "").strip()
    if not event_date:
        return jsonify({"error": "event_date required"}), 400
    db = get_db()
    cur = db.execute("INSERT INTO cinevote_events (name, event_date, status, created_at) VALUES (?,?, 'picking', ?)",
                     ((data.get("name") or "").strip(), event_date, _now()))
    db.commit()
    eid = cur.lastrowid
    db.close()
    return jsonify({"id": eid})


@bp.route("/admin/events/<int:eid>", methods=["PUT"])
@require_auth
def admin_update_event(eid):
    data = request.get_json() or {}
    db = get_db()
    ev = db.execute("SELECT * FROM cinevote_events WHERE id = ?", (eid,)).fetchone()
    if not ev:
        db.close()
        return jsonify({"error": "not found"}), 404
    db.execute("UPDATE cinevote_events SET name = ?, event_date = ? WHERE id = ?",
               (data.get("name", ev["name"]), data.get("event_date", ev["event_date"]), eid))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@bp.route("/admin/events/<int:eid>", methods=["DELETE"])
@require_auth
def admin_delete_event(eid):
    db = get_db()
    db.execute("DELETE FROM cinevote_events WHERE id = ?", (eid,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@bp.route("/admin/events/<int:eid>/start-voting", methods=["POST"])
@require_auth
def admin_start_voting(eid):
    """The 'All people picked' button: picking -> voting."""
    db = get_db()
    ev = db.execute("SELECT * FROM cinevote_events WHERE id = ?", (eid,)).fetchone()
    if not ev:
        db.close()
        return jsonify({"error": "not found"}), 404
    if ev["status"] != "picking":
        db.close()
        return jsonify({"error": "Event is not in the picking phase"}), 409
    n = db.execute("SELECT COUNT(*) c FROM cinevote_picks WHERE event_id = ?", (eid,)).fetchone()["c"]
    if n < 2:
        db.close()
        return jsonify({"error": "Need at least 2 picks to start voting"}), 409
    db.execute("UPDATE cinevote_events SET status = 'voting' WHERE id = ?", (eid,))
    db.commit()
    db.close()
    return jsonify({"ok": True})


@bp.route("/admin/events/<int:eid>/conclude", methods=["POST"])
@require_auth
def admin_conclude(eid):
    """Manual fallback if someone never votes: tally what we have and conclude."""
    db = get_db()
    ev = db.execute("SELECT * FROM cinevote_events WHERE id = ?", (eid,)).fetchone()
    if not ev or ev["status"] not in ("voting", "runoff"):
        db.close()
        return jsonify({"error": "Event is not in a voting phase"}), 409
    scores = _round1_tally(db, eid)
    if not scores:
        db.close()
        return jsonify({"error": "No votes cast yet"}), 409
    top = max(scores.values())
    winners = [pid for pid, p in scores.items() if p == top]
    row = db.execute("SELECT id FROM cinevote_picks WHERE id IN ({}) ORDER BY created_at ASC LIMIT 1"
                     .format(",".join("?" * len(winners))), winners).fetchone()
    _conclude(db, eid, row["id"])
    db.close()
    return jsonify({"ok": True})


@bp.route("/admin/events/<int:eid>/picks", methods=["GET"])
@require_auth
def admin_event_picks(eid):
    db = get_db()
    rows = db.execute(
        "SELECT p.id, p.title, p.year, p.poster_url, u.username AS owner_name "
        "FROM cinevote_picks p JOIN cinevote_users u ON u.id = p.user_id "
        "WHERE p.event_id = ? ORDER BY p.created_at ASC", (eid,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@bp.route("/admin/picks/<int:pick_id>", methods=["DELETE"])
@require_auth
def admin_delete_pick(pick_id):
    """Remove a participant's pick (and any votes for it)."""
    db = get_db()
    db.execute("DELETE FROM cinevote_votes WHERE pick_id = ?", (pick_id,))
    db.execute("DELETE FROM cinevote_picks WHERE id = ?", (pick_id,))
    db.commit()
    db.close()
    return jsonify({"ok": True})
