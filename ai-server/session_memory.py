from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionMemoryStore:
    """Persistent key-value memory for chat sessions by drawing/session key."""

    def __init__(self, base_dir: Path) -> None:
        self._path = base_dir / "replay" / "session_memory.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_all(self, payload: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, session_key: str) -> dict[str, Any] | None:
        if not session_key:
            return None
        all_data = self._load_all()
        value = all_data.get(session_key)
        if isinstance(value, dict):
            return value
        return None

    def update_from_plan(
        self,
        session_key: str,
        user_command: str,
        action_plan: dict[str, Any],
        planned_audit_handles: list[str],
    ) -> None:
        if not session_key:
            return

        all_data = self._load_all()
        existing = all_data.get(session_key)
        if not isinstance(existing, dict):
            existing = {}

        actions = action_plan.get("actions", [])
        action_types = []
        if isinstance(actions, list):
            for action in actions:
                if isinstance(action, dict):
                    action_type = action.get("type")
                    if isinstance(action_type, str):
                        action_types.append(action_type)

        existing.update(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "last_user_command": user_command,
                "last_summary": action_plan.get("summary"),
                "last_needs_clarification": action_plan.get("needs_clarification"),
                "last_action_types": action_types,
                "last_planned_handles": planned_audit_handles,
            }
        )

        all_data[session_key] = existing
        self._save_all(all_data)

    @staticmethod
    def to_prompt_fragment(memory_state: dict[str, Any] | None) -> str:
        if not isinstance(memory_state, dict) or not memory_state:
            return ""

        compact = {
            "last_user_command": memory_state.get("last_user_command"),
            "last_summary": memory_state.get("last_summary"),
            "last_action_types": memory_state.get("last_action_types"),
            "last_planned_handles": memory_state.get("last_planned_handles"),
            "updated_at": memory_state.get("updated_at"),
        }
        return f"SESSION_MEMORY:\n{json.dumps(compact, ensure_ascii=False)}"
