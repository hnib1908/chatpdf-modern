# app_services/history_service.py
#
# Lưu lịch sử cuộc trò chuyện ra file SQLite cục bộ (chat_history.db), để
# lịch sử không bị mất khi tắt/mở lại ứng dụng — không cần cài thêm thư viện
# (sqlite3 có sẵn trong Python).

import json
import sqlite3
import uuid
from datetime import datetime

DB_FILE = "chat_history.db"


def _connect(db_file: str = DB_FILE):
    conn = sqlite3.connect(db_file)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            collection_name TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            sources TEXT,
            source_filenames TEXT,
            created_at TEXT
        )
        """
    )
    return conn


def create_session(collection_name: str, title: str, db_file: str = DB_FILE) -> str:
    """Creates a new conversation session and returns its id."""
    session_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    conn = _connect(db_file)
    conn.execute(
        "INSERT INTO sessions (id, title, collection_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, title[:80], collection_name, now, now),
    )
    conn.commit()
    conn.close()
    return session_id


def add_message(session_id: str, role: str, content: str, sources=None, source_filenames=None, db_file: str = DB_FILE):
    """Appends one message to a session and bumps its updated_at (for sorting by recency)."""
    now = datetime.now().isoformat()
    conn = _connect(db_file)
    conn.execute(
        "INSERT INTO messages (session_id, role, content, sources, source_filenames, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, role, content, json.dumps(sources or []), json.dumps(source_filenames or []), now),
    )
    conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()
    conn.close()


def list_sessions(db_file: str = DB_FILE):
    """Returns all sessions, most recently updated first."""
    conn = _connect(db_file)
    rows = conn.execute(
        "SELECT id, title, collection_name, updated_at FROM sessions ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "title": r[1], "collection_name": r[2], "updated_at": r[3]}
        for r in rows
    ]


def load_messages(session_id: str, db_file: str = DB_FILE):
    """Loads all messages of a session, in chronological order, in the same
    dict shape used by app.py's st.session_state.messages."""
    conn = _connect(db_file)
    rows = conn.execute(
        "SELECT role, content, sources, source_filenames FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    messages = []
    for role, content, sources, source_filenames in rows:
        messages.append(
            {
                "role": role,
                "content": content,
                "sources": json.loads(sources) if sources else [],
                "source_filenames": json.loads(source_filenames) if source_filenames else [],
            }
        )
    return messages


def delete_session(session_id: str, db_file: str = DB_FILE):
    conn = _connect(db_file)
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()