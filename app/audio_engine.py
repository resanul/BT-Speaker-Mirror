"""
audio_engine.py

Reusable, GUI-friendly engine for mirroring Windows system audio (WASAPI
loopback) to two Bluetooth (or any WASAPI) output devices at once, with
live per-device volume control.

This is a class-based refactor of the standalone bt_speaker_mirror.py CLI
script's logic (same PyAudioWPatch-based approach, same channel-adaptation
and per-device resample fallback), so it can be driven from a GUI: start()
returns immediately (streams run in background callback threads owned by
PortAudio), set_volume() can be called at any time while running, and
stop() cleanly tears everything down.
"""

import queue
import threading

import numpy as np

try:
    import pyaudiowpatch as pyaudio
except ImportError:
    pyaudio = None  # Allows this module to be imported (e.g. for tests) on
                     # non-Windows systems where PyAudioWPatch isn't installed.


class EngineError(Exception):
    """Raised for user-facing audio engine failures (missing WASAPI, no
    devices, failed to open a stream, etc.)."""


# --------------------------------------------------------------------------
# Device discovery (same approach as the CLI script, incl. the fix for
# get_device_info_generator_by_host_api's unreliable signature)
# --------------------------------------------------------------------------

def get_wasapi_info(p) -> dict:
    try:
        return p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError as e:
        raise EngineError(
            "No WASAPI host API found on this system. This app requires "
            "Windows with WASAPI support."
        ) from e


def list_output_devices(p, wasapi_index: int):
    """Return WASAPI device-info dicts with at least one output channel.

    Deliberately filters get_device_info_generator() manually by the plain
    `hostApi` field rather than using PyAudioWPatch's
    get_device_info_generator_by_host_api() convenience wrapper, whose
    accepted arguments have proven inconsistent across installed versions.
    """
    outputs = []
    for dev in p.get_device_info_generator():
        if dev.get("hostApi") != wasapi_index:
            continue
        if dev.get("maxOutputChannels", 0) < 1:
            continue
        outputs.append(dev)
    return outputs


def get_default_output_device(p, wasapi_info: dict) -> dict:
    idx = wasapi_info.get("defaultOutputDevice", -1)
    if idx is None or idx == -1:
        raise EngineError("Could not determine the current Windows default playback device.")
    return p.get_device_info_by_index(idx)


def find_loopback_device(p, default_speakers: dict) -> dict:
    if default_speakers.get("isLoopbackDevice"):
        return default_speakers
    for loopback in p.get_loopback_device_info_generator():
        if default_speakers["name"] in loopback["name"]:
            return loopback
    raise EngineError(
        "Could not find a loopback (capture) device matching the default "
        f"playback device '{default_speakers['name']}'."
    )


# --------------------------------------------------------------------------
# Audio helpers (unchanged from the CLI script's tested logic)
# --------------------------------------------------------------------------

def adapt_channels(block: np.ndarray, target_channels: int) -> np.ndarray:
    src_channels = block.shape[1]
    if src_channels == target_channels:
        return block
    if src_channels > target_channels:
        return block[:, :target_channels]
    reps = target_channels - src_channels
    extra = np.repeat(block[:, -1:], reps, axis=1)
    return np.concatenate([block, extra], axis=1)


