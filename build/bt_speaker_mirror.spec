# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Bluetooth Speaker Mirror.
#
# Build (on Windows, from the project root):
#   pip install -r requirements.txt pyinstaller
#   pyinstaller build\bt_speaker_mirror.spec
#
# Output: dist\BTSpeakerMirror\BTSpeakerMirror.exe (a folder build, not
# --onefile, so startup is fast and the tray icon/assets are easy to find
# alongside the exe).

import os

block_cipher = None

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(SPEC), ".."))
APP_DIR = os.path.join(PROJECT_ROOT, "app")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

a = Analysis(
    [os.path.join(APP_DIR, "main.py")],
    pathex=[APP_DIR],
    binaries=[],
    datas=[
        (os.path.join(ASSETS_DIR, "icon.ico"), "assets"),
        (os.path.join(ASSETS_DIR, "icon.png"), "assets"),
    ],
    hiddenimports=[
        "pyaudiowpatch", "pystray._win32",
        "cryptography.hazmat.backends.openssl",
        "cryptography.hazmat.primitives.asymmetric.ed25519",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BTSpeakerMirror",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # windowed app, no console popup
    icon=os.path.join(ASSETS_DIR, "icon.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BTSpeakerMirror",
)
