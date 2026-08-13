import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def create_app() -> Flask:
    """Application factory used by `run.py`.

    Loads configuration from `app.config.Config`, initializes extensions,
    registers blueprints, and ensures the database exists.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Load consolidated configuration (uses app/config.py)
    app.config.from_object("app.config.Config")

    # Initialize DB engine options or sqlite pragmas if provided
    try:
        from .config import Config as AppConfig

        if hasattr(AppConfig, "init_db"):
            AppConfig.init_db(app)
    except Exception:
        pass

    # Initialize extensions and register blueprints
    from .extensions import db, login_manager, mail, csrf

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    try:
        from .blueprints.auth.routes import bp as auth_bp
        from .blueprints.admin.routes import bp as admin_bp
        from .blueprints.student.routes import bp as student_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(student_bp)
    except Exception as e:
        # Log the error for debugging
        import traceback
        print(f"[ERROR] Blueprint registration failed: {e}")
        traceback.print_exc()
        raise  # Re-raise so we can see the actual error

    # Health check endpoint
    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    # Ensure database tables exist
    with app.app_context():
        try:
            db.create_all()
        except Exception:
            pass

    return app