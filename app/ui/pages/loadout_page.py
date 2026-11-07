"""Loadout page v2: mission selection, stats cards, mission stratagems, kits."""

from __future__ import annotations

import time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...context import AppContext
from ...core.models import SIDE_OBJECTIVES, Stratagem, category_color
from .. import theme
from ..cards import KitCard, MissionCard, SegmentedTabs, SlotCard, StarLabel
from ..dialogs import StratagemPicker
from ..widgets import HotkeyBadge, icon_pixmap, section_label


class LoadoutPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._cards: list[SlotCard] = []
        self._mission_cards: list[MissionCard] = []
        self._kit_cards: list[KitCard] = []
        self._feed: list[str] = []
        self._build()
        ctx.loadout_changed.connect(self.refresh)
        ctx.executed.connect(self._on_executed)
        ctx.cooldowns_changed.connect(self._update_cooldowns)
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._update_cooldowns)
        self._timer.start()
        self.refresh()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(16)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(section_label("Einsatzvorbereitung"))
        self.title = QLabel("LOADOUT")
        self.title.setObjectName("pageTitle")
        title_box.addWidget(self.title)
        self.subtitle = QLabel("")
        self.subtitle.setObjectName("muted")
        title_box.addWidget(self.subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        self.tabs = SegmentedTabs(("LOADOUT", "MEINE KITS"))
        self.tabs.changed.connect(self._on_tab)
        header.addWidget(self.tabs, 0, Qt.AlignmentFlag.AlignBottom)
        root.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_loadout_view())
        self.stack.addWidget(self._build_kits_view())
        root.addWidget(self.stack, 1)

    # -- loadout view ----------------------------------------------------
    def _build_loadout_view(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(16)

        body = QHBoxLayout()
        body.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(14)

        self.mission_bar = QFrame()
        self.mission_bar.setObjectName("cardAlt")
        self.mission_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.mission_bar.setFixedHeight(72)
        bar_layout = QHBoxLayout(self.mission_bar)
        bar_layout.setContentsMargins(0, 0, 14, 0)
        bar_layout.setSpacing(0)
        accent = QFrame()
        accent.setFixedWidth(3)
        accent.setStyleSheet(f"background: {theme.ACCENT};")
        bar_layout.addWidget(accent)
        mission_text = QVBoxLayout()
        mission_text.setContentsMargins(14, 10, 0, 10)
        mission_text.setSpacing(2)
        mission_text.addWidget(section_label("Aktive Mission"))
        self.mission_name = QLabel("")
        self.mission_name.setStyleSheet(
            f"color: {theme.TEXT}; font-size: 12.5pt; font-weight: 600;"
            " letter-spacing: 0.6px;")
        mission_text.addWidget(self.mission_name)
        self.mission_meta = QLabel("")
        self.mission_meta.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 7.8pt; letter-spacing: 1.2px;")
        mission_text.addWidget(self.mission_meta)
        bar_layout.addLayout(mission_text, 1)

        self.mission_combo = QComboBox()
        self.mission_combo.setFixedWidth(210)
        self.mission_combo.setFixedHeight(34)
        self.mission_combo.currentIndexChanged.connect(self._on_mission_changed)
        bar_layout.addWidget(self.mission_combo)
        left.addWidget(self.mission_bar)

        grid = QGridLayout()
        grid.setSpacing(14)
        for index in range(4):
            card = SlotCard(index)
            card.clicked.connect(self._pick_slot)
            card.clear_requested.connect(lambda i: self.ctx.set_slot(i, None))
            self._cards.append(card)
            grid.addWidget(card, index // 2, index % 2)
        left.addLayout(grid)

        self.mission_panel = QFrame()
        self.mission_panel.setObjectName("card")
        self.mission_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        panel_layout = QVBoxLayout(self.mission_panel)
        panel_layout.setContentsMargins(16, 12, 16, 14)
        panel_layout.setSpacing(8)
        panel_header = QHBoxLayout()
        panel_header.addWidget(section_label("Missions-Stratagems"))
        panel_header.addStretch(1)
        self.mission_hint = QLabel("NUR IN DIESER MISSION")
        self.mission_hint.setStyleSheet(
            f"color: {theme.DIM}; font-size: 6.8pt; letter-spacing: 1.8px;")
        panel_header.addWidget(self.mission_hint)
        panel_layout.addLayout(panel_header)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background: {theme.BORDER};")
        panel_layout.addWidget(rule)
        self.mission_row = QHBoxLayout()
        self.mission_row.setSpacing(12)
        panel_layout.addLayout(self.mission_row)
        self.mission_empty = QLabel(
            "Keine Missions-Stratagems – wähle oben eine Mission aus.")
        self.mission_empty.setStyleSheet(f"color: {theme.DIM}; font-size: 8.5pt;")
        panel_layout.addWidget(self.mission_empty)
        left.addWidget(self.mission_panel)
        body.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(14)
        right.addWidget(self._build_kits_panel())
        right.addWidget(self._build_activity_panel())
        right.addWidget(self._build_side_panel())
        right.addStretch(1)
        container = QWidget()
        container.setLayout(right)
        container.setFixedWidth(340)
        body.addWidget(container)
        outer.addLayout(body, 1)
        return page

    def _build_kits_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(section_label("Meine Kits"))
        header.addStretch(1)
        link = QPushButton("ALLE KITS  →")
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: "
            f"{theme.ACCENT}; font-size: 6.8pt; font-weight: 600;"
            " letter-spacing: 1.8px; padding: 0; }"
            "QPushButton:hover { color: #FFE066; }")
        link.clicked.connect(lambda: self._on_tab(1))
        header.addWidget(link)
        layout.addLayout(header)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(rule)
        self.kit_rows_box = QVBoxLayout()
        self.kit_rows_box.setSpacing(8)
        layout.addLayout(self.kit_rows_box)
        layout.addStretch(1)
        return panel

    def _build_activity_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        layout.addWidget(section_label("Letzte Aktionen"))
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(rule)
        self.activity_rows: list[QLabel] = []
        for _ in range(3):
            row = QHBoxLayout()
            time_label = QLabel("--:--")
            time_label.setStyleSheet(
                f"color: {theme.DIM}; font-size: 8pt; letter-spacing: 1px;")
            time_label.setFixedWidth(44)
            source_label = QLabel("")
            source_label.setStyleSheet(
                f"color: {theme.MUTED}; font-size: 6.8pt; letter-spacing: 1.6px;")
            source_label.setFixedWidth(58)
            name_label = QLabel("")
            name_label.setStyleSheet(f"color: {theme.TEXT}; font-size: 9pt;")
            row.addWidget(time_label)
            row.addWidget(source_label)
            row.addWidget(name_label, 1)
            layout.addLayout(row)
            name_label.setProperty("time_label", time_label)
            name_label.setProperty("source_label", source_label)
            self.activity_rows.append(name_label)
        layout.addStretch(1)
        return panel

    def _build_side_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.addWidget(section_label("Zusatz-Hotkeys"))
        header.addStretch(1)
        badge = QLabel("IMMER")
        badge.setStyleSheet(
            f"color: {theme.DIM}; font-size: 6.4pt; letter-spacing: 1.8px;")
        header.addWidget(badge)
        layout.addLayout(header)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(rule)

        self._side_rows: list[tuple[QFrame, QLabel, QLabel]] = []
        for stratagem_id, _label in SIDE_OBJECTIVES:
            stratagem = self.ctx.db.get(stratagem_id)
            row = QFrame()
            row.setObjectName("cardAlt")
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row.setFixedHeight(42)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)
            icon = QLabel()
            icon.setFixedSize(26, 26)
            icon.setPixmap(icon_pixmap(stratagem.icon if stratagem else "", 24))
            row_layout.addWidget(icon)
            name = QLabel(stratagem.name if stratagem else stratagem_id)
            name.setStyleSheet(f"color: {theme.TEXT}; font-size: 8.4pt;")
            row_layout.addWidget(name, 1)
            key = HotkeyBadge(self.ctx.settings.hotkeys.side.get(stratagem_id, ""))
            row_layout.addWidget(key)
            row.mouseReleaseEvent = (  # type: ignore[method-assign]
                lambda _event, sid=stratagem_id: self.ctx.trigger_mission(sid))
            layout.addWidget(row)
            self._side_rows.append((row, name, key))

        rule2 = QFrame()
        rule2.setFixedHeight(1)
        rule2.setStyleSheet(f"background: {theme.BORDER};")
        layout.addWidget(rule2)
        caption = QLabel("EIGENE STRATAGEMS")
        caption.setStyleSheet(
            f"color: {theme.DIM}; font-size: 6.4pt; letter-spacing: 1.8px;")
        layout.addWidget(caption)

        self._extra_rows: list[tuple[QFrame, QLabel, QLabel, QLabel]] = []
        for index in range(2):
            row = QFrame()
            row.setObjectName("cardAlt")
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row.setFixedHeight(42)
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)
            icon = QLabel()
            icon.setFixedSize(26, 26)
            row_layout.addWidget(icon)
            name = QLabel("+ Stratagem wählen")
            name.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.4pt;")
            row_layout.addWidget(name, 1)
            key = HotkeyBadge(self.ctx.settings.hotkeys.extra[index])
            row_layout.addWidget(key)
            row.mouseReleaseEvent = (  # type: ignore[method-assign]
                lambda _event, i=index: self._pick_extra(i))
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(
                lambda _pos, i=index, r=row: self._extra_menu(i, r))
            layout.addWidget(row)
            self._extra_rows.append((row, icon, name, key))
        return panel

    def _pick_extra(self, index: int) -> None:
        extras = self.ctx.extra_stratagems()
        current = extras[index].id if index < len(extras) and extras[index] else None
        dialog = StratagemPicker(self.ctx, current, parent=self)
        dialog.picked.connect(lambda sid, i=index: self.ctx.set_extra(i, sid))
        dialog.exec()

    def _extra_menu(self, index: int, parent: QWidget) -> None:
        menu = QMenu(self)
        choose = menu.addAction("Stratagem wählen")
        clear = menu.addAction("Entfernen")
        action = menu.exec(parent.mapToGlobal(parent.rect().bottomLeft()))
        if action is choose:
            self._pick_extra(index)
        elif action is clear:
            self.ctx.set_extra(index, None)

    def _refresh_extra_rows(self) -> None:
        extras = self.ctx.extra_stratagems()
        for index, (_row, icon, name, key) in enumerate(self._extra_rows):
            stratagem = extras[index] if index < len(extras) else None
            if stratagem is not None:
                icon.setPixmap(icon_pixmap(stratagem.icon, 24))
                name.setText(stratagem.name)
                name.setStyleSheet(f"color: {theme.TEXT}; font-size: 8.4pt;")
            else:
                icon.setPixmap(QPixmap())
                name.setText("+ Stratagem wählen")
                name.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.4pt;")
            key.set_key(self.ctx.settings.hotkeys.extra[index])

    def _refresh_side_rows(self) -> None:
        for index, (_row, name, key) in enumerate(self._side_rows):
            if index >= len(SIDE_OBJECTIVES):
                continue
            stratagem_id = SIDE_OBJECTIVES[index][0]
            stratagem = self.ctx.db.get(stratagem_id)
            if stratagem is not None:
                name.setText(stratagem.name)
            key.set_key(self.ctx.settings.hotkeys.side.get(stratagem_id, ""))

    # -- kits view -------------------------------------------------------
    def _build_kits_view(self) -> QWidget:
        from PySide6.QtWidgets import QScrollArea

        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }")
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        self.kits_grid = QGridLayout()
        self.kits_grid.setSpacing(16)
        container_layout.addLayout(self.kits_grid)
        container_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        self.kits_footer = QLabel("")
        self.kits_footer.setStyleSheet(f"color: {theme.DIM}; font-size: 8pt;")
        layout.addWidget(self.kits_footer)
        return page

    # ------------------------------------------------------------------
    def _on_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.tabs.set_active(index)
        if index == 0:
            mission = self.ctx.mission.name if self.ctx.mission else "—"
            if mission == "Keine Mission":
                mission = "—"
            self.title.setText("LOADOUT")
            self.subtitle.setText(
                f"{self.ctx.loadout.name}  ·  Mission: {mission}")
        else:
            self.title.setText("MEINE KITS")
            self.subtitle.setText(
                "Gespeicherte Loadouts – „Laden“ übernimmt ein Kit in die vier Slots")

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._refresh_mission()
        self._refresh_slots()
        self._refresh_mission_panel()
        self._refresh_side_rows()
        self._refresh_extra_rows()
        self._refresh_kit_rows()
        self._refresh_kits_grid()
        self._on_tab(self.stack.currentIndex())

    def _refresh_mission(self) -> None:
        self.mission_combo.blockSignals(True)
        self.mission_combo.clear()
        for mission in self.ctx.db.missions:
            self.mission_combo.addItem(mission.name, mission.id)
        index = self.mission_combo.findData(self.ctx.settings.active_mission)
        self.mission_combo.setCurrentIndex(max(0, index))
        self.mission_combo.blockSignals(False)

        mission = self.ctx.mission
        self.mission_name.setText(mission.label.upper() if mission else "KEINE MISSION")
        count = len(self.ctx.mission_stratagems())
        self.mission_meta.setText(
            f"Bugs · Schwierigkeit 10 · {count} Missions-Stratagems" if count
            else "Standard-Loadout · keine zusätzlichen Stratagems")

    def _on_mission_changed(self, _index: int) -> None:
        mission_id = self.mission_combo.currentData()
        if mission_id:
            self.ctx.set_mission(mission_id)

    def _refresh_slots(self) -> None:
        loadout = self.ctx.loadout
        for index, card in enumerate(self._cards):
            stratagem = self.ctx.db.get(loadout.slots[index])
            card.set_stratagem(
                stratagem,
                self.ctx.settings.hotkeys.slots[index],
                cooldown=self.ctx.effective_cooldown(stratagem),
                uses=self.ctx.remaining_uses(stratagem),
            )
        self._update_cooldowns()

    def _update_cooldowns(self) -> None:
        loadout = self.ctx.loadout
        for index, card in enumerate(self._cards):
            stratagem = self.ctx.db.get(loadout.slots[index])
            if stratagem is None:
                continue
            remaining = self.ctx.cooldown_remaining(stratagem.id)
            card.set_progress(remaining, self.ctx.effective_cooldown(stratagem),
                              category_color(stratagem.category))

    def _refresh_mission_panel(self) -> None:
        while self.mission_row.count():
            item = self.mission_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._mission_cards = []
        stratagems = self.ctx.mission_stratagems()
        self.mission_empty.setVisible(not stratagems)
        self.mission_panel.setVisible(True)
        for index, stratagem in enumerate(stratagems):
            card = MissionCard()
            combo = ""
            if index < len(self.ctx.settings.hotkeys.mission_slots):
                combo = self.ctx.settings.hotkeys.mission_slots[index]
            card.set_stratagem(stratagem, combo)
            card.clicked.connect(self.ctx.trigger_mission)
            self.mission_row.addWidget(card, 1)
            self._mission_cards.append(card)
        self.mission_row.addStretch(1)

    # -- kits ------------------------------------------------------------
    def _kit_summary(self, key: str) -> tuple[str, list[tuple[str, str, str]]]:
        loadout = self.ctx.loadouts[key]
        items = [self.ctx.db.get(sid) for sid in loadout.slots if sid]
        icons = [(item.icon, category_color(item.category), item.name)
                 for item in items if item]
        return loadout.name, icons

    def _refresh_kit_rows(self) -> None:
        while self.kit_rows_box.count():
            item = self.kit_rows_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        for key in list(self.ctx.loadouts)[:3]:
            name, icons = self._kit_summary(key)
            names = [entry[2] for entry in icons]
            active = key == self.ctx.settings.active_loadout
            row = QFrame()
            row.setObjectName("cardAlt")
            row.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            row.setFixedHeight(70)
            row.setToolTip("\n".join(names) if names else "Leeres Kit")
            row.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            row.customContextMenuRequested.connect(
                lambda _pos, k=key: self._kit_row_menu(k, row))
            if active:
                row.setStyleSheet(
                    "QFrame#cardAlt { border: 1px solid %s; background: %s; }"
                    % (theme.ACCENT, theme.SURFACE_2))
            layout = QHBoxLayout(row)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(8)
            star = StarLabel(14, self.ctx.is_favorite_kit(key))
            star.clicked.connect(lambda k=key: self.ctx.toggle_favorite_kit(k))
            layout.addWidget(star)
            text = QVBoxLayout()
            text.setSpacing(1)
            title = QLabel(name)
            title.setStyleSheet(
                f"color: {theme.TEXT}; font-size: 9.5pt; font-weight: 600;")
            meta = QLabel(f"{len(names)} Stratagems" if names else "Leeres Kit")
            meta.setStyleSheet(f"color: {theme.MUTED}; font-size: 7pt;")
            text.addWidget(title)
            text.addWidget(meta)
            layout.addLayout(text, 1)
            load = QPushButton("LADEN")
            load.setFixedSize(62, 26)
            load.setStyleSheet(
                "QPushButton { background: %s; color: #14150A; border: none;"
                " font-size: 6.8pt; font-weight: 700; letter-spacing: 1.2px; }"
                % theme.ACCENT)
            load.clicked.connect(lambda _=False, k=key: self._load_kit(k))
            layout.addWidget(load)
            self.kit_rows_box.addWidget(row)

    def _refresh_kits_grid(self) -> None:
        while self.kits_grid.count():
            item = self.kits_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._kit_cards = []
        keys = list(self.ctx.loadouts)
        for index, key in enumerate(keys):
            name, icons = self._kit_summary(key)
            card = KitCard(key)
            card.set_kit(
                name=name,
                tag="AKTIV" if key == self.ctx.settings.active_loadout else "",
                icons=icons[:4],
                favorite=self.ctx.is_favorite_kit(key),
                when="zuletzt gespielt",
            )
            card.load_requested.connect(self._load_kit)
            card.edit_requested.connect(self._edit_kit)
            card.delete_requested.connect(self._delete_kit)
            card.favorite_toggled.connect(self.ctx.toggle_favorite_kit)
            self.kits_grid.addWidget(card, index // 3, index % 3)
            self._kit_cards.append(card)

        new_card = QFrame()
        new_card.setObjectName("slotCard")
        new_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        new_card.setProperty("empty", True)
        new_card.setFixedSize(288, 216)
        new_card.setCursor(Qt.CursorShape.PointingHandCursor)
        new_layout = QVBoxLayout(new_card)
        plus = QLabel("+")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plus.setStyleSheet(f"color: {theme.DIM}; font-size: 26pt;")
        label = QLabel("NEUES KIT")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(
            f"color: {theme.MUTED}; font-size: 8pt; letter-spacing: 2px;")
        new_layout.addStretch(1)
        new_layout.addWidget(plus)
        new_layout.addWidget(label)
        new_layout.addStretch(1)
        new_card.mouseReleaseEvent = (  # type: ignore[method-assign]
            lambda _event: self._new_kit())
        self.kits_grid.addWidget(new_card, len(keys) // 3, len(keys) % 3)
        self.kits_footer.setText(f"{len(keys)} Kits  ·  Klick auf den Stern markiert Favoriten")

    def _kit_row_menu(self, key: str, parent: QWidget) -> None:
        menu = QMenu(self)
        load = menu.addAction("Laden")
        edit = menu.addAction("Umbenennen")
        menu.addSeparator()
        delete = menu.addAction("Löschen")
        action = menu.exec(parent.mapToGlobal(parent.rect().bottomLeft()))
        if action is load:
            self._load_kit(key)
        elif action is edit:
            self._edit_kit(key)
        elif action is delete:
            self._delete_kit(key)

    def _load_kit(self, key: str) -> None:
        self.ctx.set_active_loadout(key)
        self._on_tab(0)

    def _edit_kit(self, key: str) -> None:
        name, ok = QInputDialog.getText(self, "Kit umbenennen", "Name:",
                                        text=self.ctx.loadouts[key].name)
        if ok and name.strip():
            self.ctx.rename_loadout(key, name.strip())

    def _delete_kit(self, key: str) -> None:
        loadout = self.ctx.loadouts.get(key)
        if loadout is None:
            return
        if len(self.ctx.loadouts) <= 1:
            QMessageBox.information(
                self, "Kit löschen",
                "Mindestens ein Kit muss bleiben – lege zuerst ein neues an.")
            return
        box = QMessageBox(self)
        box.setWindowTitle("Kit löschen")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText(f"„{loadout.name}“ wirklich löschen?")
        box.setInformativeText(
            "Das Kit verschwindet aus der Liste. Die Stratagems selbst bleiben "
            "in der Datenbank.")
        delete = box.addButton("LÖSCHEN", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("ABBRECHEN", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        if box.clickedButton() is delete:
            self.ctx.delete_loadout(key)

    def _new_kit(self) -> None:
        name, ok = QInputDialog.getText(self, "Neues Kit", "Name:", text="Neues Kit")
        if ok and name.strip():
            self.ctx.create_loadout(name.strip())
            self._on_tab(1)

    # -- selection -------------------------------------------------------
    def _pick_slot(self, index: int) -> None:
        current = self.ctx.loadout.slots[index]
        dialog = StratagemPicker(self.ctx, current, parent=self)
        dialog.picked.connect(lambda sid: self.ctx.set_slot(index, sid))
        dialog.exec()

    # -- activity --------------------------------------------------------
    def _on_executed(self, stratagem: Stratagem, source: str) -> None:
        stamp = time.strftime("%H:%M")
        source_label = {"hotkey": "HOTKEY", "voice": "STIMME", "test": "TEST"}.get(
            source, source.upper())
        self._feed.insert(0, f"{stamp}|{source_label}|{stratagem.name}")
        del self._feed[3:]
        for index, name_label in enumerate(self.activity_rows):
            if index < len(self._feed):
                stamp_, source_, name = self._feed[index].split("|", 2)
            else:
                stamp_, source_, name = "--:--", "", ""
            time_label = name_label.property("time_label")
            source_widget = name_label.property("source_label")
            if time_label is not None:
                time_label.setText(stamp_)
            if source_widget is not None:
                source_widget.setText(source_)
            name_label.setText(name)
        self._refresh_slots()
