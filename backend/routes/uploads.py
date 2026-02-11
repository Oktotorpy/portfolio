import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify
from auth import require_auth

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads")))
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".webm", ".mov"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


@bp.route("", methods=["GET"])
@require_auth
def list_files():
    """List all uploaded files with metadata."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(UPLOAD_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            ext = f.suffix.lower()
            file_type = "image" if ext in IMAGE_EXTENSIONS else "video"
            stat = f.stat()
            files.append({
                "filename": f.name,
                "path": f"/uploads/{f.name}",
                "type": file_type,
                "size": stat.st_size,
                "modified": stat.st_mtime,
            })
    return jsonify(files)


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
        return jsonify({"error": "File too large (max 100MB)"}), 400

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name

    with open(file_path, "wb") as f:
        f.write(content)

    file_type = "image" if ext in IMAGE_EXTENSIONS else "video"
    return jsonify({
        "path": f"/uploads/{unique_name}",
        "filename": file.filename,
        "type": file_type,
    }), 201


@bp.route("/<filename>", methods=["DELETE"])
@require_auth
def delete_file(filename):
    """Delete an uploaded file."""
    file_path = UPLOAD_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        return jsonify({"error": "File not found"}), 404

    # Safety: ensure the file is within UPLOAD_DIR
    try:
        file_path.resolve().relative_to(UPLOAD_DIR.resolve())
    except ValueError:
        return jsonify({"error": "Invalid file path"}), 400

    file_path.unlink()
    return jsonify({"ok": True})
