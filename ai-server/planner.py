from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from knowledge_base import KnowledgeBaseRetriever
from ollama_client import OllamaClient
from task_graph import enrich_action_plan_with_goal_graph
from tool_registry import ToolRegistry
from tool_selector import ToolSelector


ALLOWED_ACTION_PLAN_KEYS = {
    "schema_version",
    "request_id",
    "summary",
    "needs_clarification",
    "clarification_question",
    "actions",
    "goal_plan",
    "task_graph",
}

TOOL_REGISTRY = ToolRegistry()
ALLOWED_ACTION_TYPES = TOOL_REGISTRY.allowed_action_types()


@dataclass
class PlanResult:
    action_plan: dict[str, Any]
    raw_response: str
    retrieved_knowledge: list[dict[str, Any]]


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

    parsed = json.loads(cleaned[first : last + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Model response is not a JSON object.")
    return parsed


def build_prompt(
    context_payload: dict[str, Any],
    user_command: str,
    messages: list[dict[str, Any]] | None = None,
    rag_context: str = "",
) -> str:
    context_json = json.dumps(context_payload, ensure_ascii=False)
    
    # Build chat history context if messages provided
    history_context = ""
    history_hint = ""
    if messages and len(messages) > 1:
        history_lines = []
        for msg in messages:
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                history_lines.append(f"{role}: {content}")
        if history_lines:
            history_context = "\n\nCONVERSATION HISTORY:\n" + "\n".join(history_lines)
            history_hint = "\n\nIMPORTANT: The current command may reference or depend on previous requests. Use conversation history for context."

    kb_section = ""
    kb_hint = ""
    if rag_context:
        kb_section = f"\n\nKNOWLEDGE_BASE_CONTEXT:\n{rag_context}"
        kb_hint = (
            "\n\nIMPORTANT: Use KNOWLEDGE_BASE_CONTEXT for legal/domain constraints "
            "(e.g., P118, I7, EN54, block catalogs). If context conflicts, prefer explicit legal text."
        )
    
    return (
        "You are a CAD planning assistant. "
        "Return ONLY one JSON object matching this shape exactly: "
        "{schema_version:string, request_id:string, summary:string, "
        "needs_clarification:boolean, clarification_question?:string, actions:array}. "
        "Allowed action types: insert_block, create_polyline, update_attribute, find_entities. "
        "Use only actions supported by the tool registry listed below. "
        "Do not echo or repeat DWG_CONTEXT_JSON. "
        "Do not add any extra top-level keys. "
        "When command is ambiguous or unsafe, set needs_clarification=true and actions=[]. "
        "When command may reference previous identified/created entities, infer the action from context."
        "When the command is about regulation/compliance, use provided legal snippets for reasoning. "
        "Never include markdown or explanations outside JSON.\n\n"
        f"TOOL_REGISTRY:\n{TOOL_REGISTRY.planner_catalog_text()}\n\n"
        f"DWG_CONTEXT_JSON:\n{context_json}"
        f"{kb_section}"
        f"{history_context}"
        f"{kb_hint}"
        f"{history_hint}"
        f"\n\nCURRENT_COMMAND:\n{user_command}"
    )


class ActionPlanner:
    def __init__(self, ollama: OllamaClient, retriever: KnowledgeBaseRetriever | None = None) -> None:
        self.ollama = ollama
        self.retriever = retriever
        self.tool_selector = ToolSelector()

    @staticmethod
    def _attach_goal_task_graph(action_plan: dict[str, Any], user_command: str) -> dict[str, Any]:
        return enrich_action_plan_with_goal_graph(action_plan=action_plan, user_command=user_command)

    @staticmethod
    def _is_count_intent(command_text: str) -> bool:
        """Detect commands that ask for numeric totals, even if phrased with 'identifica'."""
        count_keywords = (
            "cate",
            "numar",
            "numarul",
            "count",
            "how many",
            "total",
        )
        return any(keyword in command_text for keyword in count_keywords)

    @staticmethod
    def _requested_color_index(command_text: str) -> int | None:
        """Map natural language color mentions to AutoCAD color index when possible."""
        red_terms = ("rosu", "roșu", "rosie", "roșie", "red")
        if any(term in command_text for term in red_terms):
            return 1
        return None

    @staticmethod
    def _effective_color_index(entity: dict[str, Any], layer_colors: dict[str, int]) -> int | None:
        """Resolve effective color for entities that use BYLAYER/BYBLOCK style values."""
        color_value = entity.get("color_index")
        if isinstance(color_value, int):
            if color_value == 256:
                layer_name = entity.get("layer")
                if isinstance(layer_name, str):
                    return layer_colors.get(layer_name)
                return None
            if color_value == 0:
                # BYBLOCK cannot be resolved reliably here without block ownership context.
                return None
            return color_value
        return None

    @staticmethod
    def _build_identification_plan(context_payload: dict[str, Any], user_command: str) -> dict[str, Any]:
        selector = ToolSelector()
        selected_calls = selector.select(user_command, context_payload)
        if not selected_calls:
            return {
                "schema_version": context_payload.get("schema_version", "1.0.0"),
                "request_id": context_payload.get("request_id", "unknown"),
                "summary": "Comanda este prea ambigua pentru generarea unui plan sigur.",
                "needs_clarification": True,
                "clarification_question": "Te rog clarifica exact ce tip de obiecte vrei să identifici în desen.",
                "actions": [],
            }

        actions = []
        for index, call in enumerate(selected_calls, start=1):
            actions.append(
                {
                    "id": f"action-{index}",
                    "type": call.tool,
                    "args": call.args,
                }
            )

        return {
            "schema_version": context_payload.get("schema_version", "1.0.0"),
            "request_id": context_payload.get("request_id", "unknown"),
            "summary": "Identific obiectele existente în desen prin căutare de tipuri de entități.",
            "needs_clarification": False,
            "actions": actions,
        }

    @staticmethod
    def _build_display_plan(context_payload: dict[str, Any], user_command: str) -> dict[str, Any] | None:
        """Handle display/reporting commands like 'Afiseaza numarul de blocuri'"""
        command_text = (user_command or "").strip().lower()
        has_display_intent = any(
            keyword in command_text
            for keyword in ("afiseaza", "display", "arata", "show", "rezumat", "summary")
        )
        has_count_intent = ActionPlanner._is_count_intent(command_text)
        if not (has_display_intent or has_count_intent):
            return None

        layer_colors: dict[str, int] = {}
        drawing = context_payload.get("drawing", {})
        if isinstance(drawing, dict):
            for layer in drawing.get("layers", []):
                if not isinstance(layer, dict):
                    continue
                layer_name = layer.get("name")
                layer_color = layer.get("color_index")
                if isinstance(layer_name, str) and isinstance(layer_color, int):
                    layer_colors[layer_name] = layer_color

        requested_color_index = ActionPlanner._requested_color_index(command_text)
        
        # Display block count
        if any(keyword in command_text for keyword in ("bloc", "block", "blocuri", "blocks")):
            block_count = len(context_payload.get("blocks", []))
            summary = f"Sunt {block_count} blocuri în desenul '{context_payload.get('drawing', {}).get('name', 'necunoscut')}'."
            return {
                "schema_version": context_payload.get("schema_version", "1.0.0"),
                "request_id": context_payload.get("request_id", "unknown"),
                "summary": summary,
                "needs_clarification": False,
                "actions": [],  # Display is informational, no CAD action needed
            }
        
        # Display text count
        if any(keyword in command_text for keyword in ("text", "texte", "texts", "mtext", "txt")):
            texts = context_payload.get("texts", [])
            if requested_color_index is None:
                text_count = len(texts)
                summary = f"Sunt {text_count} texte în desenul '{context_payload.get('drawing', {}).get('name', 'necunoscut')}'."
            else:
                text_count = 0
                unresolved_color_count = 0
                for text_entity in texts:
                    if not isinstance(text_entity, dict):
                        continue
                    effective_color = ActionPlanner._effective_color_index(text_entity, layer_colors)
                    if effective_color == requested_color_index:
                        text_count += 1
                    elif effective_color is None:
                        unresolved_color_count += 1
                summary = (
                    f"Sunt {text_count} texte de culoare roșie în desenul "
                    f"'{context_payload.get('drawing', {}).get('name', 'necunoscut')}'."
                )
                if unresolved_color_count > 0:
                    summary += (
                        f" {unresolved_color_count} texte au culoare nerezolvabilă "
                        "(de ex. BYBLOCK) în contextul curent."
                    )
            return {
                "schema_version": context_payload.get("schema_version", "1.0.0"),
                "request_id": context_payload.get("request_id", "unknown"),
                "summary": summary,
                "needs_clarification": False,
                "actions": [],
            }
        
        # Display line count
        if any(keyword in command_text for keyword in ("linie", "line", "linii", "lines")):
            line_count = len(context_payload.get("lines", []))
            summary = f"Sunt {line_count} linii în desenul '{context_payload.get('drawing', {}).get('name', 'necunoscut')}'."
            return {
                "schema_version": context_payload.get("schema_version", "1.0.0"),
                "request_id": context_payload.get("request_id", "unknown"),
                "summary": summary,
                "needs_clarification": False,
                "actions": [],
            }
        
        # Display polyline count
        if any(keyword in command_text for keyword in ("polilinie", "polyline", "polilinii", "polylines")):
            polyline_count = len(context_payload.get("polylines", []))
            summary = f"Sunt {polyline_count} polilinii în desenul '{context_payload.get('drawing', {}).get('name', 'necunoscut')}'."
            return {
                "schema_version": context_payload.get("schema_version", "1.0.0"),
                "request_id": context_payload.get("request_id", "unknown"),
                "summary": summary,
                "needs_clarification": False,
                "actions": [],
            }
        
        # Display all counts
        if has_display_intent or has_count_intent:
            counts = {
                "blocks": len(context_payload.get("blocks", [])),
                "texts": len(context_payload.get("texts", [])),
                "lines": len(context_payload.get("lines", [])),
                "polylines": len(context_payload.get("polylines", [])),
            }
            summary = f"Desenul '{context_payload.get('drawing', {}).get('name', 'necunoscut')}' conține: {counts['blocks']} blocuri, {counts['texts']} texte, {counts['lines']} linii, {counts['polylines']} polilinii."
            return {
                "schema_version": context_payload.get("schema_version", "1.0.0"),
                "request_id": context_payload.get("request_id", "unknown"),
                "summary": summary,
                "needs_clarification": False,
                "actions": [],
            }
        
        return None

    @staticmethod
    def _normalize_action(action: Any, index: int) -> dict[str, Any] | None:
        if not isinstance(action, dict):
            return None

        action_type = action.get("type")
        if action_type not in ALLOWED_ACTION_TYPES:
            return None

        args = action.get("args")
        if not isinstance(args, dict):
            return None

        normalized_args: dict[str, Any] = {}
        if action_type == "find_entities":
            entity_type = args.get("entity_type")
            if entity_type not in {"block", "text", "line", "polyline"}:
                return None
            normalized_args["entity_type"] = entity_type
            for key in ("layer", "name", "text_contains"):
                value = args.get(key)
                if isinstance(value, str) and value.strip():
                    normalized_args[key] = value
        elif action_type == "insert_block":
            name = args.get("name")
            position = args.get("position")
            if not isinstance(name, str) or not name.strip():
                return None
            if not isinstance(position, dict):
                return None
            x_value = position.get("x")
            y_value = position.get("y")
            if not isinstance(x_value, (int, float)) or not isinstance(y_value, (int, float)):
                return None
            normalized_args["name"] = name
            normalized_args["position"] = {"x": x_value, "y": y_value}
            for key in ("layer", "rotation_deg", "scale"):
                if key in args:
                    normalized_args[key] = args[key]
        elif action_type == "create_polyline":
            vertices = args.get("vertices")
            if not isinstance(vertices, list) or len(vertices) < 2:
                return None
            normalized_vertices = []
            valid = True
            for vertex in vertices:
                if not isinstance(vertex, dict):
                    valid = False
                    break
                x_value = vertex.get("x")
                y_value = vertex.get("y")
                if not isinstance(x_value, (int, float)) or not isinstance(y_value, (int, float)):
                    valid = False
                    break
                normalized_vertices.append({"x": x_value, "y": y_value})
            if not valid:
                return None
            normalized_args["vertices"] = normalized_vertices
            for key in ("layer", "closed"):
                if key in args:
                    normalized_args[key] = args[key]
        elif action_type == "update_attribute":
            target_handle = args.get("target_handle")
            tag = args.get("tag")
            value = args.get("value")
            if not isinstance(target_handle, str) or not target_handle.strip():
                return None
            if not isinstance(tag, str) or not tag.strip():
                return None
            normalized_args["target_handle"] = target_handle
            normalized_args["tag"] = tag
            normalized_args["value"] = value if isinstance(value, str) else str(value)

        action_id = action.get("id")
        if not isinstance(action_id, str) or not action_id.strip():
            action_id = f"action-{index + 1}"

        normalized_action: dict[str, Any] = {
            "id": action_id,
            "type": action_type,
            "args": normalized_args,
        }
        reason = action.get("reason")
        if isinstance(reason, str) and reason.strip():
            normalized_action["reason"] = reason
        return normalized_action

    @staticmethod
    def _sanitize_action_plan(parsed: dict[str, Any]) -> dict[str, Any]:
        sanitized = {key: value for key, value in parsed.items() if key in ALLOWED_ACTION_PLAN_KEYS}

        if not isinstance(sanitized.get("schema_version"), str) or not sanitized["schema_version"].strip():
            sanitized["schema_version"] = "1.0.0"

        if not isinstance(sanitized.get("request_id"), str) or not sanitized["request_id"].strip():
            sanitized["request_id"] = "unknown"

        if not isinstance(sanitized.get("summary"), str) or not sanitized["summary"].strip():
            sanitized["summary"] = "Summary unavailable."

        if not isinstance(sanitized.get("needs_clarification"), bool):
            sanitized["needs_clarification"] = True

        if "clarification_question" in sanitized and not isinstance(sanitized["clarification_question"], str):
            sanitized.pop("clarification_question")

        actions = sanitized.get("actions")
        normalized_actions: list[dict[str, Any]] = []
        if isinstance(actions, list):
            for index, action in enumerate(actions):
                normalized = ActionPlanner._normalize_action(action, index)
                if normalized is not None:
                    normalized_actions.append(normalized)

        sanitized["actions"] = normalized_actions
        if sanitized["needs_clarification"]:
            sanitized["actions"] = []
            if "clarification_question" not in sanitized or not isinstance(sanitized["clarification_question"], str):
                sanitized["clarification_question"] = "Te rog clarifica exact actiunea dorita."

        return sanitized

    async def plan(self, context_payload: dict[str, Any], user_command: str, messages: list[dict[str, Any]] | None = None) -> PlanResult:
        # Deterministic routing for count/reporting requests avoids LLM drift to find_entities.
        display_plan = self._build_display_plan(context_payload, user_command)
        if display_plan is not None and display_plan.get("needs_clarification") is False:
            return PlanResult(
                action_plan=self._attach_goal_task_graph(display_plan, user_command),
                raw_response='{"source":"deterministic_display_plan"}',
                retrieved_knowledge=[],
            )

        # Deterministic selector for obvious identify intents.
        selected_calls = self.tool_selector.select(user_command, context_payload)
        if selected_calls:
            identification_plan = self._build_identification_plan(context_payload, user_command)
            if identification_plan.get("needs_clarification") is False:
                return PlanResult(
                    action_plan=self._attach_goal_task_graph(identification_plan, user_command),
                    raw_response='{"source":"deterministic_tool_selector"}',
                    retrieved_knowledge=[],
                )

        rag_context = ""
        retrieved_knowledge: list[dict[str, Any]] = []
        if self.retriever is not None:
            rag_context, retrieved_knowledge = self.retriever.build_context(
                query=user_command,
                top_k=4,
                max_chars=3200,
            )

        prompt = build_prompt(
            context_payload=context_payload,
            user_command=user_command,
            messages=messages,
            rag_context=rag_context,
        )
        raw = await self.ollama.generate_json(prompt)
        parsed = _extract_json_object(raw)
        sanitized = self._sanitize_action_plan(parsed)

        if sanitized.get("actions") == []:
            # Try display plan first (for "Afiseaza..." type commands)
            display_plan = self._build_display_plan(context_payload, user_command)
            if display_plan is not None and display_plan.get("needs_clarification") is False:
                sanitized = display_plan
            else:
                # Fall back to identification plan
                identification_plan = self._build_identification_plan(context_payload, user_command)
                if identification_plan.get("needs_clarification") is False:
                    sanitized = identification_plan

        return PlanResult(
            action_plan=self._attach_goal_task_graph(sanitized, user_command),
            raw_response=raw,
            retrieved_knowledge=retrieved_knowledge,
        )
