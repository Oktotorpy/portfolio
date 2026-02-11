import os
import secrets
import hashlib
from functools import wraps
from flask import request, jsonify

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

# In-memory session store
active_sessions: set[str] = set()

SESSION_COOKIE_NAME = "session_id"


def hash_password(password: str) -> str:
    """Utility to generate a password hash. Run: python -c 'from auth import hash_password; print(hash_password("yourpassword"))'"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    try:
        salt, expected_hash = stored_hash.split(":", 1)
    except ValueError:
        return False
    actual_hash = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return secrets.compare_digest(actual_hash, expected_hash)


def create_session() -> str:
    session_id = secrets.token_urlsafe(32)
    active_sessions.add(session_id)
    return session_id


def delete_session(session_id: str):
    active_sessions.discard(session_id)


def require_auth(f):
    """Decorator to protect write endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = request.cookies.get(SESSION_COOKIE_NAME)
        if not session_id or session_id not in active_sessions:
            return jsonify({"error": "Not authenticated"}), 401
        return f(*args, **kwargs)
    return decorated
