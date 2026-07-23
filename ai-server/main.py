from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from observability import ObservabilityStore
from ollama_client import OllamaClient
from planner import ActionPlanner
from semantic_validation import SemanticValidator
from schema_validation import SchemaStore


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = BASE_DIR.parent / "shared" / "schemas"
PAYLOADS_DIR = BASE_DIR / "payloads"

CONTEXT_SCHEMA = "dwg-context.schema.json"
ACTION_SCHEMA = "action-plan.schema.json"

# Create payloads directory if it doesn't exist
PAYLOADS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="AutoCAD AI Server", version="0.1.0")
schemas = SchemaStore(SCHEMA_DIR)
planner = ActionPlanner(ollama=OllamaClient())
semantic_validator = SemanticValidator()
observability = ObservabilityStore(BASE_DIR)


def build_error(
    request_id: str,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "request_id": request_id,
        "error": {"code": code, "message": message},
    }
    if details:
        payload["error"]["details"] = details
    return payload


def save_payload(payload_type: str, request_id: str, payload: Any) -> None:
    """Save incoming or outgoing payloads to disk for audit trail."""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]
        filename = f"{timestamp}_{request_id}_{payload_type}.json"
        filepath = PAYLOADS_DIR / filename
        
        import json
        with open(filepath, "w") as f:
            json.dump(payload, f, indent=2, default=str)
    except Exception as e:
        # Log but don't fail the request
        observability.log_event(
            event="payload_save_error",
            request_id=request_id,
            data={"error": str(e), "type": payload_type},
        )


def resolve_error_code(details: list[dict[str, Any]]) -> str:
    codes = {str(item.get("code", "")) for item in details if item.get("code")}
    if len(codes) == 1:
        return next(iter(codes))
    return "ACTION_ARGUMENT_INVALID"


def summarize_context(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": payload.get("schema_version"),
        "drawing": payload.get("drawing", {}).get("name"),
        "counts": {
            "blocks": len(payload.get("blocks", [])),
            "texts": len(payload.get("texts", [])),
            "lines": len(payload.get("lines", [])),
            "polylines": len(payload.get("polylines", [])),
        },
    }


def extract_audit_handles(action_plan: dict[str, Any]) -> list[str]:
    handles: set[str] = set()
    for action in action_plan.get("actions", []):
        args = action.get("args", {}) if isinstance(action, dict) else {}
        if isinstance(args, dict):
            handle = args.get("target_handle")
            if isinstance(handle, str) and handle.strip():
                handles.add(handle)
    return sorted(handles)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/replay/{request_id}")
def replay(request_id: str) -> JSONResponse:
    payload = observability.load_replay(request_id)
    if payload is None:
        return JSONResponse(
            status_code=404,
            content=build_error(
                request_id=request_id,
                code="INTERNAL_ERROR",
                message="Replay not found for request_id.",
            ),
        )
    return JSONResponse(status_code=200, content=payload)


def build_safe_clarification_plan(
    request_id: str,
    schema_version: str,
    question: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "request_id": request_id,
        "summary": summary,
        "needs_clarification": True,
        "clarification_question": question,
        "actions": [],
    }


@app.post("/validate/context")
async def validate_context(request: Request) -> JSONResponse:
    payload = await request.json()
    request_id = str(payload.get("request_id", "unknown"))
    issues = schemas.validate(CONTEXT_SCHEMA, payload)

    if issues:
        details = [{"path": i.path, "message": i.message} for i in issues]
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Context payload failed schema validation.",
                details=details,
            ),
        )

    return JSONResponse(status_code=200, content={"request_id": request_id, "valid": True})


