"""Staging soft-auth: User + SessionToken + Bearer middleware.

Trust-based identity for a small group of known testers. NO password,
NO email verification, NO SMTP. Anyone who knows a tester's email can
access that tester's workspace.

See `docs/operations/STAGING_SOFT_AUTH_AND_PERSISTENCE_REPORT.md` for
the honest security boundary. Production auth (password / magic-link)
goes on top of the same User table later.

Storage:
  ${KAIROSKOPION_DATA_DIR}/users.jsonl       — append-only User log
  ${KAIROSKOPION_DATA_DIR}/sessions.jsonl    — append-only SessionToken log
  ${KAIROSKOPION_DATA_DIR}/users/<user_id>/  — per-user workspace data
"""

from __future__ import annotations

import json
import logging
import os
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, Header, HTTPException

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_user_id() -> str:
    return f"user_{secrets.token_hex(6)}"


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


def normalize_email(email: str | None) -> str | None:
    """Lowercase + strip; return None for empty/invalid."""
    if not email:
        return None
    e = email.strip().lower()
    if not e:
        return None
    if not _EMAIL_RE.match(e):
        return None
    return e


def get_data_dir() -> Path:
    raw = os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion"
    p = Path(raw)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ---------------------------------------------------------------------------
# Models (plain dataclasses; manual to_dict for forward-compat fields)
# ---------------------------------------------------------------------------

@dataclass
class User:
    user_id: str
    display_name: str
    email: str | None = None  # nullable; unique-if-present; lowercased
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "User":
        return cls(
            user_id=d["user_id"],
            display_name=d.get("display_name", ""),
            email=d.get("email"),
            created_at=d.get("created_at", _now_iso()),
        )


@dataclass
class SessionToken:
    token: str
    user_id: str
    created_at: str = field(default_factory=_now_iso)
    last_used_at: str | None = None
    revoked_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SessionToken":
        return cls(
            token=d["token"],
            user_id=d["user_id"],
            created_at=d.get("created_at", _now_iso()),
            last_used_at=d.get("last_used_at"),
            revoked_at=d.get("revoked_at"),
        )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None


# ---------------------------------------------------------------------------
# Stores (append-only JSONL; last-write-wins per id)
# ---------------------------------------------------------------------------

class UserStore:
    """Append-only JSONL log of User records. In-memory index by
    user_id and (when present) by normalized email."""

    FILENAME = "users.jsonl"

    def __init__(self, data_dir: str | Path | None = None):
        self._dir = Path(data_dir) if data_dir else get_data_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / self.FILENAME
        self._by_id: dict[str, User] = {}
        self._by_email: dict[str, str] = {}  # email -> user_id
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                u = User.from_dict(json.loads(line))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("skipping malformed user line: %s", exc)
                continue
            self._by_id[u.user_id] = u
            if u.email:
                self._by_email[u.email] = u.user_id

    def _append(self, user: User) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(user.to_dict(), ensure_ascii=False) + "\n")

    def find_by_email(self, email: str | None) -> User | None:
        ne = normalize_email(email)
        if not ne:
            return None
        uid = self._by_email.get(ne)
        return self._by_id.get(uid) if uid else None

    def get(self, user_id: str) -> User | None:
        return self._by_id.get(user_id)

    def all(self) -> list[User]:
        return list(self._by_id.values())

    def count(self) -> int:
        return len(self._by_id)

    def create(self, display_name: str, email: str | None = None) -> User:
        ne = normalize_email(email)
        # Unique-if-present rule enforced here. Callers must check
        # find_by_email first when they want the "conflict on signup"
        # behaviour rather than silent re-use.
        if ne and ne in self._by_email:
            raise ValueError(f"email_already_exists: {ne}")
        u = User(
            user_id=_generate_user_id(),
            display_name=(display_name or "").strip() or "Anonymous",
            email=ne,
        )
        self._by_id[u.user_id] = u
        if ne:
            self._by_email[ne] = u.user_id
        self._append(u)
        return u


