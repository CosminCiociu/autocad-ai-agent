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


def test_chat_with_mocked_planner(monkeypatch):
    ctx = make_minimal_context()
    messages = [
        {"role": "user", "content": "insereaza un bloc"},
    ]

    async def fake_plan(context_payload, user_command):
        action_plan = {
            "schema_version": "1.0.0",
            "request_id": context_payload.get("request_id", "test-req-1"),
            "summary": "Insert block",
            "needs_clarification": False,
            "actions": [
                {
                    "id": "a1",
                    "type": "insert_block",
                    "args": {"name": "AMP", "position": {"x": 0, "y": 0}},
                }
            ],
        }
        return type("PR", (), {"action_plan": action_plan, "raw_response": json.dumps(action_plan)})()

    server_main.planner.plan = fake_plan

    ctx["blocks"] = [
        {
            "handle": "h1",
            "name": "AMP",
            "layer": "0",
            "position": {"x": 0, "y": 0},
        }
    ]

    client = TestClient(server_main.app)
    payload = {"context": ctx, "messages": messages}
    resp = client.post("/chat", json=payload)
    assert resp.status_code == 200

    body = resp.json()
    assert "assistant_message" in body
    assert "action_plan" in body
    assert body["action_plan"].get("needs_clarification") is False
    assert isinstance(body["action_plan"].get("actions"), list)


def test_planner_strips_unexpected_top_level_fields():
    raw_text = json.dumps(
        {
            "schema_version": "1.0.0",
            "request_id": "req-1",
            "summary": "Identify objects in the drawing.",
            "needs_clarification": False,
            "actions": [],
            "drawing_elements": [],
            "text_elements": [],
            "polylines": [],
        }
    )

    sanitized = server_main.ActionPlanner._sanitize_action_plan(json.loads(raw_text))

    assert sanitized["schema_version"] == "1.0.0"
    assert sanitized["needs_clarification"] is False
    assert sanitized["actions"] == []
    assert "drawing_elements" not in sanitized
    assert "text_elements" not in sanitized
    assert "polylines" not in sanitized


def test_planner_normalizes_incomplete_actions():
    raw_text = json.dumps(
        {
            "schema_version": "1.0.0",
            "request_id": "req-1",
            "summary": "Identify objects in the drawing.",
            "needs_clarification": False,
            "actions": [
                {
                    "type": "find_entities",
                    "args": {"entity_type": "text"},
                }
            ],
        }
    )

    sanitized = server_main.ActionPlanner._sanitize_action_plan(json.loads(raw_text))

    assert sanitized["needs_clarification"] is False
    assert len(sanitized["actions"]) == 1
    assert sanitized["actions"][0]["id"] == "action-1"
    assert sanitized["actions"][0]["type"] == "find_entities"
    assert sanitized["actions"][0]["args"] == {"entity_type": "text"}


def test_identification_prompt_builds_real_find_entities_actions():
    ctx = make_minimal_context()
    ctx["blocks"] = [{"handle": "b1", "name": "AMP", "layer": "0", "position": {"x": 0, "y": 0}}]
    ctx["texts"] = [{"handle": "t1", "value": "TEXT", "layer": "0", "position": {"x": 1, "y": 1}, "height": 2.5}]
    ctx["lines"] = [{"handle": "l1", "layer": "0", "start": {"x": 0, "y": 0}, "end": {"x": 5, "y": 0}}]
    ctx["polylines"] = [{"handle": "p1", "layer": "0", "closed": False, "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 1}]}]

    fallback = server_main.ActionPlanner._build_identification_plan(ctx, "Identifica obiectele din desen")

    assert fallback["needs_clarification"] is False
    assert [action["type"] for action in fallback["actions"]] == [
        "find_entities",
        "find_entities",
        "find_entities",
        "find_entities",
    ]
    assert {action["args"]["entity_type"] for action in fallback["actions"]} == {
        "block",
        "text",
        "line",
        "polyline",
    }
