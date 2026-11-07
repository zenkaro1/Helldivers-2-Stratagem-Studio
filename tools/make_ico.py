"""Build a multi-size Windows .ico from the logo PNG (no Pillow needed)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "app" / "assets" / "logo.png"
TARGET = ROOT / "app" / "assets" / "logo.ico"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def bmp_entry(image: QImage) -> bytes:
    width, height = image.width(), image.height()
    header = struct.pack(
        "<IiiHHIIiiII",
        40,          # biSize
        width,       # biWidth
        height * 2,  # biHeight (XOR + AND mask)
        1,           # biPlanes
        32,          # biBitCount
        0,           # biCompression
        width * height * 4 + ((width + 31) // 32) * 4 * height,
        0, 0, 0, 0,
    )
    pixels = bytearray()
    for row in range(height - 1, -1, -1):  # bottom-up
        line = image.constScanLine(row)
        pixels += bytes(line)[: width * 4]
    mask_row = ((width + 31) // 32) * 4
    mask = bytes(mask_row * height)
    return header + bytes(pixels) + mask


def png_entry(image: QImage) -> bytes:
    from PySide6.QtCore import QBuffer, QByteArray

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def main() -> int:
    app = QGuiApplication(sys.argv)  # noqa: F841 - needed for QImage
    base = QImage(str(SOURCE)).convertToFormat(QImage.Format.Format_ARGB32)
    if base.isNull():
        raise SystemExit(f"cannot read {SOURCE}")

    entries: list[tuple[int, bytes]] = []
    for size in SIZES:
        scaled = base.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        payload = png_entry(scaled) if size >= 256 else bmp_entry(scaled)
        entries.append((size, payload))

    offset = 6 + 16 * len(entries)
    header = struct.pack("<HHH", 0, 1, len(entries))
    directory = b""
    data = b""
    for size, payload in entries:
        directory += struct.pack(
            "<BBBBHHII",
            0 if size >= 256 else size,
            0 if size >= 256 else size,
            0, 0, 1, 32, len(payload), offset,
        )
        offset += len(payload)
        data += payload

    TARGET.write_bytes(header + directory + data)
    print(f"wrote {TARGET} ({TARGET.stat().st_size} bytes, sizes {SIZES})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
