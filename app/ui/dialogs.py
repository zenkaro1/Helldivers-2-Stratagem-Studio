"""Stratagem picker v2: category tabs, favorites, recent and search."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..context import AppContext
from ..core.models import Stratagem, category_color, category_label
from . import theme
from .cards import StarLabel
from .widgets import CodeStrip, icon_pixmap, section_label

TABS = [
    ("fav", "FAVORITEN"),
    ("recent", "ZULETZT"),
    ("orbital", "ORBITAL"),
    ("eagle", "EAGLE"),
    ("support", "SUPPORT"),
    ("sentry", "GESCHÜTZ"),
    ("mission", "MISSION"),
]


class PickerRow(QWidget):
    favorite_toggled = Signal(str)
    clicked = Signal(str)

    def __init__(self, ctx: AppContext, stratagem: Stratagem,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.stratagem = stratagem
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 10, 5)
        layout.setSpacing(10)

        self.star = StarLabel(13, ctx.is_favorite(stratagem.id))
        self.star.clicked.connect(self._toggle)
        layout.addWidget(self.star)

        icon = QLabel()
        icon.setFixedSize(36, 36)
        icon.setPixmap(icon_pixmap(stratagem.icon, 34))
        layout.addWidget(icon)

        text = QVBoxLayout()
        text.setSpacing(0)
        name = QLabel(stratagem.name)
        name.setStyleSheet(f"color: {theme.TEXT}; font-size: 9.6pt;")
        cooldown = ctx.effective_cooldown(stratagem)
        uses = ctx.effective_uses(stratagem)
        extra = []
        if stratagem.radius:
            extra.append(f"{stratagem.radius} m Radius")
        if stratagem.ap:
            extra.append(f"Panzerung {stratagem.ap_text}")
        slot = next((index + 1 for index, value in enumerate(ctx.loadout.slots)
                     if value == stratagem.id), None)
        meta_text = (
            f"{category_label(stratagem.category)}  ·  "
            f"{cooldown if cooldown else '—'} s Cooldown"
            f"  ·  {uses if uses else '—'} Einsätze"
            + ("  ·  " + "  ·  ".join(extra) if extra else ""))
        meta = QLabel(meta_text)
        meta.setStyleSheet(
            f"color: {theme.ACCENT if slot else theme.MUTED}; font-size: 7.4pt;")
        if slot:
            name.setText(f"{stratagem.name}   ·   in Slot {slot}")
        text.addWidget(name)
        text.addWidget(meta)
        layout.addLayout(text, 1)

        code = CodeStrip(stratagem.code, chip=15, gap=3,
                         color=category_color(stratagem.category))
        layout.addWidget(code)

    def _toggle(self) -> None:
        self.ctx.toggle_favorite(self.stratagem.id)
        self.star.set_filled(self.ctx.is_favorite(self.stratagem.id))
        self.favorite_toggled.emit(self.stratagem.id)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.stratagem.id)
        super().mouseReleaseEvent(event)


class InputSelfTest(QDialog):
    """Sends one real key press into a focused field to verify SendInput."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtCore import QTimer

        from ..core.input_sender import MacroSender

        self.setWindowTitle("Eingabe-Selbsttest")
        self.setModal(True)
        self.resize(460, 190)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        title = QLabel("EINGABE-SELBSTTEST")
        title.setObjectName("kicker")
        layout.addWidget(title)
        hint = QLabel(
            "Das Feld ist gleich im Fokus. Nach zwei Sekunden sendet die App ein "
            "echtes „a“ über SendInput – erscheint es im Feld, funktioniert die "
            "Tastatureingabe.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        layout.addWidget(hint)

        self.field = QLineEdit()
        self.field.setPlaceholderText("Hier sollte gleich ein „a“ erscheinen …")
        layout.addWidget(self.field)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.result.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        layout.addWidget(self.result)
        close = QPushButton("SCHLIESSEN")
        close.setObjectName("ghost")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

        def send() -> None:
            sender = MacroSender()
            sender.key("a", True)
            sender.key("a", False)
            QTimer.singleShot(350, check)

        def check() -> None:
            if "a" in self.field.text():
                self.result.setText("Eingabe angekommen – SendInput funktioniert.")
                self.result.setStyleSheet(f"color: {theme.GREEN}; font-size: 9pt;")
            else:
                self.result.setText(
                    "Keine Eingabe angekommen. Dann blockiert etwas die synthetische "
                    "Tastatur (Antivirus, anderes Fenster im Vordergrund) – bitte "
                    "melden.")
                self.result.setStyleSheet(f"color: {theme.RED}; font-size: 9pt;")

        self.field.setFocus()
        QTimer.singleShot(1500, send)


class HotkeyCheck(QDialog):
    """Waits a few seconds for a global hotkey and reports whether it arrived."""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        from PySide6.QtCore import QTimer

        self.ctx = ctx
        self._fired = False
        self.setWindowTitle("Hotkey-Test")
        self.setModal(True)
        self.resize(470, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        title = QLabel("HOTKEY-TEST")
        title.setObjectName("kicker")
        layout.addWidget(title)
        hint = QLabel(
            "Drücke jetzt eine belegte Taste (F1–F6). Der Test läuft 8 Sekunden. "
            "Wichtig: Die App darf dafür im Hintergrund sein – genau wie im Spiel.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        layout.addWidget(hint)
        self.state = QLabel("Warte auf Tastendruck …")
        self.state.setStyleSheet(f"color: {theme.ACCENT}; font-size: 11pt;")
        layout.addWidget(self.state)
        self.result = QLabel("")
        self.result.setWordWrap(True)
        self.result.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        layout.addWidget(self.result)
        close = QPushButton("SCHLIESSEN")
        close.setObjectName("ghost")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

        ctx.hotkeys.triggered.connect(self._on_trigger)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(8000)

    def _on_trigger(self, action: str) -> None:
        self._fired = True
        self._timer.stop()
        self.state.setText(f"Hotkey erkannt: {action}")
        self.state.setStyleSheet(f"color: {theme.GREEN}; font-size: 11pt;")
        self.result.setText(
            "Die App reagiert auf die Taste. Klappt es im Spiel trotzdem nicht, "
            "liegt es an der Übergabe ans Spiel – dann die App als Administrator "
            "starten (start-admin.cmd) und die Haltezeit erhöhen.")

    def _on_timeout(self) -> None:
        if self._fired:
            return
        from ..core.winutil import is_elevated

        self.state.setText("Kein Hotkey erkannt.")
        self.state.setStyleSheet(f"color: {theme.RED}; font-size: 11pt;")
        extra = "" if is_elevated() else (
            " Die App läuft nicht als Administrator – falls das Spiel erhöht läuft, "
            "starte die App über start-admin.cmd.")
        self.result.setText(
            "Taste kommt nicht an: prüfe, ob sie hier belegt ist, ob „HOTKEYS: AN“ "
            "steht und ob ein anderes Programm die Taste abfängt." + extra)

    def done(self, result: int) -> None:  # noqa: A003
        try:
            self.ctx.hotkeys.triggered.disconnect(self._on_trigger)
        except (RuntimeError, TypeError):
            pass
        super().done(result)


class KeywordDialog(QDialog):
    """Manage user defined voice keywords ("380" → Orbital 380mm HE Barrage)."""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setWindowTitle("Eigene Sprachbefehle")
        self.setModal(True)
        self.resize(620, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(10)
        root.addWidget(section_label("Sprachbefehle"))

        title = QLabel("EIGENE KEYWORDS")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        hint = QLabel(
            "Lege fest, was du sagst – z. B. „380“ für die 380er Barrage oder "
            "„dickes Sperrfeuer“. Groß-/Kleinschreibung ist egal.")
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.MUTED}; font-size: 8.5pt;")
        root.addWidget(hint)

        self.list = QListWidget()
        self.list.setSpacing(1)
        root.addWidget(self.list, 1)

        self.empty = QLabel("Noch keine eigenen Keywords.")
        self.empty.setStyleSheet(f"color: {theme.DIM}; font-size: 9pt;")
        root.addWidget(self.empty)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.count = QLabel("")
        self.count.setStyleSheet(
            f"color: {theme.DIM}; font-size: 7.4pt; letter-spacing: 1.4px;")
        footer.addWidget(self.count)
        footer.addStretch(1)
        add = QPushButton("HINZUFÜGEN")
        add.setObjectName("primary")
        add.clicked.connect(self._add)
        footer.addWidget(add)
        remove = QPushButton("ENTFERNEN")
        remove.setObjectName("danger")
        remove.clicked.connect(self._remove)
        footer.addWidget(remove)
        close = QPushButton("SCHLIESSEN")
        close.setObjectName("ghost")
        close.clicked.connect(self.accept)
        footer.addWidget(close)
        root.addLayout(footer)

        self._refresh()

    def _refresh(self) -> None:
        self.list.clear()
        for keyword, stratagem_id in self.ctx.all_custom_keywords():
            stratagem = self.ctx.db.get(stratagem_id)
            if stratagem is None:
                continue
            item = QListWidgetItem(f"„{keyword}“   →   {stratagem.name}")
            item.setData(Qt.ItemDataRole.UserRole, (stratagem_id, keyword))
            self.list.addItem(item)
        self.count.setText(f"{self.list.count()} EIGENE BEGRIFFE")
        self.empty.setVisible(self.list.count() == 0)

    def _add(self) -> None:
        picker = StratagemPicker(self.ctx, None, parent=self)
        chosen: dict[str, str] = {}
        picker.picked.connect(lambda sid: chosen.setdefault("id", sid))
        if picker.exec() != QDialog.DialogCode.Accepted or "id" not in chosen:
            return
        stratagem = self.ctx.db.get(chosen["id"])
        if stratagem is None:
            return
        keyword, ok = QInputDialog.getText(
            self, "Keyword", f"Begriff für „{stratagem.name}“:")
        if not ok or not keyword.strip():
            return
        if not self.ctx.add_custom_keyword(stratagem.id, keyword.strip()):
            QMessageBox.information(
                self, "Keyword", "Der Begriff ist leer oder schon vorhanden.")
        self._refresh()

    def _remove(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        stratagem_id, keyword = item.data(Qt.ItemDataRole.UserRole)
        self.ctx.remove_custom_keyword(stratagem_id, keyword)
        self._refresh()


class StratagemPicker(QDialog):
    picked = Signal(str)

    def __init__(self, ctx: AppContext, current_id: str | None = None,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.current_id = current_id
        self.tab = "fav"
        self.setWindowTitle("Stratagem wählen")
        self.setModal(True)
        self.resize(780, 660)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.addWidget(section_label("Datenbank"))
        title = QLabel("STRATAGEM WÄHLEN")
        title.setObjectName("pageTitle")
        title_box.addWidget(title)
        root.addLayout(title_box)

        self.search = QLineEdit()
        self.search.setObjectName("search")
        self.search.setPlaceholderText("Suchen – Name, Kürzel oder deutscher Sprachname …")
        self.search.textChanged.connect(self._rebuild)
        root.addWidget(self.search)

        click_hint = QLabel("Ein Klick übernimmt das Stratagem · Esc schließt")
        click_hint.setStyleSheet(f"color: {theme.DIM}; font-size: 7.6pt;")
        root.addWidget(click_hint)

        self.tab_row = QHBoxLayout()
        self.tab_row.setSpacing(6)
        self.tab_buttons: dict[str, QPushButton] = {}
        for key, label in TABS:
            button = QPushButton(label)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(28)
            button.clicked.connect(lambda _=False, k=key: self._set_tab(k))
            self.tab_row.addWidget(button)
            self.tab_buttons[key] = button
        self.tab_row.addStretch(1)
        root.addLayout(self.tab_row)

        self.list = QListWidget()
        self.list.setSpacing(1)
        self.list.itemDoubleClicked.connect(self._accept_item)
        self.list.currentItemChanged.connect(self._update_footer)
        root.addWidget(self.list, 1)

        footer = QHBoxLayout()
        footer.setSpacing(10)
        self.footer_name = QLabel("Keine Auswahl")
        self.footer_name.setStyleSheet(f"color: {theme.MUTED}; font-size: 9pt;")
        footer.addWidget(self.footer_name, 1)
        self.footer_code = CodeStrip("", chip=18, gap=3)
        footer.addWidget(self.footer_code)
        cancel = QPushButton("ABBRECHEN")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        root.addLayout(footer)

        self._set_tab("fav", emit=False)
        self._rebuild()
        self.search.setFocus()

    # ------------------------------------------------------------------
    def _set_tab(self, key: str, emit: bool = True) -> None:
        self.tab = key
        for name, button in self.tab_buttons.items():
            active = name == key
            button.setChecked(active)
            button.setStyleSheet(self._tab_style(active))
        if emit:
            self._rebuild()

    def _tab_style(self, active: bool) -> str:
        if active:
            return ("QPushButton { background: %s; color: #14150A; border: none;"
                    " border-radius: 2px; font-size: 6.9pt; font-weight: 700;"
                    " letter-spacing: 1.3px; padding: 0 10px; }" % theme.ACCENT)
        return ("QPushButton { background: #0E100B; color: %s; border: 1px solid %s;"
                " border-radius: 2px; font-size: 6.9pt; font-weight: 600;"
                " letter-spacing: 1.3px; padding: 0 10px; }"
                % (theme.MUTED, theme.BORDER_LIGHT))

    def _items(self) -> list[Stratagem]:
        query = self.search.text().strip()
        if query:
            return self.ctx.db.search(query)
        if self.tab == "fav":
            return self.ctx.favorite_stratagems()
        if self.tab == "recent":
            return self.ctx.recent_stratagems()
        if self.tab == "support":
            items = self.ctx.db.by_category("support")
            for extra in ("backpack", "vehicle"):
                items += self.ctx.db.by_category(extra)
            return items
        return self.ctx.db.by_category(self.tab)

    def _rebuild(self) -> None:
        self.list.clear()
        items = self._items()
        if not items:
            placeholder = QListWidgetItem(
                "Noch keine Einträge – markiere Stratagems mit dem Stern.")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            placeholder.setForeground(Qt.GlobalColor.gray)
            self.list.addItem(placeholder)
            return
        current_row = None
        for stratagem in items:
            row = QListWidgetItem()
            widget = PickerRow(self.ctx, stratagem)
            row.setSizeHint(QSize(0, 50))
            row.setData(Qt.ItemDataRole.UserRole, stratagem.id)
            self.list.addItem(row)
            self.list.setItemWidget(row, widget)
            widget.clicked.connect(self._choose)
            widget.favorite_toggled.connect(lambda _sid: self._rebuild())
            if stratagem.id == self.current_id:
                current_row = row
        if current_row is not None:
            self.list.setCurrentItem(current_row)

    def _choose(self, stratagem_id: str) -> None:
        """One left click is enough – no extra confirm button needed."""
        self._select(stratagem_id)
        self.picked.emit(str(stratagem_id))
        self.accept()

    def _select(self, stratagem_id: str) -> None:
        for index in range(self.list.count()):
            item = self.list.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == stratagem_id:
                self.list.setCurrentItem(item)
                return

    def _update_footer(self, current: QListWidgetItem | None) -> None:
        if current is None:
            return
        stratagem = self.ctx.db.get(current.data(Qt.ItemDataRole.UserRole))
        if stratagem is None:
            self.footer_name.setText("Keine Auswahl")
            self.footer_code.set_code("")
            return
        self.footer_name.setText(
            f"{stratagem.name}  ·  {self.ctx.effective_cooldown(stratagem)} s Cooldown"
            f"  ·  {self.ctx.effective_uses(stratagem) or '—'} Einsätze")
        self.footer_code.set_code(stratagem.code)

    def _accept_item(self, item: QListWidgetItem) -> None:
        stratagem_id = item.data(Qt.ItemDataRole.UserRole)
        if stratagem_id:
            self.picked.emit(str(stratagem_id))
            self.accept()

    def _accept_current(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self._accept_item(item)

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._accept_current()
            return
        super().keyPressEvent(event)
