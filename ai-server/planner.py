from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ollama_client import OllamaClient


@dataclass
class PlanResult:
    action_plan: dict[str, Any]
    raw_response: str


def _extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    # Handle fenced markdown responses just in case model ignores format=json.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first == -1 or last == -1 or first >= last:
        raise ValueError("No JSON object found in model response.")

    return json.loads(cleaned[first : last + 1])


def build_prompt(context_payload: dict[str, Any], user_command: str) -> str:
    context_json = json.dumps(context_payload, ensure_ascii=False)
    return (
        "You are a CAD planning assistant. "
        "Return ONLY one JSON object matching this shape: "
        "{schema_version:string, request_id:string, summary:string, "
        "needs_clarification:boolean, clarification_question?:string, actions:array}. "
        "Allowed action types: insert_block, create_polyline, update_attribute, find_entities. "
        "When command is ambiguous or unsafe, set needs_clarification=true and actions=[]. "
        "Never include markdown or explanations outside JSON.\n\n"
        f"USER_COMMAND:\n{user_command}\n\n"
        f"DWG_CONTEXT_JSON:\n{context_json}"
    )


class ActionPlanner:
    def __init__(self, ollama: OllamaClient) -> None:
        self.ollama = ollama

    async def plan(self, context_payload: dict[str, Any], user_command: str) -> PlanResult:
        prompt = build_prompt(context_payload=context_payload, user_command=user_command)
        raw = await self.ollama.generate_json(prompt)
        return PlanResult(action_plan=_extract_json_object(raw), raw_response=raw)
