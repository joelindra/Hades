"""SQLite database management for HADES web interface"""

import sqlite3
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

# Database path
DB_PATH = Path(__file__).parent.parent.parent / "config" / "hades.db"
PROFILE_IMAGES_DIR = Path(__file__).parent.parent.parent / "config" / "profile_images"

# Ensure directories exist
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
PROFILE_IMAGES_DIR.mkdir(exist_ok=True)


@contextmanager
def get_db_connection():
    """Get database connection with proper error handling"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize database schema"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                username TEXT,
                profile_image TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        # Username changes tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS username_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                old_username TEXT,
                new_username TEXT NOT NULL,
                changed_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        # Reset tokens table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username_changes_user_id ON username_changes(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_username_changes_changed_at ON username_changes(changed_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reset_tokens_token ON reset_tokens(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reset_tokens_email ON reset_tokens(email)")
        
        conn.commit()


def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed


def create_user(email: str, password: str, name: str) -> Dict[str, Any]:
    """Create a new user"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hashed_password = hash_password(password)
        created_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO users (email, password, name, username, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (email.lower(), hashed_password, name, name, created_at))
        
        user_id = cursor.lastrowid
        
        # Get created user
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_user_password(email: str, new_password: str) -> bool:
    """Update user password"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        hashed_password = hash_password(new_password)
        updated_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE users 
            SET password = ?, updated_at = ?
            WHERE email = ?
        """, (hashed_password, updated_at, email.lower()))
        
        return cursor.rowcount > 0


def update_user_email(old_email: str, new_email: str) -> bool:
    """Update user email"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        updated_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE users 
            SET email = ?, updated_at = ?
            WHERE email = ?
        """, (new_email.lower(), updated_at, old_email.lower()))
        
        return cursor.rowcount > 0


def update_username(email: str, new_username: str) -> Dict[str, Any]:
    """Update username and track change"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get current user
        user = get_user_by_email(email)
        if not user:
            raise ValueError("User not found")
        
        old_username = user.get('username') or user.get('name', '')
        updated_at = datetime.utcnow().isoformat()
        
        # Update username
        cursor.execute("""
            UPDATE users 
            SET username = ?, name = ?, updated_at = ?
            WHERE email = ?
        """, (new_username, new_username, updated_at, email.lower()))
        
        # Track username change
        cursor.execute("""
            INSERT INTO username_changes (user_id, old_username, new_username, changed_at)
            VALUES (?, ?, ?, ?)
        """, (user['id'], old_username, new_username, updated_at))
        
        # Get updated user
        updated_user = get_user_by_email(email)
        return updated_user


def get_username_changes_count(email: str, days: int = 7) -> int:
    """Get count of username changes in last N days"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = get_user_by_email(email)
        if not user:
            return 0
        
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM username_changes
            WHERE user_id = ? AND changed_at > ?
        """, (user['id'], cutoff_date))
        
        row = cursor.fetchone()
        return row['count'] if row else 0


def get_username_changes(email: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get username change history"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        user = get_user_by_email(email)
        if not user:
            return []
        
        cursor.execute("""
            SELECT * FROM username_changes
            WHERE user_id = ?
            ORDER BY changed_at DESC
            LIMIT ?
        """, (user['id'], limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def update_profile_image(email: str, image_filename: str) -> bool:
    """Update user profile image"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        updated_at = datetime.utcnow().isoformat()
        
        cursor.execute("""
            UPDATE users 
            SET profile_image = ?, updated_at = ?
            WHERE email = ?
        """, (image_filename, updated_at, email.lower()))
        
        return cursor.rowcount > 0


def create_reset_token(email: str, token: str, expires_in_hours: int = 1) -> bool:
    """Create a password reset token"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        created_at = datetime.utcnow().isoformat()
        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()
        
        cursor.execute("""
            INSERT INTO reset_tokens (token, email, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        """, (token, email.lower(), created_at, expires_at))
        
        return True


def get_reset_token(token: str) -> Optional[Dict[str, Any]]:
    """Get reset token if valid"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM reset_tokens 
            WHERE token = ? AND expires_at > ?
        """, (token, datetime.utcnow().isoformat()))
        
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_reset_token(token: str) -> bool:
    """Delete a reset token"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reset_tokens WHERE token = ?", (token,))
        return cursor.rowcount > 0


