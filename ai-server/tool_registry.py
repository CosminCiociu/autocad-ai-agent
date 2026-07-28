from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    action_type: str | None = None
    args_schema: dict[str, Any] | None = None


class ToolRegistry:
    """Canonical registry for planner-visible tools.

    action_type links a high-level tool to an executable action type from action-plan schema.
    """

    def __init__(self) -> None:
        self._tools: list[ToolSpec] = [
            ToolSpec(
                name="find_entities",
                description="Find drawing entities by type/layer/name/text filter.",
                action_type="find_entities",
                args_schema={"entity_type": "block|text|line|polyline", "layer": "string?", "name": "string?", "text_contains": "string?"},
            ),
            ToolSpec(
                name="insert_block",
                description="Insert a block definition at x,y with optional layer/scale/rotation.",
                action_type="insert_block",
                args_schema={"name": "string", "position": "{x:number,y:number}", "layer": "string?", "rotation_deg": "number?", "scale": "number?"},
            ),
            ToolSpec(
                name="create_polyline",
                description="Create a polyline from vertices with optional layer/closed.",
                action_type="create_polyline",
                args_schema={"vertices": "[{x:number,y:number}, ...]", "layer": "string?", "closed": "bool?"},
            ),
            ToolSpec(
                name="update_attribute",
                description="Update a block attribute by handle/tag.",
                action_type="update_attribute",
                args_schema={"target_handle": "string", "tag": "string", "value": "string"},
            ),
            # Future-orchestrated tools (planned for milestone 2+).
            ToolSpec(name="find_room", description="Identify room-like enclosed spaces from drawing geometry."),
            ToolSpec(name="compute_room_center", description="Compute representative center points for rooms."),
            ToolSpec(name="find_nearest_wall", description="Find nearest wall segment to a reference point."),
            ToolSpec(name="check_normative", description="Check an operation against legal/technical constraints."),
        ]

    def allowed_action_types(self) -> set[str]:
        return {tool.action_type for tool in self._tools if isinstance(tool.action_type, str)}

    def planner_catalog_text(self) -> str:
        lines = []
        for tool in self._tools:
            suffix = f" -> action_type={tool.action_type}" if tool.action_type else ""
            lines.append(f"- {tool.name}{suffix}: {tool.description}")
        return "\n".join(lines)
