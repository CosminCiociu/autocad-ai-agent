from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from schema_validation import SchemaStore


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = BASE_DIR.parent / "shared" / "schemas"

CONTEXT_SCHEMA = "dwg-context.schema.json"
ACTION_SCHEMA = "action-plan.schema.json"

app = FastAPI(title="AutoCAD AI Server", version="0.1.0")
schemas = SchemaStore(SCHEMA_DIR)


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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

    # Placeholder planner: returns a safe clarification until model/tool-calling is wired.
    action_plan: dict[str, Any] = {
        "schema_version": payload["schema_version"],
        "request_id": request_id,
        "summary": "Schema valid. Waiting for tool-calling integration.",
        "needs_clarification": True,
        "clarification_question": "Ce actiune vrei sa execut pe desen?",
        "actions": [],
    }

    action_issues = schemas.validate(ACTION_SCHEMA, action_plan)
    if action_issues:
        details = [{"path": i.path, "message": i.message} for i in action_issues]
        return JSONResponse(
            status_code=500,
            content=build_error(
                request_id=request_id,
                code="INTERNAL_ERROR",
                message="Generated action plan failed schema validation.",
                details=details,
            ),
        )

    return JSONResponse(status_code=200, content=action_plan)
