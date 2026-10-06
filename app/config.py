import os
from dotenv import load_dotenv
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

load_dotenv()

class Config:
    # Core settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    
    # Database setup
    INSTANCE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
    os.makedirs(INSTANCE_PATH, exist_ok=True)
    
    _database_url = (os.getenv("DATABASE_URL") or "").strip()
    _requires_postgres = FLASK_ENV == "production" or os.getenv("RENDER") == "true"
    if _requires_postgres:
        if not _database_url:
            raise ValueError(
                "DATABASE_URL is required in production. Set the Supabase PostgreSQL "
                "connection string in your Render web service's Environment settings."
            )
        try:
            _backend = make_url(_database_url).get_backend_name()
        except (ArgumentError, ValueError):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string.") from None
        if _backend not in ("postgresql", "postgres"):
            raise ValueError(
                "Production requires PostgreSQL, not SQLite or another database. "
                "Set DATABASE_URL to your Supabase connection string."
            )
    if not _database_url:
        _database_url = f"sqlite:///{os.path.join(INSTANCE_PATH, 'check8_fixed.db')}"
    
    # Use the installed psycopg2 driver for both PostgreSQL URL forms.
    if _database_url.startswith(("postgresql://", "postgres://")):
        _database_url = "postgresql+psycopg2://" + _database_url.split("://", 1)[1]
    
    DATABASE_URL = _database_url
    SQLALCHEMY_DATABASE_URI = _database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database engine options
    if 'sqlite' in _database_url:
        _engine_options = {
            'connect_args': {
                'check_same_thread': False,
                'timeout': 10.0,
            },
            'pool_pre_ping': False,
            'pool_size': 1,
            'max_overflow': 0,
        }
    else:
        # PostgreSQL settings
        _engine_options = {
            'pool_size': 20,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
            'max_overflow': 40,
        }

    SQLALCHEMY_ENGINE_OPTIONS = _engine_options
    
    # Security settings for production
    SESSION_COOKIE_SECURE = FLASK_ENV == "production"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes
    
    # Email configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@gordoncollege.edu.ph")
    
    @staticmethod
    def init_db(app):
        """Initialize SQLite with WAL mode for better concurrent performance"""
        def init_sqlite():
            from sqlalchemy import event, Engine
            
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, _connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
                cursor.execute("PRAGMA synchronous=NORMAL")  # Less sync overhead
                cursor.execute("PRAGMA cache_size=10000")  # Larger cache
                cursor.execute("PRAGMA temp_store=MEMORY")  # In-memory temp storage
                cursor.close()
        
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            init_sqlite()

