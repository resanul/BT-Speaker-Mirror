#!/usr/bin/env python3
"""
generate_license.py

PRIVATE tool for the app developer/seller. Do NOT ship this file, or the
`private_key.pem` it creates, to customers - anyone with the private key
can forge unlimited valid licenses for the app.

One-time setup
--------------
    python generate_license.py --init-keys

This creates `private_key.pem` (keep this secret, back it up somewhere
safe) and prints a public key. Paste that public key into
`app/license_manager.py`'s PUBLIC_KEY_B64 constant, then rebuild the app.
Until you do this, the app ships with a placeholder public key and will
reject every license (fails closed).

Issuing a license to a customer
--------------------------------
    python generate_license.py --customer "jane@example.com" --days 365

    # Lock it to one PC (ask the customer to run the app once and read the
    # "Machine ID" shown in its About/License dialog, or run
    # get_machine_id.py on their machine):
    python generate_license.py --customer "jane@example.com" --days 365 --machine-id XXXXXXXX-XXXX-...

    # Perpetual (no expiry) license:
    python generate_license.py --customer "jane@example.com" --no-expiry

Every issued license is appended to `licenses_issued.csv` in this folder
so you have your own record of who you sold a key to and when - this is
your distribution tracking, fully offline (no server, no phone-home).
"""

import argparse
import base64
import csv
import json
import os
import sys
from datetime import datetime, timedelta, timezone

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    print("ERROR: the 'cryptography' package is required. Install it with:")
    print("    pip install cryptography")
    sys.exit(1)

PRIVATE_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "private_key.pem")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "licenses_issued.csv")


def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def init_keys():
    if os.path.isfile(PRIVATE_KEY_PATH):
        print(f"A private key already exists at {PRIVATE_KEY_PATH}.")
        print("Refusing to overwrite it (that would invalidate every license you've already issued).")
        print("Delete it manually first if you really want a fresh key pair.")
        sys.exit(1)

    private_key = Ed25519PrivateKey.generate()
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(pem)

    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    public_b64 = _b64u_encode(public_bytes)

    print(f"Private key written to: {PRIVATE_KEY_PATH}")
    print("KEEP THIS FILE SECRET AND BACK IT UP. If you lose it, you can never issue")
    print("new licenses compatible with keys you've already given customers.\n")
    print("Paste this into app/license_manager.py as PUBLIC_KEY_B64, then rebuild the app:\n")
    print(f'PUBLIC_KEY_B64 = "{public_b64}"')


def load_private_key() -> "Ed25519PrivateKey":
    if not os.path.isfile(PRIVATE_KEY_PATH):
        print(f"ERROR: no private key found at {PRIVATE_KEY_PATH}.")
        print("Run: python generate_license.py --init-keys")
        sys.exit(1)
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def issue_license(customer: str, days, no_expiry: bool, machine_id: str):
    private_key = load_private_key()

    now = datetime.now(timezone.utc)
    expires = None
    if not no_expiry:
        if days is None:
            print("ERROR: pass --days N or --no-expiry.")
            sys.exit(1)
        expires = (now + timedelta(days=days)).isoformat()

    payload = {
        "customer": customer,
        "issued": now.isoformat(),
        "expires": expires,
        "machine_id": machine_id or None,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(payload_bytes)

    license_str = f"{_b64u_encode(payload_bytes)}.{_b64u_encode(signature)}"

    _log_issued(customer, now.isoformat(), expires, machine_id, license_str)

    print("\nLicense key (send this to the customer):\n")
    print(license_str)
    print(f"\nCustomer: {customer}")
    print(f"Expires:  {expires or 'never'}")
    print(f"Machine-locked: {machine_id or 'no'}")
    print(f"\nLogged to: {LOG_PATH}")


def _log_issued(customer, issued, expires, machine_id, license_str):
    is_new = not os.path.isfile(LOG_PATH)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["customer", "issued", "expires", "machine_id", "license_key"])
        writer.writerow([customer, issued, expires or "", machine_id or "", license_str])


def main():
    parser = argparse.ArgumentParser(description="Issue offline license keys for BT Speaker Mirror.")
    parser.add_argument("--init-keys", action="store_true", help="One-time: generate the signing key pair.")
    parser.add_argument("--customer", help="Customer name or email to embed in the license.")
    parser.add_argument("--days", type=int, help="License validity in days from now.")
    parser.add_argument("--no-expiry", action="store_true", help="Issue a perpetual (never-expiring) license.")
    parser.add_argument("--machine-id", default="", help="Lock the license to this machine ID (optional).")
    args = parser.parse_args()

    if args.init_keys:
        init_keys()
        return

    if not args.customer:
        parser.error("--customer is required (or use --init-keys for one-time setup).")

    issue_license(args.customer, args.days, args.no_expiry, args.machine_id)


if __name__ == "__main__":
    main()
