from __future__ import annotations

from typing import Any


def _get_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload.get(key)
    return None


def _action_report_by_id(execution_report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(execution_report, dict):
        return {}

    raw_actions = _get_value(execution_report, "actions", "Actions")
    if not isinstance(raw_actions, list):
        return {}

    reports: dict[str, dict[str, Any]] = {}
    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        action_id = _get_value(item, "action_id", "ActionId", "id", "Id")
        if isinstance(action_id, str) and action_id.strip():
            reports[action_id] = item
    return reports


def _block_by_handle(context_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    blocks = context_payload.get("blocks", [])
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(blocks, list):
        return result

    for block in blocks:
        if not isinstance(block, dict):
            continue
        handle = block.get("handle")
        if isinstance(handle, str) and handle.strip():
            result[handle] = block
    return result


def _extract_attr_value(block: dict[str, Any], tag: str) -> str | None:
    attributes = block.get("attributes", [])
    if not isinstance(attributes, list):
        return None

    for item in attributes:
        if not isinstance(item, dict):
            continue
        attr_tag = item.get("tag")
        if not isinstance(attr_tag, str):
            continue
        if attr_tag.strip().lower() == tag.strip().lower():
            value = item.get("value")
            return value if isinstance(value, str) else str(value)
    return None


def verify_execution(
    action_plan: dict[str, Any],
    context_before: dict[str, Any],
    context_after: dict[str, Any],
    execution_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    actions = action_plan.get("actions", [])
    if not isinstance(actions, list):
        actions = []

    request_id = str(action_plan.get("request_id", "unknown"))

    before_blocks = _block_by_handle(context_before)
    after_blocks = _block_by_handle(context_after)
    before_handles = set(before_blocks.keys())
    after_handles = set(after_blocks.keys())

    reports_by_id = _action_report_by_id(execution_report)

    node_results: list[dict[str, Any]] = []
    has_failure = False

    for action in actions:
        if not isinstance(action, dict):
            continue

        action_id = action.get("id")
        action_type = action.get("type")
        args = action.get("args", {})

        if not isinstance(action_id, str) or not isinstance(action_type, str) or not isinstance(args, dict):
            continue

        if action_type not in {"insert_block", "update_attribute"}:
            continue

        report_item = reports_by_id.get(action_id, {})
        report_success = _get_value(report_item, "success", "Success")
        if isinstance(report_success, bool) and report_success is False:
            has_failure = True
            node_results.append(
                {
                    "action_id": action_id,
                    "action_type": action_type,
                    "status": "failed",
                    "code": "EXECUTION_FAILED",
                    "message": "Execution report marks this action as failed.",
                }
            )
            continue

        if action_type == "insert_block":
            name = args.get("name")
            position = args.get("position")

            inserted_handle = _get_value(report_item, "result_handle", "ResultHandle")
            if isinstance(inserted_handle, str) and inserted_handle in after_blocks:
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "done",
                        "code": "INSERT_VERIFIED",
                        "message": f"Inserted block handle '{inserted_handle}' exists in post-context.",
                    }
                )
                continue

            created_handles = sorted(after_handles - before_handles)
            candidate_found = False
            for handle in created_handles:
                block = after_blocks.get(handle, {})
                if not isinstance(block, dict):
                    continue

                if isinstance(name, str) and name.strip():
                    block_name = block.get("name")
                    if not isinstance(block_name, str) or block_name.strip().lower() != name.strip().lower():
                        continue

                if isinstance(position, dict):
                    px = position.get("x")
                    py = position.get("y")
                    after_position = block.get("position", {})
                    ax = after_position.get("x") if isinstance(after_position, dict) else None
                    ay = after_position.get("y") if isinstance(after_position, dict) else None
                    if isinstance(px, (int, float)) and isinstance(py, (int, float)):
                        if not (isinstance(ax, (int, float)) and isinstance(ay, (int, float))):
                            continue
                        if abs(float(px) - float(ax)) > 1e-6 or abs(float(py) - float(ay)) > 1e-6:
                            continue

                candidate_found = True
                break

            if candidate_found:
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "done",
                        "code": "INSERT_VERIFIED",
                        "message": "A matching inserted block was found in post-context.",
                    }
                )
            else:
                has_failure = True
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "failed",
                        "code": "INSERT_NOT_FOUND",
                        "message": "Could not verify a newly inserted block in post-context.",
                    }
                )

        elif action_type == "update_attribute":
            target_handle = args.get("target_handle")
            tag = args.get("tag")
            expected_value = args.get("value")

            if not isinstance(target_handle, str) or not isinstance(tag, str):
                has_failure = True
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "failed",
                        "code": "VERIFY_ARGUMENT_INVALID",
                        "message": "target_handle/tag missing for verification.",
                    }
                )
                continue

            after_block = after_blocks.get(target_handle)
            if not isinstance(after_block, dict):
                has_failure = True
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "failed",
                        "code": "TARGET_NOT_FOUND",
                        "message": f"Target block '{target_handle}' missing in post-context.",
                    }
                )
                continue

            actual_value = _extract_attr_value(after_block, tag)
            expected_text = expected_value if isinstance(expected_value, str) else str(expected_value)
            if actual_value is not None and actual_value == expected_text:
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "done",
                        "code": "ATTRIBUTE_VERIFIED",
                        "message": f"Attribute '{tag}' has expected value in post-context.",
                    }
                )
            else:
                has_failure = True
                node_results.append(
                    {
                        "action_id": action_id,
                        "action_type": action_type,
                        "status": "failed",
                        "code": "ATTRIBUTE_MISMATCH",
                        "message": f"Attribute '{tag}' does not match expected value.",
                    }
                )

    return {
        "request_id": request_id,
        "status": "failed" if has_failure else "done",
        "verified_action_types": ["insert_block", "update_attribute"],
        "node_results": node_results,
    }
