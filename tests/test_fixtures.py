from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate


ROOT = Path(__file__).resolve().parents[1]


def test_validator_and_extractor_run():
    # run validator
    import fixtures.dwg.validate_fixtures as vf

    rc = vf.main()
    assert rc == 0

    index_path = ROOT / "fixtures" / "dwg" / "fixtures_index.json"
    assert index_path.exists()
    idx = json.loads(index_path.read_text(encoding="utf-8"))
    count = idx.get("count", 0)

    # run extractor
    import fixtures.dwg.extract_contexts as ex

    rc2 = ex.main()
    assert rc2 == 0

    exports_dir = ROOT / "fixtures" / "dwg" / "exports"
    exports = sorted(exports_dir.glob("*.context.json"))
    assert len(exports) == count

    # validate exports against schema
    schema_path = ROOT / "shared" / "schemas" / "dwg-context.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    for f in exports:
        data = json.loads(f.read_text(encoding="utf-8"))
        validate(instance=data, schema=schema)
