from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ollama_client import OllamaClient
from planner import ActionPlanner
from semantic_validation import SemanticValidator
from schema_validation import SchemaStore


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = BASE_DIR.parent / "shared" / "schemas"

CONTEXT_SCHEMA = "dwg-context.schema.json"
ACTION_SCHEMA = "action-plan.schema.json"

app = FastAPI(title="AutoCAD AI Server", version="0.1.0")
schemas = SchemaStore(SCHEMA_DIR)
planner = ActionPlanner(ollama=OllamaClient())
semantic_validator = SemanticValidator()


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


def resolve_error_code(details: list[dict[str, Any]]) -> str:
    codes = {str(item.get("code", "")) for item in details if item.get("code")}
    if len(codes) == 1:
        return next(iter(codes))
    return "ACTION_ARGUMENT_INVALID"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    request_id = str(payload.get("request_id", "unknown"))
    schema_version = str(payload.get("schema_version", "1.0.0"))

    context_issues = schemas.validate(CONTEXT_SCHEMA, payload)
    if context_issues:
        details = [{"path": i.path, "message": i.message} for i in context_issues]
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code="SCHEMA_INVALID",
                message="Context payload failed schema validation.",
                details=details,
            ),
        )

    user_command = request.headers.get("x-user-command", "").strip()
    if not user_command:
        action_plan = build_safe_clarification_plan(
            request_id=request_id,
            schema_version=schema_version,
            question="Ce actiune vrei sa execut pe desen?",
            summary="Comanda lipsa. Nu execut nimic pana la clarificare.",
        )
    else:
        try:
            action_plan = await planner.plan(context_payload=payload, user_command=user_command)
        except Exception:
            action_plan = build_safe_clarification_plan(
                request_id=request_id,
                schema_version=schema_version,
                question="Nu am putut genera un plan sigur. Reformuleaza comanda in pasi clari.",
                summary="Model indisponibil sau raspuns invalid. Executie oprita preventiv.",
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
        return JSONResponse(
            status_code=422,
            content=build_error(
                request_id=request_id,
                code=resolve_error_code(details),
                message="Action plan failed semantic validation.",
                details=details,
            ),
        )

    return JSONResponse(status_code=200, content=action_plan)
