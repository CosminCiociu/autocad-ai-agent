from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ObservabilityStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.log_dir = self.base_dir / "logs"
        self.replay_dir = self.base_dir / "replay"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.replay_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.log_dir / "events.json"

    def log_event(self, event: str, request_id: str, data: dict[str, Any]) -> None:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "request_id": request_id,
            "data": data,
        }
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def save_replay(self, request_id: str, payload: dict[str, Any]) -> Path:
        replay_path = self.replay_dir / f"{request_id}.json"
        replay_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return replay_path

    def load_replay(self, request_id: str) -> dict[str, Any] | None:
        replay_path = self.replay_dir / f"{request_id}.json"
        if not replay_path.exists():
            return None
        return json.loads(replay_path.read_text(encoding="utf-8"))
