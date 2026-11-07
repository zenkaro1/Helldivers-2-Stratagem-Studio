"""Settings page: app behaviour, data location, legal note."""

from __future__ import annotations

import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from .. import theme
from ..widgets import section_label


class SettingsPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._build()

    def _build_ship_card(self) -> QWidget:
        from PySide6.QtWidgets import QGridLayout

        card = QFrame()
        card.setObjectName("card")
        card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(section_label("Schiff-Upgrades"))
        head.addStretch(1)
        self.ship_summary = QLabel("")
        self.ship_summary.setStyleSheet(
            f"color: {theme.ACCENT}; font-size: 7.4pt; letter-spacing: 1.4px;")
        head.addWidget(self.ship_summary)
        layout.addLayout(head)

        hint = QLabel(
            "Hake an, was dein Zerstörer schon freigeschaltet hat – die Cooldowns "
            "passen sich automatisch an.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 8pt;")
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(4)
        self.ship_boxes: dict[str, QCheckBox] = {}
        modules = self.ctx.db.ship_modules
        for index, module in enumerate(modules):
            box = QCheckBox(f"{module.name}  ·  {module.note}")
            box.setChecked(self.ctx.has_ship_module(module.id))
            box.setStyleSheet("font-size: 8.6pt;")
            box.toggled.connect(
                lambda checked, mid=module.id: self._set_ship_module(mid, checked))
            grid.addWidget(box, index // 2, index % 2)
            self.ship_boxes[module.id] = box

        layout.addLayout(grid)

        self.ship_example = QLabel("")
        self.ship_example.setStyleSheet(f"color: {theme.MUTED}; font-size: 8pt;")
        layout.addWidget(self.ship_example)
        self._update_ship_summary()
        return card

    def _set_ship_module(self, module_id: str, checked: bool) -> None:
        if checked == self.ctx.has_ship_module(module_id):
            return
        self.ctx.toggle_ship_module(module_id)
        self._update_ship_summary()

    def _update_ship_summary(self) -> None:
        installed = [m for m in self.ctx.db.ship_modules if self.ctx.has_ship_module(m.id)]
        self.ship_summary.setText(
            f"{len(installed)} AKTIV" if installed else "KEINE AKTIV")
        sample = self.ctx.db.get("orbital_380mm_he_barrage")
        parts = []
        if sample is not None:
            base = sample.cooldown or 0
            effective = self.ctx.effective_cooldown(sample) or base
            parts.append(f"{sample.name}: {base} s → {effective} s")
        eagle = self.ctx.db.get("eagle_500kg_bomb")
        if eagle is not None:
            uses = self.ctx.effective_uses(eagle)
            base_uses = eagle.uses or 0
            if uses and uses != base_uses:
                parts.append(f"{eagle.name}: {base_uses} → {uses} Einsätze")
        self.ship_example.setText("   ·   ".join(parts) if parts else "")

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(18)

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(section_label("System"))
        title = QLabel("EINSTELLUNGEN")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        subtitle = QLabel("Overlay, Infobereich und deine Daten.")
        subtitle.setObjectName("muted")
        header.addWidget(subtitle)
        root.addLayout(header)

        root.addWidget(self._build_ship_card())

        body = QHBoxLayout()
        body.setSpacing(18)

        behaviour = QFrame()
        behaviour.setObjectName("card")
        behaviour.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(behaviour)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(section_label("Verhalten"))

        self.overlay = QCheckBox("Bestätigungs-Overlay über dem Spiel anzeigen")
        self.overlay.setChecked(self.ctx.settings.show_overlay)
        self.overlay.toggled.connect(self._set_overlay)
        layout.addWidget(self.overlay)

        self.tray = QCheckBox("Beim Schließen in den Infobereich minimieren")
        self.tray.setChecked(self.ctx.settings.minimize_to_tray)
        self.tray.toggled.connect(self._set_tray)
        layout.addWidget(self.tray)

        self.notifications = QCheckBox("Benachrichtigungen anzeigen")
        self.notifications.setChecked(self.ctx.settings.notifications)
        self.notifications.toggled.connect(self._set_notifications)
        layout.addWidget(self.notifications)

        self.hotkeys_enabled = QCheckBox("Globale Hotkeys aktiv")
        self.hotkeys_enabled.setChecked(self.ctx.settings.hotkeys.enabled)
        self.hotkeys_enabled.toggled.connect(self._set_hotkeys_enabled)
        layout.addWidget(self.hotkeys_enabled)

        self.block_cooldown = QCheckBox("Stratagems im Cooldown nicht auslösen")
        self.block_cooldown.setChecked(self.ctx.settings.macro.block_on_cooldown)
        self.block_cooldown.toggled.connect(self._set_block_cooldown)
        layout.addWidget(self.block_cooldown)

        layout.addSpacing(8)
        layout.addWidget(section_label("So geht's"))
        tips = [
            "Loadout: Stratagem auf einen der vier Slots legen.",
            "Makros: F1–F4 lösen die Slots aus, F5/F6 Nachschub und Verstärkung.",
            "Stimme: F8 halten und das Stratagem sagen.",
        ]
        for tip in tips:
            label = QLabel(tip)
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
            layout.addWidget(label)
        layout.addStretch(1)

        data = QFrame()
        data.setObjectName("card")
        data.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        data_layout = QVBoxLayout(data)
        data_layout.setContentsMargins(18, 16, 18, 16)
        data_layout.setSpacing(8)
        data_layout.addWidget(section_label("Daten"))
        self.db_info = QLabel("")
        self.db_info.setWordWrap(True)
        self.db_info.setStyleSheet(f"color: {theme.TEXT}; font-size: 9pt;")
        data_layout.addWidget(self.db_info)
        self.path_info = QLabel("")
        self.path_info.setWordWrap(True)
        self.path_info.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        data_layout.addWidget(self.path_info)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        open_button = QPushButton("ORDNER ÖFFNEN")
        open_button.setObjectName("ghost")
        open_button.clicked.connect(self._open_folder)
        buttons.addWidget(open_button)
        reload_button = QPushButton("DATENBANK NEU LADEN")
        reload_button.setObjectName("ghost")
        reload_button.clicked.connect(self._reload_db)
        buttons.addWidget(reload_button)
        buttons.addStretch(1)
        data_layout.addLayout(buttons)

        note = QLabel(
            "Makros senden nur Tasteneingaben – Nutzung auf eigene Verantwortung."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        data_layout.addSpacing(6)
        data_layout.addWidget(note)
        data_layout.addStretch(1)

        body.addWidget(behaviour, 1)
        body.addWidget(data, 1)
        root.addLayout(body, 3)

        about = QFrame()
        about.setObjectName("card")
        about.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        about_layout = QHBoxLayout(about)
        about_layout.setContentsMargins(18, 14, 18, 14)
        about_layout.setSpacing(24)
        about_text = QVBoxLayout()
        about_text.setSpacing(3)
        about_text.addWidget(section_label("Über"))
        title = QLabel("STRATAGEM STUDIO  ·  v1.0")
        title.setStyleSheet(f"color: {theme.TEXT}; font-size: 10.5pt; font-weight: 600;")
        about_text.addWidget(title)
        description = QLabel(
            "Loadout planen, Stratagems per Hotkey oder Stimme auslösen. "
            "Läuft lokal auf deinem PC."
        )
        description.setWordWrap(True)
        description.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        about_text.addWidget(description)
        about_text_widget = QWidget()
        about_text_widget.setLayout(about_text)
        about_layout.addWidget(about_text_widget, 1, Qt.AlignmentFlag.AlignTop)
        root.addWidget(about, 0)
        self.refresh()

    def refresh(self) -> None:
        self.db_info.setText(f"{len(self.ctx.db)} Stratagems verfügbar")
        self.path_info.setText(f"Deine Einstellungen: {self.ctx.storage.dir}")

    def _set_overlay(self, value: bool) -> None:
        self.ctx.settings.show_overlay = value
        self.ctx.save_settings()

    def _set_tray(self, value: bool) -> None:
        self.ctx.settings.minimize_to_tray = value
        self.ctx.save_settings()

    def _set_notifications(self, value: bool) -> None:
        self.ctx.settings.notifications = value
        self.ctx.save_settings()

    def _set_hotkeys_enabled(self, value: bool) -> None:
        self.ctx.settings.hotkeys.enabled = value
        self.ctx.save_settings()
        self.ctx.apply_hotkeys()

    def _set_block_cooldown(self, value: bool) -> None:
        self.ctx.settings.macro.block_on_cooldown = value
        self.ctx.save_settings()

    def _open_folder(self) -> None:
        try:
            os.startfile(str(self.ctx.storage.dir))  # noqa: S606 - user action
        except Exception:  # noqa: BLE001
            subprocess.Popen(["explorer", str(self.ctx.storage.dir)])

    def _reload_db(self) -> None:
        try:
            self.ctx.db.load()
            self.ctx.loadout_changed.emit()
            self.refresh()
        except Exception as exc:  # noqa: BLE001
            self.ctx.error.emit(f"Datenbank konnte nicht geladen werden: {exc}")
