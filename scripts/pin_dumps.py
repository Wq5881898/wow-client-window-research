"""SHA-256 pin of archived Forever API dumps.

Read-only. Does not download. Re-run after any dump change.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DUMPS = ROOT / "sources" / "forever_dumps"
OUT = ROOT / "results" / "dump_hashes.json"


def main() -> int:
    files = sorted(p for p in DUMPS.iterdir() if p.is_file())
    items = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        items.append({"file": path.name, "bytes": path.stat().st_size, "sha256": digest})
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dump_dir": "sources/forever_dumps",
        "count": len(items),
        "files": items,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"pinned {len(items)} files -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
