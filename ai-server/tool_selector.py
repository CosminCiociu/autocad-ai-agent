from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]


class ToolSelector:
    """Deterministic selector for obvious intents.

    This does not replace the LLM planner. It handles clear low-risk cases and
    provides structured hints for multi-step planning.
    """

    def select(self, user_command: str, context_payload: dict[str, Any]) -> list[ToolCall]:
        command = (user_command or "").strip().lower()
        if not command:
            return []

        if any(keyword in command for keyword in ("identifica", "identify", "obiecte", "objects")):
            # If a specific entity type is requested, keep selection focused.
            if any(keyword in command for keyword in ("text", "texte", "mtext", "txt")):
                return [ToolCall(tool="find_entities", args={"entity_type": "text"})]
            if any(keyword in command for keyword in ("bloc", "block", "blocuri", "blocks")):
                return [ToolCall(tool="find_entities", args={"entity_type": "block"})]
            if any(keyword in command for keyword in ("linie", "line", "linii", "lines")):
                return [ToolCall(tool="find_entities", args={"entity_type": "line"})]
            if any(keyword in command for keyword in ("polilinie", "polyline", "polylines", "polilinii")):
                return [ToolCall(tool="find_entities", args={"entity_type": "polyline"})]

            # Generic identification: select tools based on available context.
            calls: list[ToolCall] = []
            if context_payload.get("blocks"):
                calls.append(ToolCall(tool="find_entities", args={"entity_type": "block"}))
            if context_payload.get("texts"):
                calls.append(ToolCall(tool="find_entities", args={"entity_type": "text"}))
            if context_payload.get("lines"):
                calls.append(ToolCall(tool="find_entities", args={"entity_type": "line"}))
            if context_payload.get("polylines"):
                calls.append(ToolCall(tool="find_entities", args={"entity_type": "polyline"}))

            if not calls:
                return [
                    ToolCall(tool="find_entities", args={"entity_type": "block"}),
                    ToolCall(tool="find_entities", args={"entity_type": "text"}),
                    ToolCall(tool="find_entities", args={"entity_type": "line"}),
                    ToolCall(tool="find_entities", args={"entity_type": "polyline"}),
                ]
            return calls

        return []
