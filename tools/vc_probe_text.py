import json
import sys

sys.path.insert(0, r"C:\Projekte\Website Design\hd2-stratagem-studio")
from tools.vectorcraft_mcp import Session  # noqa: E402

s = Session(headless=True)
s.call("run_command", {"command": "file.new", "params": {
    "width": 800, "height": 300, "units": "Pixels", "backgroundContents": "transparent"}})
for font in ("Bahnschrift", "Noto Sans", "Arial"):
    try:
        res = s.call("run_command", {"command": "text.create", "params": {
            "x": 40, "y": 150, "text": f"SAMPLE {font}", "size": 48, "font": font,
            "color": "#F5D13F"}})
        print(font, "->", json.dumps(res, ensure_ascii=False)[:300])
    except Exception as exc:  # noqa: BLE001
        print(font, "ERROR", str(exc)[:300])
print(json.dumps(s.call("inspect_document"), ensure_ascii=False)[:800])
s.close()
