import json
import sys

sys.path.insert(0, r"C:\Projekte\Website Design\hd2-stratagem-studio")
from tools.vectorcraft_mcp import Session  # noqa: E402

s = Session(headless=True)
print("new:", s.call("run_command", {"command": "file.new", "params": {
    "width": 400, "height": 400, "units": "Pixels", "backgroundContents": "white"}}))
print("rect:", s.call("run_command", {"command": "shape.rectangle", "params": {
    "x": 100, "y": 100, "width": 200, "height": 200, "fill": "#ff0000", "stroke": "none"}}))
print("poly:", s.call("shape.polygon", {"cx": 200, "cy": 200, "radius": 80, "sides": 6,
                                        "fill": "#00ff00", "stroke": "none"}))
print("path:", s.call("draw_path", {"points": [[50, 50], [150, 50], [100, 150]],
                                    "closed": True, "fill": "#0000ff", "stroke": "none"}))
print("inspect:", json.dumps(s.call("inspect_document"), ensure_ascii=False)[:1200])
print("export:", s.call("run_command", {"command": "file.export", "params": {
    "path": r"C:\Projekte\Website Design\hd2-stratagem-studio\.tmp\probe.png",
    "format": "png", "scale": 1}}))
s.close()
