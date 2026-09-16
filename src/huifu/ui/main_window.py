from __future__ import annotations

from datetime import datetime
import re

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPalette
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
        self._device_records: list[dict[str, str]] = []

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
        test_connection = QPushButton("测试选中设备")
        test_connection.clicked.connect(self.test_selected_device)
        screenshot = QPushButton("截取手机屏幕")
        screenshot.clicked.connect(self.capture_selected_device)
        refresh = QPushButton("检测安卓设备")
        refresh.clicked.connect(self.refresh_devices)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(test_connection)
        header.addWidget(screenshot)
        header.addWidget(refresh)
        layout.addLayout(header)

        self.device_status = QLabel("尚未检测")
        self.device_status.setWordWrap(True)
        self.device_table = QTableWidget(0, 6)
        self.device_table.setHorizontalHeaderLabels(
            ["设备序列号", "状态", "品牌/型号", "安卓版本", "连接方式", "说明"]
        )
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.device_status)
        layout.addWidget(self.device_table, 1)
        help_text = QLabel(
            "使用说明：手机需开启开发者选项和USB调试。状态为“device/在线”后，"
            "可先执行连接测试，再通过截图确认程序能够读取手机画面。"
        )
        help_text.setObjectName("deviceHelp")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
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
        probe = self.adb.probe()
        devices = self.adb.list_devices() if probe.available else []
        self._device_records = [
            {
                "serial": device.serial,
                "status": "online" if device.state == "device" else device.state,
                "adb_state": device.state,
                "model": device.model,
                "android_version": "",
                "connection_type": device.connection_type,
            }
            for device in devices
        ]
        self.database.sync_devices(self._device_records)
        self.device_table.setRowCount(len(devices))
        for row, device in enumerate(devices):
            values = [
                device.serial,
                self._state_label(device.state),
                device.model or "待连接测试",
                "待连接测试" if device.state == "device" else "—",
                device.connection_type,
                self._state_explanation(device.state),
            ]
            for column, value in enumerate(values):
                self.device_table.setItem(row, column, QTableWidgetItem(value))
        if devices:
            self.device_table.selectRow(0)
        if not probe.available:
            self.device_status.setText(
                f"ADB不可用：{probe.error}。请重新解压完整安装包，确保HuifuAI.exe旁的_internal文件夹没有被删除。"
            )
        else:
            online_count = sum(device.state == "device" for device in devices)
            if devices:
                self.device_status.setText(
                    f"ADB已就绪（{probe.source}）｜检测到 {len(devices)} 台设备，在线 {online_count} 台"
                )
            else:
                self.device_status.setText(
                    f"ADB已就绪（{probe.source}），但没有发现安卓设备。请连接数据线、开启USB调试并在手机上允许调试授权。"
                )
        self.refresh_dashboard()

    @staticmethod
    def _state_label(state: str) -> str:
        labels = {
            "device": "在线",
            "unauthorized": "未授权",
            "offline": "离线",
            "recovery": "恢复模式",
            "sideload": "刷机模式",
            "no permissions": "无权限",
        }
        return labels.get(state, state or "未知")

    @staticmethod
    def _state_explanation(state: str) -> str:
        explanations = {
            "device": "连接正常，可以执行设备操作",
            "unauthorized": "请解锁手机并点击“允许USB调试”",
            "offline": "请重新插拔数据线或重启ADB",
            "recovery": "手机处于Recovery模式",
            "sideload": "手机处于ADB Sideload模式",
            "no permissions": "请检查Windows安卓ADB驱动",
        }
        return explanations.get(state, "需要检查设备连接状态")

    def _selected_device(self) -> tuple[int, dict[str, str]] | None:
        row = self.device_table.currentRow()
        if row < 0 or row >= len(self._device_records):
            QMessageBox.information(self, "请选择设备", "请先检测设备，然后在表格中选择一台手机。")
            return None
        return row, self._device_records[row]

    def test_selected_device(self) -> None:
        selected = self._selected_device()
        if selected is None:
            return
        row, record = selected
        if record["adb_state"] != "device":
            QMessageBox.warning(
                self,
                "设备不可用",
                self._state_explanation(record["adb_state"]),
            )
            return

        info = self.adb.device_info(record["serial"])
        if not any((info.manufacturer, info.model, info.android_version, info.sdk_version)):
            QMessageBox.warning(self, "连接测试失败", "ADB可以看到设备，但无法读取手机系统信息。")
            return

        model = " ".join(value for value in (info.manufacturer, info.model) if value).strip()
        android_version = info.android_version or "未知"
        if info.sdk_version:
            android_version = f"{android_version}（SDK {info.sdk_version}）"
        record["model"] = model or record["model"]
        record["android_version"] = info.android_version
        self.device_table.item(row, 2).setText(record["model"] or "未知型号")
        self.device_table.item(row, 3).setText(android_version)
        self.database.sync_devices(self._device_records)
        self.refresh_dashboard()
        QMessageBox.information(
            self,
            "连接测试成功",
            f"设备：{record['serial']}\n型号：{record['model'] or '未知'}\nAndroid：{android_version}",
        )

    def capture_selected_device(self) -> None:
        selected = self._selected_device()
        if selected is None:
            return
        _, record = selected
        if record["adb_state"] != "device":
            QMessageBox.warning(self, "设备不可用", self._state_explanation(record["adb_state"]))
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe_serial = re.sub(r"[^A-Za-z0-9_.-]", "_", record["serial"])
        destination = self.paths.diagnostics / f"device-{safe_serial}-{timestamp}.png"
        success, detail = self.adb.capture_screenshot(record["serial"], destination)
        if not success:
            QMessageBox.critical(self, "截图失败", detail)
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(detail))
        QMessageBox.information(self, "截图成功", f"截图已保存到：\n{detail}")

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
            #deviceHelp { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; color: #475569; }
            #planned { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 18px; }
            QPushButton { background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 8px 14px; }
            QPushButton:hover { background: #1d4ed8; }
            QTableWidget { background: white; border: 1px solid #e5e7eb; gridline-color: #eef2f7; }
            QHeaderView::section { background: #f8fafc; padding: 8px; border: 0; border-bottom: 1px solid #e5e7eb; }
            """
        )
