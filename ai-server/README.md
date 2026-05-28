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
