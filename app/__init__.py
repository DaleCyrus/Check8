import os

from dotenv import load_dotenv
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

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
    from .config import Config as AppConfig

    AppConfig.init_db(app)

    # Initialize extensions and register blueprints
    from .extensions import db, login_manager, mail, csrf

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    _ensure_compatible_schema(app)

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
            _ensure_admin_account()
        except SQLAlchemyError:
            pass

    return app


def _ensure_admin_account() -> None:
    """Create the configured administrator without seeding sample records."""
    from .extensions import db
    from .models import Role, User

    email = os.getenv("ADMIN_EMAIL", "admin@gordoncollege.edu.ph").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    if not email or not password:
        raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD must be configured")

    user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        user = User()
        user.role = Role.ADMIN.value
        user.username = email.split("@", 1)[0]
        user.full_name = "System Administrator"
        user.email = email
        user.is_active = True  # type: ignore[assignment]
        user.set_password(password)
        db.session.add(user)
    else:
        user.role = Role.ADMIN.value
        user.is_active = True

    db.session.commit()


def _ensure_compatible_schema(app: Flask) -> None:
    """Add nullable role fields when opening a database created by an older version."""
    with app.app_context():
        from sqlalchemy import inspect, text
        from .extensions import db

        db.create_all()
        inspector = inspect(db.engine)
        if "user" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("user")}
        additions = {
            "is_active": "BOOLEAN NOT NULL DEFAULT 1",
            "employee_number": "VARCHAR(32)",
            "last_name": "VARCHAR(60)",
            "first_name": "VARCHAR(60)",
            "middle_name": "VARCHAR(60)",
        }
        for name, column_type in additions.items():
            if name not in columns:
                db.session.execute(text(f"ALTER TABLE user ADD COLUMN {name} {column_type}"))
        db.session.commit()