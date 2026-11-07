import json
import sys

sys.path.insert(0, r"C:\Projekte\Website Design\hd2-stratagem-studio")
from tools.vectorcraft_mcp import Session  # noqa: E402

s = Session(headless=True)
s.call("run_command", {"command": "file.new", "params": {
    "width": 1024, "height": 1024, "units": "Pixels", "backgroundContents": "transparent"}})
fonts = s.call("run_command", {"command": "text.fonts"})
print("type:", type(fonts).__name__, "len:", len(fonts) if isinstance(fonts, list) else "")
print(json.dumps(fonts[:3] if isinstance(fonts, list) else fonts, ensure_ascii=False)[:600])
if isinstance(fonts, list):
    names = []
    for item in fonts:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, dict):
            names.append(str(item.get("family") or item.get("name")))
    print("matches:", [n for n in names if any(k in n.lower() for k in ("bahn", "noto sans", "arial", "inter", "roboto", "oswald", "barlow"))][:30])
s.close()
