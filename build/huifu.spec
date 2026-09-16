# -*- mode: python ; coding: utf-8 -*-

import os

from PyInstaller.utils.hooks import collect_data_files


project_root = os.path.abspath(os.path.join(SPECPATH, ".."))
entrypoint = os.path.join(project_root, "src", "huifu", "launcher.py")
source_root = os.path.join(project_root, "src")

datas = collect_data_files("PySide6")

# GitHub Actions downloads the official Android Platform Tools into vendor/.
# PyInstaller places them in _internal/platform-tools for the onedir build.
platform_tools = os.path.join(project_root, "vendor", "platform-tools")
if os.path.isdir(platform_tools):
    for current_dir, _directories, filenames in os.walk(platform_tools):
        relative_dir = os.path.relpath(current_dir, platform_tools)
        destination = "platform-tools" if relative_dir == "." else os.path.join("platform-tools", relative_dir)
        for filename in filenames:
            datas.append((os.path.join(current_dir, filename), destination))

a = Analysis(
    [entrypoint],
    pathex=[source_root],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HuifuAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="HuifuAI",
)
