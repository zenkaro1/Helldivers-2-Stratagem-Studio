"""Voice page: push-to-talk, speech model settings, history."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...core.keymap import pretty_key
from ...core.voice.matcher import VoiceMatch
from ...core.voice.recorder import available as audio_available
from ...core.voice.recorder import list_input_devices
from .. import theme
from ..widgets import HotkeyEdit, section_label

MODELS = ["tiny", "base", "small", "medium", "large-v3"]
LANGUAGES = [("Deutsch", "de"), ("Englisch", "en"), ("Automatisch", "auto")]


class LevelBar(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._level = 0.0

    def set_level(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        if abs(value - self._level) > 0.01:
            self._level = value
            self.update()

    def paintEvent(self, _event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.BORDER))
        painter.drawRoundedRect(self.rect(), 3, 3)
        if self._level > 0.01:
            width = int(self.width() * self._level)
            painter.setBrush(QColor(theme.RED))
            painter.drawRoundedRect(0, 0, max(6, width), self.height(), 3, 3)


class VoicePage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._build()
        self._refresh_from_settings()
        ctx.voice_state.connect(self._on_state)
        ctx.voice_text.connect(self._on_text)
        ctx.voice_match.connect(self._on_match)
        ctx.info.connect(self._on_info)
        self._level_timer = QTimer(self)
        self._level_timer.setInterval(70)
        self._level_timer.timeout.connect(self._poll_level)
        self._level_timer.start()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(18)

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(section_label("Sprachsteuerung"))
        title = QLabel("STIMME")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        subtitle = QLabel("Taste halten, Stratagem sagen – die App tippt den Code.")
        subtitle.setObjectName("muted")
        subtitle.setWordWrap(True)
        header.addWidget(subtitle)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        form = QVBoxLayout(settings_card)
        form.setContentsMargins(18, 16, 18, 16)
        form.setSpacing(10)
        form.addWidget(section_label("Erkennung"))

        self.ptt_edit = HotkeyEdit(self.ctx.settings.voice.ptt_key)
        self.ptt_edit.changed.connect(self._set_ptt)
        form.addLayout(self._row("Push-to-Talk", self.ptt_edit))

        self.mic = QComboBox()
        self.mic.addItem("Standardgerät", None)
        for index, name in list_input_devices():
            self.mic.addItem(name, index)
        self.mic.currentIndexChanged.connect(self._set_device)
        form.addLayout(self._row("Mikrofon", self.mic))

        self.backend = QComboBox()
        self.backend.addItem("Lokal (faster-whisper)", "local")
        self.backend.addItem("OpenAI-kompatible API", "openai")
        self.backend.currentIndexChanged.connect(self._set_backend)
        form.addLayout(self._row("Backend", self.backend))

        self.model = QComboBox()
        for name in MODELS:
            self.model.addItem(name, name)
        self.model.currentIndexChanged.connect(self._set_model)
        self.local_box = QWidget()
        local_layout = QVBoxLayout(self.local_box)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(10)
        local_layout.addLayout(self._row("Whisper-Modell", self.model))
        form.addWidget(self.local_box)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key.setPlaceholderText("sk-…")
        self.api_key.editingFinished.connect(self._set_api)
        self.api_base = QLineEdit()
        self.api_base.editingFinished.connect(self._set_api)
        self.api_box = QWidget()
        api_layout = QVBoxLayout(self.api_box)
        api_layout.setContentsMargins(0, 0, 0, 0)
        api_layout.setSpacing(10)
        api_layout.addLayout(self._row("API-Schlüssel", self.api_key))
        api_layout.addLayout(self._row("API-Basis-URL", self.api_base))
        form.addWidget(self.api_box)

        self.language = QComboBox()
        for label, value in LANGUAGES:
            self.language.addItem(label, value)
        self.language.currentIndexChanged.connect(self._set_language)
        form.addLayout(self._row("Sprache", self.language))

        self.threshold = QSlider(Qt.Orientation.Horizontal)
        self.threshold.setRange(40, 92)
        self.threshold.setValue(int(self.ctx.settings.voice.threshold * 100))
        self.threshold.valueChanged.connect(self._set_threshold)
        self.threshold_label = QLabel("")
        self.threshold_label.setFixedWidth(40)
        self.threshold_label.setStyleSheet(f"color: {theme.MUTED}; font-family: Consolas;")
        row = self._row("Treffer-Schwelle", self.threshold)
        row.addWidget(self.threshold_label)
        form.addLayout(row)

        self.only_loadout = QCheckBox("Nur Stratagems aus dem aktiven Loadout erkennen")
        self.only_loadout.toggled.connect(self._set_only_loadout)
        form.addWidget(self.only_loadout)

        form.addSpacing(6)
        self.load_button = QPushButton("MODELL VORLADEN")
        self.load_button.setObjectName("primary")
        self.load_button.clicked.connect(self.ctx.preload_voice)
        form.addWidget(self.load_button)
        self.model_status = QLabel("")
        self.model_status.setWordWrap(True)
        self.model_status.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        form.addWidget(self.model_status)
        download_hint = QLabel(
            "Beim ersten Mal wird das Sprachmodell einmalig geladen, danach läuft "
            "alles offline."
        )
        download_hint.setWordWrap(True)
        download_hint.setStyleSheet(f"color: #6c7062; font-size: 8pt;")
        form.addWidget(download_hint)

        form.addSpacing(10)
        self.keyword_button = QPushButton("EIGENE KEYWORDS")
        self.keyword_button.setObjectName("ghost")
        self.keyword_button.clicked.connect(self._open_keywords)
        form.addWidget(self.keyword_button)
        self.keyword_status = QLabel("")
        self.keyword_status.setWordWrap(True)
        self.keyword_status.setStyleSheet(f"color: {theme.MUTED}; font-size: 8pt;")
        form.addWidget(self.keyword_status)
        self._update_keyword_status()
        form.addStretch(1)
        body.addWidget(settings_card, 0)

        right = QVBoxLayout()
        right.setSpacing(14)

        ptt_card = QFrame()
        ptt_card.setObjectName("card")
        ptt_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        ptt_layout = QVBoxLayout(ptt_card)
        ptt_layout.setContentsMargins(20, 18, 20, 18)
        ptt_layout.setSpacing(10)
        ptt_layout.addWidget(section_label("Push-to-Talk"))
        self.ptt_label = QLabel("F8 HALTEN & SPRECHEN")
        self.ptt_label.setStyleSheet(
            f"color: {theme.ACCENT}; font-size: 17pt; font-weight: 600; letter-spacing: 1px;"
        )
        ptt_layout.addWidget(self.ptt_label)
        self.state_label = QLabel("Bereit – Taste halten und Stratagem nennen.")
        self.state_label.setStyleSheet(f"color: {theme.MUTED}; font-size: 9.5pt;")
        ptt_layout.addWidget(self.state_label)
        self.level = LevelBar()
        ptt_layout.addWidget(self.level)
        self.transcript = QLabel("")
        self.transcript.setWordWrap(True)
        self.transcript.setStyleSheet(
            f"color: {theme.TEXT}; font-size: 11pt; font-style: italic;"
        )
        ptt_layout.addWidget(self.transcript)
        right.addWidget(ptt_card, 2)

        test_row = QHBoxLayout()
        test_row.setSpacing(8)
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("Text testen, z. B. „Adler fünfhundert Kilo“ …")
        self.test_input.returnPressed.connect(self._test_text)
        test_row.addWidget(self.test_input, 1)
        test_button = QPushButton("PRÜFEN")
        test_button.clicked.connect(self._test_text)
        test_row.addWidget(test_button)
        right.addLayout(test_row)

        history_card = QFrame()
        history_card.setObjectName("card")
        history_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(16, 14, 16, 14)
        history_layout.setSpacing(6)
        history_layout.addWidget(section_label("Verlauf"))
        self.history_hint = QLabel(
            "Noch keine Befehle. Halte die Push-to-Talk-Taste und sage z. B. "
            "„Nachschub“ oder „Adler 500 Kilo“."
        )
        self.history_hint.setWordWrap(True)
        self.history_hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        history_layout.addWidget(self.history_hint)
        self.history = QListWidget()
        self.history.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        history_layout.addWidget(self.history, 1)
        if not audio_available():
            warning = QLabel("Kein Audio-Backend gefunden (sounddevice fehlt).")
            warning.setStyleSheet(f"color: {theme.RED}; font-size: 8.5pt;")
            history_layout.addWidget(warning)
        right.addWidget(history_card, 3)

        body.addLayout(right, 1)
        root.addLayout(body, 1)

    def _row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        tag = QLabel(label)
        tag.setFixedWidth(150)
        tag.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        row.addWidget(tag)
        row.addWidget(widget, 1)
        return row

    def _open_keywords(self) -> None:
        from ..dialogs import KeywordDialog

        KeywordDialog(self.ctx, self).exec()
        self._update_keyword_status()

    def _update_keyword_status(self) -> None:
        count = len(self.ctx.all_custom_keywords())
        if count:
            self.keyword_status.setText(
                f"{count} eigene Begriffe aktiv – sie zählen zusätzlich zu den "
                "eingebauten Namen.")
        else:
            self.keyword_status.setText(
                "Noch keine eigenen Begriffe – z. B. „380“ für die 380-mm-Barrage.")

    # ------------------------------------------------------------------
    def _refresh_from_settings(self) -> None:
        voice = self.ctx.settings.voice
        self.ptt_edit.blockSignals(True)
        self.ptt_edit.set_key(voice.ptt_key)
        self.ptt_edit.blockSignals(False)
        self.ptt_label.setText(f"{pretty_key(voice.ptt_key)} HALTEN & SPRECHEN")

        position = self.mic.findData(voice.device)
        self.mic.blockSignals(True)
        self.mic.setCurrentIndex(position if position >= 0 else 0)
        self.mic.blockSignals(False)

        index = self.backend.findData(voice.backend)
        self.backend.blockSignals(True)
        self.backend.setCurrentIndex(max(0, index))
        self.backend.blockSignals(False)

        index = self.model.findData(voice.model)
        self.model.blockSignals(True)
        self.model.setCurrentIndex(max(0, index))
        self.model.blockSignals(False)

        index = self.language.findData(voice.language)
        self.language.blockSignals(True)
        self.language.setCurrentIndex(max(0, index))
        self.language.blockSignals(False)

        self.api_key.setText(voice.api_key)
        self.api_base.setText(voice.api_base)
        self.only_loadout.blockSignals(True)
        self.only_loadout.setChecked(voice.only_loadout)
        self.only_loadout.blockSignals(False)
        self.threshold.blockSignals(True)
        self.threshold.setValue(int(voice.threshold * 100))
        self.threshold.blockSignals(False)
        self.threshold_label.setText(f"{voice.threshold:.2f}")
        self._update_backend_visibility()

    def _update_backend_visibility(self) -> None:
        local = self.ctx.settings.voice.backend == "local"
        self.local_box.setVisible(local)
        self.api_box.setVisible(not local)

    # ------------------------------------------------------------------
    def _set_ptt(self, key: str) -> None:
        self.ctx.settings.voice.ptt_key = key
        self.ctx.apply_ptt()
        self.ctx.save_settings()
        self.ptt_label.setText(f"{pretty_key(key)} HALTEN & SPRECHEN")
        self.model_status.setText(f"Push-to-Talk: {pretty_key(key)}")

    def _set_device(self, *_args) -> None:
        self.ctx.settings.voice.device = self.mic.currentData()
        self.ctx.save_settings()

    def _set_backend(self, *_args) -> None:
        self.ctx.settings.voice.backend = self.backend.currentData()
        self.ctx.save_settings()
        self._update_backend_visibility()
        self.ctx.preload_voice()

    def _set_model(self, *_args) -> None:
        self.ctx.settings.voice.model = self.model.currentData()
        self.ctx.save_settings()
        self.model_status.setText("Modell geändert – „Modell vorladen“ startet den Download.")

    def _set_language(self, *_args) -> None:
        self.ctx.settings.voice.language = self.language.currentData()
        self.ctx.save_settings()

    def _set_api(self) -> None:
        self.ctx.settings.voice.api_key = self.api_key.text().strip()
        self.ctx.settings.voice.api_base = self.api_base.text().strip() or "https://api.openai.com/v1"
        self.ctx.save_settings()

    def _set_threshold(self, value: int) -> None:
        self.ctx.settings.voice.threshold = value / 100.0
        self.ctx.matcher.threshold = self.ctx.settings.voice.threshold
        self.threshold_label.setText(f"{value / 100:.2f}")
        self.ctx.save_settings()

    def _set_only_loadout(self, value: bool) -> None:
        self.ctx.settings.voice.only_loadout = value
        self.ctx.save_settings()

    # ------------------------------------------------------------------
    def _poll_level(self) -> None:
        recorder = getattr(self.ctx, "_recorder", None)
        if recorder is not None and recorder.recording:
            self.level.set_level(min(1.0, recorder.peak * 6.0))
        else:
            self.level.set_level(0.0)

    def _on_state(self, state: str) -> None:
        texts = {
            "idle": "Bereit – Taste halten und Stratagem nennen.",
            "listening": "Aufnahme läuft …",
            "transcribing": "Erkenne Sprache …",
            "loading": "Modell wird geladen …",
        }
        self.state_label.setText(texts.get(state, state))
        if state == "listening":
            self.ptt_label.setStyleSheet(
                f"color: {theme.RED}; font-size: 17pt; font-weight: 600; letter-spacing: 1px;"
            )
        else:
            self.ptt_label.setStyleSheet(
                f"color: {theme.ACCENT}; font-size: 17pt; font-weight: 600; letter-spacing: 1px;"
            )

    def _on_text(self, text: str) -> None:
        self.transcript.setText(f"„{text}“" if text else "")

    def _on_match(self, match: VoiceMatch) -> None:
        if match.stratagem is not None:
            detail = f"{match.score:.2f}  ·  {match.stratagem.code_pretty}"
            self._add_history(f"„{match.spoken}“  →  {match.stratagem.name}", detail, True)
        elif match.slot is not None:
            self._add_history(f"„{match.spoken}“  →  Slot {match.slot}", "", True)
        elif match.outside_loadout is not None:
            self._add_history(
                f"„{match.spoken}“  →  nicht im aktiven Loadout: "
                f"{match.outside_loadout.name}",
                "", False, theme.ACCENT)
        else:
            alternatives = ", ".join(name for name, _ in match.alternatives[:2])
            self._add_history(
                f"„{match.spoken}“  →  nicht erkannt",
                f"nächste Kandidaten: {alternatives}" if alternatives else "",
                False,
            )

    def _test_text(self) -> None:
        text = self.test_input.text().strip()
        if not text:
            return
        self.ctx.submit_text(text, execute=False)
        self.transcript.setText(f"„{text}“")

    def _add_history(self, text: str, detail: str, ok: bool, color: str | None = None) -> None:
        self.history_hint.setVisible(False)
        line = f"{text}   ·   {detail}" if detail else text
        item = QListWidgetItem(line)
        item.setForeground(QColor(color or (theme.TEXT if ok else theme.MUTED)))
        item.setToolTip(line)
        self.history.insertItem(0, item)
        while self.history.count() > 40:
            self.history.takeItem(self.history.count() - 1)

    def _on_info(self, message: str) -> None:
        self.model_status.setText(message)
