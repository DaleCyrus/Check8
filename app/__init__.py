from flask import Flask

from .config import Config
from .extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config())

    db.init_app(app)
    login_manager.init_app(app)

    from .blueprints.auth.routes import bp as auth_bp
    from .blueprints.student.routes import bp as student_bp
    from .blueprints.admin.routes import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

    return app

