"""
tray.py

System tray icon wrapper using pystray. Runs the tray icon's event loop on
its own thread (pystray requirement on Windows) and marshals all menu
actions back onto the GUI's Tk main loop via a supplied `dispatch`
callable (typically `root.after(0, fn)`), since Tkinter is not thread-safe.
"""

import os
import threading

try:
    import pystray
    from PIL import Image
except ImportError:
    pystray = None
    Image = None


def _load_icon_image(icon_path: str):
    if Image is None:
        return None
    if icon_path and os.path.isfile(icon_path):
        try:
            return Image.open(icon_path)
        except Exception:
            pass
    # Fallback: draw a simple blue circle with "BT" so the app still has a
    # usable tray icon even if the packaged icon asset is missing.
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    try:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        draw.ellipse((2, 2, 62, 62), fill=(30, 100, 200, 255))
        draw.text((16, 22), "BT", fill=(255, 255, 255, 255))
    except Exception:
        pass
    return img


class TrayIcon:
    """Wraps a pystray.Icon. Call start() once; stop() to tear down."""

    def __init__(self, icon_path: str, dispatch, on_show, on_start, on_stop, on_exit):
        if pystray is None:
            raise RuntimeError(
                "pystray/Pillow are not installed. Install them with: "
                "pip install -r requirements.txt"
            )
        self.dispatch = dispatch
        self._icon = pystray.Icon(
            "BTSpeakerMirror",
            _load_icon_image(icon_path),
            "Bluetooth Speaker Mirror",
            menu=pystray.Menu(
                pystray.MenuItem("Show", lambda: self.dispatch(on_show), default=True),
                pystray.MenuItem("Start Mirroring", lambda: self.dispatch(on_start)),
                pystray.MenuItem("Stop Mirroring", lambda: self.dispatch(on_stop)),
                pystray.MenuItem("Exit", lambda: self.dispatch(on_exit)),
            ),
        )
        self._thread = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass
