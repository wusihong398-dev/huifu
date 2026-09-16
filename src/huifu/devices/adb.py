from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def model(self) -> str:
        return self.attributes.get("model", "")

    @property
    def connection_type(self) -> str:
        if self.serial.startswith("emulator-"):
            return "安卓模拟器"
        if ":" in self.serial:
            return "无线连接"
        return "USB连接"


@dataclass(frozen=True)
class AdbProbe:
    available: bool
    executable: str
    source: str
    version: str = ""
    error: str = ""


@dataclass(frozen=True)
class AndroidDeviceInfo:
    manufacturer: str = ""
    model: str = ""
    android_version: str = ""
    sdk_version: str = ""


def parse_adb_devices(output: str) -> list[AdbDevice]:
    devices: list[AdbDevice] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of devices") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state, *extra = parts
        attributes: dict[str, str] = {}
        for item in extra:
            if ":" in item:
                key, value = item.split(":", 1)
                attributes[key] = value
        devices.append(AdbDevice(serial=serial, state=state, attributes=attributes))
    return devices


def parse_android_properties(output: str) -> dict[str, str]:
    properties: dict[str, str] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line.startswith("[") or "]: [" not in line or not line.endswith("]"):
            continue
        key, value = line.split("]: [", 1)
        properties[key[1:]] = value[:-1]
    return properties


def _default_search_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        roots.extend((executable_dir, executable_dir / "_internal"))
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            roots.append(Path(bundle_dir))

    project_root = Path(__file__).resolve().parents[3]
    roots.extend((project_root, project_root / "vendor"))
    return roots


def resolve_adb_executable(
    explicit: str | os.PathLike[str] | None = None,
    search_roots: Iterable[Path] | None = None,
) -> tuple[str, str]:
    """Return the preferred ADB executable and a user-facing source label."""
    if explicit:
        explicit_text = os.fspath(explicit)
        explicit_path = Path(explicit_text).expanduser()
        if explicit_path.is_file():
            return str(explicit_path.resolve()), "指定路径"
        located = shutil.which(explicit_text)
        if located:
            return located, "指定命令"
        return explicit_text, "指定路径"

    configured = os.environ.get("HUIFU_ADB_PATH", "").strip()
    if configured:
        configured_path = Path(configured).expanduser()
        if configured_path.is_file():
            return str(configured_path.resolve()), "自定义ADB"

    executable_name = "adb.exe" if os.name == "nt" else "adb"
    roots = list(search_roots) if search_roots is not None else _default_search_roots()
    for root in roots:
        for candidate in (
            root / "platform-tools" / executable_name,
            root / executable_name,
        ):
            if candidate.is_file():
                return str(candidate.resolve()), "内置ADB"

    located = shutil.which("adb")
    if located:
        return located, "系统ADB"
    return "adb", "未找到"


class AdbService:
    def __init__(
        self,
        executable: str | os.PathLike[str] | None = None,
        *,
        search_roots: Iterable[Path] | None = None,
    ):
        self.executable, self.source = resolve_adb_executable(executable, search_roots)

    @staticmethod
    def _creation_flags() -> int:
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def _run(
        self,
        arguments: list[str],
        *,
        timeout: int = 15,
        binary: bool = False,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.executable, *arguments],
            capture_output=True,
            text=not binary,
            timeout=timeout,
            check=False,
            creationflags=self._creation_flags(),
        )

    def probe(self) -> AdbProbe:
        try:
            result = self._run(["version"], timeout=10)
        except FileNotFoundError:
            return AdbProbe(False, self.executable, self.source, error="未找到ADB程序")
        except PermissionError:
            return AdbProbe(False, self.executable, self.source, error="ADB没有运行权限")
        except subprocess.TimeoutExpired:
            return AdbProbe(False, self.executable, self.source, error="ADB启动超时")
        except OSError as exc:
            return AdbProbe(False, self.executable, self.source, error=str(exc))

        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()
        if result.returncode != 0:
            return AdbProbe(False, self.executable, self.source, error=error or output or "ADB启动失败")
        version = output.splitlines()[0] if output else "ADB可用"
        return AdbProbe(True, self.executable, self.source, version=version)

    def is_available(self) -> bool:
        return self.probe().available

    def list_devices(self) -> list[AdbDevice]:
        try:
            result = self._run(["devices", "-l"])
        except (OSError, subprocess.TimeoutExpired):
            return []
        if result.returncode != 0:
            return []
        return parse_adb_devices(result.stdout or "")

    def device_info(self, serial: str) -> AndroidDeviceInfo:
        try:
            result = self._run(["-s", serial, "shell", "getprop"], timeout=15)
        except (OSError, subprocess.TimeoutExpired):
            return AndroidDeviceInfo()
        if result.returncode != 0:
            return AndroidDeviceInfo()
        properties = parse_android_properties(result.stdout or "")
        return AndroidDeviceInfo(
            manufacturer=properties.get("ro.product.manufacturer", ""),
            model=properties.get("ro.product.model", ""),
            android_version=properties.get("ro.build.version.release", ""),
            sdk_version=properties.get("ro.build.version.sdk", ""),
        )

    def capture_screenshot(self, serial: str, destination: Path) -> tuple[bool, str]:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = self._run(
                ["-s", serial, "exec-out", "screencap", "-p"],
                timeout=30,
                binary=True,
            )
        except subprocess.TimeoutExpired:
            return False, "手机截图超时"
        except OSError as exc:
            return False, str(exc)

        if result.returncode != 0 or not result.stdout:
            error = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            return False, error or "手机没有返回截图"
        destination.write_bytes(result.stdout)
        return True, str(destination)