@app.post("/analyze")
async def analyze(request: Request) -> JSONResponse:
    payload = await request.json()
    request_id = str(payload.get("request_id", "")).strip() or f"req-{uuid4()}"
    schema_version = str(payload.get("schema_version", "1.0.0"))
    payload["request_id"] = request_id

    user_command = request.headers.get("x-user-command", "").strip()
    observability.log_event(
        event="input_received",
        request_id=request_id,
        data={
            "user_command": user_command,
            "context_summary": summarize_context(payload),
        },
    )

    context_issues = schemas.validate(CONTEXT_SCHEMA, payload)
    if context_issues:
        details = [{"path": i.path, "message": i.message} for i in context_issues]
        observability.log_event(
            event="context_schema_invalid",
            request_id=request_id,
            data={"details": details},
        )
        observability.save_replay(
            request_id,
            {
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "user_command": user_command,
                "model_raw_response": None,
                "action_plan": None,
                "validation": {"context_schema": details},
                "execution_result": "not_executed_server_side",
            },
        )
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Context payload failed schema validation.",
                details=details,
            ),
        )

    model_raw_response: str | None = None
    if not user_command:
        action_plan = build_safe_clarification_plan(
            request_id=request_id,
            schema_version=schema_version,
            question="Ce actiune vrei sa execut pe desen?",
            summary="Comanda lipsa. Nu execut nimic pana la clarificare.",
        )
        observability.log_event(
            event="clarification_requested",
            request_id=request_id,
            data={"reason": "missing_user_command"},
        )
    else:
        try:
            plan_result = await planner.plan(context_payload=payload, user_command=user_command)
            action_plan = plan_result.action_plan
            model_raw_response = plan_result.raw_response
            observability.log_event(
                event="llm_response_received",
                request_id=request_id,
                data={"raw_response": model_raw_response[:4000]},
            )
        except Exception:
            action_plan = build_safe_clarification_plan(
                request_id=request_id,
                schema_version=schema_version,
                question="Nu am putut genera un plan sigur. Reformuleaza comanda in pasi clari.",
                summary="Model indisponibil sau raspuns invalid. Executie oprita preventiv.",
            )
            observability.log_event(
                event="llm_failure_fallback",
                request_id=request_id,
                data={"reason": "model_unavailable_or_invalid_response"},
            )

    # Enforce request identity and schema version for consistency.
    action_plan["request_id"] = request_id
    action_plan["schema_version"] = schema_version

    if not isinstance(action_plan.get("needs_clarification"), bool):
        action_plan["needs_clarification"] = True

    if action_plan["needs_clarification"]:
        action_plan["actions"] = []
        if not isinstance(action_plan.get("clarification_question"), str) or not action_plan[
            "clarification_question"
        ].strip():
            action_plan["clarification_question"] = "Te rog clarifica exact actiunea dorita."

    action_issues = schemas.validate(ACTION_SCHEMA, action_plan)
    if action_issues:
        details = [{"path": i.path, "message": i.message} for i in action_issues]
        observability.log_event(
            event="action_schema_invalid",
            request_id=request_id,
            data={"details": details},
        )
        observability.save_replay(
            request_id,
            {
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "user_command": user_command,
                "model_raw_response": model_raw_response,
                "action_plan": action_plan,
                "validation": {"action_schema": details},
                "execution_result": "not_executed_server_side",
            },
        )
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Generated action plan failed schema validation.",
                details=details,
            ),
        )

    semantic_issues = semantic_validator.validate(context_payload=payload, action_plan=action_plan)
    if semantic_issues:
        details = [
            {
                "action_id": i.action_id,
                "path": i.path,
                "code": i.code,
                "message": i.message,
            }
            for i in semantic_issues
        ]
        observability.log_event(
            event="semantic_validation_failed",
            request_id=request_id,
            data={"details": details},
        )
        observability.save_replay(
            request_id,
            {
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "user_command": user_command,
                "model_raw_response": model_raw_response,
                "action_plan": action_plan,
                "validation": {"semantic": details},
                "execution_result": "not_executed_server_side",
            },
        )
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code=resolve_error_code(details),
                message="Action plan failed semantic validation.",
                details=details,
            ),
        )

    observability.log_event(
        event="validation_passed",
        request_id=request_id,
        data={
            "action_count": len(action_plan.get("actions", [])),
            "planned_audit_handles": extract_audit_handles(action_plan),
            "execution_result": "not_executed_server_side",
        },
    )
    observability.save_replay(
        request_id,
        {
            "request_id": request_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input": payload,
            "user_command": user_command,
            "model_raw_response": model_raw_response,
            "action_plan": action_plan,
            "validation": {"context_schema": "ok", "action_schema": "ok", "semantic": "ok"},
            "planned_audit_handles": extract_audit_handles(action_plan),
            "execution_result": "not_executed_server_side",
        },
    )

    return JSONResponse(status_code=200, content=action_plan)


