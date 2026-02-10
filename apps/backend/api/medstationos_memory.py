"""
MedStation Memory - Minimal stub for chat memory integration.
"""


class MedStationMemory:
    """Simple in-memory conversation tracking."""

    def __init__(self):
        self._sessions: dict = {}

    def store(self, session_id: str, role: str, content: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append({"role": role, "content": content})

    def recall(self, session_id: str, limit: int = 20) -> list:
        return self._sessions.get(session_id, [])[-limit:]

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
