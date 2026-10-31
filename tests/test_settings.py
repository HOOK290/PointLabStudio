"""E22：设置持久化、最近文件、文件日志。"""

from __future__ import annotations

import logging
import os
import time

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from core.applog import LOGGER_NAME, setup_logging
from core.settings import Settings, load_settings, save_settings
from ui.main_window import MainWindow


def test_settings_recent_dedupe_and_limit():
    s = Settings(max_recent=3)
    s.add_recent("/a/one.xyz")
    s.add_recent("/a/two.xyz")
    s.add_recent("/a/one.xyz")
    assert s.recent_files[0] == os.path.abspath("/a/one.xyz")
    s.add_recent("/a/three.xyz")
    s.add_recent("/a/four.xyz")
    assert len(s.recent_files) == 3
    s.remove_recent("/a/two.xyz")
    assert all(not p.endswith("two.xyz") for p in s.recent_files)


def test_settings_roundtrip(tmp_path):
    s = Settings(theme="light", last_dir="D:/data")
    s.add_recent(str(tmp_path / "x.xyz"))
    s.window_geometry = "AAAA"
    path = tmp_path / "settings.json"
    assert save_settings(s, path)
    loaded = load_settings(path)
    assert loaded.theme == "light"
    assert loaded.last_dir == "D:/data"
    assert loaded.window_geometry == "AAAA"
    assert loaded.recent_files == s.recent_files


def test_load_settings_missing_returns_defaults(tmp_path):
    loaded = load_settings(tmp_path / "missing.json")
    assert loaded.theme == "dark"
    assert loaded.recent_files == []


def test_file_logger_writes(tmp_path):
    logfile = tmp_path / "logs" / "app.log"
    target = setup_logging(logfile)
    assert target is not None
    logging.getLogger(f"{LOGGER_NAME}.test").info("hello-pointlab")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()
    text = logfile.read_text(encoding="utf-8")
    assert "hello-pointlab" in text


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("POINTLAB_HOME", str(tmp_path))
    yield tmp_path


def test_window_records_recent_and_persists(home, app, tmp_path):
    cloud = tmp_path / "cloud.xyz"
    cloud.write_text("0 0 0\n1 0 0\n0 1 0\n", encoding="utf-8")
    win = MainWindow()
    win.show()
    app.processEvents()
    win.open_paths([str(cloud)])
    app.processEvents()
    assert win.settings.recent_files
    assert win._recent_menu.isEnabled()

    geometry = win.saveGeometry()
    win.close()
    deadline = time.monotonic() + 5
    while win.isVisible() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    saved = load_settings(home / "settings.json")
    assert saved.recent_files[0].endswith("cloud.xyz")
    assert saved.window_geometry
    assert geometry.size() > 0


def test_two_windows_share_saved_theme(home, app):
    first = MainWindow(theme="light")
    first._set_theme("light")
    first.close()
    app.processEvents()
    saved = load_settings(home / "settings.json")
    assert saved.theme == "light"
