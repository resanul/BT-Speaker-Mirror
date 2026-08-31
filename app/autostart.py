"""
autostart.py

Windows "start with Windows" support via the per-user registry Run key
(HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run). This does not
require admin rights (HKCU, not HKLM).

Safe to import on non-Windows systems: winreg only exists on Windows, so
everything here degrades to explicit EngineError-free no-ops guarded by
`is_supported()` when unavailable (e.g. this sandbox, or a future
cross-platform port), rather than crashing at import time.
"""

import sys

try:
    import winreg
except ImportError:
    winreg = None

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "BTSpeakerMirror"


def is_supported() -> bool:
    return winreg is not None


def build_launch_command(script_path: str) -> str:
    """Build the command line to register for autostart.

    - When frozen by PyInstaller (sys.frozen == True), sys.executable IS the
      packaged app - launch it directly with no arguments.
    - When running from source, sys.executable is the Python interpreter,
      so the command must also include the path to main.py, or Windows
      would just launch a bare Python REPL at login.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{script_path}"'


def is_enabled(script_path: str) -> bool:
    if not is_supported():
        return False
    expected = build_launch_command(script_path)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return value == expected
    except FileNotFoundError:
        return False
    except OSError:
        return False


def enable(script_path: str) -> None:
    if not is_supported():
        raise RuntimeError("Autostart is only supported on Windows.")
    command = build_launch_command(script_path)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)


def disable() -> None:
    if not is_supported():
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    except OSError:
        pass
