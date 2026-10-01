import hashlib
import hmac
import secrets
import time

from fastapi import HTTPException, Request, Response

from .config import settings
from .db import begin_write, connect

COOKIE = "mg_session"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    value = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${value.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        # Equal work for an unknown account.
        hash_password(password)
        return False
    try:
        _, salt, expected = stored.split("$")
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1, dklen=32)
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def create_session(c, user_id: str, response: Response, demo=False) -> str:
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
    lifetime = 48 * 3600 if demo else 7 * 86400
    c.execute(
        "INSERT INTO sessions VALUES(?,?,?,?)",
        (hashlib.sha256(token.encode()).hexdigest(), user_id, csrf, time.time() + lifetime),
    )
    response.set_cookie(
        COOKIE,
        token,
        max_age=lifetime,
        httponly=True,
        secure=settings().cookie_secure,
        samesite="lax",
        path="/",
    )
    return csrf


def current_user(request: Request) -> dict:
    raw = request.cookies.get(COOKIE, "")
    if not raw:
        raise HTTPException(401, "Please sign in or open a demo workspace.")
    token = hashlib.sha256(raw.encode()).hexdigest()
    with connect() as c:
        row = c.execute(
            """SELECT u.*,s.csrf,w.id AS workspace_id,w.name AS workspace_name
                           FROM sessions s JOIN users u ON u.id=s.user_id
                           JOIN workspaces w ON w.owner_id=u.id
                           WHERE s.token_hash=? AND s.expires_at>?""",
            (token, time.time()),
        ).fetchone()
    if not row:
        raise HTTPException(401, "Your session expired. Please sign in again.")
    user = dict(row)
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(supplied, user["csrf"]):
            raise HTTPException(403, "Session verification failed. Refresh the page and retry.")
    return user


def rate_limit(bucket: str, limit: int, seconds: int):
    timestamp = time.time()
    with connect() as c:
        begin_write(c)
        c.execute("DELETE FROM rate_limits WHERE reset_at<?", (timestamp,))
        row = c.execute("SELECT * FROM rate_limits WHERE bucket=?", (bucket,)).fetchone()
        if row and row["count"] >= limit:
            raise HTTPException(
                429,
                "Too many requests. Please try again shortly.",
                headers={"Retry-After": str(max(1, int(row["reset_at"] - timestamp)))},
            )
        c.execute(
            """INSERT INTO rate_limits VALUES(?,1,?) ON CONFLICT(bucket)
                    DO UPDATE SET count=rate_limits.count+1""",
            (bucket, timestamp + seconds),
        )
