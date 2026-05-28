# Changelog

All notable changes to this project are documented in this file.

The format is based on Keep a Changelog principles.

## [Unreleased]

### Added

- Initial project structure:
  - `autocad-plugin/`
  - `ai-server/`
  - `shared/schemas/`
  - `docs/`
- Initial conventions document in `docs/CONVENTIONS.md`.
- Initial task list in `TODO.md`.
- FastAPI server scaffold in `ai-server/main.py` with `GET /health` and `POST /analyze`.
- JSON Schema validation utility in `ai-server/schema_validation.py`.
- Plugin-side schema validation helpers in `autocad-plugin/SchemaValidation/`.
- Schema usage notes in `docs/SCHEMAS.md` and `autocad-plugin/README.md`.
