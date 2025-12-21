# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for g13 macOS menubar app.
Build with: pyinstaller build_macos.spec
"""

from pathlib import Path

root = Path(".").parent

a = Analysis(
    ["slop.py"],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "font"), "font"),
    ],
    hiddenimports=[
        "g13lib",
        "g13lib.apps",
        "g13lib.apps.davinci_resolve",
        "g13lib.apps.general",
        "g13lib.apps.vscode",
        "g13lib.device",
        "g13lib.device.g13_output",
        "g13lib.device.g13_usb_device",
        "g13lib.device.keycodes",
        "g13lib.lcd",
        "g13lib.lcd.images",
        "g13lib.lcd.terminal",
        "g13lib.monitors",
        "g13lib.monitors.current_app",
        "loguru",
        "rumps",
        "blinker",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="g13",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="g13",
)

app = BUNDLE(
    coll,
    name="g13.app",
    icon=None,
    bundle_identifier="com.local.g13",
    info_plist={
        "NSPrincipalClass": "NSApplication",
    },
)