@app.post("/chat")
async def chat(request: Request) -> JSONResponse:
    payload = await request.json()
    request_id = str(payload.get("request_id", "")).strip() or f"req-{uuid4()}"
    schema_version = str(payload.get("schema_version", "1.0.0"))
    context_payload = payload.get("context")
    
    # Save incoming request payload
    save_payload("request", request_id, {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "schema_version": schema_version,
        "context": context_payload,
        "messages": payload.get("messages"),
    })
    
    if not isinstance(context_payload, dict):
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Chat payload must include a valid context object.",
            ),
        )

    context_payload["request_id"] = request_id
    context_payload["schema_version"] = schema_version
    messages = payload.get("messages")
    if not isinstance(messages, list):
        messages = []

    user_command = ""
    for entry in reversed(messages):
        if isinstance(entry, dict) and entry.get("role") == "user" and isinstance(entry.get("content"), str):
            user_command = entry["content"].strip()
            if user_command:
                break

    observability.log_event(
        event="chat_input_received",
        request_id=request_id,
        data={
            "message_count": len(messages),
            "user_command_preview": user_command[:200] if user_command else "",
            "context_summary": summarize_context(context_payload),
        },
    )

    context_issues = schemas.validate(CONTEXT_SCHEMA, context_payload)
    if context_issues:
        details = [{"path": i.path, "message": i.message} for i in context_issues]
        observability.log_event(
            event="context_schema_invalid",
            request_id=request_id,
            data={"details": details},
        )
        observability.save_replay(
            request_id,
            {
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "user_command": user_command,
                "model_raw_response": None,
                "assistant_message": None,
                "action_plan": None,
                "validation": {"context_schema": details},
                "execution_result": "not_executed_server_side",
            },
        )
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Context payload failed schema validation.",
                details=details,
            ),
        )

    model_raw_response: str | None = None
    if not user_command:
        action_plan = build_safe_clarification_plan(
            request_id=request_id,
            schema_version=schema_version,
            question="Ce actiune vrei sa execut pe desen?",
            summary="Comanda lipsa. Nu execut nimic pana la clarificare.",
        )
        observability.log_event(
            event="clarification_requested",
            request_id=request_id,
            data={"reason": "missing_user_command"},
        )
    else:
        try:
            plan_result = await planner.plan(context_payload=context_payload, user_command=user_command, messages=messages)
            action_plan = plan_result.action_plan
            model_raw_response = plan_result.raw_response
            observability.log_event(
                event="llm_response_received",
                request_id=request_id,
                data={"raw_response": model_raw_response[:4000]},
            )
        except Exception:
            action_plan = build_safe_clarification_plan(
                request_id=request_id,
                schema_version=schema_version,
                question="Nu am putut genera un plan sigur. Reformuleaza comanda in pasi clari.",
                summary="Model indisponibil sau raspuns invalid. Executie oprita preventiv.",
            )
            observability.log_event(
                event="llm_failure_fallback",
                request_id=request_id,
                data={"reason": "model_unavailable_or_invalid_response"},
            )

    action_plan["request_id"] = request_id
    action_plan["schema_version"] = schema_version

    if not isinstance(action_plan.get("needs_clarification"), bool):
        action_plan["needs_clarification"] = True

    if action_plan["needs_clarification"]:
        action_plan["actions"] = []
        if not isinstance(action_plan.get("clarification_question"), str) or not action_plan["clarification_question"].strip():
            action_plan["clarification_question"] = "Te rog clarifica exact actiunea dorita."

    action_issues = schemas.validate(ACTION_SCHEMA, action_plan)
    if action_issues:
        details = [{"path": i.path, "message": i.message} for i in action_issues]
        observability.log_event(
            event="action_schema_invalid",
            request_id=request_id,
            data={"details": details},
        )
        observability.save_replay(
            request_id,
            {
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "user_command": user_command,
                "model_raw_response": model_raw_response,
                "assistant_message": None,
                "action_plan": action_plan,
                "validation": {"action_schema": details},
                "execution_result": "not_executed_server_side",
            },
        )
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Generated action plan failed schema validation.",
                details=details,
            ),
        )

    semantic_issues = semantic_validator.validate(context_payload=context_payload, action_plan=action_plan)
    if semantic_issues:
        details = [
            {
                "action_id": i.action_id,
                "path": i.path,
                "code": i.code,
                "message": i.message,
            }
            for i in semantic_issues
        ]
        observability.log_event(
            event="semantic_validation_failed",
            request_id=request_id,
            data={"details": details},
        )
        observability.save_replay(
            request_id,
            {
                "request_id": request_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "input": payload,
                "user_command": user_command,
                "model_raw_response": model_raw_response,
                "assistant_message": None,
                "action_plan": action_plan,
                "validation": {"semantic": details},
                "execution_result": "not_executed_server_side",
            },
        )
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code=resolve_error_code(details),
                message="Action plan failed semantic validation.",
                details=details,
            ),
        )

    observability.log_event(
        event="validation_passed",
        request_id=request_id,
        data={
            "action_count": len(action_plan.get("actions", [])),
            "planned_audit_handles": extract_audit_handles(action_plan),
            "execution_result": "not_executed_server_side",
        },
    )
    observability.save_replay(
        request_id,
        {
            "request_id": request_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "input": payload,
            "user_command": user_command,
            "model_raw_response": model_raw_response,
            "assistant_message": action_plan.get("clarification_question") if action_plan.get("needs_clarification") else action_plan.get("summary"),
            "action_plan": action_plan,
            "validation": {"context_schema": "ok", "action_schema": "ok", "semantic": "ok"},
            "planned_audit_handles": extract_audit_handles(action_plan),
            "execution_result": "not_executed_server_side",
        },
    )

    assistant_message = (
        action_plan.get("clarification_question")
        if action_plan.get("needs_clarification")
        else action_plan.get("summary")
    )
    if not isinstance(assistant_message, str) or not assistant_message.strip():
        assistant_message = "Am generat un plan."

    # Save outgoing response payload
    response_content = {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "assistant_message": assistant_message,
        "action_plan": action_plan,
    }
    save_payload("response", request_id, response_content)

    return JSONResponse(
        status_code=200,
        content=response_content,
    )
