"""
Lightweight SQLite persistence layer.
Tracks users, per-command usage stats, and a rolling activity log for
the admin dashboard. SQLite is fine for a single-instance free-tier bot;
swap out for Postgres later if you outgrow it (the query surface here
is intentionally small).
"""
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import config

Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def _connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at INTEGER,
                last_seen INTEGER,
                is_banned INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS command_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                timestamp INTEGER,
                success INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS command_stats (
                command TEXT PRIMARY KEY,
                total_uses INTEGER DEFAULT 0
            );
            """
        )


def upsert_user(user_id: int, username: str, first_name: str):
    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
                (username, first_name, now, user_id),
            )
        else:
            conn.execute(
                "INSERT INTO users (user_id, username, first_name, joined_at, last_seen) VALUES (?,?,?,?,?)",
                (user_id, username, first_name, now, now),
            )


def is_banned(user_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT is_banned FROM users WHERE user_id=?", (user_id,)).fetchone()
        return bool(row and row["is_banned"])


def set_banned(user_id: int, banned: bool):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))


def log_command(user_id: int, command: str, success: bool = True):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO command_log (user_id, command, timestamp, success) VALUES (?,?,?,?)",
            (user_id, command, now, 1 if success else 0),
        )
        conn.execute(
            """
            INSERT INTO command_stats (command, total_uses) VALUES (?, 1)
            ON CONFLICT(command) DO UPDATE SET total_uses = total_uses + 1
            """,
            (command,),
        )


def get_user_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]


def get_active_today() -> int:
    since = int(time.time()) - 86400
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(DISTINCT user_id) c FROM command_log WHERE timestamp >= ?", (since,)
        ).fetchone()["c"]


def get_top_commands(limit: int = 10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT command, total_uses FROM command_stats ORDER BY total_uses DESC LIMIT ?", (limit,)
        ).fetchall()


def get_recent_log(limit: int = 20):
    with get_conn() as conn:
        return conn.execute(
            "SELECT user_id, command, timestamp, success FROM command_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()


def get_total_commands() -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT SUM(total_uses) c FROM command_stats").fetchone()
        return row["c"] or 0
