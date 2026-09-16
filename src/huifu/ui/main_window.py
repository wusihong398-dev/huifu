from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from huifu import __version__
from huifu.backup import create_backup
from huifu.database import Database
from huifu.devices import AdbService
from huifu.paths import AppPaths
from huifu.platforms import PlatformRegistry


PAGE_NAMES = [
    "首页",
    "设备管理",
    "平台账号",
    "AI配置",
    "业务方案",
    "目标作品画像",
    "关键词库",
    "搜索任务",
    "候选作品",
    "目标作品",
    "回复素材",
    "发布队列",
    "发布记录",
    "失败诊断",
    "数据备份",
    "系统设置",
]


class MetricCard(QFrame):
    def __init__(self, title: str, value: int = 0) -> None:
        super().__init__()
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        title_label = QLabel(title)
        title_label.setObjectName("metricTitle")
        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("metricValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value: int) -> None:
        self.value_label.setText(str(value))


class MainWindow(QMainWindow):
    def __init__(
        self,
        database: Database,
        paths: AppPaths,
        adb: AdbService,
        platforms: PlatformRegistry,
    ) -> None:
        super().__init__()
        self.database = database
        self.paths = paths
        self.adb = adb
        self.platforms = platforms
        self.metrics: dict[str, MetricCard] = {}

        self.setWindowTitle(f"多平台 AI 互动助手 {__version__}")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 680)
        self._build_ui()
        self._apply_style()
        self.refresh_dashboard()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar)
        brand = QLabel("回复 AI")
        brand.setObjectName("brand")
        subtitle = QLabel("多平台互动助手")
        subtitle.setObjectName("brandSubtitle")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(subtitle)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setSelectionMode(QAbstractItemView.SingleSelection)
        for name in PAGE_NAMES:
            self.navigation.addItem(QListWidgetItem(name))
        self.navigation.currentRowChanged.connect(self._switch_page)
        sidebar_layout.addWidget(self.navigation, 1)
        version = QLabel(f"版本 {__version__}")
        version.setObjectName("version")
        sidebar_layout.addWidget(version)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._dashboard_page())
        self.pages.addWidget(self._devices_page())
        for name in PAGE_NAMES[2:]:
            self.pages.addWidget(self._planned_page(name))

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)
        self.navigation.setCurrentRow(0)

    def _dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        title = QLabel("运行概览")
        title.setObjectName("pageTitle")
        refresh = QPushButton("刷新数据")
        refresh.clicked.connect(self.refresh_dashboard)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh)
        layout.addLayout(header)

        rows = [
            (("devices", "在线设备"), ("accounts", "正常账号"), ("candidates", "候选作品"), ("targets", "目标作品")),
            (("drafts", "回复草稿"), ("queued", "等待发布"), ("succeeded", "发布成功"), ("failed", "失败/待核验")),
        ]
        for row in rows:
            row_layout = QHBoxLayout()
            for key, label in row:
                card = MetricCard(label)
                self.metrics[key] = card
                row_layout.addWidget(card)
            layout.addLayout(row_layout)

        notice = QLabel(
            "当前为基础框架版本：平台实际搜索和发布将在真机验证后逐项启用。"
            "未验证功能不会标记为可用。"
        )
        notice.setWordWrap(True)
        notice.setObjectName("notice")
        layout.addWidget(notice)
        layout.addStretch(1)
        return page

    def _devices_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        title = QLabel("设备管理")
        title.setObjectName("pageTitle")
        refresh = QPushButton("检测安卓设备")
        refresh.clicked.connect(self.refresh_devices)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(refresh)
        layout.addLayout(header)

        self.device_status = QLabel("尚未检测")
        self.device_table = QTableWidget(0, 4)
        self.device_table.setHorizontalHeaderLabels(["设备序列号", "状态", "型号", "说明"])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.device_status)
        layout.addWidget(self.device_table, 1)
        return page

    def _planned_page(self, name: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel(name)
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        if name == "数据备份":
            message = QLabel("备份包含SQLite数据库；图片、语音和诊断文件将在后续版本加入完整备份清单。")
            message.setWordWrap(True)
            button = QPushButton("立即备份数据库")
            button.clicked.connect(self.backup_now)
            layout.addWidget(message)
            layout.addWidget(button, alignment=Qt.AlignLeft)
        else:
            message = QLabel(f"{name}功能已纳入本地版架构，正在按版本计划实现。")
            message.setObjectName("planned")
            message.setWordWrap(True)
            layout.addWidget(message)
        layout.addStretch(1)
        return page

    def _switch_page(self, index: int) -> None:
        if index >= 0:
            self.pages.setCurrentIndex(index)

    def refresh_dashboard(self) -> None:
        counts = self.database.dashboard_counts()
        for key, card in self.metrics.items():
            card.set_value(counts.get(key, 0))

    def refresh_devices(self) -> None:
        available = self.adb.is_available()
        devices = self.adb.list_devices() if available else []
        self.device_table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            values = [device.serial, device.state, device.model, "已连接" if device.state == "device" else "需要检查"]
            for column, value in enumerate(values):
                self.device_table.setItem(row, column, QTableWidgetItem(value))
        if not available:
            self.device_status.setText("未找到ADB。后续安装包将携带ADB；开发环境请先安装Android Platform Tools。")
        else:
            self.device_status.setText(f"检测到 {len(devices)} 台设备")

    def backup_now(self) -> None:
        try:
            target = create_backup(self.database, self.paths)
        except Exception as exc:  # UI boundary: present unexpected file/DB failures
            QMessageBox.critical(self, "备份失败", str(exc))
            return
        QMessageBox.information(self, "备份完成", f"数据库已备份到：\n{target}")

    def _apply_style(self) -> None:
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#f6f8fb"))
        self.setPalette(palette)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { color: #172033; font-family: "Microsoft YaHei UI"; font-size: 13px; }
            #sidebar { background: #111827; }
            #brand { color: white; font-size: 25px; font-weight: 700; padding: 20px 16px 0 16px; }
            #brandSubtitle { color: #9ca3af; padding: 0 16px 16px 16px; }
            #version { color: #6b7280; padding: 14px; }
            #navigation { background: transparent; border: 0; color: #cbd5e1; padding: 6px; }
            #navigation::item { padding: 10px 14px; margin: 2px 4px; border-radius: 6px; }
            #navigation::item:selected { background: #2563eb; color: white; }
            #pageTitle { font-size: 24px; font-weight: 700; padding-bottom: 12px; }
            #metricCard { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px; }
            #metricTitle { color: #64748b; }
            #metricValue { font-size: 28px; font-weight: 700; color: #0f172a; }
            #notice { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 14px; color: #1e40af; }
            #planned { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 18px; }
            QPushButton { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 8px 14px; }
            QPushButton:hover { background: #1d4ed8; }
            QTableWidget { background: white; border: 1px solid #e5e7eb; gridline-color: #eef2f7; }
            QHeaderView::section { background: #f8fafc; padding: 8px; border: 0; border-bottom: 1px solid #e5e7eb; }
            """
        )

