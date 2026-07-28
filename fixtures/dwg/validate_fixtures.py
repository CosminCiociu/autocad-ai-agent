from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
RECURSIVE = True
OUTPUT = ROOT / "fixtures_index.json"

REQUIRED_META_KEYS = {"filename", "description", "units", "coordinate_system"}


def validate_meta(meta: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in REQUIRED_META_KEYS:
        if key not in meta:
            errors.append(f"missing required meta key: {key}")
    # basic types
    if "units" in meta and meta["units"] not in {"mm", "cm", "m", "inch", "foot", "unitless"}:
        errors.append(f"unknown units: {meta.get('units')}")
    if "coordinate_system" in meta and meta["coordinate_system"] not in {"WCS", "UCS"}:
        errors.append(f"unknown coordinate_system: {meta.get('coordinate_system')}")
    return errors


def collect_fixtures(root: Path, recursive: bool = True) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    pattern = "**/*.dwg" if recursive else "*.dwg"
    for dwg_path in sorted(root.glob(pattern)):
        if dwg_path.name.startswith("~$"):
            continue
        meta_path = dwg_path.with_name(dwg_path.name + ".meta.json")
        has_meta = meta_path.exists()
        meta = None
        meta_errors: list[str] = []
        if has_meta:
            try:
                # support files that may include a UTF-8 BOM
                meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
                meta_errors = validate_meta(meta)
            except Exception as e:
                meta_errors = [f"failed to parse meta json: {e}"]
        entries.append(
            {
                "dwg": str(dwg_path.relative_to(ROOT.parent)),
                "meta_path": str(meta_path.relative_to(ROOT.parent)) if has_meta else None,
                "has_meta": has_meta,
                "meta": meta,
                "meta_errors": meta_errors,
            }
        )
    return entries


def main() -> int:
    entries = collect_fixtures(ROOT, recursive=RECURSIVE)
    # Auto-create minimal meta files for DWGs that don't have one
    for ent in entries:
        if not ent.get("has_meta"):
            dwg_rel = ent["dwg"]
            dwg_path = ROOT.parent / dwg_rel
            meta_path = dwg_path.with_name(dwg_path.name + ".meta.json")
            default_meta = {
                "filename": dwg_path.name,
                "description": "Imported fixture (auto-generated metadata)",
                "tags": ["edge", "imported"],
                "units": "unitless",
                "coordinate_system": "WCS"
            }
            try:
                meta_path.write_text(json.dumps(default_meta, ensure_ascii=False, indent=2), encoding="utf-8")
                ent["has_meta"] = True
                ent["meta_path"] = str(meta_path.relative_to(ROOT.parent))
                ent["meta"] = default_meta
                ent["meta_errors"] = []
            except Exception as e:
                ent["meta_errors"] = [f"failed to write auto meta: {e}"]
    out = {"count": len(entries), "entries": entries}
    OUTPUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT} with {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
