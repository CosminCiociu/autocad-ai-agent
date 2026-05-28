# AI Server

FastAPI orchestrator for schema validation and local LLM planning.

## Endpoints

- `GET /health`:
  - Returns service status.

- `POST /validate/context`:
  - Validates DWG payload against `dwg-context.schema.json`.

- `POST /analyze`:
  - Validates incoming DWG context.
  - Reads user command from `x-user-command` header.
  - Calls local Ollama model for action planning.
  - Validates generated action plan against `action-plan.schema.json`.
  - Runs semantic validation gate before returning executable actions:
    - block existence checks
    - layer checks
    - coordinate range checks
    - attribute target/tag checks
  - Returns safe clarification response if command is missing, ambiguous, or model output is invalid.
  - Returns 422 with per-action validation report when semantic rules fail.

- `GET /replay/{request_id}`:
  - Returns saved replay artifact for debugging.
  - Includes input payload, user command, model raw response, validation results, and action plan.

## Local run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Optional env config:

- Copy `.env.example` and adjust values.
- Default model: `qwen2.5:7b`

3. Start API:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Request notes

- `POST /analyze` expects context JSON body conforming to `shared/schemas/dwg-context.schema.json`.
- Send natural language command in HTTP header `x-user-command`.

## Observability

- `request_id` is guaranteed for every analyze call (generated if missing).
- Structured events are appended to `ai-server/logs/events.jsonl`.
- Replay artifacts are stored in `ai-server/replay/{request_id}.json`.
- Current server scope is planning/validation only, so `execution_result` is recorded as `not_executed_server_side`.
