"""Render the upstream vector artwork for the macOS application icon."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

root = Path(__file__).resolve().parents[1]
folder = root / "build" / "macos-icon" / "PointLabStudio.iconset"
folder.mkdir(parents=True, exist_ok=True)
app = QGuiApplication([])
renderer = QSvgRenderer(str(root / "resources" / "app.svg"))
if not renderer.isValid():
    raise RuntimeError("Unable to load resources/app.svg")
for size in (16, 32, 128, 256, 512):
    for scale in (1, 2):
        image = QImage(size * scale, size * scale, QImage.Format_ARGB32)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        suffix = "@2x" if scale == 2 else ""
        if not image.save(str(folder / f"icon_{size}x{size}{suffix}.png")):
            raise RuntimeError("Unable to save icon")
