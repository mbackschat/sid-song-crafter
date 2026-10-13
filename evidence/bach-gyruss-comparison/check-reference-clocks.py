"""Record registered local reference clock declarations without executing songs."""
import hashlib
import json
from pathlib import Path
import sys

root = Path.cwd()
sys.path.insert(0, str(root / "scripts"))
from sid_intake import inspect_sid

registry = root / "config/local-assets.json"
records = []
for entry in json.loads(registry.read_text())["references"]:
    path = root / entry["path"]
    if not path.is_file():
        records.append({"id": entry["id"], "status": "not installed"})
        continue
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError("Registered source fingerprint differs: " + entry["id"])
    header = inspect_sid(data, subtune=1)
    records.append({"id": entry["id"], "sourcePath": entry["path"], "sourceUrl": entry["url"], "header": header})
print(json.dumps({"date": "2026-10-14", "registrySha256": hashlib.sha256(registry.read_bytes()).hexdigest(), "method": "Pinned source bytes and PSID/RSID header declarations; not measured cadence or a claim about every release of the game", "references": records}, indent=2))
