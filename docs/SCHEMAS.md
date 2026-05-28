# Schemas Overview

This document describes the JSON schema files used by the project.

## Files

- `shared/schemas/dwg-context.schema.json`
  - Input payload from AutoCAD plugin to AI server.
  - Contains drawing metadata and extracted entities.

- `shared/schemas/action-plan.schema.json`
  - Output payload from AI server to AutoCAD plugin.
  - Contains action list for tool-based execution.

- `shared/schemas/error-response.schema.json`
  - Standard error payload for schema or semantic validation failures.

## Versioning

- All payloads include `schema_version` in semantic version format: `MAJOR.MINOR.PATCH`.
- Breaking changes require a MAJOR bump.
- Backward-compatible additions require a MINOR bump.
- Fix-only adjustments require a PATCH bump.

## Standard Error Codes

- `SCHEMA_INVALID`
- `ACTION_UNKNOWN`
- `ACTION_ARGUMENT_INVALID`
- `LAYER_NOT_ALLOWED`
- `BLOCK_NOT_FOUND`
- `COORDINATE_OUT_OF_RANGE`
- `AMBIGUOUS_REQUEST`
- `INTERNAL_ERROR`

## Notes

- Coordinates should be normalized to WCS in integration payloads.
- Plugin and AI server should both validate payloads against schemas.
