from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from .database import Database
from .devices import AdbService
from .paths import AppPaths
from .platforms import default_registry
from .ui.main_window import MainWindow


def configure_logging(paths: AppPaths) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(paths.logs / "huifu.log", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main() -> int:
    paths = AppPaths.discover()
    paths.ensure()
    configure_logging(paths)

    app = QApplication(sys.argv)
    app.setApplicationName("多平台 AI 互动助手")
    app.setOrganizationName("HuifuAI")

    database = Database(paths.database)
    try:
        database.migrate()
        if database.integrity_check() != "ok":
            raise RuntimeError("本地数据库完整性检查未通过")
    except Exception as exc:
        logging.exception("database initialization failed")
        QMessageBox.critical(None, "启动失败", f"本地数据库初始化失败：\n{exc}")
        return 1

    window = MainWindow(database, paths, AdbService(), default_registry())
    window.show()
    return app.exec()

