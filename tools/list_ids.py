import json
from pathlib import Path

ROOT = Path(r"C:\Projekte\Website Design\hd2-stratagem-studio")
data = json.loads((ROOT / "data" / "stratagems.json").read_text(encoding="utf-8"))
items = data["stratagems"] if isinstance(data, dict) else data
for item in items:
    print(f"{item['category']:11} {item['id']:38} {item['name']}")
