from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from schema_validation import SchemaStore


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str


def _load_latest_request(payload_dir: Path) -> tuple[Path | None, dict[str, Any] | None]:
    files = sorted(payload_dir.glob("*_request.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None, None
    latest = files[0]
    return latest, json.loads(latest.read_text(encoding="utf-8"))


def _response_exists(payload_dir: Path, request_payload_name: str, request_id: str) -> bool:
    # Prefer matching by request_id in filename because request and response timestamps differ.
    expected_fragment = f"_{request_id}_response.json"
    for response_file in payload_dir.glob("*_response.json"):
        if expected_fragment in response_file.name:
            return True

    # Fallback by same prefix replacement (legacy behavior).
    return (payload_dir / request_payload_name.replace("_request.json", "_response.json")).exists()


def _entity_required_like_counts(context: dict[str, Any]) -> dict[str, int]:
    issues = {"blocks": 0, "texts": 0, "lines": 0, "polylines": 0}

    for item in context.get("blocks", []):
        ok = (
            isinstance(item, dict)
            and all(k in item for k in ("handle", "name", "layer", "position"))
            and isinstance(item.get("position"), dict)
            and all(k in item.get("position", {}) for k in ("x", "y"))
        )
        if not ok:
            issues["blocks"] += 1

    for item in context.get("texts", []):
        ok = (
            isinstance(item, dict)
            and all(k in item for k in ("handle", "value", "layer", "position", "height"))
            and isinstance(item.get("position"), dict)
            and all(k in item.get("position", {}) for k in ("x", "y"))
        )
        if not ok:
            issues["texts"] += 1

    for item in context.get("lines", []):
        ok = (
            isinstance(item, dict)
            and all(k in item for k in ("handle", "layer", "start", "end"))
            and isinstance(item.get("start"), dict)
            and isinstance(item.get("end"), dict)
            and all(k in item.get("start", {}) for k in ("x", "y"))
            and all(k in item.get("end", {}) for k in ("x", "y"))
        )
        if not ok:
            issues["lines"] += 1

    for item in context.get("polylines", []):
        ok = (
            isinstance(item, dict)
            and all(k in item for k in ("handle", "layer", "closed", "vertices"))
            and isinstance(item.get("vertices"), list)
            and len(item.get("vertices", [])) >= 2
        )
        if not ok:
            issues["polylines"] += 1

    return issues


def _check_events(log_files: list[Path], request_id: str) -> tuple[bool, bool]:
    seen_input = False
    seen_validation = False

    for log_file in log_files:
        if not log_file.exists():
            continue

        with log_file.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if event.get("request_id") != request_id:
                    continue

                name = event.get("event")
                if name in {"chat_input_received", "input_received"}:
                    seen_input = True
                if name == "validation_passed":
                    seen_validation = True

    return seen_input, seen_validation


def run() -> int:
    base_dir = Path(__file__).resolve().parent
    payload_dir = base_dir / "payloads"
    schema_dir = base_dir.parent / "shared" / "schemas"
    event_logs = [
        base_dir / "logs" / "events.jsonl",
        base_dir / "logs" / "events.json",
    ]

    req_path, req_payload = _load_latest_request(payload_dir)
    if req_path is None or req_payload is None:
        print("FAIL: no request payload found in ai-server/payloads")
        return 1

    context = req_payload.get("context")
    if not isinstance(context, dict):
        print("FAIL: latest request has no valid context object")
        return 1

    request_id = str(req_payload.get("request_id", "")).strip()

    checks: list[CheckResult] = []

    checks.append(
        CheckResult(
            name="request_id_present",
            passed=bool(request_id),
            details=request_id or "missing",
        )
    )

    schema_issues = SchemaStore(schema_dir).validate("dwg-context.schema.json", context)
    checks.append(
        CheckResult(
            name="context_schema_valid",
            passed=len(schema_issues) == 0,
            details=f"issues={len(schema_issues)}",
        )
    )

    drawing_name = context.get("drawing", {}).get("name") if isinstance(context.get("drawing"), dict) else None
    checks.append(
        CheckResult(
            name="drawing_name_present",
            passed=bool(drawing_name),
            details=str(drawing_name),
        )
    )

    counts = {
        "blocks": len(context.get("blocks", [])),
        "texts": len(context.get("texts", [])),
        "lines": len(context.get("lines", [])),
        "polylines": len(context.get("polylines", [])),
    }
    checks.append(
        CheckResult(
            name="entities_non_empty",
            passed=any(value > 0 for value in counts.values()),
            details=str(counts),
        )
    )

    required_like_issues = _entity_required_like_counts(context)
    checks.append(
        CheckResult(
            name="entity_required_fields_complete",
            passed=all(value == 0 for value in required_like_issues.values()),
            details=str(required_like_issues),
        )
    )

    checks.append(
        CheckResult(
            name="response_payload_exists",
            passed=_response_exists(payload_dir, req_path.name, request_id),
            details=req_path.name,
        )
    )

    seen_input, seen_validation = _check_events(event_logs, request_id)
    checks.append(CheckResult("server_logged_input", seen_input, "events_files=events.jsonl,events.json"))
    checks.append(CheckResult("server_validation_passed", seen_validation, "events_files=events.jsonl,events.json"))

    print("=== CURRENT DRAWING INGESTION AUDIT ===")
    print(f"payload_file: {req_path.name}")
    print(f"request_id: {request_id}")
    print(f"drawing: {drawing_name}")
    print(f"counts: {counts}")

    if schema_issues:
        print("schema_issues:")
        for issue in schema_issues[:10]:
            print(f"  - {issue.path}: {issue.message}")

    print("checks:")
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  - {status} {check.name}: {check.details}")

    failed = [c for c in checks if not c.passed]
    if failed:
        print(f"result: FAIL ({len(failed)} checks failed)")
        return 1

    print("result: PASS (all checks passed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
