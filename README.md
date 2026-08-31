# Bluetooth Speaker Mirror (Pro)

## Download

⬇ **Download link: coming soon** — this repo is kept private (source
protected), so the installer is distributed via a separate public link
rather than GitHub Releases. Once published, the link will be added here.

The app works immediately with a **free 7-day trial** — no key, no email,
just install and use it. When the trial ends (or if you want to buy a
permanent license before then), email **resanul@gmail.com** with your
name — you'll get a license key back to paste into the app's
"Enter License Key..." dialog to keep using it.

---

A Windows app that mirrors **all** current system audio (YouTube, Spotify,
games, calls — anything) to **two Bluetooth speakers/headphones at once**,
with:

- A simple GUI (pick Speaker A / Speaker B from dropdowns)
- **Independent volume control** per speaker (0–150%)
- **Remembers** your last-used devices and volumes
- **System tray icon** (Show / Start / Stop / Exit) — closing the window
  minimizes to tray instead of quitting, if you want
- Optional **"Start with Windows"**
- A real Windows installer (`Setup.exe`) with a Start Menu shortcut
- **Offline license activation** — a 7-day free trial, then a signed
  license key unlocks it permanently (no internet/server needed). See
  `licensing/README.md` — that's the part *you* (the seller) use to issue
  keys to customers.

This builds on the earlier CLI script (`bt_speaker_mirror.py`) — same
underlying WASAPI-loopback-via-PyAudioWPatch approach, now wrapped in a
GUI and packaged as an installable app.

## Important: one build step happens on YOUR Windows machine

I can't cross-compile a Windows `.exe` from the Linux sandbox this was
written in — PyInstaller has to run on the target OS. So there's a
**one-time** build step:

1. You run `build\build.ps1` once on your Windows PC.
2. That produces `dist\BTSpeakerMirror\BTSpeakerMirror.exe` and, if you
   have Inno Setup installed, `installer\Output\BTSpeakerMirrorSetup.exe`
   — a normal double-click installer you (or anyone else) can then use to
   install the app, with a Start Menu shortcut, uninstaller, etc.

After that one build, you never need Python or this build step again to
*use* the app — only if you want to change the code and rebuild.

## Step 1: Run it from source first (recommended sanity check)

Before packaging, confirm it actually runs on your machine:

```powershell
pip install --user -r requirements.txt
python app\main.py
```

You should see the GUI window. Pick Speaker A and B, hit **Start
Mirroring**, and play some audio.

> Same PowerShell execution-policy note as before: if `.venv\Scripts\activate`
> is blocked, just skip the venv and use `pip install --user ...` as above.

## Step 1.5: Set up licensing (one time, before you sell/distribute)

The app works fine in trial mode without this — but to actually issue
paid license keys to customers, set up your private signing key once:

```powershell
cd licensing
pip install cryptography
python generate_license.py --init-keys
```

Copy the public key it prints into `app/license_manager.py`'s
`PUBLIC_KEY_B64`, then rebuild (Step 2 below). Full details, including how
to issue a key to a customer, are in `licensing/README.md`. Keep
`private_key.pem` secret — never put it in a build you hand out.

## Step 2: Build the installer (one time)

```powershell
.\build\build.ps1
```

This will:
1. `pip install` the app's dependencies plus `pyinstaller`.
2. Build `dist\BTSpeakerMirror\BTSpeakerMirror.exe`.
3. If **Inno Setup** is installed, also compile
   `installer\Output\BTSpeakerMirrorSetup.exe`.

If Inno Setup isn't installed, the script tells you so and still leaves
you with a fully working `BTSpeakerMirror.exe` (just not wrapped in a
Setup.exe yet). Inno Setup is free: https://jrsoftware.org/isdl.php —
install it, re-run `build\build.ps1`, done.

## Step 3: Install

Double-click `installer\Output\BTSpeakerMirrorSetup.exe`. It installs to
your user's Program Files, adds a Start Menu entry (and optionally a
Desktop shortcut, your choice during install), and registers an
uninstaller. No admin rights required (per-user install).

## Using the app

1. Pair and connect both Bluetooth speakers/headphones in **Windows
   Settings > Bluetooth & devices** first — this app doesn't pair devices.
2. Open **Bluetooth Speaker Mirror**.
3. Pick **Speaker A** and **Speaker B** from the dropdowns.
4. Adjust the volume sliders if one speaker is louder than the other.
5. Click **Start Mirroring**. Play anything — it should come out of both.
6. Closing the window minimizes to the system tray by default (uncheck
   "Minimize to tray when closed" if you'd rather it fully quit). Right-click
   (or click, on some Windows versions) the tray icon for Show / Start /
   Stop / Exit.
7. Check **Start with Windows** if you want it running automatically at
   login.

Your device choices and volumes are remembered automatically (stored in
`%APPDATA%\BTSpeakerMirror\config.json`) — devices are matched by name, so
if a device isn't connected next time, you'll just need to reselect it.

## Known limitations (same underlying constraints as the CLI version)

- **Some latency drift between the two speakers is normal** — Bluetooth
  transmission delay differs per device/chipset; this isn't fixable in
  software.
- WASAPI loopback only produces data while something is actually playing;
  if Windows is completely silent, capture pauses until playback resumes.
- If a Bluetooth device rejects the system audio's sample rate, this app
  automatically falls back to that device's own default rate with a
  lightweight on-the-fly resample.
- "Start with Windows" uses the per-user registry Run key (no admin
  needed), so it only starts the app for your Windows user account.
- The audio source is always the current Windows **default playback
  device** at the moment you click Start; if you change your system's
  default output device while mirroring, restart mirroring to pick it up.

## Troubleshooting

- **App won't start / crashes immediately** — run it from source
  (`python app\main.py`) instead of the packaged exe to see the actual
  error in the console.
- **"No WASAPI host API found"** — you're not on Windows, or PyAudioWPatch
  isn't installed correctly. Try `python -m pyaudiowpatch` to check.
- **Tray icon doesn't appear** — `pystray`/`Pillow` failed to load; the app
  still works without it (window-only), just without tray/minimize
  support. Re-run `pip install -r requirements.txt` and check for errors.
- **"Start with Windows" checkbox doesn't do anything** — it only works on
  Windows (uses the registry); on any other OS it shows a message and
  unchecks itself.
- **Crackling/dropouts** — this is controlled by `blocksize` in
  `%APPDATA%\BTSpeakerMirror\config.json` (default `1024`); try `2048` or
  `4096` for more stability at the cost of latency (edit the file while
  the app is closed, then relaunch).

## Project layout

```
bt_speaker_mirror_pro/
  app/
    main.py            GUI entry point
    audio_engine.py    Core WASAPI loopback + dual-output mirroring engine
    config.py          JSON config persistence
    autostart.py       Windows "start with Windows" (registry Run key)
    tray.py            System tray icon (pystray)
    license_manager.py Offline license verification (ships PUBLIC key only)
  licensing/
    generate_license.py  PRIVATE tool - issues license keys (keep off customer downloads)
    README.md             How to set up keys and issue licenses
  assets/
    icon.ico        App/installer icon
    icon.png        Tray icon
  build/
    bt_speaker_mirror.spec  PyInstaller build spec
    build.ps1               One-command build script (run on Windows)
  installer/
    setup.iss        Inno Setup installer script
  requirements.txt
```