def resample_linear(block: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    if orig_sr == target_sr or block.shape[0] == 0:
        return block
    n_in = block.shape[0]
    n_out = max(1, int(round(n_in * target_sr / orig_sr)))
    x_old = np.linspace(0.0, 1.0, n_in, endpoint=False)
    x_new = np.linspace(0.0, 1.0, n_out, endpoint=False)
    out = np.empty((n_out, block.shape[1]), dtype=np.float32)
    for ch in range(block.shape[1]):
        out[:, ch] = np.interp(x_new, x_old, block[:, ch])
    return out


# --------------------------------------------------------------------------
# Per-device output sink with live volume control
# --------------------------------------------------------------------------

class DeviceSink:
    QUEUE_MAXSIZE = 40

    def __init__(self, label, p, device_index, channels, output_samplerate,
                 source_samplerate, blocksize, get_volume):
        self.label = label
        self.p = p
        self.device_index = device_index
        self.channels = channels
        self.output_samplerate = output_samplerate
        self.source_samplerate = source_samplerate
        self.blocksize = blocksize
        self.get_volume = get_volume  # callable -> float, read live each push
        self.q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=self.QUEUE_MAXSIZE)
        self.stream = None
        self._leftover = np.zeros((0, channels), dtype=np.float32)

    def open(self):
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.output_samplerate,
            output=True,
            output_device_index=self.device_index,
            frames_per_buffer=self.blocksize,
            stream_callback=self._callback,
        )

    def _callback(self, in_data, frame_count, time_info, status):
        buf = self._leftover
        while buf.shape[0] < frame_count:
            try:
                block = self.q.get_nowait()
            except queue.Empty:
                break
            buf = np.concatenate([buf, block], axis=0)

        if buf.shape[0] >= frame_count:
            out = buf[:frame_count]
            self._leftover = buf[frame_count:]
        else:
            pad = np.zeros((frame_count - buf.shape[0], self.channels), dtype=np.float32)
            out = np.concatenate([buf, pad], axis=0)
            self._leftover = np.zeros((0, self.channels), dtype=np.float32)

        return (out.astype(np.float32, copy=False).tobytes(), pyaudio.paContinue)

    def push(self, block: np.ndarray) -> None:
        vol = self.get_volume()
        if vol != 1.0:
            block = block * vol
        if self.output_samplerate != self.source_samplerate:
            block = resample_linear(block, self.source_samplerate, self.output_samplerate)
        block = adapt_channels(block, self.channels).astype(np.float32, copy=False)
        try:
            self.q.put_nowait(block)
        except queue.Full:
            try:
                self.q.get_nowait()
                self.q.put_nowait(block)
            except queue.Empty:
                pass

    def close(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass


def open_sink_with_fallback(label, p, device_info, source_samplerate,
                             source_channels, blocksize, get_volume):
    channels = min(source_channels, int(device_info["maxOutputChannels"]) or source_channels)
    channels = max(channels, 1)

    sink = DeviceSink(label, p, device_info["index"], channels,
                       source_samplerate, source_samplerate, blocksize, get_volume)
    try:
        sink.open()
        return sink, None
    except Exception as e:
        fallback_sr = int(device_info["defaultSampleRate"])
        warning = (
            f"Could not open '{device_info['name']}' at {source_samplerate} Hz "
            f"({e}). Falling back to its default {fallback_sr} Hz with on-the-fly resampling."
        )
        sink = DeviceSink(label, p, device_info["index"], channels,
                           fallback_sr, source_samplerate, blocksize, get_volume)
        sink.open()
        return sink, warning


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

class MirrorEngine:
    """Owns the PyAudio instance and all streams for one mirroring session.
    Thread-safe enough for GUI use: start()/stop() should be called from one
    controller thread at a time (e.g. the GUI's main thread), while
    set_volume() may be called from the GUI thread at any time - it's a
    single float write per label, read by the audio callback threads."""

    def __init__(self, blocksize: int = 1024):
        if pyaudio is None:
            raise EngineError(
                "PyAudioWPatch is not installed. Install it with: pip install -r requirements.txt"
            )
        self.blocksize = blocksize
        self._p = None
        self._sinks = []
        self._capture_stream = None
        self._volumes = {"A": 1.0, "B": 1.0}
        self._lock = threading.Lock()
        self.running = False
        self.last_warnings = []

    # -- device discovery, usable before start() -------------------------

    def list_devices(self):
        """Return [(index, name, channels, default_rate), ...] for all
        WASAPI output devices. Opens and closes a throwaway PyAudio
        instance so this can be called for a device-refresh at any time,
        even while a mirror session is (or isn't) running."""
        p = pyaudio.PyAudio()
        try:
            wasapi_info = get_wasapi_info(p)
            devices = list_output_devices(p, wasapi_info["index"])
            return [
                {
                    "index": d["index"],
                    "name": d["name"],
                    "channels": d["maxOutputChannels"],
                    "default_rate": int(d["defaultSampleRate"]),
                }
                for d in devices
            ]
        finally:
            p.terminate()

    # -- volume -----------------------------------------------------------

    def set_volume(self, label: str, value: float) -> None:
        """value is a linear gain, e.g. 1.0 = 100%, 0.5 = 50%, 1.5 = 150%."""
        with self._lock:
            self._volumes[label] = max(0.0, value)

    def get_volume(self, label: str) -> float:
        with self._lock:
            return self._volumes.get(label, 1.0)

    # -- lifecycle ----------------------------------------------------------

    def start(self, device_a_index: int, device_b_index: int,
              volume_a: float = 1.0, volume_b: float = 1.0) -> list:
        """Start mirroring. Returns a list of non-fatal warning strings
        (e.g. sample-rate fallbacks). Raises EngineError on failure."""
        if self.running:
            raise EngineError("Already running - call stop() first.")

        self.set_volume("A", volume_a)
        self.set_volume("B", volume_b)
        warnings = []

        self._p = pyaudio.PyAudio()
        try:
            wasapi_info = get_wasapi_info(self._p)
            default_out_info = get_default_output_device(self._p, wasapi_info)
            loopback_info = find_loopback_device(self._p, default_out_info)

            loopback_channels = int(loopback_info["maxInputChannels"])
            loopback_samplerate = int(loopback_info["defaultSampleRate"])

            dev_a_info = self._p.get_device_info_by_index(device_a_index)
            dev_b_info = self._p.get_device_info_by_index(device_b_index)

            sink_a, warn_a = open_sink_with_fallback(
                "A", self._p, dev_a_info, loopback_samplerate, loopback_channels,
                self.blocksize, lambda: self.get_volume("A"),
            )
            sink_b, warn_b = open_sink_with_fallback(
                "B", self._p, dev_b_info, loopback_samplerate, loopback_channels,
                self.blocksize, lambda: self.get_volume("B"),
            )
            self._sinks = [sink_a, sink_b]
            for w in (warn_a, warn_b):
                if w:
                    warnings.append(w)

            def loopback_callback(in_data, frame_count, time_info, status):
                arr = np.frombuffer(in_data, dtype=np.float32).reshape(-1, loopback_channels)
                for sink in self._sinks:
                    sink.push(arr.copy())
                return (None, pyaudio.paContinue)

            self._capture_stream = self._p.open(
                format=pyaudio.paFloat32,
                channels=loopback_channels,
                rate=loopback_samplerate,
                input=True,
                input_device_index=loopback_info["index"],
                frames_per_buffer=self.blocksize,
                stream_callback=loopback_callback,
            )
            self.running = True
            self.last_warnings = warnings
            return warnings
        except EngineError:
            self._cleanup()
            raise
        except Exception as e:
            self._cleanup()
            raise EngineError(f"Failed to start mirroring: {e}") from e

    def stop(self) -> None:
        self._cleanup()
        self.running = False

    def _cleanup(self):
        if self._capture_stream is not None:
            try:
                self._capture_stream.stop_stream()
                self._capture_stream.close()
            except Exception:
                pass
            self._capture_stream = None
        for sink in self._sinks:
            sink.close()
        self._sinks = []
        if self._p is not None:
            try:
                self._p.terminate()
            except Exception:
                pass
            self._p = None
