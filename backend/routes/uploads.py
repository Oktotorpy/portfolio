import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify
from auth import require_auth

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads")))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".webm", ".mov"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@bp.route("", methods=["POST"])
@require_auth
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No filename provided"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"File type '{ext}' not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"}), 400

    content = file.read()
    if len(content) > MAX_FILE_SIZE:
        return jsonify({"error": "File too large (max 50MB)"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    return jsonify({"path": f"/uploads/{unique_name}", "filename": file.filename}), 201
