"""In-memory session store for the Mentor Agent.

Each conversation is keyed by "{username}:{owner}/{repo}#{issue_number}" and maps to
an ADK session_id. Sessions expire after SESSION_TTL_SECONDS to free memory and
prevent stale context from bleeding into new conversations about the same issue.

**This store must stay co-located with the ADK session service.** It holds only
session *ids*; the conversation itself lives in `coordinator.session_service`, which
is an `InMemorySessionService` — in-process, not shared. Moving this mapping to Redis
or a database without also replacing that service would be actively harmful: another
worker would read an id its own ADK store has never seen, and `run_mentor_chat` would
take the "existing session" branch and skip priming the agent with issue context. The
result is a mentor answering with no idea what issue it is discussing.

Making mentor conversations survive a restart or span workers therefore means
replacing `InMemorySessionService` with a persistent ADK session service first; this
module follows it, not the other way round.

Design notes:
- Thread-safety is not a concern here because FastAPI runs async handlers on a
  single event loop; no concurrent writes to _sessions can occur.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 3600  # 1 hour

# Entries expire lazily on read, so a conversation nobody returns to is never looked
# up again and would sit in the dict for the life of the process. Sweep once the
# store grows past this, which bounds memory without paying O(n) on every write.
SWEEP_THRESHOLD = 512

# Absolute ceiling. If a sweep cannot get under it — every entry still live — evict
# the oldest, so the store can never grow without limit under sustained traffic.
MAX_SESSIONS = 2048


@dataclass
class _SessionEntry:
    session_id: str
    created_at: float = field(default_factory=time.monotonic)


# Maps conversation key → session entry.
_sessions: dict[str, _SessionEntry] = {}


def _make_key(username: str, owner: str, repo: str, issue_number: int) -> str:
    return f"{username}:{owner}/{repo}#{issue_number}"


def _is_expired(entry: _SessionEntry, now: float) -> bool:
    return now - entry.created_at > SESSION_TTL_SECONDS


def _sweep_expired() -> int:
    """Drop every expired entry. Returns how many were removed."""
    now = time.monotonic()
    expired = [key for key, entry in _sessions.items() if _is_expired(entry, now)]
    for key in expired:
        del _sessions[key]
    return len(expired)


def _enforce_capacity() -> None:
    """Keep the store bounded: sweep first, then evict oldest if still over MAX."""
    if len(_sessions) < SWEEP_THRESHOLD:
        return

    removed = _sweep_expired()
    if removed:
        logger.info("Swept %d expired mentor sessions (%d remain)", removed, len(_sessions))

    overflow = len(_sessions) - MAX_SESSIONS
    if overflow > 0:
        oldest = sorted(_sessions.items(), key=lambda kv: kv[1].created_at)[:overflow]
        for key, _ in oldest:
            del _sessions[key]
        logger.warning(
            "Mentor session store hit MAX_SESSIONS; evicted %d live sessions", overflow
        )


def get_session_id(username: str, owner: str, repo: str, issue_number: int) -> str | None:
    """Return the live ADK session_id for this conversation, or None if expired/absent."""
    key = _make_key(username, owner, repo, issue_number)
    entry = _sessions.get(key)
    if entry is None:
        return None
    if _is_expired(entry, time.monotonic()):
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
    _enforce_capacity()
    key = _make_key(username, owner, repo, issue_number)
    _sessions[key] = _SessionEntry(session_id=session_id)


def clear_session(username: str, owner: str, repo: str, issue_number: int) -> None:
    """Remove a session entry (e.g. on explicit reset)."""
    key = _make_key(username, owner, repo, issue_number)
    _sessions.pop(key, None)


def active_session_count() -> int:
    """Return the number of non-expired sessions (for monitoring/tests)."""
    now = time.monotonic()
    return sum(1 for entry in _sessions.values() if not _is_expired(entry, now))
