from __future__ import annotations

from typing import Any


class TaskGraphExecutionError(ValueError):
    """Raised when task graph structure is invalid for execution."""


def _normalize_nodes(task_graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_nodes = task_graph.get("nodes", [])
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise TaskGraphExecutionError("task_graph.nodes must contain at least one node.")

    nodes: dict[str, dict[str, Any]] = {}
    for node in raw_nodes:
        if not isinstance(node, dict):
            raise TaskGraphExecutionError("Each node in task_graph.nodes must be an object.")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id.strip():
            raise TaskGraphExecutionError("Each task node must define a non-empty id.")
        if node_id in nodes:
            raise TaskGraphExecutionError(f"Duplicate task node id: {node_id}")
        nodes[node_id] = node
    return nodes


def _extract_dependencies(
    task_graph: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    dependencies: dict[str, set[str]] = {}
    for node_id, node in nodes.items():
        depends_on_raw = node.get("depends_on", [])
        if not isinstance(depends_on_raw, list):
            raise TaskGraphExecutionError(f"Node {node_id} must have depends_on as a list.")
        dependencies[node_id] = set()
        for dep_id in depends_on_raw:
            if not isinstance(dep_id, str) or not dep_id.strip():
                raise TaskGraphExecutionError(f"Node {node_id} has invalid dependency id.")
            dependencies[node_id].add(dep_id)

    raw_edges = task_graph.get("edges", [])
    if not isinstance(raw_edges, list):
        raise TaskGraphExecutionError("task_graph.edges must be an array.")

    for edge in raw_edges:
        if not isinstance(edge, dict):
            raise TaskGraphExecutionError("Each edge in task_graph.edges must be an object.")
        if edge.get("type") != "depends_on":
            continue
        from_id = edge.get("from")
        to_id = edge.get("to")
        if not isinstance(from_id, str) or not isinstance(to_id, str):
            raise TaskGraphExecutionError("Each depends_on edge must define string from and to.")
        if to_id not in dependencies:
            raise TaskGraphExecutionError(f"Edge points to unknown task node: {to_id}")
        dependencies[to_id].add(from_id)

    for node_id, dep_ids in dependencies.items():
        for dep_id in dep_ids:
            if dep_id not in nodes:
                raise TaskGraphExecutionError(
                    f"Node {node_id} depends on unknown task node: {dep_id}"
                )

    return dependencies


def simulate_task_graph_execution(
    action_plan: dict[str, Any],
    fail_node_ids: set[str] | None = None,
) -> dict[str, Any]:
    task_graph = action_plan.get("task_graph")
    if not isinstance(task_graph, dict):
        raise TaskGraphExecutionError("action_plan.task_graph is required for simulation.")

    fail_node_ids = fail_node_ids or set()
    nodes = _normalize_nodes(task_graph)
    dependencies = _extract_dependencies(task_graph, nodes)

    incoming_count: dict[str, int] = {node_id: len(dep_ids) for node_id, dep_ids in dependencies.items()}
    dependents: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for node_id, dep_ids in dependencies.items():
        for dep_id in dep_ids:
            dependents[dep_id].add(node_id)

    ready = sorted([node_id for node_id, count in incoming_count.items() if count == 0])
    if not ready:
        raise TaskGraphExecutionError("Task graph has no entry node with zero dependencies.")

    status_by_node: dict[str, str] = {node_id: "pending" for node_id in nodes}
    skipped_by_failed_dep: dict[str, list[str]] = {}
    execution_order: list[str] = []

    processed = 0
    while ready:
        node_id = ready.pop(0)
        processed += 1
        execution_order.append(node_id)

        failed_dependencies = [dep for dep in sorted(dependencies[node_id]) if status_by_node.get(dep) == "failed"]
        if failed_dependencies:
            status_by_node[node_id] = "pending"
            skipped_by_failed_dep[node_id] = failed_dependencies
        elif node_id in fail_node_ids:
            status_by_node[node_id] = "failed"
        else:
            status_by_node[node_id] = "done"

        for dependent_id in sorted(dependents[node_id]):
            incoming_count[dependent_id] -= 1
            if incoming_count[dependent_id] == 0:
                ready.append(dependent_id)
        ready.sort()

    if processed != len(nodes):
        remaining_nodes = [node_id for node_id, count in incoming_count.items() if count > 0]
        raise TaskGraphExecutionError(
            "Task graph contains a cycle or unresolved dependency chain: "
            + ", ".join(sorted(remaining_nodes))
        )

    failed_nodes = sorted([node_id for node_id, status in status_by_node.items() if status == "failed"])
    overall_status = "failed" if failed_nodes else "done"

    node_results: list[dict[str, Any]] = []
    for node_id in execution_order:
        node = nodes[node_id]
        result = {
            "id": node_id,
            "title": node.get("title"),
            "kind": node.get("kind"),
            "status": status_by_node[node_id],
            "action_id": node.get("action_id"),
            "depends_on": sorted(list(dependencies[node_id])),
        }
        if node_id in skipped_by_failed_dep:
            result["skipped_due_to_failed_dependencies"] = skipped_by_failed_dep[node_id]
        node_results.append(result)

    return {
        "status": overall_status,
        "graph_version": task_graph.get("version", "unknown"),
        "execution_order": execution_order,
        "failed_nodes": failed_nodes,
        "node_results": node_results,
    }
