"""
main.py

Bluetooth Speaker Mirror - GUI application.

Mirrors all current Windows system audio to two Bluetooth (or any WASAPI)
speakers/headphones at once, with independent volume control for each,
a system tray icon, remembered device selection, and optional
"start with Windows".

Run from source:
    python main.py

Packaged (after building with PyInstaller, see build/README in the repo
root): double-click BTSpeakerMirror.exe, or install via the generated
Setup.exe for a Start Menu entry.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio_engine import MirrorEngine, EngineError  # noqa: E402
from config import load_config, save_config  # noqa: E402
import autostart  # noqa: E402
import license_manager  # noqa: E402

APP_TITLE = "Bluetooth Speaker Mirror"
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
ICON_ICO = os.path.join(ASSETS_DIR, "icon.ico")
ICON_PNG = os.path.join(ASSETS_DIR, "icon.png")


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.resizable(False, False)
        self._set_window_icon()

        self.config = load_config()
        self.engine = MirrorEngine(blocksize=self.config.get("blocksize", 1024))
        self.devices = []
        self.tray = None
        self.license_status = license_manager.get_activation_status()

        self._build_ui()
        self._refresh_devices(initial=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close_button)
        self._init_tray()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _set_window_icon(self):
        try:
            if os.path.isfile(ICON_ICO):
                self.root.iconbitmap(ICON_ICO)
        except Exception:
            pass  # Non-Windows or missing icon - not fatal.

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}
        frame = ttk.Frame(self.root)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text=APP_TITLE, font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad
        )

        # --- Device A ---
        ttk.Label(frame, text="Speaker A:").grid(row=1, column=0, sticky="w", **pad)
        self.device_a_var = tk.StringVar()
        self.device_a_combo = ttk.Combobox(frame, textvariable=self.device_a_var, width=38, state="readonly")
        self.device_a_combo.grid(row=1, column=1, sticky="we", **pad)

        self.volume_a_var = tk.DoubleVar(value=self.config.get("volume_a", 1.0) * 100)
        self.volume_a_label = ttk.Label(frame, text="100%")
        ttk.Label(frame, text="Volume A:").grid(row=2, column=0, sticky="w", **pad)
        self.volume_a_scale = ttk.Scale(
            frame, from_=0, to=150, variable=self.volume_a_var,
            command=lambda v: self._on_volume_change("A", v),
        )
        self.volume_a_scale.grid(row=2, column=1, sticky="we", **pad)
        self.volume_a_label.grid(row=2, column=2, sticky="w")

        # --- Device B ---
        ttk.Label(frame, text="Speaker B:").grid(row=3, column=0, sticky="w", **pad)
        self.device_b_var = tk.StringVar()
        self.device_b_combo = ttk.Combobox(frame, textvariable=self.device_b_var, width=38, state="readonly")
        self.device_b_combo.grid(row=3, column=1, sticky="we", **pad)

        self.volume_b_var = tk.DoubleVar(value=self.config.get("volume_b", 1.0) * 100)
        self.volume_b_label = ttk.Label(frame, text="100%")
        ttk.Label(frame, text="Volume B:").grid(row=4, column=0, sticky="w", **pad)
        self.volume_b_scale = ttk.Scale(
            frame, from_=0, to=150, variable=self.volume_b_var,
            command=lambda v: self._on_volume_change("B", v),
        )
        self.volume_b_scale.grid(row=4, column=1, sticky="we", **pad)
        self.volume_b_label.grid(row=4, column=2, sticky="w")

        # --- Refresh + Start/Stop ---
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=3, sticky="we", **pad)
        ttk.Button(btn_frame, text="Refresh Devices", command=self._refresh_devices).pack(side="left")
        self.start_button = ttk.Button(btn_frame, text="Start Mirroring", command=self._start)
        self.start_button.pack(side="left", padx=8)
        self.stop_button = ttk.Button(btn_frame, text="Stop", command=self._stop, state="disabled")
        self.stop_button.pack(side="left")

        # --- Options ---
        self.autostart_var = tk.BooleanVar(value=self.config.get("autostart", False))
        ttk.Checkbutton(
            frame, text="Start with Windows", variable=self.autostart_var,
            command=self._on_autostart_toggle,
        ).grid(row=6, column=0, columnspan=2, sticky="w", **pad)

        self.tray_var = tk.BooleanVar(value=self.config.get("minimize_to_tray", True))
        ttk.Checkbutton(
            frame, text="Minimize to tray when closed", variable=self.tray_var,
            command=self._save_current_config,
        ).grid(row=7, column=0, columnspan=2, sticky="w", **pad)

        # --- License ---
        license_frame = ttk.Frame(frame)
        license_frame.grid(row=8, column=0, columnspan=3, sticky="we", **pad)
        self.license_status_var = tk.StringVar(value=self.license_status["message"])
        license_color = "#1a7d1a" if self.license_status["mode"] == "licensed" else "#a15c00"
        self.license_label = ttk.Label(license_frame, textvariable=self.license_status_var, foreground=license_color)
        self.license_label.pack(side="left")
        ttk.Button(license_frame, text="Enter License Key...", command=self._open_license_dialog).pack(side="right")

        # --- Status ---
        self.status_var = tk.StringVar(value="Stopped")
        ttk.Label(frame, textvariable=self.status_var, foreground="#555").grid(
            row=9, column=0, columnspan=3, sticky="w", **pad
        )

        if not autostart.is_supported():
            # Non-Windows (e.g. testing this UI logic elsewhere) - disable
            # the control rather than let it silently fail.
            for child in frame.winfo_children():
                pass

    # ------------------------------------------------------------------
    # Device handling
    # ------------------------------------------------------------------

    def _refresh_devices(self, initial: bool = False):
        try:
            self.devices = self.engine.list_devices()
        except EngineError as e:
            messagebox.showerror(APP_TITLE, str(e))
            self.devices = []

        names = [d["name"] for d in self.devices]
        self.device_a_combo["values"] = names
        self.device_b_combo["values"] = names

        if initial:
            saved_a = self.config.get("device_a_name")
            saved_b = self.config.get("device_b_name")
            if saved_a in names:
                self.device_a_var.set(saved_a)
            elif names:
                self.device_a_var.set(names[0])
            if saved_b in names:
                self.device_b_var.set(saved_b)
            elif len(names) > 1:
                self.device_b_var.set(names[1])
        else:
            # Keep current selection if it still exists, else clear it.
            if self.device_a_var.get() not in names:
                self.device_a_var.set("")
            if self.device_b_var.get() not in names:
                self.device_b_var.set("")

    def _device_index_by_name(self, name: str):
        for d in self.devices:
            if d["name"] == name:
                return d["index"]
        return None

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    def _on_volume_change(self, label: str, value_str: str):
        pct = float(value_str)
        gain = pct / 100.0
        if label == "A":
            self.volume_a_label.config(text=f"{int(pct)}%")
            self.config["volume_a"] = gain
        else:
            self.volume_b_label.config(text=f"{int(pct)}%")
            self.config["volume_b"] = gain
        if self.engine.running:
            self.engine.set_volume(label, gain)
        # Debounced-ish: persist immediately, config writes are cheap/small.
        save_config(self.config)

    # ------------------------------------------------------------------
    # Start / Stop
    # ------------------------------------------------------------------

    def _start(self):
        self.license_status = license_manager.get_activation_status()
        if not self.license_status["allowed"]:
            messagebox.showwarning(APP_TITLE, self.license_status["message"])
            self._open_license_dialog()
            return

        name_a = self.device_a_var.get()
        name_b = self.device_b_var.get()
        if not name_a or not name_b:
            messagebox.showwarning(APP_TITLE, "Please select both Speaker A and Speaker B.")
            return
        if name_a == name_b:
            messagebox.showwarning(APP_TITLE, "Speaker A and Speaker B must be different devices.")
            return

        idx_a = self._device_index_by_name(name_a)
        idx_b = self._device_index_by_name(name_b)
        if idx_a is None or idx_b is None:
            messagebox.showerror(APP_TITLE, "Selected device is no longer available. Try Refresh Devices.")
            return

        try:
            warnings = self.engine.start(
                idx_a, idx_b,
                volume_a=self.volume_a_var.get() / 100.0,
                volume_b=self.volume_b_var.get() / 100.0,
            )
        except EngineError as e:
            messagebox.showerror(APP_TITLE, str(e))
            return

        self.status_var.set(f"Mirroring to: {name_a}  +  {name_b}")
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.device_a_combo.config(state="disabled")
        self.device_b_combo.config(state="disabled")

        if warnings:
            messagebox.showwarning(APP_TITLE, "\n\n".join(warnings))

        self.config["device_a_name"] = name_a
        self.config["device_b_name"] = name_b
        save_config(self.config)

    def _stop(self):
        self.engine.stop()
        self.status_var.set("Stopped")
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.device_a_combo.config(state="readonly")
        self.device_b_combo.config(state="readonly")

    # ------------------------------------------------------------------
    # Autostart
    # ------------------------------------------------------------------

    def _on_autostart_toggle(self):
        if not autostart.is_supported():
            messagebox.showinfo(APP_TITLE, "Start with Windows is only available on Windows.")
            self.autostart_var.set(False)
            return
        script_path = os.path.abspath(__file__)
        try:
            if self.autostart_var.get():
                autostart.enable(script_path)
            else:
                autostart.disable()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Could not update Windows startup setting: {e}")
            self.autostart_var.set(not self.autostart_var.get())
            return
        self._save_current_config()

    def _save_current_config(self):
        self.config["autostart"] = self.autostart_var.get()
        self.config["minimize_to_tray"] = self.tray_var.get()
        save_config(self.config)

    # ------------------------------------------------------------------
    # License
    # ------------------------------------------------------------------

    def _open_license_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("License")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        pad = {"padx": 10, "pady": 6}

        ttk.Label(dialog, text=self.license_status["message"], wraplength=380).grid(
            row=0, column=0, columnspan=2, sticky="w", **pad
        )

        machine_id = license_manager.get_machine_id()
        ttk.Label(dialog, text="Your Machine ID (send this if your license is machine-locked):").grid(
            row=1, column=0, columnspan=2, sticky="w", **pad
        )
        machine_id_entry = ttk.Entry(dialog, width=48)
        machine_id_entry.insert(0, machine_id)
        machine_id_entry.config(state="readonly")
        machine_id_entry.grid(row=2, column=0, columnspan=2, sticky="we", **pad)

        ttk.Label(dialog, text="License key:").grid(row=3, column=0, sticky="w", **pad)
        key_entry = ttk.Entry(dialog, width=48)
        key_entry.grid(row=4, column=0, columnspan=2, sticky="we", **pad)

        result_var = tk.StringVar(value="")
        ttk.Label(dialog, textvariable=result_var, foreground="#a11").grid(
            row=5, column=0, columnspan=2, sticky="w", **pad
        )

        def activate():
            key = key_entry.get().strip()
            if not key:
                result_var.set("Please paste a license key.")
                return
            try:
                license_manager.verify_license(key)
            except license_manager.LicenseError as e:
                result_var.set(str(e))
                return
            license_manager.save_license(key)
            self.license_status = license_manager.get_activation_status()
            self.license_status_var.set(self.license_status["message"])
            self.license_label.config(
                foreground="#1a7d1a" if self.license_status["mode"] == "licensed" else "#a15c00"
            )
            messagebox.showinfo(APP_TITLE, "License activated. Thank you!")
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=6, column=0, columnspan=2, sticky="e", **pad)
        ttk.Button(btn_frame, text="Activate", command=activate).pack(side="right")
        ttk.Button(btn_frame, text="Close", command=dialog.destroy).pack(side="right", padx=6)

    # ------------------------------------------------------------------
    # Tray
    # ------------------------------------------------------------------

    def _init_tray(self):
        try:
            from tray import TrayIcon
        except Exception:
            self.tray = None
            return
        try:
            self.tray = TrayIcon(
                icon_path=ICON_PNG,
                dispatch=lambda fn: self.root.after(0, fn),
                on_show=self._show_window,
                on_start=self._start,
                on_stop=self._stop,
                on_exit=self._exit_app,
            )
            self.tray.start()
        except Exception:
            self.tray = None  # pystray/Pillow missing - tray is optional.

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _on_close_button(self):
        self._save_current_config()
        if self.tray_var.get() and self.tray is not None:
            self.root.withdraw()
        else:
            self._exit_app()

    def _exit_app(self):
        self._save_current_config()
        try:
            self.engine.stop()
        except Exception:
            pass
        if self.tray is not None:
            self.tray.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
