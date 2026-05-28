from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient

import importlib.util
import sys
from pathlib import Path as P

# Ensure ai-server dir is on sys.path so its intra-package imports resolve
ai_server_dir = str(P(__file__).resolve().parents[1] / "ai-server")
if ai_server_dir not in sys.path:
    sys.path.insert(0, ai_server_dir)

# load ai-server/main.py as a module
spec = importlib.util.spec_from_file_location(
    "server_main",
    str(P(__file__).resolve().parents[1] / "ai-server" / "main.py"),
)
server_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server_main)  # type: ignore


def make_minimal_context() -> dict:
    return {
        "schema_version": "1.0.0",
        "request_id": "test-req-1",
        "drawing": {"name": "test", "units": "unitless", "coordinate_system": "WCS"},
        "blocks": [],
        "texts": [],
        "lines": [],
        "polylines": [],
    }


def test_analyze_with_mocked_planner(monkeypatch):
    ctx = make_minimal_context()

    async def fake_plan(context_payload, user_command):
        action_plan = {
            "schema_version": "1.0.0",
            "request_id": context_payload.get("request_id", "test-req-1"),
            "summary": "Find texts",
            "needs_clarification": False,
            "actions": [
                {
                    "id": "a1",
                    "type": "find_entities",
                    "args": {"entity_type": "text"},
                }
            ],
        }
        # simple container object expected by main.planner.plan usage
        return type("PR", (), {"action_plan": action_plan, "raw_response": json.dumps(action_plan)})()

    # Patch planner.plan to avoid external Ollama calls (works with pytest monkeypatch or direct invocation)
    server_main.planner.plan = fake_plan

    client = TestClient(server_main.app)
    headers = {"x-user-command": "insereaza AMP"}
    resp = client.post("/analyze", json=ctx, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("needs_clarification") is False
    assert isinstance(body.get("actions"), list)
