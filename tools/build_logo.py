"""Build the Stratagem Studio logo in VectorCraft (MCP, headless)."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.vectorcraft_mcp import Session  # noqa: E402

OUT = ROOT / "design" / "exports" / "logo"
OUT.mkdir(parents=True, exist_ok=True)

PLATE = "#12140F"
PLATE_DARK = "#0B0C08"
BORDER = "#3D4231"
BORDER_SOFT = "#2B2F22"
ACCENT = "#F5D13F"
TEXT = "#EAE8DD"
MUTED = "#8F9484"


class Draw:
    def __init__(self, session: Session):
        self.session = session

    def run(self, command: str, params: dict) -> dict:
        result = self.session.call("run_command", {"command": command, "params": params})
        if result.get("isError"):
            raise RuntimeError(f"{command}: {result.get('text')}")
        return result

    def shape(self, **params) -> dict:
        result = self.session.call("draw_shape", params)
        if result.get("isError"):
            raise RuntimeError(f"draw_shape: {result.get('text')}")
        return result

    def path(self, **params) -> dict:
        result = self.session.call("draw_path", params)
        if result.get("isError"):
            raise RuntimeError(f"draw_path: {result.get('text')}")
        return result

    def text(self, **params) -> dict:
        return self.run("text.create", params)

    def style(self, object_id: int, **params) -> dict:
        payload = {"id": object_id}
        payload.update(params)
        return self.run("text.setStyle", payload)


def rotate(points: list[tuple[float, float]], cx: float, cy: float,
           degrees: float) -> list[list[float]]:
    rad = math.radians(degrees)
    cos, sin = math.cos(rad), math.sin(rad)
    return [
        [cx + (x - cx) * cos - (y - cy) * sin, cy + (x - cx) * sin + (y - cy) * cos]
        for x, y in points
    ]


def chevron(cx: float, cy: float, scale: float, angle: float) -> list[list[float]]:
    up = [
        (0.0, -352.0),
        (150.0, -186.0),
        (54.0, -186.0),
        (0.0, -244.0),
        (-54.0, -186.0),
        (-150.0, -186.0),
    ]
    points = [(cx + x * scale, cy + y * scale) for x, y in up]
    return rotate(points, cx, cy, angle)


def draw_mark(draw: Draw, cx: float, cy: float, scale: float = 1.0) -> None:
    draw.shape(shape="polygon", cx=cx, cy=cy, radius=470 * scale, sides=6,
               rotation=30, fill=PLATE, stroke=BORDER,
               strokeWidth=max(2.0, 12 * scale), name="Badge")
    draw.shape(shape="polygon", cx=cx, cy=cy, radius=408 * scale, sides=6,
               rotation=30, fill="none", stroke=BORDER_SOFT,
               strokeWidth=max(1.5, 4 * scale), name="Inner ring")

    for angle in (0, 90, 180, 270):
        draw.path(points=chevron(cx, cy, scale * 0.93, angle), closed=True,
                  fill=ACCENT, stroke="none", name=f"Chevron {angle}")

    diamond = [[cx, cy - 158 * scale], [cx + 158 * scale, cy],
               [cx, cy + 158 * scale], [cx - 158 * scale, cy]]
    draw.path(points=diamond, closed=True, fill=ACCENT, stroke="none",
              name="Core diamond")
    inner = [[cx, cy - 66 * scale], [cx + 66 * scale, cy],
             [cx, cy + 66 * scale], [cx - 66 * scale, cy]]
    draw.path(points=inner, closed=True, fill=PLATE_DARK, stroke="none",
              name="Core cutout")


def export(draw: Draw, name: str, fmt: str, scale: float = 1.0) -> Path:
    path = OUT / f"{name}.{fmt}"
    result = draw.run("file.export", {"path": str(path), "format": fmt, "scale": scale})
    print(f"{path.name}: {result.get('bytes')} bytes")
    return path


def main() -> int:
    session = Session(headless=True)
    draw = Draw(session)
    try:
        session.run_command if False else None
        draw.run("file.new", {"width": 1024, "height": 1024, "units": "Pixels",
                              "backgroundContents": "transparent", "colorMode": "rgb"})
        draw_mark(draw, 512, 512, 1.0)
        export(draw, "logo-mark", "png", 1.0)
        export(draw, "logo-mark", "svg")
        export(draw, "logo-mark-512", "png", 0.5)

        draw.run("file.new", {"width": 1800, "height": 560, "units": "Pixels",
                              "backgroundContents": "transparent", "colorMode": "rgb"})
        draw_mark(draw, 300, 280, 0.5)

        title = draw.text(x=600, y=300, text="STRATAGEM STUDIO", size=110,
                          font="Bahnschrift", style="Bold", color=TEXT)
        draw.style(title["id"], tracking=60)

        sub = draw.text(x=604, y=372, text="HELLDIVERS 2  ·  TAKTIK-WERKZEUG",
                        size=28, font="Bahnschrift", style="SemiBold", color=MUTED)
        draw.style(sub["id"], tracking=240)

        export(draw, "logo-lockup", "png", 1.0)
        export(draw, "logo-lockup", "svg")

        draw.run("file.new", {"width": 1024, "height": 1024, "units": "Pixels",
                              "backgroundContents": "transparent", "colorMode": "rgb"})
        draw.shape(shape="rectangle", x=0, y=0, width=1024, height=1024, radius=210,
                   fill=PLATE_DARK, stroke=BORDER, strokeWidth=10, name="Icon plate")
        draw_mark(draw, 512, 512, 0.62)
        export(draw, "logo-icon", "png", 1.0)
        export(draw, "logo-icon", "svg")
        export(draw, "logo-icon-256", "png", 0.25)
        info = draw.run("document.inspect", {})
        print("objects:", info.get("objects"))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
