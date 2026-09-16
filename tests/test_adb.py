import subprocess
from pathlib import Path

from huifu.devices import (
    AdbDevice,
    AdbService,
    parse_adb_devices,
    parse_android_properties,
    resolve_adb_executable,
)


def test_parse_adb_devices() -> None:
    output = """List of devices attached
emulator-5554 device product:sdk_gphone model:Pixel_7 device:emu transport_id:1
ABC123 unauthorized usb:1-2 transport_id:2
"""

    devices = parse_adb_devices(output)

    assert len(devices) == 2
    assert devices[0].serial == "emulator-5554"
    assert devices[0].state == "device"
    assert devices[0].model == "Pixel_7"
    assert devices[1].state == "unauthorized"


def test_parse_android_properties() -> None:
    output = """[ro.product.manufacturer]: [Xiaomi]
[ro.product.model]: [Redmi K50G]
[ro.build.version.release]: [14]
[ro.build.version.sdk]: [34]
"""

    properties = parse_android_properties(output)

    assert properties["ro.product.manufacturer"] == "Xiaomi"
    assert properties["ro.product.model"] == "Redmi K50G"
    assert properties["ro.build.version.release"] == "14"


def test_device_connection_type() -> None:
    assert AdbDevice("ABC123", "device").connection_type == "USB连接"
    assert AdbDevice("192.168.1.9:5555", "device").connection_type == "无线连接"
    assert AdbDevice("emulator-5554", "device").connection_type == "安卓模拟器"


def test_resolve_bundled_adb_before_path(tmp_path: Path, monkeypatch) -> None:
    executable_name = "adb.exe" if __import__("os").name == "nt" else "adb"
    bundled = tmp_path / "platform-tools" / executable_name
    bundled.parent.mkdir(parents=True)
    bundled.write_bytes(b"test")
    monkeypatch.setattr("huifu.devices.adb.shutil.which", lambda _name: "/system/adb")

    executable, source = resolve_adb_executable(search_roots=[tmp_path])

    assert executable == str(bundled.resolve())
    assert source == "内置ADB"


def test_capture_screenshot(tmp_path: Path, monkeypatch) -> None:
    service = AdbService(executable="adb")
    completed = subprocess.CompletedProcess([], 0, stdout=b"\x89PNG\r\n", stderr=b"")
    monkeypatch.setattr(service, "_run", lambda *_args, **_kwargs: completed)
    destination = tmp_path / "screen.png"

    success, detail = service.capture_screenshot("ABC123", destination)

    assert success is True
    assert detail == str(destination)
    assert destination.read_bytes() == b"\x89PNG\r\n"
