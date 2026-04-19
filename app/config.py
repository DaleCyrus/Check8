import os

from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///check8_new.db")
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

