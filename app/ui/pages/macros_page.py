"""Macros page: hotkey assignment, timing and a dry-run test."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext, QUICK_LABELS
from ...core.input_sender import build_sequence
from ...core.keymap import DIRECTION_SCHEMES, pretty_key
from ...core.models import ARROW_GLYPHS, SIDE_OBJECTIVES
from .. import theme
from ..widgets import HotkeyEdit, section_label

SLOT_LABELS = ["SLOT 1", "SLOT 2", "SLOT 3", "SLOT 4"]


class MacrosPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._build()
        ctx.loadout_changed.connect(self.refresh_names)
        ctx.settings_changed.connect(self.refresh_names)
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(350)
        self._save_timer.timeout.connect(self._persist)
        self.refresh_names()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(18)

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(section_label("Steuerung"))
        title = QLabel("MAKROS & HOTKEYS")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        subtitle = QLabel(
            "Ein Hotkey tippt den Stratagem-Code für dich – auf Wunsch mit Wurf."
        )
        subtitle.setObjectName("muted")
        header.addWidget(subtitle)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(18)

        # -- key bindings -------------------------------------------------
        bind_card = QFrame()
        bind_card.setObjectName("card")
        bind_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bind_outer = QVBoxLayout(bind_card)
        bind_outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        inner = QWidget()
        bind_layout = QVBoxLayout(inner)
        bind_layout.setContentsMargins(16, 12, 16, 12)
        bind_layout.setSpacing(6)
        scroll.setWidget(inner)
        bind_outer.addWidget(scroll)
        bind_layout.addWidget(section_label("Tastenbelegung"))
        hint = QLabel("Klicke ein Feld und drücke die gewünschte Taste. Rechtsklick löscht.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        bind_layout.addWidget(hint)

        self.slot_names: list[QLabel] = []
        self.slot_edits: list[HotkeyEdit] = []
        for index in range(4):
            bind_layout.addWidget(self._binding_row(
                SLOT_LABELS[index], lambda i=index: self.ctx.set_slot(i, None),
                on_key=lambda key, i=index: self._set_slot_key(i, key),
                store_names=self.slot_names, store_edits=self.slot_edits,
            ))
        bind_layout.addSpacing(4)
        self.quick_names: dict[str, QLabel] = {}
        self.quick_edits: dict[str, HotkeyEdit] = {}
        for key, label in QUICK_LABELS.items():
            if key not in self.ctx.settings.hotkeys.quick:
                continue
            bind_layout.addWidget(self._binding_row(
                label.upper(), None,
                on_key=lambda combo, k=key: self._set_quick_key(k, combo),
                store_names=None, store_edits=None, name_store=self.quick_names,
                edit_store=self.quick_edits, name_key=key,
            ))
        bind_layout.addSpacing(6)
        bind_layout.addWidget(section_label("Missions-Stratagems"))
        self.mission_hint = QLabel(
            "Platz 1–3 gelten für jede Mission – einmal belegen reicht.")
        self.mission_hint.setStyleSheet(f"color: {theme.DIM}; font-size: 7.8pt;")
        self.mission_hint.setWordWrap(True)
        bind_layout.addWidget(self.mission_hint)
        self.mission_box = QVBoxLayout()
        self.mission_box.setSpacing(6)
        bind_layout.addLayout(self.mission_box)
        self.mission_names: list[QLabel] = []
        self.mission_edits: list[HotkeyEdit] = []
        for index in range(3):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(10)
            tag = QLabel(f"MISSION {index + 1}")
            tag.setFixedWidth(96)
            tag.setStyleSheet(
                f"color: {theme.MUTED}; font-size: 8.5pt; letter-spacing: 1.4px;")
            name = QLabel("—")
            name.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
            edit = HotkeyEdit("")
            edit.changed.connect(
                lambda combo, i=index: self._set_mission_key(i, combo))
            row_layout.addWidget(tag)
            row_layout.addWidget(name, 1)
            row_layout.addWidget(edit)
            self.mission_box.addWidget(row)
            self.mission_names.append(name)
            self.mission_edits.append(edit)
        bind_layout.addStretch(1)
        bind_layout.addSpacing(4)
        note = QLabel("Die Tasten gelten auch im Spiel – nimm keine, die du dort brauchst.")
        note.setWordWrap(True)
        note.setStyleSheet(f"color: #6c7062; font-size: 8pt;")
        bind_layout.addWidget(note)
        from ...core.winutil import is_elevated

        if not is_elevated():
            elevation_hint = QLabel(
                "Läuft das Spiel als Administrator? Dann die App über start-admin.cmd "
                "starten.")
            elevation_hint.setWordWrap(True)
            elevation_hint.setStyleSheet(f"color: {theme.ACCENT}; font-size: 8pt;")
            bind_layout.addWidget(elevation_hint)
        body.addWidget(bind_card, 3)

        # -- timing -------------------------------------------------------
        timing = QFrame()
        timing.setObjectName("card")
        timing.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        timing_layout = QVBoxLayout(timing)
        timing_layout.setContentsMargins(18, 16, 18, 16)
        timing_layout.setSpacing(10)
        timing_layout.addWidget(section_label("Makro-Feinstimmung"))

        self.menu_key = HotkeyEdit(self.ctx.settings.macro.menu_key)
        self.menu_key.changed.connect(self._set_menu_key)
        timing_layout.addLayout(self._field_row("Stratagem-Taste", self.menu_key))

        self.scheme = QComboBox()
        self.scheme.addItem("WASD", "wasd")
        self.scheme.addItem("Pfeiltasten", "arrows")
        self.scheme.setCurrentIndex(0 if self.ctx.settings.macro.direction_scheme == "wasd" else 1)
        self.scheme.currentIndexChanged.connect(self._set_scheme)
        timing_layout.addLayout(self._field_row("Richtungstasten", self.scheme))

        self.hold = QSpinBox()
        self.hold.setRange(0, 120)
        self.hold.setSuffix(" ms")
        self.hold.setValue(self.ctx.settings.macro.key_hold_ms)
        self.hold.valueChanged.connect(self._set_hold)
        timing_layout.addLayout(self._field_row("Taste halten", self.hold))

        self.gap = QSpinBox()
        self.gap.setRange(10, 300)
        self.gap.setSuffix(" ms")
        self.gap.setValue(self.ctx.settings.macro.key_gap_ms)
        self.gap.valueChanged.connect(self._set_gap)
        timing_layout.addLayout(self._field_row("Pause zwischen Tasten", self.gap))

        self.throw_delay = QSpinBox()
        self.throw_delay.setRange(0, 800)
        self.throw_delay.setSuffix(" ms")
        self.throw_delay.setValue(self.ctx.settings.macro.throw_delay_ms)
        self.throw_delay.valueChanged.connect(self._set_throw_delay)
        timing_layout.addLayout(self._field_row("Wurf-Verzögerung", self.throw_delay))

        self.auto_throw = QCheckBox("Nach dem Code automatisch werfen (Linksklick)")
        self.auto_throw.setChecked(self.ctx.settings.macro.auto_throw)
        self.auto_throw.toggled.connect(self._set_auto_throw)
        timing_layout.addWidget(self.auto_throw)

        self.hold_menu = QCheckBox("Stratagem-Menü beim Tippen halten")
        self.hold_menu.setChecked(self.ctx.settings.macro.hold_menu)
        self.hold_menu.toggled.connect(self._set_hold_menu)
        timing_layout.addWidget(self.hold_menu)
        self.hold_menu_warning = QLabel(
            "Ohne gehaltene Stratagem-Taste (STRG) empfängt das Spiel nur die "
            "Richtungstasten – das Makro löst dann nichts aus.")
        self.hold_menu_warning.setWordWrap(True)
        self.hold_menu_warning.setStyleSheet(
            f"color: {theme.RED}; font-size: 8pt;")
        self.hold_menu_warning.setVisible(not self.ctx.settings.macro.hold_menu)
        timing_layout.addWidget(self.hold_menu_warning)

        self.input_mode = QComboBox()
        self.input_mode.addItem("Scan-Code (empfohlen)", "scancode")
        self.input_mode.addItem("Virtuelle Taste", "vk")
        self.input_mode.setCurrentIndex(0 if self.ctx.settings.macro.input_mode == "scancode" else 1)
        self.input_mode.currentIndexChanged.connect(self._set_input_mode)
        timing_layout.addLayout(self._field_row("Eingabe-Modus", self.input_mode))

        self.dry_run = QCheckBox("Testmodus (sendet nichts ins Spiel)")
        self.dry_run.setChecked(self.ctx.settings.macro.dry_run)
        self.dry_run.toggled.connect(self._set_dry_run)
        timing_layout.addWidget(self.dry_run)
        self.dry_warning = QLabel(
            "Testmodus ist aktiv: Makros werden nur simuliert, das Spiel bekommt "
            "keine Tasten. Zum Spielen das Häkchen entfernen.")
        self.dry_warning.setWordWrap(True)
        self.dry_warning.setStyleSheet(f"color: {theme.RED}; font-size: 8pt;")
        self.dry_warning.setVisible(self.ctx.settings.macro.dry_run)
        timing_layout.addWidget(self.dry_warning)

        timing_layout.addSpacing(10)
        timing_layout.addWidget(section_label("Zusatz-Hotkeys"))
        self.side_edits: dict[str, HotkeyEdit] = {}
        for stratagem_id, label in SIDE_OBJECTIVES:
            row = QHBoxLayout()
            row.setSpacing(12)
            tag = QLabel(label)
            tag.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
            tag.setFixedWidth(150)
            edit = HotkeyEdit(self.ctx.settings.hotkeys.side.get(stratagem_id, ""))
            edit.changed.connect(
                lambda combo, sid=stratagem_id: self._set_side_key(sid, combo))
            row.addWidget(tag)
            row.addWidget(edit, 1)
            timing_layout.addLayout(row)
            self.side_edits[stratagem_id] = edit

        timing_layout.addSpacing(6)
        self.extra_names: list[QLabel] = []
        self.extra_edits: list[HotkeyEdit] = []
        for index in range(2):
            row = QHBoxLayout()
            row.setSpacing(12)
            tag = QLabel(f"Extra {index + 1}")
            tag.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
            tag.setFixedWidth(64)
            name = QLabel("—")
            name.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.4pt;")
            edit = HotkeyEdit(self.ctx.settings.hotkeys.extra[index])
            edit.changed.connect(
                lambda combo, i=index: self._set_extra_key(i, combo))
            row.addWidget(tag)
            row.addWidget(name, 1)
            row.addWidget(edit)
            timing_layout.addLayout(row)
            self.extra_names.append(name)
            self.extra_edits.append(edit)
        timing_layout.addStretch(1)
        body.addWidget(timing, 2)
        root.addLayout(body, 1)

        # -- test ---------------------------------------------------------
        test_card = QFrame()
        test_card.setObjectName("card")
        test_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        test_layout = QVBoxLayout(test_card)
        test_layout.setContentsMargins(18, 14, 18, 14)
        test_layout.setSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addWidget(section_label("Testlauf"))
        self.test_target = QComboBox()
        self.test_target.setMinimumWidth(240)
        self.test_target.currentIndexChanged.connect(self._update_test_preview)
        row.addWidget(self.test_target)
        row.addStretch(1)
        hotspot_button = QPushButton("HOTKEY TESTEN")
        hotspot_button.setObjectName("ghost")
        hotspot_button.clicked.connect(self._open_hotkey_check)
        row.addWidget(hotspot_button)
        diag_button = QPushButton("EINGABE TESTEN")
        diag_button.setObjectName("ghost")
        diag_button.clicked.connect(self._open_self_test)
        row.addWidget(diag_button)
        test_button = QPushButton("MAKRO AUSFÜHREN")
        test_button.setObjectName("primary")
        test_button.clicked.connect(self._run_test)
        row.addWidget(test_button)
        test_layout.addLayout(row)
        self.preview = QLineEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("Sequenz erscheint hier …")
        test_layout.addWidget(self.preview)
        self.test_hint = QLabel("")
        self.test_hint.setWordWrap(True)
        self.test_hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        test_layout.addWidget(self.test_hint)
        root.addWidget(test_card)
        self._fill_test_targets()

    # ------------------------------------------------------------------
    def _binding_row(self, label: str, on_clear, on_key, store_names, store_edits,
                     name_store=None, edit_store=None, name_key=None) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(10)
        tag = QLabel(label)
        tag.setFixedWidth(96)
        tag.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt; letter-spacing: 1.4px;")
        name = QLabel("—")
        name.setStyleSheet(f"color: {theme.TEXT}; font-size: 9.5pt;")
        edit = HotkeyEdit("")
        edit.changed.connect(on_key)
        layout.addWidget(tag)
        layout.addWidget(name, 1)
        layout.addWidget(edit)
        if store_names is not None:
            store_names.append(name)
        if store_edits is not None:
            store_edits.append(edit)
        if name_store is not None and name_key is not None:
            name_store[name_key] = name
        if edit_store is not None and name_key is not None:
            edit_store[name_key] = edit
        return row

    def _field_row(self, label: str, widget: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        tag = QLabel(label)
        tag.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        tag.setFixedWidth(170)
        row.addWidget(tag)
        row.addWidget(widget, 1)
        return row

    # ------------------------------------------------------------------
    def refresh_names(self) -> None:
        loadout = self.ctx.loadout
        for index, name in enumerate(self.slot_names):
            stratagem = self.ctx.db.get(loadout.slots[index])
            name.setText(stratagem.name if stratagem else "nicht belegt")
            name.setStyleSheet(
                f"color: {theme.TEXT if stratagem else theme.MUTED}; font-size: 9.5pt;"
            )
            if index < len(self.slot_edits):
                self.slot_edits[index].blockSignals(True)
                self.slot_edits[index].set_key(self.ctx.settings.hotkeys.slots[index])
                self.slot_edits[index].blockSignals(False)
        for key, name in self.quick_names.items():
            stratagem = self.ctx.db.get(loadout.quick.get(key))
            name.setText(stratagem.name if stratagem else "nicht belegt")
            edit = self.quick_edits.get(key)
            if edit is not None:
                edit.blockSignals(True)
                edit.set_key(self.ctx.settings.hotkeys.quick.get(key, ""))
                edit.blockSignals(False)
        self._refresh_mission_rows()
        self._refresh_side_rows()
        self._fill_test_targets()

    def _refresh_side_rows(self) -> None:
        for stratagem_id, edit in self.side_edits.items():
            edit.blockSignals(True)
            edit.set_key(self.ctx.settings.hotkeys.side.get(stratagem_id, ""))
            edit.blockSignals(False)
        extras = self.ctx.extra_stratagems()
        for index, name in enumerate(self.extra_names):
            stratagem = extras[index] if index < len(extras) else None
            if stratagem is not None:
                name.setText(stratagem.name)
                name.setStyleSheet(f"color: {theme.TEXT}; font-size: 8.4pt;")
            else:
                name.setText("—")
                name.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.4pt;")
            edit = self.extra_edits[index]
            edit.blockSignals(True)
            edit.set_key(self.ctx.settings.hotkeys.extra[index])
            edit.blockSignals(False)

    def _set_extra_key(self, index: int, combo: str) -> None:
        slots = self.ctx.settings.hotkeys.extra
        if 0 <= index < len(slots):
            slots[index] = combo or ""
        self._save_timer.start()

    def _refresh_mission_rows(self) -> None:
        stratagems = self.ctx.mission_stratagems()
        self.mission_hint.setVisible(True)
        for index, name in enumerate(self.mission_names):
            if index < len(stratagems):
                name.setText(f"{index + 1}. {stratagems[index].name}")
                name.setStyleSheet(f"color: {theme.TEXT}; font-size: 9pt;")
            else:
                name.setText("— keine Mission")
                name.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
            if index < len(self.mission_edits):
                edit = self.mission_edits[index]
                edit.blockSignals(True)
                edit.set_key(self.ctx.settings.hotkeys.mission_slots[index])
                edit.blockSignals(False)

    def _set_mission_key(self, index: int, combo: str) -> None:
        slots = self.ctx.settings.hotkeys.mission_slots
        if 0 <= index < len(slots):
            slots[index] = combo or ""
        self._save_timer.start()

    def _set_side_key(self, stratagem_id: str, combo: str) -> None:
        if combo:
            self.ctx.settings.hotkeys.side[stratagem_id] = combo
        else:
            self.ctx.settings.hotkeys.side.pop(stratagem_id, None)
        self._save_timer.start()

    def _fill_test_targets(self) -> None:
        current = self.test_target.currentData() if hasattr(self, "test_target") else None
        self.test_target.blockSignals(True)
        self.test_target.clear()
        loadout = self.ctx.loadout
        for index, stratagem_id in enumerate(loadout.slots):
            stratagem = self.ctx.db.get(stratagem_id)
            if stratagem:
                self.test_target.addItem(f"Slot {index + 1}: {stratagem.name}", stratagem.id)
        for key, label in QUICK_LABELS.items():
            stratagem = self.ctx.db.get(loadout.quick.get(key))
            if stratagem:
                self.test_target.addItem(f"{label}: {stratagem.name}", stratagem.id)
        for stratagem in self.ctx.mission_stratagems():
            self.test_target.addItem(f"Mission: {stratagem.name}", stratagem.id)
        if current is not None:
            position = self.test_target.findData(current)
            if position >= 0:
                self.test_target.setCurrentIndex(position)
        self.test_target.blockSignals(False)
        self._update_test_preview()

    def _update_test_preview(self) -> None:
        stratagem = self.ctx.db.get(self.test_target.currentData())
        if stratagem is None:
            self.preview.setText("")
            return
        steps = build_sequence(stratagem.code, self.ctx.settings.macro)
        parts: list[str] = []
        for kind, value in steps:
            if kind == "down":
                parts.append(f"[{pretty_key(str(value))} \u2193]")
            elif kind == "up":
                parts.append(f"[{pretty_key(str(value))} \u2191]")
            elif kind == "sleep":
                parts.append(f"{int(value)}ms")
            elif kind == "click":
                parts.append("KLICK")
        self.preview.setText("  ".join(parts))
        self.test_hint.setText(
            "Sendet die Sequenz ans aktive Fenster. Im Testmodus passiert im Spiel "
            "nichts."
        )

    # ------------------------------------------------------------------
    def _set_slot_key(self, index: int, key: str) -> None:
        self.ctx.settings.hotkeys.slots[index] = key
        self._save_timer.start()

    def _set_quick_key(self, name: str, key: str) -> None:
        self.ctx.settings.hotkeys.quick[name] = key
        self._save_timer.start()

    def _save_soon(self) -> None:
        self._save_timer.start()

    def _persist(self) -> None:
        self.ctx.save_settings()
        self.ctx.apply_hotkeys()

    def _set_menu_key(self, key: str) -> None:
        self.ctx.settings.macro.menu_key = key
        self._save_soon()
        self._update_test_preview()

    def _set_scheme(self, *_args) -> None:
        self.ctx.settings.macro.direction_scheme = self.scheme.currentData()
        self._save_soon()
        self._update_test_preview()

    def _set_hold(self, value: int) -> None:
        self.ctx.settings.macro.key_hold_ms = value
        self._save_soon()
        self._update_test_preview()

    def _set_gap(self, value: int) -> None:
        self.ctx.settings.macro.key_gap_ms = value
        self._save_soon()
        self._update_test_preview()

    def _set_throw_delay(self, value: int) -> None:
        self.ctx.settings.macro.throw_delay_ms = value
        self._save_soon()

    def _set_auto_throw(self, value: bool) -> None:
        self.ctx.settings.macro.auto_throw = value
        self._save_soon()
        self._update_test_preview()

    def _set_hold_menu(self, value: bool) -> None:
        self.ctx.settings.macro.hold_menu = value
        self.hold_menu_warning.setVisible(not value)
        self._save_soon()
        self._update_test_preview()

    def _set_input_mode(self, *_args) -> None:
        self.ctx.settings.macro.input_mode = self.input_mode.currentData()
        self._save_soon()

    def _set_dry_run(self, value: bool) -> None:
        self.ctx.settings.macro.dry_run = value
        self.dry_warning.setVisible(value)
        self._save_soon()

    def _run_test(self) -> None:
        stratagem = self.ctx.db.get(self.test_target.currentData())
        if stratagem is None:
            return
        self.ctx.execute(stratagem, "test")

    def _open_self_test(self) -> None:
        from ..dialogs import InputSelfTest

        InputSelfTest(self).exec()

    def _open_hotkey_check(self) -> None:
        from ..dialogs import HotkeyCheck

        HotkeyCheck(self.ctx, self).exec()
