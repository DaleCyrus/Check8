from flask import Flask
from sqlalchemy import text

from .config import Config
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    config = Config()
    app.config.from_object(config)

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

