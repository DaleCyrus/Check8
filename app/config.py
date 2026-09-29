import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Core settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    
    # Database setup
    INSTANCE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
    os.makedirs(INSTANCE_PATH, exist_ok=True)
    
    _database_url = os.getenv("DATABASE_URL")
    if not _database_url:
        _database_url = f"sqlite:///{os.path.join(INSTANCE_PATH, 'check8_fixed.db')}"
    
    # Fix Render's postgresql:// to use psycopg2 driver
    if _database_url and _database_url.startswith("postgresql://"):
        _database_url = _database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
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

