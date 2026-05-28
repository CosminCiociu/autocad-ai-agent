from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


@dataclass
class ValidationIssue:
    path: str
    message: str


def _display_path(error_path: list[Any]) -> str:
    if not error_path:
        return "$"
    return "$." + ".".join(str(part) for part in error_path)


class SchemaStore:
    def __init__(self, schema_dir: Path) -> None:
        self.schema_dir = schema_dir
        self._validators: dict[str, Draft202012Validator] = {}

    def load_validator(self, file_name: str) -> Draft202012Validator:
        if file_name in self._validators:
            return self._validators[file_name]

        schema_path = self.schema_dir / file_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
        self._validators[file_name] = validator
        return validator

    def validate(self, file_name: str, payload: dict[str, Any]) -> list[ValidationIssue]:
        validator = self.load_validator(file_name)
        errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
        return [
            ValidationIssue(path=_display_path(list(error.path)), message=error.message)
            for error in errors
        ]
