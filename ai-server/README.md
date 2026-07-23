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
python -m venv .venv
# Activate the virtualenv (Windows PowerShell)
& .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

2. Optional env config:

- Copy `.env.example` to `.env` and adjust values (OLLAMA_HOST, MODEL_NAME, etc.).
- Default model: `qwen2.5:7b` (change in `.env` if needed).

3. Ollama (local LLM runtime):

- This project uses a local Ollama instance by default. Install Ollama from https://ollama.com and run the daemon locally, or configure `OLLAMA_HOST` in `.env` to point to your Ollama server.

4. Start API:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

5. Quick verification:

- Run the validator test to ensure JSON schema and server libs work:

```bash
python -c "from jsonschema import validate; import json; print('jsonschema OK')"
```

6. Fixtures and testing:

- If you want to test with local DWG fixtures, we provide simple extractors that generate context JSON placeholders in `fixtures/dwg/exports/`. These are ignored by git by default. To regenerate:

```bash
python fixtures/dwg/extract_contexts.py
python fixtures/dwg/validate_fixtures.py
```

3. Start API:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8001
```

## Request notes

- `POST /analyze` expects context JSON body conforming to `shared/schemas/dwg-context.schema.json`.
- Send natural language command in HTTP header `x-user-command`.

## Observability

- `request_id` is guaranteed for every analyze call (generated if missing).
- Structured events are appended to `ai-server/logs/events.json`.
- Replay artifacts are stored in `ai-server/replay/{request_id}.json`.
- Current server scope is planning/validation only, so `execution_result` is recorded as `not_executed_server_side`.

#Uselfull commands
Set-Location 'E:\Ai agent'; dotnet build "e:\Ai agent\autocad-plugin\AutocadPlugin.csproj" -p:OutputPath='E:\AiAgentBuild\' -p:AppendTargetFrameworkToOutputPath=false
