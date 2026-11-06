import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from core.settings import Settings, app_home, load_settings, save_settings


class AppHomeTests(unittest.TestCase):
    def test_macos_settings_use_application_support_even_with_appdata(self):
        with patch("sys.platform", "darwin"), patch.dict(
            os.environ, {"APPDATA": "/unrelated/windows"}, clear=True
        ):
            self.assertEqual(
                app_home(),
                Path.home() / "Library" / "Application Support" / "PointLabStudio",
            )

    def test_explicit_home_override_is_preserved(self):
        with patch.dict(os.environ, {"POINTLAB_HOME": "/tmp/点云设置"}, clear=True):
            self.assertEqual(app_home(), Path("/tmp/点云设置"))

    def test_windows_appdata_is_preserved(self):
        with patch("sys.platform", "win32"), patch.dict(
            os.environ, {"APPDATA": "/windows/appdata"}, clear=True
        ):
            self.assertEqual(app_home(), Path("/windows/appdata/PointLabStudio"))

    def test_settings_round_trip_with_unicode_filename(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "用户设置" / "settings.json"
            settings = Settings(recent_files=["/tmp/点云 测试.ply"], theme="light")
            self.assertTrue(save_settings(settings, target))
            self.assertEqual(load_settings(target), settings)


if __name__ == "__main__":
    unittest.main()
