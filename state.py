"""
Per-session conversation state.

Each unique session_id (e.g. an offender's user ID on the source
platform) gets its own isolated history so conversations do not bleed
into each other. History is kept in memory for the MVP; swap the store
for Redis / a database in production.
"""
from collections import defaultdict
from config import MAX_HISTORY_TURNS

# { session_id -> [{"role": ..., "content": ...}, ...] }
_histories: dict[str, list[dict]] = defaultdict(list)

# Track which sessions have already triggered the platform-switch alert
_alerted: set[str] = set()


def get_history(session_id: str) -> list[dict]:
    return list(_histories[session_id])


def append_message(session_id: str, role: str, content: str) -> None:
    """Append a message and trim to MAX_HISTORY_TURNS pairs."""
    _histories[session_id].append({"role": role, "content": content})
    # Each turn = 1 user + 1 assistant message → keep last N*2 entries
    max_entries = MAX_HISTORY_TURNS * 2
    if len(_histories[session_id]) > max_entries:
        _histories[session_id] = _histories[session_id][-max_entries:]


def mark_alerted(session_id: str) -> None:
    _alerted.add(session_id)


def was_alerted(session_id: str) -> bool:
    return session_id in _alerted


def clear_session(session_id: str) -> None:
    _histories.pop(session_id, None)
    _alerted.discard(session_id)
