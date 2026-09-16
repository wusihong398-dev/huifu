from huifu.devices import parse_adb_devices


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

