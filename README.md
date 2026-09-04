# Bluetooth Speaker Mirror for Windows — Play Audio on Two Bluetooth Speakers at Once

**Bluetooth Speaker Mirror** is a lightweight Windows app that lets you
**play the same audio on two Bluetooth speakers or headphones simultaneously**
— something Windows 10 and Windows 11 don't support out of the box. Mirror
Spotify, YouTube, games, Zoom calls, or literally any sound your PC plays,
to two Bluetooth audio devices at the same time, in real time.

📥 **[Download the installer](https://github.com/resanul/BT-Speaker-Mirror/releases/download/v1.0.1/BTSpeakerMirrorSetup.exe)** · 🎁 **7-day free trial, no signup required** · 📧 **[Get a license](#pricing--license)**

---

## Table of Contents

- [Why this app exists](#why-this-app-exists)
- [Features](#features)
- [How it works](#how-it-works)
- [System requirements](#system-requirements)
- [Download](#download)
- [Installation guide](#installation-guide)
- [Free trial & pricing / license](#pricing--license)
- [Frequently asked questions](#frequently-asked-questions)
- [Support](#support)

## Why this app exists

Windows has no built-in way to **combine two Bluetooth audio outputs** or
**play the same sound on multiple Bluetooth speakers**. If you've ever
wanted to fill a room with two Bluetooth speakers, sync audio across two
sets of headphones, or mirror your PC's sound to a second Bluetooth
device for a party, presentation, or accessibility setup — Windows simply
won't let you pick two Bluetooth outputs at once.

**Bluetooth Speaker Mirror** solves this by capturing all current system
audio and streaming it to two independently connected Bluetooth
speakers or headphones at the same time — no cables, no third-party audio
mixers, no registry hacks.

## Features

- 🔊 **Mirror ALL system audio** — Spotify, YouTube, games, calls,
  notifications — anything Windows plays, mirrored live to two Bluetooth
  devices.
- 🎚 **Independent volume control** — separately adjust the volume of
  Speaker A and Speaker B (0–150%) if one device is quieter than the
  other.
- 🖥 **Simple, clean GUI** — pick your two Bluetooth speakers from a
  dropdown list, click Start, done.
- 🔁 **Remembers your setup** — your last-used devices and volume levels
  are saved automatically.
- 🧰 **System tray support** — runs quietly in the background; closing
  the window minimizes it instead of quitting.
- ⚙️ **Optional auto-start with Windows** — have it ready every time you
  log in.
- 📦 **Real Windows installer** — a proper `Setup.exe` with a Start Menu
  shortcut and clean uninstall, not a raw script.

## How it works

1. Pair and connect both Bluetooth speakers/headphones in **Windows
   Settings → Bluetooth & devices** first.
2. Open Bluetooth Speaker Mirror and select **Speaker A** and **Speaker B**
   from the device list.
3. Click **Start Mirroring** — whatever plays on your PC now comes out of
   both speakers at once.

Internally, the app uses Windows' WASAPI audio loopback capture to grab
your system's current audio output and re-streams it to two independent
Bluetooth output devices in real time.

## System requirements

- Windows 10 or Windows 11 (64-bit)
- Two Bluetooth speakers or headphones, each already paired and
  connected via Windows Bluetooth settings
- No installation of Python or any other runtime needed — the installer
  ships a fully standalone app

## Download

⬇ **[Download BTSpeakerMirrorSetup.exe](https://pub.hyperagent.com/api/published/pbf01M1CP9250_GWT8BC0XG9B0GT4K/BTSpeakerMirrorSetup.exe)**

No account, sign-up, or payment needed to try it — the installer includes
a full 7-day free trial.

## Installation guide

1. Download `BTSpeakerMirrorSetup.exe`.
2. Run it — no admin rights required (installs to your user profile).
3. Launch **Bluetooth Speaker Mirror** from the Start Menu.
4. Pick your two Bluetooth devices and hit **Start Mirroring**.

That's it — the app works immediately with a full-featured **7-day free
trial**.

## Pricing & License

- ✅ **Free 7-day trial** — every install starts with full functionality
  for 7 days. No email, no signup, no credit card.
- 💳 **After the trial**, a license key is required to keep using the app.
  Email **[resanul@gmail.com](mailto:resanul@gmail.com)** with your name
  to get a license key — you'll paste it into the app's
  "Enter License Key..." dialog to unlock it permanently.
- 🔒 Licenses are verified fully **offline** — no internet connection or
  account is ever required to run the app.

## Frequently asked questions

**Does this work with any Bluetooth speaker or headphone?**
Yes — any Bluetooth audio device that Windows can pair and show as a
playback device will work.

**Will there be audio delay/lag between the two speakers?**
A small amount of latency drift between the two speakers is normal and
expected — this comes from Bluetooth's own transmission delay, which
differs slightly per device, and isn't something any software can fully
eliminate.

**Do I need to keep both speakers exactly in sync sample-for-sample?**
The app mirrors the same audio stream to both devices in real time; minor
timing differences are inherent to Bluetooth audio hardware.

**Can I use this with wired speakers too?**
The app mirrors to any WASAPI playback device Windows recognizes,
including wired outputs — it's not limited to Bluetooth only.

**Is my data or audio sent anywhere online?**
No. All audio processing happens entirely on your PC. Licensing is
verified offline as well — nothing is uploaded or transmitted.

## Support

Questions, trial requests, or license purchases:
📧 **resanul@gmail.com**
