"""CineVote multi-user auth — separate from the single-admin CMS auth.

Username/password only (no email). DB-backed sessions (token in an httpOnly
cookie) so logins survive restarts and identify the user. Password hashing is
reused from auth.py.
"""

import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import request, jsonify, g

from database import get_db
from auth import hash_password, verify_password

CV_COOKIE = "cv_session"


def _now():
    return datetime.now(timezone.utc).isoformat()


def create_user(username, password):
    """Insert a user; raises sqlite3.IntegrityError if the username is taken."""
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO cinevote_users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username, hash_password(password), _now()),
        )
        db.commit()
        return cur.lastrowid
    finally:
        db.close()


def authenticate(username, password):
    db = get_db()
    row = db.execute(
        "SELECT id, password_hash FROM cinevote_users WHERE username = ?", (username,)
    ).fetchone()
    db.close()
    if row and verify_password(password, row["password_hash"]):
        return row["id"]
    return None


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    db = get_db()
    db.execute(
        "INSERT INTO cinevote_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, _now()),
    )
    db.commit()
    db.close()
    return token


def delete_session(token):
    db = get_db()
    db.execute("DELETE FROM cinevote_sessions WHERE token = ?", (token,))
    db.commit()
    db.close()


def current_user():
    """Return {id, username} for the request's session cookie, or None."""
    token = request.cookies.get(CV_COOKIE)
    if not token:
        return None
    db = get_db()
    row = db.execute(
        "SELECT u.id, u.username FROM cinevote_sessions s "
        "JOIN cinevote_users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    ).fetchone()
    db.close()
    return dict(row) if row else None


def require_user(f):
    """Gate a route on a logged-in CineVote user; sets g.cv_user."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u:
            return jsonify({"error": "Not authenticated"}), 401
        g.cv_user = u
        return f(*args, **kwargs)
    return wrapper
