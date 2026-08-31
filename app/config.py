"""
config.py

Small JSON config persistence for BT Speaker Mirror: remembers the last
two chosen output devices (by NAME, since device indices can shift across
reboots or reconnects), their volumes, and UI preferences (autostart,
minimize-to-tray).

Config lives at %APPDATA%\\BTSpeakerMirror\\config.json on Windows. Falls
back to a local file next to this module on other platforms (useful when
testing this module outside Windows).
"""

import os
import json

CONFIG_FILENAME = "config.json"

DEFAULT_CONFIG = {
    "device_a_name": None,
    "device_b_name": None,
    "volume_a": 1.0,
    "volume_b": 1.0,
    "autostart": False,
    "minimize_to_tray": True,
    "blocksize": 1024,
}


def get_config_dir() -> str:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, "BTSpeakerMirror")
    # Non-Windows fallback (sandbox testing, or a future cross-platform port)
    return os.path.join(os.path.expanduser("~"), ".bt_speaker_mirror")


def get_config_path() -> str:
    return os.path.join(get_config_dir(), CONFIG_FILENAME)


def load_config() -> dict:
    path = get_config_path()
    config = dict(DEFAULT_CONFIG)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                config.update({k: v for k, v in loaded.items() if k in DEFAULT_CONFIG})
        except (OSError, json.JSONDecodeError):
            # Corrupt or unreadable config - fall back to defaults rather
            # than crash the app on startup.
            pass
    return config


def save_config(config: dict) -> None:
    directory = get_config_dir()
    os.makedirs(directory, exist_ok=True)
    path = get_config_path()
    # Only persist known keys, to avoid an ever-growing file if callers pass
    # extra transient state by mistake.
    to_save = {k: config.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(to_save, f, indent=2)
    os.replace(tmp_path, path)
