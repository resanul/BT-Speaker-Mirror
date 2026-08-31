# Licensing tool (private - keep this out of customer downloads)

This folder is for **you**, the developer/seller, only. Never send this
folder, `private_key.pem`, or `licenses_issued.csv` to a customer.

## One-time setup

```powershell
pip install cryptography
python generate_license.py --init-keys
```

This creates `private_key.pem` (back it up somewhere safe and private —
if you lose it, you can never issue new licenses compatible with keys
you've already sold) and prints a public key.

**Copy that public key into `app/license_manager.py`'s `PUBLIC_KEY_B64`**,
then rebuild the app (`build\build.ps1`). Until you do this, the shipped
app has a placeholder key and will reject every license — that's
intentional (fails closed, not open), so you can't accidentally ship an
app that accepts anyone's forged key.

## Issuing a license to a customer

```powershell
# Simple: 1-year license, not locked to a specific PC
python generate_license.py --customer "jane@example.com" --days 365

# Locked to one PC (ask the customer for the "Machine ID" shown in the
# app's License dialog first, then pass it here):
python generate_license.py --customer "jane@example.com" --days 365 --machine-id XXXXXXXX-XXXX-...

# Perpetual (never expires):
python generate_license.py --customer "jane@example.com" --no-expiry
```

The generated key prints to your terminal — send that string to the
customer (they paste it into the app's "Enter License Key..." dialog).

Every issued key is also appended to `licenses_issued.csv` in this folder
— that's your own private record of who you've sold a license to and
when. This is entirely local; nothing is sent anywhere.

## How the trial works

Every install gets 7 free days (from first launch) before the app
requires a key — no action needed from you, it's built into
`app/license_manager.py`'s `TRIAL_DAYS` constant (change it there if you
want a different trial length, then rebuild).

## Security notes

- The app only ships the **public** key — it can verify a license was
  signed by you, but can't forge new ones. Even someone who fully
  decompiles the app can't mint new working licenses from it.
- What it does NOT stop: someone with real reverse-engineering skill and
  access to the Python **source** (this zip) could patch the check out
  entirely. If you want stronger protection, only distribute the
  compiled `Setup.exe` from `build.ps1` to customers — don't hand out this
  source zip itself.
- Machine-locking ties a key to one PC's Windows `MachineGuid`. It's a
  deterrent against casual key-sharing, not a hardware DRM system.
