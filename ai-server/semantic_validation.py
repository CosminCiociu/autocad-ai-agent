from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass
class SemanticIssue:
    code: str
    action_id: str
    path: str
    message: str


def _num(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


class SemanticValidator:
    def __init__(self) -> None:
        self.min_coord = float(os.getenv("MIN_COORD", "-1000000"))
        self.max_coord = float(os.getenv("MAX_COORD", "1000000"))

    def validate(
        self,
        context_payload: dict[str, Any],
        action_plan: dict[str, Any],
    ) -> list[SemanticIssue]:
        issues: list[SemanticIssue] = []

        blocks = context_payload.get("blocks", [])
        texts = context_payload.get("texts", [])
        lines = context_payload.get("lines", [])
        polylines = context_payload.get("polylines", [])

        block_names = {str(b.get("name", "")).upper() for b in blocks}
        layers = {
            str(e.get("layer", "")).upper()
            for collection in (blocks, texts, lines, polylines)
            for e in collection
            if str(e.get("layer", "")).strip()
        }

        block_by_handle = {str(b.get("handle", "")): b for b in blocks}

        for index, action in enumerate(action_plan.get("actions", [])):
            action_id = str(action.get("id", f"action-{index}"))
            action_type = str(action.get("type", ""))
            args = action.get("args", {})

            if action_type == "insert_block":
                self._validate_insert_block(action_id, args, block_names, layers, issues)
            elif action_type == "create_polyline":
                self._validate_create_polyline(action_id, args, layers, issues)
            elif action_type == "update_attribute":
                self._validate_update_attribute(action_id, args, block_by_handle, issues)
            elif action_type == "find_entities":
                self._validate_find_entities(action_id, args, layers, issues)

        return issues

    def _validate_insert_block(
        self,
        action_id: str,
        args: dict[str, Any],
        block_names: set[str],
        layers: set[str],
        issues: list[SemanticIssue],
    ) -> None:
        name = str(args.get("name", "")).upper()
        if name and name not in block_names:
            issues.append(
                SemanticIssue(
                    code="BLOCK_NOT_FOUND",
                    action_id=action_id,
                    path="$.args.name",
                    message=f"Block '{args.get('name')}' was not found in drawing context.",
                )
            )

        layer = str(args.get("layer", "")).upper()
        if layer and layer not in layers:
            issues.append(
                SemanticIssue(
                    code="LAYER_NOT_ALLOWED",
                    action_id=action_id,
                    path="$.args.layer",
                    message=f"Layer '{args.get('layer')}' is not present in drawing context.",
                )
            )

        position = args.get("position", {})
        x = _num(position.get("x")) if isinstance(position, dict) else None
        y = _num(position.get("y")) if isinstance(position, dict) else None
        self._validate_point(action_id, "$.args.position", x, y, issues)

    def _validate_create_polyline(
        self,
        action_id: str,
        args: dict[str, Any],
        layers: set[str],
        issues: list[SemanticIssue],
    ) -> None:
        layer = str(args.get("layer", "")).upper()
        if layer and layer not in layers:
            issues.append(
                SemanticIssue(
                    code="LAYER_NOT_ALLOWED",
                    action_id=action_id,
                    path="$.args.layer",
                    message=f"Layer '{args.get('layer')}' is not present in drawing context.",
                )
            )

        vertices = args.get("vertices", [])
        if isinstance(vertices, list):
            for idx, point in enumerate(vertices):
                if not isinstance(point, dict):
                    issues.append(
                        SemanticIssue(
                            code="ACTION_ARGUMENT_INVALID",
                            action_id=action_id,
                            path=f"$.args.vertices[{idx}]",
                            message="Vertex must be an object with x and y.",
                        )
                    )
                    continue
                self._validate_point(
                    action_id,
                    f"$.args.vertices[{idx}]",
                    _num(point.get("x")),
                    _num(point.get("y")),
                    issues,
                )

    def _validate_update_attribute(
        self,
        action_id: str,
        args: dict[str, Any],
        block_by_handle: dict[str, dict[str, Any]],
        issues: list[SemanticIssue],
    ) -> None:
        handle = str(args.get("target_handle", ""))
        block = block_by_handle.get(handle)
        if not block:
            issues.append(
                SemanticIssue(
                    code="BLOCK_NOT_FOUND",
                    action_id=action_id,
                    path="$.args.target_handle",
                    message=f"Target block handle '{handle}' not found in context.",
                )
            )
            return

        requested_tag = str(args.get("tag", "")).upper()
        attributes = block.get("attributes", [])
        known_tags = {
            str(item.get("tag", "")).upper() for item in attributes if isinstance(item, dict)
        }

        if known_tags and requested_tag not in known_tags:
            issues.append(
                SemanticIssue(
                    code="ACTION_ARGUMENT_INVALID",
                    action_id=action_id,
                    path="$.args.tag",
                    message=f"Tag '{args.get('tag')}' is not available on block '{block.get('name')}'.",
                )
            )

    def _validate_find_entities(
        self,
        action_id: str,
        args: dict[str, Any],
        layers: set[str],
        issues: list[SemanticIssue],
    ) -> None:
        layer = str(args.get("layer", "")).upper()
        if layer and layer not in layers:
            issues.append(
                SemanticIssue(
                    code="LAYER_NOT_ALLOWED",
                    action_id=action_id,
                    path="$.args.layer",
                    message=f"Layer '{args.get('layer')}' is not present in drawing context.",
                )
            )

    def _validate_point(
        self,
        action_id: str,
        path: str,
        x: float | None,
        y: float | None,
        issues: list[SemanticIssue],
    ) -> None:
        if x is None or y is None:
            issues.append(
                SemanticIssue(
                    code="ACTION_ARGUMENT_INVALID",
                    action_id=action_id,
                    path=path,
                    message="Point must contain numeric x and y.",
                )
            )
            return

        if x < self.min_coord or x > self.max_coord or y < self.min_coord or y > self.max_coord:
            issues.append(
                SemanticIssue(
                    code="COORDINATE_OUT_OF_RANGE",
                    action_id=action_id,
                    path=path,
                    message=(
                        f"Point ({x}, {y}) outside allowed range "
                        f"[{self.min_coord}, {self.max_coord}]."
                    ),
                )
            )
