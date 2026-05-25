import sqlite3
import os
import bcrypt

DB_PATH = os.path.join(os.path.dirname(__file__), "kukurma.db")

UNLIMITED = -1
DEFAULT_CREDITS = 5


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            credits INTEGER NOT NULL DEFAULT 5
        )
    """)
    conn.commit()
    existing = conn.execute(
        "SELECT id FROM users WHERE username = ? COLLATE NOCASE", ("kyonayr",)
    ).fetchone()
    if not existing:
        pw_hash = bcrypt.hashpw("C66".encode(), bcrypt.gensalt()).decode()
        conn.execute(
            "INSERT INTO users (username, password_hash, credits) VALUES (?, ?, ?)",
            ("kyonayr", pw_hash, UNLIMITED),
        )
        conn.commit()
    conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_user(username: str, password: str) -> dict | None:
    conn = get_db()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, credits) VALUES (?, ?, ?)",
            (username, pw_hash, DEFAULT_CREDITS),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE", (username,)
        ).fetchone()
        conn.close()
        return dict(row)
    except sqlite3.IntegrityError:
        conn.close()
        return None


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def deduct_credit(user_id: int) -> int:
    """Deduct 1 credit. Returns new credit count. -1 = unlimited (never deducted)."""
    conn = get_db()
    row = conn.execute("SELECT credits FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return 0
    credits = row["credits"]
    if credits == UNLIMITED:
        conn.close()
        return UNLIMITED
    if credits <= 0:
        conn.close()
        return 0
    new_credits = credits - 1
    conn.execute("UPDATE users SET credits = ? WHERE id = ?", (new_credits, user_id))
    conn.commit()
    conn.close()
    return new_credits
