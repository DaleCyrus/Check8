from flask import Flask
from sqlalchemy import text
from pathlib import Path

from .config import Config
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    config = Config()
    app.config.from_object(config)
    app.logger.info("Database URI: %s", app.config["SQLALCHEMY_DATABASE_URI"])

    db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if db_uri.startswith("sqlite:///"):
        sqlite_target = db_uri.replace("sqlite:///", "", 1)
        if not Path(sqlite_target).is_absolute():
            sqlite_target = str(Path(app.instance_path) / sqlite_target)
        app.logger.info("Resolved SQLite path: %s", sqlite_target)

    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize SQLite optimizations
    config.init_db(app)

    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.student.routes import bp as student_bp
    from .blueprints.admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

    @app.after_request
    def add_cache_control_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app

