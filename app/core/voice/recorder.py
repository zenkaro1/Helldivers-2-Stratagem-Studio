"""Push-to-talk microphone capture."""

from __future__ import annotations

import threading

import numpy as np

try:
    import sounddevice as sd
except Exception:  # noqa: BLE001 - no audio stack installed
    sd = None

SAMPLE_RATE = 16000


def available() -> bool:
    return sd is not None


def list_input_devices() -> list[tuple[int, str]]:
    if sd is None:
        return []
    try:
        devices = sd.query_devices()
    except Exception:  # noqa: BLE001
        return []
    result = []
    for index, device in enumerate(devices):
        if device.get("max_input_channels", 0) > 0:
            name = str(device.get("name", f"Gerät {index}"))
            result.append((index, name))
    return result


class RecorderError(RuntimeError):
    pass


class MicrophoneRecorder:
    def __init__(self, device: int | None = None, sample_rate: int = SAMPLE_RATE):
        self.device = device
        self.sample_rate = sample_rate
        self._chunks: list[np.ndarray] = []
        self._stream = None
        self._lock = threading.Lock()
        self._peak = 0.0
        self._recording = False

    @property
    def recording(self) -> bool:
        return self._recording

    @property
    def peak(self) -> float:
        return self._peak

    def start(self) -> None:
        if sd is None:
            raise RecorderError("sounddevice ist nicht installiert.")
        if self._recording:
            return
        with self._lock:
            self._chunks = []
            self._peak = 0.0
        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
                callback=self._callback,
            )
            self._stream.start()
        except Exception as exc:  # noqa: BLE001
            self._stream = None
            raise RecorderError(f"Mikrofon konnte nicht geöffnet werden: {exc}") from exc
        self._recording = True

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        chunk = indata.copy()
        with self._lock:
            self._chunks.append(chunk)
            peak = float(np.max(np.abs(chunk))) if chunk.size else 0.0
            self._peak = max(self._peak, peak)

    def stop(self) -> np.ndarray | None:
        if not self._recording:
            return None
        self._recording = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:  # noqa: BLE001
                pass
        with self._lock:
            chunks = list(self._chunks)
            self._chunks = []
        if not chunks:
            return None
        audio = np.concatenate(chunks, axis=0).reshape(-1)
        return trim_silence(audio, self.sample_rate)


def trim_silence(audio: np.ndarray, sample_rate: int, threshold: float = 0.010,
                 pad_ms: int = 120) -> np.ndarray | None:
    """Cut leading/trailing silence; returns None when nothing audible was said."""
    if audio.size == 0:
        return None
    envelope = np.abs(audio)
    loud = np.flatnonzero(envelope > threshold)
    if loud.size == 0:
        return None
    start = max(0, loud[0] - int(sample_rate * pad_ms / 1000))
    end = min(audio.size, loud[-1] + int(sample_rate * pad_ms / 1000))
    return audio[start:end]
