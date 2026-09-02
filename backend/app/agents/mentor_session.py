"""In-memory session store for the Mentor Agent.

Each conversation is keyed by "{username}:{owner}/{repo}#{issue_number}".
Sessions expire after SESSION_TTL_SECONDS to free memory and prevent stale
context from bleeding into new conversations about the same issue.

Design notes:
- Pure in-memory: no Redis, no DB. A server restart clears all sessions, which
  is acceptable — the mentor conversation is ephemeral by design.
- Thread-safety is not a concern here because FastAPI runs async handlers on a
  single event loop; no concurrent writes to _sessions can occur.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

SESSION_TTL_SECONDS = 3600  # 1 hour


@dataclass
class _SessionEntry:
    session_id: str
    created_at: float = field(default_factory=time.monotonic)


# Maps conversation key → session entry.
_sessions: dict[str, _SessionEntry] = {}


def _make_key(username: str, owner: str, repo: str, issue_number: int) -> str:
    return f"{username}:{owner}/{repo}#{issue_number}"


def get_session_id(username: str, owner: str, repo: str, issue_number: int) -> str | None:
    """Return the live ADK session_id for this conversation, or None if expired/absent."""
    key = _make_key(username, owner, repo, issue_number)
    entry = _sessions.get(key)
    if entry is None:
        return None
    if time.monotonic() - entry.created_at > SESSION_TTL_SECONDS:
        del _sessions[key]
        return None
    return entry.session_id


def store_session_id(
    username: str,
    owner: str,
    repo: str,
    issue_number: int,
    session_id: str,
) -> None:
    """Persist a new ADK session_id for this conversation."""
    key = _make_key(username, owner, repo, issue_number)
    _sessions[key] = _SessionEntry(session_id=session_id)


def clear_session(username: str, owner: str, repo: str, issue_number: int) -> None:
    """Remove a session entry (e.g. on explicit reset)."""
    key = _make_key(username, owner, repo, issue_number)
    _sessions.pop(key, None)


def active_session_count() -> int:
    """Return the number of non-expired sessions (for monitoring/tests)."""
    now = time.monotonic()
    return sum(
        1 for entry in _sessions.values()
        if now - entry.created_at <= SESSION_TTL_SECONDS
    )
