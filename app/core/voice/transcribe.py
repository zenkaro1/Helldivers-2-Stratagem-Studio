"""Speech-to-text backends: local faster-whisper or an OpenAI-compatible API."""

from __future__ import annotations

import io
import threading
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

LANGUAGE_CODES = {"de": "de", "en": "en", "auto": None}


class TranscribeError(RuntimeError):
    pass


def to_wav_bytes(audio: np.ndarray, sample_rate: int = 16000) -> bytes:
    pcm = np.clip(audio, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype("<i2")
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return buffer.getvalue()


class LocalWhisper:
    """faster-whisper on CPU (int8).  The model downloads on first use."""

    def __init__(self, model_size: str = "small", language: str = "de",
                 models_dir: Path | None = None):
        self.model_size = model_size
        self.language = LANGUAGE_CODES.get(language, None)
        self.models_dir = models_dir
        self._model = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def preload(self, status_cb=None) -> None:
        self._ensure_model(status_cb)

    def _ensure_model(self, status_cb=None):
        with self._lock:
            if self._model is not None:
                return self._model
            try:
                from faster_whisper import WhisperModel
            except Exception as exc:  # noqa: BLE001
                raise TranscribeError(
                    "faster-whisper ist nicht installiert. Bitte die Abhängigkeiten "
                    "installieren oder in den Einstellungen den API-Modus wählen."
                ) from exc
            if status_cb:
                status_cb(f"Lade Whisper-Modell „{self.model_size}“ …")
            kwargs = {"device": "cpu", "compute_type": "int8"}
            if self.models_dir:
                self.models_dir.mkdir(parents=True, exist_ok=True)
                kwargs["download_root"] = str(self.models_dir)
            try:
                self._model = WhisperModel(self.model_size, **kwargs)
            except Exception as exc:  # noqa: BLE001
                raise TranscribeError(f"Whisper-Modell konnte nicht geladen werden: {exc}") from exc
            if status_cb:
                status_cb("Whisper bereit.")
            return self._model

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        model = self._ensure_model()
        try:
            segments, _info = model.transcribe(
                audio.astype(np.float32),
                language=self.language,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as exc:  # noqa: BLE001
            raise TranscribeError(f"Transkription fehlgeschlagen: {exc}") from exc


class OpenAIWhisper:
    """Any OpenAI-compatible /audio/transcriptions endpoint (OpenAI, Groq, ...)."""

    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1",
                 model: str = "whisper-1", language: str = "de"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.language = LANGUAGE_CODES.get(language, None)

    @property
    def loaded(self) -> bool:
        return bool(self.api_key)

    def preload(self, status_cb=None) -> None:
        if not self.api_key:
            raise TranscribeError("Kein API-Schlüssel hinterlegt.")
        if status_cb:
            status_cb("API-Modus bereit.")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        if not self.api_key:
            raise TranscribeError("Kein API-Schlüssel hinterlegt.")
        try:
            import requests
        except Exception as exc:  # noqa: BLE001
            raise TranscribeError("requests ist nicht installiert.") from exc
        data = {"model": self.model, "response_format": "json"}
        if self.language:
            data["language"] = self.language
        try:
            response = requests.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": ("audio.wav", to_wav_bytes(audio, sample_rate), "audio/wav")},
                data=data,
                timeout=60,
            )
        except Exception as exc:  # noqa: BLE001
            raise TranscribeError(f"API nicht erreichbar: {exc}") from exc
        if response.status_code >= 400:
            raise TranscribeError(f"API-Fehler {response.status_code}: {response.text[:200]}")
        try:
            return str(response.json().get("text", "")).strip()
        except ValueError as exc:
            raise TranscribeError("Ungültige API-Antwort.") from exc


@dataclass
class BackendConfig:
    backend: str
    model: str
    language: str
    api_key: str
    api_base: str
    api_model: str
    models_dir: Path | None


def build_backend(config: BackendConfig):
    if config.backend == "openai":
        return OpenAIWhisper(config.api_key, config.api_base, config.api_model, config.language)
    return LocalWhisper(config.model, config.language, config.models_dir)


def model_cached(model_size: str, models_dir: Path) -> bool:
    """True when the faster-whisper model was downloaded before (avoids surprises)."""
    try:
        return any(models_dir.glob(f"models--*faster-whisper-{model_size}"))
    except OSError:
        return False
