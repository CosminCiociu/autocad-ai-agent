from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from typing import Any

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "fixtures_index.json"
OUT_DIR = ROOT / "exports"
OUT_DIR.mkdir(exist_ok=True)


def load_index() -> dict[str, Any]:
    if not INDEX.exists():
        raise SystemExit(f"Index not found: {INDEX}")
    return json.loads(INDEX.read_text(encoding="utf-8"))


def make_context(entry: dict[str, Any]) -> dict[str, Any]:
    meta = entry.get("meta") or {}
    drawing = {
        "name": meta.get("filename") or Path(entry["dwg"]).name,
        "units": meta.get("units", "unitless"),
        "coordinate_system": meta.get("coordinate_system", "WCS"),
    }
    request_id = str(uuid4())
    ctx = {
        "schema_version": "1.0.0",
        "request_id": request_id,
        "drawing": drawing,
        "blocks": [],
        "texts": [],
        "lines": [],
        "polylines": [],
    }
    return ctx


def main() -> int:
    idx = load_index()
    entries = idx.get("entries", [])
    written = 0
    for ent in entries:
        try:
            ctx = make_context(ent)
            dwg_rel = ent["dwg"].replace("\\", "_")
            out_name = f"{Path(dwg_rel).stem}.context.json"
            out_path = OUT_DIR / out_name
            out_path.write_text(json.dumps(ctx, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1
        except Exception as e:
            print(f"failed to export {ent.get('dwg')}: {e}")
    print(f"Wrote {written} context files to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
