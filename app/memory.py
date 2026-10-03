
import sqlite3
from pathlib import Path

from app.config import DB_PATH


# ============================================================
# INITIAL DATABASE SETUP
# ============================================================

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    # --------------------------------------------------------
    # Conversations table
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            session_id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # --------------------------------------------------------
    # Messages table
    # --------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            message TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_session_id
        ON messages (session_id, id)
    """)

    conn.commit()
    conn.close()


# ============================================================
# CREATE CONVERSATION
# ============================================================

def create_conversation(
    session_id: str,
    title: str = "New Chat"
):

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO conversations
        (session_id, title)
        VALUES (?, ?)
    """, (
        session_id,
        title
    ))

    conn.commit()
    conn.close()


# ============================================================
# ADD MESSAGE
# ============================================================

def add_message(
    session_id: str,
    role: str,
    message: str
):

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO messages
        (session_id, role, message)
        VALUES (?, ?, ?)
    """, (
        session_id,
        role,
        message
    ))

    if role == "user":
        cursor.execute("""
            UPDATE conversations
            SET title = CASE
                WHEN title IS NULL OR title = 'New Chat'
                THEN substr(?, 1, 60)
                ELSE title
            END
            WHERE session_id = ?
        """, (message.strip(), session_id))

    conn.commit()
    conn.close()


# ============================================================
# GET HISTORY
# ============================================================

def get_history(
    session_id: str,
    limit: int = 20
):

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, message
        FROM messages
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (
        session_id,
        limit
    ))

    rows = cursor.fetchall()

    conn.close()

    # Oldest → newest
    return rows[::-1]


# ============================================================
# CLEAR HISTORY
# ============================================================

def clear_history(
    session_id: str
):

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    # Delete messages
    cursor.execute("""
        DELETE FROM messages
        WHERE session_id = ?
    """, (
        session_id,
    ))

    # Delete conversation
    cursor.execute("""
        DELETE FROM conversations
        WHERE session_id = ?
    """, (
        session_id,
    ))

    conn.commit()
    conn.close()


# ============================================================
# GET ALL CONVERSATIONS
# ============================================================

def get_conversations():

    conn = sqlite3.connect(DB_PATH, timeout=10)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT session_id, title, created_at
        FROM conversations
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows

