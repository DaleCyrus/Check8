"""
Migration: Remove email verification columns from User table
"""
import sqlite3
import sys
from pathlib import Path

def migrate():
    """Remove email verification columns from database."""
    # Find the database file
    db_paths = [
        Path("instance/check8_new.db"),
        Path("instance/check8.db"),
    ]
    
    db_path = None
    for path in db_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("Error: Could not find database file")
        sys.exit(1)
    
    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Get existing columns
        cursor.execute("PRAGMA table_info(user)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Check if columns exist before attempting to drop
        columns_to_drop = []
        if "email_verification_token" in existing_columns:
            columns_to_drop.append("email_verification_token")
        if "email_verification_token_expires" in existing_columns:
            columns_to_drop.append("email_verification_token_expires")
        if "email_verified" in existing_columns:
            columns_to_drop.append("email_verified")
        
        if not columns_to_drop:
            print("✓ Email verification columns already removed or don't exist")
            return
        
        # SQLite doesn't support DROP COLUMN, so we need to recreate the table
        print(f"Removing columns: {', '.join(columns_to_drop)}")
        
        # Backup original schema
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='user'")
        original_schema = cursor.fetchone()[0]
        print(f"Original schema:\n{original_schema}\n")
        
        # Get all data from user table
        cursor.execute("SELECT * FROM user")
        all_data = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(user)")
        all_columns = [row[1] for row in cursor.fetchall()]
        
        # Filter out columns we're removing
        new_columns = [col for col in all_columns if col not in columns_to_drop]
        
        # Create new table without the verification columns
        cursor.execute(f"ALTER TABLE user RENAME TO user_old")
        
        # Recreate table without email verification columns
        # We'll do this by selecting the right columns
        column_indices = [i for i, col in enumerate(all_columns) if col in new_columns]
        
        if all_data:
            # Get the column types from original table
            cursor.execute("PRAGMA table_info(user_old)")
            column_info = {row[1]: row[2] for row in cursor.fetchall()}
            
            # Build CREATE TABLE statement
            create_cols = []
            for col in new_columns:
                col_type = column_info.get(col, "TEXT")
                if col == "id":
                    create_cols.append(f"{col} INTEGER PRIMARY KEY AUTOINCREMENT")
                elif col == "email":
                    create_cols.append(f"{col} VARCHAR(120) UNIQUE NOT NULL")
                elif col == "full_name":
                    create_cols.append(f"{col} VARCHAR(120) NOT NULL")
                elif col == "password_hash":
                    create_cols.append(f"{col} VARCHAR(255) NOT NULL")
                elif col == "role":
                    create_cols.append(f"{col} VARCHAR(20) NOT NULL")
                elif col == "is_active":
                    create_cols.append(f"{col} BOOLEAN NOT NULL DEFAULT 1")
                elif col == "created_at":
                    create_cols.append(f"{col} DATETIME DEFAULT CURRENT_TIMESTAMP")
                elif col == "updated_at":
                    create_cols.append(f"{col} DATETIME DEFAULT CURRENT_TIMESTAMP")
                else:
                    create_cols.append(f"{col} {col_type}")
            
            create_table_sql = f"CREATE TABLE user ({', '.join(create_cols)})"
            print(f"New schema:\n{create_table_sql}\n")
            
            cursor.execute(create_table_sql)
            
            # Copy data, selecting only the columns we want to keep
            placeholders = ', '.join(['?' for _ in new_columns])
            insert_sql = f"INSERT INTO user ({', '.join(new_columns)}) VALUES ({placeholders})"
            
            for row in all_data:
                new_row = tuple(row[i] for i in column_indices)
                cursor.execute(insert_sql, new_row)
        
        # Drop old table
        cursor.execute("DROP TABLE user_old")
        
        conn.commit()
        print("✓ Successfully removed email verification columns from database")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
