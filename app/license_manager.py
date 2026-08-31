"""
license_manager.py

Offline, cryptographically-signed license verification for BT Speaker
Mirror. No internet connection is required or used.

How it works
------------
- License keys are Ed25519-signed JSON payloads (customer, issued date,
  optional expiry, optional machine lock), created by the separate
  `licensing/generate_license.py` tool (NOT shipped to end users - only
  the app developer runs it).
- This module ships only the Ed25519 PUBLIC key, embedded as PUBLIC_KEY_B64
  below. It can verify a signature was produced by the matching private
  key, but cannot itself produce valid new keys - so even a fully
  decompiled app can't be used to forge new licenses. Update
  PUBLIC_KEY_B64 after running generate_license.py's key-pair setup step.
- A free trial (TRIAL_DAYS) runs from first launch, tracked via a small
  local marker file, before a license becomes required.

Honesty note: since this app also ships as source, a sufficiently
determined person could patch this check out of the Python source
entirely. This scheme stops casual copying/sharing (the realistic threat
for a tool like this) - it is not designed to defeat a determined,
skilled attacker with full source access. For stronger protection, only
distribute the compiled Setup.exe to customers, not the source zip.
"""

import base64
import json
import os
import platform
import uuid
from datetime import datetime, timezone

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from config import get_config_dir

# Replace this with the public key printed by
# `python licensing/generate_license.py --init-keys` before shipping to
# customers. This placeholder will make ALL license keys fail verification
# until replaced - that's intentional (fails closed, not open).
PUBLIC_KEY_B64 = "REPLACE_WITH_YOUR_GENERATED_PUBLIC_KEY_BASE64"

TRIAL_DAYS = 7
LICENSE_FILENAME = "license.lic"
TRIAL_MARKER_FILENAME = "trial_start.json"


class LicenseError(Exception):
    pass


# --------------------------------------------------------------------------
# Machine fingerprint (for optional machine-locked licenses)
# --------------------------------------------------------------------------

def get_machine_id() -> str:
    """Best-effort stable machine identifier. Prefers the Windows
    MachineGuid (survives reinstalls of this app, tied to the OS install);
    falls back to a MAC-address-derived id on non-Windows or if the
    registry read fails, so this module stays importable/testable
    everywhere."""
    if platform.system() == "Windows":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0,
                winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
            ) as key:
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                return value
        except Exception:
            pass
    return f"fallback-{uuid.getnode():012x}"


# --------------------------------------------------------------------------
# License key format: base64url(payload_json) + "." + base64url(signature)
# --------------------------------------------------------------------------

def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(s: str) -> bytes:
    padding = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def encode_license(payload: dict, signature: bytes) -> str:
    payload_b64 = _b64u_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig_b64 = _b64u_encode(signature)
    return f"{payload_b64}.{sig_b64}"


def _decode_license(license_str: str):
    license_str = license_str.strip()
    if "." not in license_str:
        raise LicenseError("Malformed license key.")
    payload_b64, sig_b64 = license_str.split(".", 1)
    payload_bytes = _b64u_decode(payload_b64)
    signature = _b64u_decode(sig_b64)
    payload = json.loads(payload_bytes)
    return payload, payload_bytes, signature


def verify_license(license_str: str) -> dict:
    """Verify a license key string. Returns the payload dict on success.
    Raises LicenseError with a human-readable reason on failure."""
    if not CRYPTO_AVAILABLE:
        raise LicenseError("The 'cryptography' package is required to verify licenses.")

    try:
        payload, payload_bytes, signature = _decode_license(license_str)
    except Exception as e:
        raise LicenseError(f"Could not parse license key: {e}") from e

    try:
        public_key = Ed25519PublicKey.from_public_bytes(_b64u_decode(PUBLIC_KEY_B64))
        public_key.verify(signature, payload_bytes)
    except InvalidSignature as e:
        raise LicenseError("License key signature is invalid.") from e
    except Exception as e:
        raise LicenseError(f"Could not verify license key: {e}") from e

    expires = payload.get("expires")
    if expires:
        expires_dt = datetime.fromisoformat(expires)
        if expires_dt.tzinfo is None:
            expires_dt = expires_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires_dt:
            raise LicenseError(f"License expired on {expires}.")

    machine_id = payload.get("machine_id")
    if machine_id:
        current = get_machine_id()
        if machine_id != current:
            raise LicenseError("This license key is locked to a different computer.")

    return payload


# --------------------------------------------------------------------------
# Persistence: saved license + trial tracking
# --------------------------------------------------------------------------

def _license_path() -> str:
    return os.path.join(get_config_dir(), LICENSE_FILENAME)


def _trial_marker_path() -> str:
    return os.path.join(get_config_dir(), TRIAL_MARKER_FILENAME)


def save_license(license_str: str) -> None:
    os.makedirs(get_config_dir(), exist_ok=True)
    with open(_license_path(), "w", encoding="utf-8") as f:
        f.write(license_str.strip())


def load_saved_license() -> str:
    path = _license_path()
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _read_trial_start() -> datetime:
    path = _trial_marker_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return datetime.fromisoformat(data["started"])
        except Exception:
            pass
    # First run: create the marker now.
    os.makedirs(get_config_dir(), exist_ok=True)
    now = datetime.now(timezone.utc)
    tmp_path = _trial_marker_path() + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump({"started": now.isoformat()}, f)
    os.replace(tmp_path, _trial_marker_path())
    return now


def get_trial_status() -> dict:
    """Returns {"active": bool, "days_left": int}. days_left is 0 or
    negative once the trial has expired."""
    started = _read_trial_start()
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = datetime.now(timezone.utc) - started
    days_left = TRIAL_DAYS - elapsed.days
    return {"active": days_left > 0, "days_left": max(days_left, 0)}


def get_activation_status() -> dict:
    """Top-level check the GUI should call. Returns:
    {
        "allowed": bool,           # may the app be used right now
        "mode": "licensed" | "trial" | "expired" | "invalid",
        "message": str,            # human-readable summary
        "payload": dict or None,   # license payload, if licensed
    }
    """
    saved = load_saved_license()
    if saved:
        try:
            payload = verify_license(saved)
            return {
                "allowed": True,
                "mode": "licensed",
                "message": f"Licensed to {payload.get('customer', 'unknown')}",
                "payload": payload,
            }
        except LicenseError as e:
            # Fall through to trial status, but surface why the saved
            # license didn't work.
            trial = get_trial_status()
            if trial["active"]:
                return {
                    "allowed": True,
                    "mode": "trial",
                    "message": f"Saved license invalid ({e}). Trial: {trial['days_left']} day(s) left.",
                    "payload": None,
                }
            return {
                "allowed": False,
                "mode": "invalid",
                "message": f"Saved license invalid ({e}) and trial period has ended.",
                "payload": None,
            }

    trial = get_trial_status()
    if trial["active"]:
        return {
            "allowed": True,
            "mode": "trial",
            "message": f"Trial: {trial['days_left']} day(s) left.",
            "payload": None,
        }
    return {
        "allowed": False,
        "mode": "expired",
        "message": "Trial period has ended. Please enter a license key.",
        "payload": None,
    }
