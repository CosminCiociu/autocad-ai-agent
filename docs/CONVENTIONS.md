# Project Conventions

## Naming

- Use `snake_case` for JSON keys.
- Use `PascalCase` for C# class names.
- Use `camelCase` for C# local variables and method parameters.
- Prefix all action types with verb-first style: `insert_block`, `create_polyline`, `update_attribute`, `find_entities`.

## Schema Versioning

- Keep schema files in `shared/schemas/`.
- Use semantic versions in payloads, e.g. `"schema_version": "1.0.0"`.
- Breaking schema changes require major version bump.
- Add a changelog entry for each schema update.

## Layer and Entity Rules

- Normalize layer names to uppercase when validating rules.
- Preserve original AutoCAD handle values in payloads.
- Use WCS coordinates in all API payloads.

## Logging and Traceability

- Generate one `request_id` per user command.
- Include `request_id` in plugin logs, API logs, validation logs, and execution logs.
- Log machine-readable JSON lines where possible.

## Branching and Commits

- Branch naming: `feature/<short-topic>`, `fix/<short-topic>`, `docs/<short-topic>`.
- Commit message style: `<type>: <summary>`
- Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`.
