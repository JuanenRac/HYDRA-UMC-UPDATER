# =============================================================================
# HYDRA-UMC-UPDATER - Generate the Windows application icon from the official
# HYDRA-UMC SVG identity asset: generate_app_icon.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
"""Render the public HYDRA-UMC SVG into the icon consumed by Windows.

The source of truth remains images/HYDRA_UMC_ICON.svg.  This small tool is
kept in the repository so a future branding change can regenerate the ICO
rather than hand-editing a binary asset.  The icon holds every size from 16
to 256 pixels (Windows picks the one that fits the title bar, the taskbar or
the file list) and is written to both places that use it: images/ and the
package assets, which is what an installed copy loads.
"""
from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "images" / "HYDRA_UMC_ICON.svg"
OUTPUTS = (
    ROOT / "images" / "HYDRA_UMC_ICON.ico",
    ROOT / "src" / "hydra_umc_updater" / "assets" / "HYDRA_UMC_ICON.ico",
)
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)


def build_ico(png_images: list[tuple[int, bytes]]) -> bytes:
    """Assembles an ICO file from (size, PNG bytes) pairs. Windows reads PNG
    data inside an ICO directly; a size of 256 is stored as 0."""
    header = struct.pack("<HHH", 0, 1, len(png_images))
    offset = 6 + 16 * len(png_images)
    directory = b""
    payload = b""
    for size, data in png_images:
        directory += struct.pack(
            "<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset + len(payload)
        )
        payload += data
    return header + directory + payload


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError(f"Qt could not encode the {size}px icon")
    data = buffer.data()
    return bytes(data if isinstance(data, QByteArray) else QByteArray(data))


def main() -> int:
    renderer = QSvgRenderer(str(SOURCE))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid SVG icon source: {SOURCE}")

    ico = build_ico([(size, render_png(renderer, size)) for size in ICON_SIZES])
    for output in OUTPUTS:
        output.write_bytes(ico)
        print(f"APP_ICON=GENERATED source={SOURCE.name} output={output.relative_to(ROOT)} sizes={len(ICON_SIZES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
