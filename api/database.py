import sqlite3
import os
import bcrypt

# Attempt to import psycopg2 for PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES_LIB = True
except ImportError:
    HAS_POSTGRES_LIB = False

# Auto-detect database URL for hosting compatibility
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL")
IS_POSTGRES = HAS_POSTGRES_LIB and DATABASE_URL is not None

# Ephemeral fallback location on Vercel read-only filesystem
if os.environ.get("VERCEL") or os.environ.get("NOW_BUILDER"):
    DB_PATH = "/tmp/kukurma.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "kukurma.db")

UNLIMITED = -1
DEFAULT_CREDITS = 5


def compile_sql(sql: str) -> str:
    """Translates SQLite query syntax to PostgreSQL if in Postgres mode."""
    if IS_POSTGRES:
        # Translate placeholder ? to %s
        sql = sql.replace("?", "%s")
        # Translate primary key auto-increment
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        # Remove SQLite specific COLLATE NOCASE (we handle it using LOWER() comparisons)
        sql = sql.replace("COLLATE NOCASE", "")
    return sql


def get_db():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def execute_query(conn, sql: str, params=()):
    compiled = compile_sql(sql)
    if IS_POSTGRES:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(compiled, params)
        return cur
    else:
        cur = conn.cursor()
        cur.execute(compiled, params)
        return cur


def init_db():
    conn = get_db()
    try:
        execute_query(conn, """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                credits INTEGER NOT NULL DEFAULT 5
            )
        """)
        conn.commit()

        # Check if default admin kyonayr exists (case-insensitively)
        cur = execute_query(
            conn,
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?)",
            ("kyonayr",)
        )
        existing = cur.fetchone()
        if not existing:
            pw_hash = bcrypt.hashpw("C66".encode(), bcrypt.gensalt()).decode()
            execute_query(
                conn,
                "INSERT INTO users (username, password_hash, credits) VALUES (?, ?, ?)",
                ("kyonayr", pw_hash, UNLIMITED),
            )
            conn.commit()
    except Exception as e:
        print(f"[Database] Initialization warning/error: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def get_user_by_username(username: str) -> dict | None:
    conn = get_db()
    try:
        cur = execute_query(
            conn,
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict | None:
    conn = get_db()
    try:
        cur = execute_query(
            conn,
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        return None
    finally:
        conn.close()


def create_user(username: str, password: str) -> dict | None:
    conn = get_db()
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        execute_query(
            conn,
            "INSERT INTO users (username, password_hash, credits) VALUES (?, ?, ?)",
            (username, pw_hash, DEFAULT_CREDITS),
        )
        conn.commit()
        
        cur = execute_query(
            conn,
            "SELECT * FROM users WHERE LOWER(username) = LOWER(?)",
            (username,)
        )
        row = cur.fetchone()
        return dict(row) if row else None
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None
    finally:
        conn.close()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def deduct_credit(user_id: int) -> int:
    """Deduct 1 credit. Returns new credit count. -1 = unlimited."""
    conn = get_db()
    try:
        cur = execute_query(
            conn,
            "SELECT credits FROM users WHERE id = ?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            return 0
        credits = row["credits"]
        if credits == UNLIMITED:
            return UNLIMITED
        if credits <= 0:
            return 0
        new_credits = credits - 1
        execute_query(
            conn,
            "UPDATE users SET credits = ? WHERE id = ?",
            (new_credits, user_id)
        )
        conn.commit()
        return new_credits
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return 0
    finally:
        conn.close()
