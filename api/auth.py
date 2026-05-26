import os
import secrets
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

# Ensure a secure session secret is used in production / hosting environment
SESSION_SECRET = os.environ.get("SESSION_SECRET")
if not SESSION_SECRET:
    # If running on Vercel or in production, generate a secure random secret dynamically
    if os.environ.get("VERCEL") or os.environ.get("NODE_ENV") == "production":
        SECRET_KEY = secrets.token_hex(32)
    else:
        SECRET_KEY = "kukurma-fallback-secret-key-2026"
else:
    SECRET_KEY = SESSION_SECRET

ALGORITHM = "HS256"
EXPIRE_DAYS = 7


def create_token(user_id: int, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=EXPIRE_DAYS)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
