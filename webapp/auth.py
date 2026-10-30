"""Token auth for the mobile API (JWT, HS256) + login throttling."""

import hashlib
import hmac
import os
import secrets
import time
from threading import Lock

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from database import get_connection

ALGORITHM = "HS256"
TTL_HOURS = int(os.environ.get("TOKEN_TTL_HOURS", "12"))

MAX_FAILS = int(os.environ.get("LOGIN_MAX_FAILS", "5"))
WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "600"))

_secret = os.environ.get("WEBAPP_SECRET")
if not _secret:
    _secret = secrets.token_hex(32)
    print("[webapp] WARNING: WEBAPP_SECRET not set — tokens break on restart")

SECRET_KEY = _secret
bearer = HTTPBearer(auto_error=False)

_fails: dict[str, list[float]] = {}
_fails_lock = Lock()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def client_ip(request: Request) -> str:
    for header in ("cf-connecting-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def is_blocked(key: str) -> bool:
    now = time.time()
    with _fails_lock:
        stamps = [t for t in _fails.get(key, []) if now - t < WINDOW_SECONDS]
        _fails[key] = stamps
        return len(stamps) >= MAX_FAILS


def register_failure(key: str) -> None:
    now = time.time()
    with _fails_lock:
        if len(_fails) > 10_000:
            _fails.clear()
        _fails.setdefault(key, []).append(now)


def clear_failures(key: str) -> None:
    with _fails_lock:
        _fails.pop(key, None)


def authenticate(username: str, password: str) -> dict | None:
    row = get_connection().execute(
        "SELECT id, username, password_hash, full_name, role FROM users WHERE username=?",
        (username.strip(),),
    ).fetchone()
    if not row:
        return None
    if not hmac.compare_digest(row["password_hash"], hash_password(password.strip())):
        return None
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
    }


def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    row = get_connection().execute(
        "SELECT password_hash FROM users WHERE id=?", (user_id,)
    ).fetchone()
    if not row or not hmac.compare_digest(row["password_hash"], hash_password(current_password.strip())):
        return False
    conn = get_connection()
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (hash_password(new_password.strip()), user_id),
    )
    conn.commit()
    return True


def create_token(user: dict) -> tuple[str, int]:
    expires_in = TTL_HOURS * 3600
    now = int(time.time())
    payload = {
        "sub": str(user["id"]),
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), expires_in


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    if creds is None or not creds.credentials:
        raise _unauthorized()
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Token expired")
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid token")
    return {
        "id": int(payload["sub"]),
        "username": payload.get("username", ""),
        "full_name": payload.get("full_name", ""),
        "role": payload.get("role", "user"),
    }


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Administrator access required")
    return user
