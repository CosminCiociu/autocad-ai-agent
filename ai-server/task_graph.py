from __future__ import annotations

from typing import Any


def _goal_title(action_plan: dict[str, Any], user_command: str) -> str:
    summary = action_plan.get("summary")
    if isinstance(summary, str) and summary.strip():
        return summary.strip()
    command = (user_command or "").strip()
    if command:
        return command
    return "Generate safe CAD plan"


def enrich_action_plan_with_goal_graph(
    action_plan: dict[str, Any],
    user_command: str,
) -> dict[str, Any]:
    """Attach Milestone 3 skeleton fields while preserving existing action-plan contract."""
    enriched = dict(action_plan)
    actions = enriched.get("actions", [])
    if not isinstance(actions, list):
        actions = []

    needs_clarification = bool(enriched.get("needs_clarification"))
    goal_title = _goal_title(enriched, user_command)

    subgoals: list[dict[str, Any]] = [
        {
            "id": "goal-intent",
            "title": "Interpret intent and scope",
            "status": "pending",
            "kind": "analysis",
        }
    ]

    task_nodes: list[dict[str, Any]] = [
        {
            "id": "task-intent",
            "title": "Parse intent and contextual constraints",
            "kind": "analysis",
            "status": "pending",
            "depends_on": [],
        }
    ]
    edges: list[dict[str, str]] = []

    previous_task_id = "task-intent"

    if needs_clarification:
        subgoals.append(
            {
                "id": "goal-clarify",
                "title": "Request clarification before execution",
                "status": "pending",
                "kind": "clarification",
            }
        )
        task_nodes.append(
            {
                "id": "task-clarify",
                "title": "Ask clarification question",
                "kind": "clarification",
                "status": "pending",
                "depends_on": [previous_task_id],
            }
        )
        edges.append({"from": previous_task_id, "to": "task-clarify", "type": "depends_on"})
        previous_task_id = "task-clarify"
    elif actions:
        for index, action in enumerate(actions, start=1):
            action_id = action.get("id") if isinstance(action, dict) else None
            action_type = action.get("type") if isinstance(action, dict) else None

            normalized_action_id = (
                action_id
                if isinstance(action_id, str) and action_id.strip()
                else f"action-{index}"
            )
            normalized_action_type = (
                action_type if isinstance(action_type, str) and action_type.strip() else "unknown"
            )

            goal_id = f"goal-action-{index}"
            task_id = f"task-action-{index}"

            subgoals.append(
                {
                    "id": goal_id,
                    "title": f"Execute {normalized_action_type}",
                    "status": "pending",
                    "kind": "execution",
                    "action_id": normalized_action_id,
                }
            )
            task_nodes.append(
                {
                    "id": task_id,
                    "title": f"Run action {normalized_action_type}",
                    "kind": "action",
                    "status": "pending",
                    "action_id": normalized_action_id,
                    "depends_on": [previous_task_id],
                }
            )
            edges.append({"from": previous_task_id, "to": task_id, "type": "depends_on"})
            previous_task_id = task_id

        subgoals.append(
            {
                "id": "goal-verify",
                "title": "Verify post-conditions",
                "status": "pending",
                "kind": "verification",
            }
        )
        task_nodes.append(
            {
                "id": "task-verify",
                "title": "Validate execution result against context",
                "kind": "verification",
                "status": "pending",
                "depends_on": [previous_task_id],
            }
        )
        edges.append({"from": previous_task_id, "to": "task-verify", "type": "depends_on"})
        previous_task_id = "task-verify"
    else:
        subgoals.append(
            {
                "id": "goal-report",
                "title": "Produce informational response",
                "status": "pending",
                "kind": "report",
            }
        )
        task_nodes.append(
            {
                "id": "task-report",
                "title": "Return summary with no CAD execution",
                "kind": "report",
                "status": "pending",
                "depends_on": [previous_task_id],
            }
        )
        edges.append({"from": previous_task_id, "to": "task-report", "type": "depends_on"})
        previous_task_id = "task-report"

    enriched["goal_plan"] = {
        "version": "0.1",
        "goal": goal_title,
        "status": "pending",
        "subgoals": subgoals,
    }
    enriched["task_graph"] = {
        "version": "0.1",
        "entrypoints": ["task-intent"],
        "terminal_nodes": [previous_task_id],
        "execution_order": [node["id"] for node in task_nodes],
        "nodes": task_nodes,
        "edges": edges,
    }

    return enriched