class SessionTokenStore:
    """Append-only JSONL log of SessionToken records."""

    FILENAME = "sessions.jsonl"

    def __init__(self, data_dir: str | Path | None = None):
        self._dir = Path(data_dir) if data_dir else get_data_dir()
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / self.FILENAME
        self._by_token: dict[str, SessionToken] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                t = SessionToken.from_dict(json.loads(line))
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning("skipping malformed session line: %s", exc)
                continue
            # Last write wins per token
            self._by_token[t.token] = t

    def _append(self, t: SessionToken) -> None:
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(t.to_dict(), ensure_ascii=False) + "\n")

    def issue(self, user_id: str) -> SessionToken:
        t = SessionToken(token=_generate_token(), user_id=user_id)
        self._by_token[t.token] = t
        self._append(t)
        return t

    def lookup(self, token: str) -> SessionToken | None:
        return self._by_token.get(token)

    def touch(self, token: str) -> None:
        t = self._by_token.get(token)
        if t is None:
            return
        t.last_used_at = _now_iso()
        # Re-append so the durable log reflects the touch (next load wins).
        self._append(t)

    def revoke(self, token: str) -> bool:
        t = self._by_token.get(token)
        if t is None or t.revoked_at is not None:
            return False
        t.revoked_at = _now_iso()
        self._append(t)
        return True


# ---------------------------------------------------------------------------
# Module-level stores (default data_dir from env)
# ---------------------------------------------------------------------------

_user_store: UserStore | None = None
_session_store: SessionTokenStore | None = None


def _get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
    return _user_store


def _get_session_store() -> SessionTokenStore:
    global _session_store
    if _session_store is None:
        _session_store = SessionTokenStore()
    return _session_store


def reset_stores_for_tests(data_dir: str | Path) -> tuple[UserStore, SessionTokenStore]:
    """Reset module-level stores against a specific data_dir. Test-only."""
    global _user_store, _session_store
    _user_store = UserStore(data_dir=data_dir)
    _session_store = SessionTokenStore(data_dir=data_dir)
    return _user_store, _session_store


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_current_user(authorization: str | None = Header(default=None)) -> User:
    """Resolve `Authorization: Bearer <token>` → User, or 401.

    Touches `last_used_at` on the session.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_authorization")
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401, detail="invalid_authorization_format",
        )
    token = parts[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="empty_token")
    sess = _get_session_store().lookup(token)
    if sess is None or not sess.is_active:
        raise HTTPException(status_code=401, detail="invalid_or_revoked_token")
    user = _get_user_store().get(sess.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="user_not_found")
    _get_session_store().touch(token)
    return user


# ---------------------------------------------------------------------------
# High-level operations (used by endpoints)
# ---------------------------------------------------------------------------

def signup(display_name: str, email: str | None = None) -> dict:
    """Create new user + first session token.

    If the email already belongs to an existing user, return that user
    with a fresh session token (acts as login). No 409, no separate
    /continue flow — one form for both signup and return.
    """
    users = _get_user_store()
    ne = normalize_email(email)
    if ne:
        existing = users.find_by_email(ne)
        if existing is not None:
            sess = _get_session_store().issue(existing.user_id)
            return {"user": existing.to_dict(), "session_token": sess.token}
    try:
        user = users.create(display_name=display_name, email=email)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    sess = _get_session_store().issue(user.user_id)
    return {"user": user.to_dict(), "session_token": sess.token}


def continue_session(email: str) -> dict:
    """Return a fresh SessionToken for the user with this email.

    Behaviour per task spec section D:
      Known email → new SessionToken on the existing user.
      Unknown email → 404 with `email_not_found`. The frontend routes
      the user to the signup tab. NO silent user creation here.
    """
    user = _get_user_store().find_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "email_not_found",
                "message": (
                    "No tester registered with this email. "
                    "Use /signup to create a new account."
                ),
            },
        )
    sess = _get_session_store().issue(user.user_id)
    return {"user": user.to_dict(), "session_token": sess.token}


def me(user: User) -> dict:
    return {"user": user.to_dict()}


def logout(token: str) -> dict:
    revoked = _get_session_store().revoke(token)
    return {"revoked": revoked}
