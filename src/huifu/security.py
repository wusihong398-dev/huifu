from __future__ import annotations

import ctypes
import os
from ctypes import wintypes


class SecretProtectionUnavailable(RuntimeError):
    pass


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte))), buffer


def protect_secret(value: str) -> bytes:
    if os.name != "nt":
        raise SecretProtectionUnavailable("API Key 加密仅在 Windows DPAPI 环境中可用")
    source, source_buffer = _blob(value.encode("utf-8"))
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptProtectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del source_buffer


def unprotect_secret(value: bytes) -> str:
    if os.name != "nt":
        raise SecretProtectionUnavailable("API Key 解密仅在 Windows DPAPI 环境中可用")
    source, source_buffer = _blob(value)
    output = _DataBlob()
    crypt32 = ctypes.windll.crypt32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(output)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
        del source_buffer

