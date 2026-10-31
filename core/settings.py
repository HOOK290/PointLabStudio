"""E22：用户设置持久化（主题、最近文件、窗口状态）。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path


def app_home() -> Path:
    """配置目录：POINTLAB_HOME > %APPDATA%/PointLabStudio > ~/.pointlabstudio。"""
    override = os.environ.get("POINTLAB_HOME")
    if override:
        return Path(override)
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "PointLabStudio"
    return Path.home() / ".pointlabstudio"


def settings_path() -> Path:
    return app_home() / "settings.json"


def log_path() -> Path:
    return app_home() / "logs" / "pointlab.log"


@dataclass
class Settings:
    theme: str = "dark"
    recent_files: list[str] = field(default_factory=list)
    last_dir: str = ""
    window_geometry: str = ""          # base64(QWidget.saveGeometry())
    max_recent: int = 10
    language: str = "zh"

    # ---------------- 最近文件 ----------------
    def add_recent(self, path: str) -> None:
        if not path:
            return
        path = os.path.abspath(path)
        self.recent_files = [p for p in self.recent_files if os.path.normcase(p) != os.path.normcase(path)]
        self.recent_files.insert(0, path)
        del self.recent_files[self.max_recent:]

    def remove_recent(self, path: str) -> None:
        target = os.path.normcase(os.path.abspath(path))
        self.recent_files = [p for p in self.recent_files if os.path.normcase(p) != target]

    # ---------------- 序列化 ----------------
    def to_dict(self) -> dict:
        return {
            "theme": self.theme,
            "recent_files": list(self.recent_files),
            "last_dir": self.last_dir,
            "window_geometry": self.window_geometry,
            "max_recent": self.max_recent,
            "language": self.language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        if not isinstance(data, dict):
            return cls()
        theme = data.get("theme") if data.get("theme") in ("dark", "light") else "dark"
        recent = [str(p) for p in data.get("recent_files") or [] if isinstance(p, str)]
        return cls(
            theme=theme,
            recent_files=recent[:10],
            last_dir=str(data.get("last_dir") or ""),
            window_geometry=str(data.get("window_geometry") or ""),
            language=str(data.get("language") or "zh"),
        )


def load_settings(path: Path | None = None) -> Settings:
    target = Path(path) if path else settings_path()
    try:
        with open(target, encoding="utf-8") as f:
            return Settings.from_dict(json.load(f))
    except (OSError, ValueError):
        return Settings()


def save_settings(settings: Settings, path: Path | None = None) -> bool:
    target = Path(path) if path else settings_path()
    tmp = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp, target)
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False
