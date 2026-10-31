"""PointLabStudio 桌面应用入口。"""

from __future__ import annotations

import argparse
import sys


def build_parser():
    parser = argparse.ArgumentParser(description="PointLabStudio — 点云综合处理平台")
    parser.add_argument("path", nargs="?", default=None, help="点云文件或点云目录")
    parser.add_argument("--background", choices=["dark", "light"], default=None,
                        help="背景主题（默认沿用上次设置）")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    from core.applog import get_logger, setup_logging
    from core.i18n import set_language
    from core.recovery import install_excepthook, is_unclean, mark_running
    from core.settings import load_settings

    setup_logging()
    install_excepthook()
    logger = get_logger("main")
    settings = load_settings()
    if is_unclean():
        logger.warning("检测到上次未正常退出（残留 session.running）")
    mark_running()
    try:
        set_language(settings.language)
    except ValueError:
        set_language("zh")
    theme = args.background or settings.theme

    from PySide6.QtWidgets import QApplication

    from ui.main_window import MainWindow
    from ui.theme import build_stylesheet

    app = QApplication(sys.argv[:1] if argv is not None else sys.argv)
    app.setApplicationName("PointLabStudio")
    app.setOrganizationName("PointLabStudio")
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet(theme))

    window = MainWindow(start_path=args.path, theme=theme)
    window.show()
    code = app.exec()
    from core.recovery import clear_running
    clear_running()
    sys.exit(code)


if __name__ == "__main__":
    main()
