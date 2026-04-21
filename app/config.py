import os

from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    # Use instance folder for database
    INSTANCE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "instance")
    os.makedirs(INSTANCE_PATH, exist_ok=True)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(INSTANCE_PATH, 'check8_fixed.db')}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'connect_args': {
            'check_same_thread': False,
            'timeout': 10.0,  # Reduced from 30s - WAL mode is faster
        },
        'pool_pre_ping': False,  # Disable ping checks - adds overhead
        'pool_size': 1,  # SQLite doesn't benefit from connection pooling
        'max_overflow': 0,
    }
    
    @staticmethod
    def init_db(app):
        """Initialize SQLite with WAL mode for better concurrent performance"""
        def init_sqlite():
            from sqlalchemy import event, Engine
            
            @event.listens_for(Engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for concurrency
                cursor.execute("PRAGMA synchronous=NORMAL")  # Less sync overhead
                cursor.execute("PRAGMA cache_size=10000")  # Larger cache
                cursor.execute("PRAGMA temp_store=MEMORY")  # In-memory temp storage
                cursor.close()
        
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            init_sqlite()

