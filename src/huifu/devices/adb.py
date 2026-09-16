from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    state: str
    attributes: dict[str, str] = field(default_factory=dict)

    @property
    def model(self) -> str:
        return self.attributes.get("model", "")


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


class AdbService:
    def __init__(self, executable: str | None = None):
        self.executable = executable or shutil.which("adb") or "adb"

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                [self.executable, "version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def list_devices(self) -> list[AdbDevice]:
        if not self.is_available():
            return []
        result = subprocess.run(
            [self.executable, "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return []
        return parse_adb_devices(result.stdout)