def cleanup_expired_tokens():
    """Clean up expired reset tokens"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM reset_tokens 
            WHERE expires_at < ?
        """, (datetime.utcnow().isoformat(),))
        
        deleted = cursor.rowcount
        return deleted


def migrate_from_json():
    """Migrate data from JSON files to SQLite database"""
    import json
    
    users_file = DB_PATH.parent / "users.json"
    reset_tokens_file = DB_PATH.parent / "reset_tokens.json"
    
    migrated_users = 0
    migrated_tokens = 0
    
    # Migrate users
    if users_file.exists():
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                
            for email, user_data in users_data.items():
                # Check if user already exists
                existing = get_user_by_email(email)
                if existing:
                    continue
                
                # Create user
                try:
                    created_user = create_user(
                        email=user_data.get('email', email),
                        password='',  # Password already hashed, need to handle differently
                        name=user_data.get('name', '')
                    )
                    
                    if created_user:
                        # Update with existing data
                        with get_db_connection() as conn:
                            cursor = conn.cursor()
                            
                            # Update password (already hashed)
                            if 'password' in user_data:
                                cursor.execute("""
                                    UPDATE users 
                                    SET password = ?
                                    WHERE id = ?
                                """, (user_data['password'], created_user['id']))
                            
                            # Update username and profile image
                            updates = []
                            params = []
                            
                            if 'username' in user_data:
                                updates.append("username = ?")
                                params.append(user_data['username'])
                            
                            if 'profile_image' in user_data:
                                updates.append("profile_image = ?")
                                params.append(user_data['profile_image'])
                            
                            if updates:
                                params.append(created_user['id'])
                                cursor.execute(f"""
                                    UPDATE users 
                                    SET {', '.join(updates)}
                                    WHERE id = ?
                                """, params)
                            
                            # Migrate username changes
                            if 'username_changes' in user_data:
                                for change in user_data['username_changes']:
                                    cursor.execute("""
                                        INSERT INTO username_changes 
                                        (user_id, old_username, new_username, changed_at)
                                        VALUES (?, ?, ?, ?)
                                    """, (
                                        created_user['id'],
                                        change.get('old_username'),
                                        change.get('new_username'),
                                        change.get('timestamp', datetime.utcnow().isoformat())
                                    ))
                        
                        migrated_users += 1
                except Exception:
                    pass
            
            # Migration successful
        except Exception:
            pass
    
    # Migrate reset tokens
    if reset_tokens_file.exists():
        try:
            with open(reset_tokens_file, 'r', encoding='utf-8') as f:
                tokens_data = json.load(f)
                
            for token, token_data in tokens_data.items():
                # Check if token already exists
                existing = get_reset_token(token)
                if existing:
                    continue
                
                try:
                    create_reset_token(
                        email=token_data.get('email', ''),
                        token=token,
                        expires_in_hours=1
                    )
                    migrated_tokens += 1
                except Exception:
                    pass
            
        except Exception:
            pass
    
    return migrated_users, migrated_tokens


def flush_database() -> bool:
    """Clear all data from all database tables"""
    try:
        # Step 1: Delete data using the standard connection wrapper (handles transactions)
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users")
            cursor.execute("DELETE FROM username_changes")
            cursor.execute("DELETE FROM reset_tokens")
            # We don't call commit() here manually because the context manager does it.
        
        # Step 2: VACUUM must be performed outside of a transaction
        # and after the previous connection is closed.
        import sqlite3
        conn_v = sqlite3.connect(str(DB_PATH))
        conn_v.isolation_level = None  # Crucial for VACUUM
        conn_v.execute("VACUUM")
        conn_v.close()
        
        return True
    except Exception as e:
        import sys
        # Silent error, handled by caller
        return False


# Database initialization is done explicitly via init_database() call
# This prevents automatic initialization on import which can cause issues

