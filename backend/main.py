import os
import sys

# Add backend dir to path
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask
from database import init_db

from routes.auth_routes import bp as auth_bp
from routes.contact import bp as contact_bp
from routes.jobs import bp as jobs_bp
from routes.roles import bp as roles_bp
from routes.projects import bp as projects_bp
from routes.lookups import bp as lookups_bp
from routes.uploads import bp as uploads_bp
from routes.election import bp as election_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    # CORS headers (in production, Caddy handles this — keep for local dev)
    @app.after_request
    def add_cors(response):
        origin = os.environ.get("CORS_ORIGIN", "http://localhost:5173")
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        return response

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(lookups_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(election_bp)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    # Serve uploaded files in dev mode (Caddy handles this in production)
    from flask import send_from_directory
    from pathlib import Path

    upload_dir = Path(os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads")))

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(str(upload_dir), filename)

    # Initialize database
    with app.app_context():
        init_db()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
