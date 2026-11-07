"""Application controller: wires settings, database, macros, hotkeys and voice."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal

from .core.database import StratagemDatabase
from .core.hotkeys import HotkeyManager, PushToTalk, backend_available
from .core.input_sender import MacroRunner
from .core.models import (
    AppSettings,
    Loadout,
    Mission,
    Stratagem,
    effective_cooldown,
    effective_uses,
)
from .core.storage import Storage
from .core.voice.matcher import VoiceMatch, VoiceMatcher
from .core.voice.recorder import MicrophoneRecorder, RecorderError, available as audio_available
from .core.voice.transcribe import (
    BackendConfig,
    TranscribeError,
    build_backend,
)

QUICK_LABELS = {
    "resupply": "Nachschub",
    "reinforce": "Verstärkung",
    "sos_beacon": "SOS-Bake",
}


class AppContext(QObject):
    status_changed = Signal(str)
    executed = Signal(object, str)          # Stratagem, source
    voice_state = Signal(str)               # idle | listening | transcribing | error
    voice_text = Signal(str)                # raw transcript
    voice_match = Signal(object)            # VoiceMatch
    voice_level = Signal(float)
    loadout_changed = Signal()
    settings_changed = Signal()
    cooldowns_changed = Signal()
    hotkey_errors = Signal(list)
    error = Signal(str)
    info = Signal(str)

    def __init__(self, db: StratagemDatabase, storage: Storage,
                 settings: AppSettings, loadouts: dict[str, Loadout],
                 parent: QObject | None = None):
        super().__init__(parent)
        self.db = db
        self.storage = storage
        self.settings = settings
        self.loadouts = loadouts
        self._cooldowns: dict[str, float] = {}
        self._charges: dict[str, int] = {}
        self._last_hotkey_warning: str | None = None

        self.runner = MacroRunner(lambda: self.settings.macro, self)
        self.runner.finished.connect(self._on_macro_finished)
        self.runner.failed.connect(lambda message: self.error.emit(message))
        self.runner.busy_changed.connect(self._on_macro_busy)

        self.hotkeys = HotkeyManager(self)
        self.hotkeys.triggered.connect(self._on_hotkey)
        self.ptt = PushToTalk(self)
        self.ptt.pressed.connect(self.on_ptt_pressed)
        self.ptt.released.connect(self.on_ptt_released)

        self.matcher = VoiceMatcher(settings.voice.threshold)
        self.matcher.set_custom_aliases(settings.custom_aliases)
        self._recorder: MicrophoneRecorder | None = None
        self._transcriber = None
        self._transcribing = False
        self._lock = threading.Lock()
        self._last_ptt = 0.0

        if not backend_available():
            self.error.emit("Globale Hotkeys sind nicht verfügbar (Windows-Funktion fehlt).")

    # ------------------------------------------------------------------
    # loadout
    # ------------------------------------------------------------------
    @property
    def loadout(self) -> Loadout:
        return self.loadouts.get(self.settings.active_loadout) or next(iter(self.loadouts.values()))

    def set_active_loadout(self, key: str) -> None:
        if key in self.loadouts:
            self.settings.active_loadout = key
            self.save_settings()
            self.loadout_changed.emit()

    def set_slot(self, index: int, stratagem_id: str | None) -> None:
        if not 0 <= index < 4:
            return
        if stratagem_id:
            for other_index, existing in enumerate(self.loadout.slots):
                if existing == stratagem_id and other_index != index:
                    stratagem = self.db.get(stratagem_id)
                    name = stratagem.name if stratagem else "Das Stratagem"
                    self.error.emit(
                        f"{name} ist schon in Slot {other_index + 1} – Du kannst "
                        "dasselbe Stratagem nicht zweimal benutzen.")
                    return
        self.loadout.slots[index] = stratagem_id
        self._persist_loadouts()

    # -- free slots for event stratagems ---------------------------------
    def extra_stratagems(self) -> list[Stratagem | None]:
        result: list[Stratagem | None] = []
        for stratagem_id in (list(self.settings.extra_stratagems) + [None, None])[:2]:
            result.append(self.db.get(stratagem_id) if stratagem_id else None)
        return result

    def set_extra(self, index: int, stratagem_id: str | None) -> None:
        if not 0 <= index < 2:
            return
        extras = self.settings.extra_stratagems
        if stratagem_id:
            stratagem = self.db.get(stratagem_id)
            name = stratagem.name if stratagem else "Das Stratagem"
            if stratagem_id in self.loadout.slots:
                self.error.emit(f"{name} liegt schon im Loadout.")
                return
            for other, existing in enumerate(extras):
                if existing == stratagem_id and other != index:
                    self.error.emit(f"{name} ist schon in Extra {other + 1}.")
                    return
        extras[index] = stratagem_id
        self.save_settings()
        self.apply_hotkeys()
        self.loadout_changed.emit()

    def trigger_extra(self, index: int) -> bool:
        extras = self.extra_stratagems()
        if not 0 <= index < len(extras):
            return False
        return self.execute(extras[index], "hotkey")

    def set_quick(self, key: str, stratagem_id: str | None) -> None:
        self.loadout.quick[key] = stratagem_id
        self._persist_loadouts()

    # -- mission ---------------------------------------------------------
    @property
    def mission(self) -> Mission | None:
        return self.db.mission(self.settings.active_mission)

    def set_mission(self, mission_id: str) -> None:
        if self.db.mission(mission_id) is None:
            return
        self.settings.active_mission = mission_id
        self.save_settings()
        self.apply_hotkeys()
        self.loadout_changed.emit()

    def mission_stratagems(self) -> list[Stratagem]:
        return self.db.mission_stratagems(self.settings.active_mission)

    # -- ship modules ----------------------------------------------------
    @property
    def ship_modules(self) -> tuple:
        """Installed Super Destroyer modules (only cooldown relevant ones)."""
        return tuple(
            module for module in self.db.ship_modules
            if module.id in self.settings.ship_modules
        )

    def has_ship_module(self, module_id: str) -> bool:
        return module_id in self.settings.ship_modules

    def toggle_ship_module(self, module_id: str) -> None:
        if self.db.ship_module(module_id) is None:
            return
        installed = self.settings.ship_modules
        if module_id in installed:
            installed.remove(module_id)
        else:
            installed.append(module_id)
        self.save_settings()
        self.cooldowns_changed.emit()
        self.loadout_changed.emit()

    def effective_cooldown(self, stratagem: Stratagem | None) -> int | None:
        if stratagem is None:
            return None
        return effective_cooldown(stratagem.cooldown, stratagem, self.ship_modules)

    def effective_uses(self, stratagem: Stratagem | None) -> int | None:
        if stratagem is None:
            return None
        return effective_uses(stratagem.uses, stratagem, self.ship_modules)

    # -- favorites / recent ----------------------------------------------
    def is_favorite(self, stratagem_id: str) -> bool:
        return stratagem_id in self.settings.favorites

    def toggle_favorite(self, stratagem_id: str) -> None:
        favorites = self.settings.favorites
        if stratagem_id in favorites:
            favorites.remove(stratagem_id)
        else:
            favorites.append(stratagem_id)
        self.save_settings()

    def mark_recent(self, stratagem_id: str) -> None:
        recent = [item for item in self.settings.recent if item != stratagem_id]
        recent.insert(0, stratagem_id)
        self.settings.recent = recent[:12]
        self.save_settings()

    def recent_stratagems(self) -> list[Stratagem]:
        return [item for item in (self.db.get(sid) for sid in self.settings.recent) if item]

    # -- custom voice keywords -------------------------------------------
    def custom_keywords(self, stratagem_id: str) -> list[str]:
        return list(self.settings.custom_aliases.get(stratagem_id, []))

    def all_custom_keywords(self) -> list[tuple[str, str]]:
        """(keyword, stratagem id) for every user defined keyword."""
        rows: list[tuple[str, str]] = []
        for stratagem_id, keywords in self.settings.custom_aliases.items():
            if self.db.get(stratagem_id) is None:
                continue
            rows.extend((keyword, stratagem_id) for keyword in keywords)
        return rows

    def add_custom_keyword(self, stratagem_id: str, keyword: str) -> bool:
        keyword = keyword.strip()
        if not keyword or self.db.get(stratagem_id) is None:
            return False
        keywords = self.settings.custom_aliases.setdefault(stratagem_id, [])
        if any(existing.casefold() == keyword.casefold() for existing in keywords):
            return False
        keywords.append(keyword)
        self.matcher.set_custom_aliases(self.settings.custom_aliases)
        self.save_settings()
        return True

    def remove_custom_keyword(self, stratagem_id: str, keyword: str) -> None:
        keywords = [item for item in self.settings.custom_aliases.get(stratagem_id, [])
                    if item != keyword]
        if keywords:
            self.settings.custom_aliases[stratagem_id] = keywords
        else:
            self.settings.custom_aliases.pop(stratagem_id, None)
        self.matcher.set_custom_aliases(self.settings.custom_aliases)
        self.save_settings()

    def favorite_stratagems(self) -> list[Stratagem]:
        return [item for item in (self.db.get(sid) for sid in self.settings.favorites) if item]

    def is_favorite_kit(self, key: str) -> bool:
        return key in self.settings.favorite_kits

    def toggle_favorite_kit(self, key: str) -> None:
        favorites = self.settings.favorite_kits
        if key in favorites:
            favorites.remove(key)
        else:
            favorites.append(key)
        self.save_settings()
        self.loadout_changed.emit()

    def randomize(self) -> None:
        picks = self.db.random_loadout()
        for index in range(4):
            self.loadout.slots[index] = picks[index].id if index < len(picks) else None
        self._persist_loadouts()

    def _persist_loadouts(self) -> None:
        self.storage.save_loadouts(self.loadouts)
        self.loadout_changed.emit()

    def create_loadout(self, name: str) -> str:
        key = name.strip() or "Loadout"
        base, counter = key, 2
        while key in self.loadouts:
            key = f"{base} {counter}"
            counter += 1
        self.loadouts[key] = Loadout(name=key)
        self.storage.save_loadouts(self.loadouts)
        self.set_active_loadout(key)
        return key

    def rename_loadout(self, old: str, new: str) -> None:
        new = new.strip()
        if not new or new == old or new in self.loadouts:
            return
        loadout = self.loadouts.pop(old)
        loadout.name = new
        self.loadouts[new] = loadout
        if self.settings.active_loadout == old:
            self.settings.active_loadout = new
            self.save_settings()
        self._persist_loadouts()

    def delete_loadout(self, key: str) -> None:
        if len(self.loadouts) <= 1:
            self.error.emit("Mindestens ein Loadout muss bleiben.")
            return
        self.loadouts.pop(key, None)
        if self.settings.active_loadout == key:
            self.settings.active_loadout = next(iter(self.loadouts))
            self.save_settings()
        self._persist_loadouts()

    # ------------------------------------------------------------------
    # execution
    # ------------------------------------------------------------------
    def remaining_uses(self, stratagem: Stratagem | None) -> int | None:
        """Eagle charges left; None for stratagems without a use limit."""
        if stratagem is None:
            return None
        total = self.effective_uses(stratagem)
        if not total:
            return None
        # Rearm finished -> charges are full again.
        if self.cooldown_remaining(stratagem.id) <= 0 and self._charges.get(
                stratagem.id, total) <= 0:
            self._charges[stratagem.id] = total
        return max(0, self._charges.get(stratagem.id, total))

    def execute(self, stratagem: Stratagem | None, source: str = "hotkey") -> bool:
        if stratagem is None:
            return False
        if self.runner.busy:
            return False
        total_uses = self.effective_uses(stratagem)
        blocking = self.settings.macro.block_on_cooldown
        if blocking:
            if total_uses and (self.remaining_uses(stratagem) or 0) <= 0:
                self.info.emit(f"{stratagem.name} ist im Rearm.")
                return False
            remaining = self.cooldown_remaining(stratagem.id)
            if remaining > 0:
                self.info.emit(
                    f"{stratagem.name} ist noch {round(remaining)} s im Cooldown.")
                return False
        elif total_uses and (self.remaining_uses(stratagem) or 0) <= 0:
            # No blocking by default: treat it as rearmed and send anyway.
            self._charges[stratagem.id] = total_uses
            self._cooldowns.pop(stratagem.id, None)
        started = self.runner.run(stratagem, source)
        if not started:
            return False
        cooldown = self.effective_cooldown(stratagem) or 0
        if total_uses:
            left = (self.remaining_uses(stratagem) or 0) - 1
            self._charges[stratagem.id] = left
            if left <= 0:
                self._cooldowns[stratagem.id] = time.time() + cooldown
            else:
                self._cooldowns.pop(stratagem.id, None)
        else:
            self._cooldowns[stratagem.id] = time.time() + cooldown
        self.mark_recent(stratagem.id)
        if cooldown:
            self.cooldowns_changed.emit()
        return True

    def trigger_slot(self, index: int) -> bool:
        if not 0 <= index < 4:
            return False
        return self.execute(self.db.get(self.loadout.slots[index]), "hotkey")

    def trigger_quick(self, key: str) -> bool:
        return self.execute(self.db.get(self.loadout.quick.get(key)), "hotkey")

    def trigger_mission(self, stratagem_id: str) -> bool:
        return self.execute(self.db.get(stratagem_id), "hotkey")

    def trigger_mission_slot(self, index: int) -> bool:
        """Trigger the mission stratagem in position 0..2 for the active mission."""
        stratagems = self.mission_stratagems()
        if not 0 <= index < len(stratagems):
            return False
        return self.execute(stratagems[index], "hotkey")

    def _on_hotkey(self, action: str) -> None:
        from . import diagnostics

        diagnostics.macro_log(f"hotkey triggered: {action}")
        if action.startswith("mission_slot"):
            self.trigger_mission_slot(int(action[-1]) - 1)
        elif action.startswith("extra"):
            self.trigger_extra(int(action[-1]) - 1)
        elif action.startswith("side:"):
            self.trigger_mission(action.split(":", 1)[1])
        elif action.startswith("mission:"):
            self.trigger_mission(action.split(":", 1)[1])
        elif action.startswith("slot"):
            self.trigger_slot(int(action[-1]) - 1)
        elif action in QUICK_LABELS:
            self.trigger_quick(action)

    def _on_macro_finished(self, label: str) -> None:
        self.info.emit(f"{label} ausgeführt")

    def _on_macro_busy(self, busy: bool) -> None:
        # The macro itself sends keys (W/A/S/D, CTRL): ignore them while running.
        self.hotkeys.suspend(busy)

    def cooldown_remaining(self, stratagem_id: str) -> float:
        end = self._cooldowns.get(stratagem_id)
        if not end:
            return 0.0
        return max(0.0, end - time.time())

    # ------------------------------------------------------------------
    # settings / hotkeys
    # ------------------------------------------------------------------
    def save_settings(self) -> None:
        self.storage.save_settings(self.settings)
        self.settings_changed.emit()

    @staticmethod
    def _action_label(action: str) -> str:
        if action.startswith("side:"):
            from .core.models import SIDE_OBJECTIVES

            side_id = action.split(":", 1)[1]
            return dict(SIDE_OBJECTIVES).get(side_id, "Sonderziel")
        if action.startswith("mission_slot"):
            return f"Missions-Slot {action[-1]}"
        if action.startswith("extra"):
            return f"Extra {action[-1]}"
        if action.startswith("slot"):
            return f"Slot {action[-1]}"
        return {"resupply": "Nachschub", "reinforce": "Verstärkung",
                "sos_beacon": "SOS-Bake"}.get(action, action)

    def _hotkey_conflicts(self, bindings: dict[str, str]) -> list[str]:
        """Two actions on the same key (or PTT) would silently never fire."""
        grouped: dict[str, list[str]] = {}
        for action, combo in bindings.items():
            if combo:
                grouped.setdefault(combo.lower(), []).append(action)
        messages: list[str] = []
        for combo, actions in sorted(grouped.items()):
            if len(actions) > 1:
                labels = ", ".join(self._action_label(action) for action in actions)
                messages.append(f"{combo.upper()} ist doppelt belegt: {labels}")
        ptt = (self.settings.voice.ptt_key or "").lower()
        if ptt and ptt in grouped:
            labels = ", ".join(self._action_label(action) for action in grouped[ptt])
            messages.append(f"{ptt.upper()} ist Push-to-Talk und {labels}")
        return messages

    def apply_hotkeys(self) -> None:
        from . import diagnostics

        if not self.settings.hotkeys.enabled:
            self.hotkeys.clear()
            self._last_hotkey_warning = None
            diagnostics.macro_log("hotkeys disabled")
            return
        bindings: dict[str, str] = {}
        for index, combo in enumerate(self.settings.hotkeys.slots, start=1):
            if combo:
                bindings[f"slot{index}"] = combo
        for key, combo in self.settings.hotkeys.quick.items():
            if combo:
                bindings[key] = combo
        for index, combo in enumerate(self.settings.hotkeys.mission_slots, start=1):
            if combo:
                bindings[f"mission_slot{index}"] = combo
        for stratagem_id, combo in self.settings.hotkeys.side.items():
            if combo and self.db.get(stratagem_id) is not None:
                bindings[f"side:{stratagem_id}"] = combo
        for index, combo in enumerate(self.settings.hotkeys.extra, start=1):
            extras = self.settings.extra_stratagems
            has_stratagem = index - 1 < len(extras) and extras[index - 1]
            if combo and has_stratagem:
                bindings[f"extra{index}"] = combo
        errors = self.hotkeys.apply(bindings)
        if errors:
            self.hotkey_errors.emit(errors)
        conflicts = self._hotkey_conflicts(bindings)
        warning = "; ".join(conflicts) if conflicts else None
        if warning and warning != self._last_hotkey_warning:
            self.error.emit(warning)
        self._last_hotkey_warning = warning
        diagnostics.macro_log(f"hotkeys applied: {bindings or '{}'} errors={errors}")

    def apply_ptt(self) -> None:
        errors = self.ptt.bind(self.settings.voice.ptt_key)
        if errors:
            self.hotkey_errors.emit(errors)

    # ------------------------------------------------------------------
    # voice
    # ------------------------------------------------------------------
    def _build_transcriber(self):
        config = BackendConfig(
            backend=self.settings.voice.backend,
            model=self.settings.voice.model,
            language=self.settings.voice.language,
            api_key=self.settings.voice.api_key,
            api_base=self.settings.voice.api_base,
            api_model=self.settings.voice.api_model,
            models_dir=self.storage.dir / "models",
        )
        return build_backend(config)

    def preload_voice(self) -> None:
        """Warm up the model/API in the background (downloads on first use)."""
        def work():
            try:
                self.voice_state.emit("loading")
                transcriber = self._build_transcriber()
                transcriber.preload(lambda message: self.info.emit(message))
                self._transcriber = transcriber
                self.voice_state.emit("idle")
            except (TranscribeError, Exception) as exc:  # noqa: BLE001
                self.voice_state.emit("error")
                self.error.emit(str(exc))
        threading.Thread(target=work, daemon=True).start()

    def _ensure_recorder(self) -> MicrophoneRecorder:
        device = self.settings.voice.device
        if self._recorder is None or self._recorder.device != device:
            self._recorder = MicrophoneRecorder(device=device)
        return self._recorder

    def on_ptt_pressed(self) -> None:
        if not self.settings.voice.enabled or self._transcribing:
            return
        if not audio_available():
            self.voice_state.emit("error")
            self.error.emit("Keine Audio-Unterstützung (sounddevice fehlt).")
            return
        if time.time() - self._last_ptt < 0.15:
            return
        try:
            self._ensure_recorder().start()
            self.voice_state.emit("listening")
        except RecorderError as exc:
            self.voice_state.emit("error")
            self.error.emit(str(exc))

    def on_ptt_released(self) -> None:
        recorder = self._recorder
        if recorder is None or not recorder.recording:
            return
        self._last_ptt = time.time()
        audio = recorder.stop()
        self.voice_state.emit("transcribing")
        if audio is None or audio.size < 1200:
            self.voice_state.emit("idle")
            self.info.emit("Zu kurz – nichts erkannt.")
            return
        threading.Thread(target=self._transcribe_worker, args=(audio,), daemon=True).start()

    def _transcribe_worker(self, audio) -> None:
        with self._lock:
            if self._transcribing:
                return
            self._transcribing = True
        try:
            if self._transcriber is None:
                self._transcriber = self._build_transcriber()
            text = self._transcriber.transcribe(audio)
            self.voice_text.emit(text)
            if not text:
                self.info.emit("Nichts verstanden.")
                return
            self.submit_text(text)
        except TranscribeError as exc:
            self.voice_state.emit("error")
            self.error.emit(str(exc))
        finally:
            self._transcribing = False
            self.voice_state.emit("idle")

    def candidates(self) -> list[Stratagem]:
        if not self.settings.voice.only_loadout:
            return self.db.items
        ids: list[str] = [slot for slot in self.loadout.slots if slot]
        ids += [value for value in self.loadout.quick.values() if value]
        ids += [item.id for item in self.mission_stratagems()]
        # Explicitly configured keywords should always be reachable, even when the
        # stratagem is not part of the current loadout.
        ids += [key for key, words in self.settings.custom_aliases.items() if words]
        seen: list[Stratagem] = []
        added: set[str] = set()
        for stratagem_id in ids:
            if stratagem_id in added:
                continue
            item = self.db.get(stratagem_id)
            if item:
                seen.append(item)
                added.add(stratagem_id)
        return seen or self.db.items

    def submit_text(self, text: str, execute: bool = True) -> VoiceMatch:
        self.matcher.threshold = self.settings.voice.threshold
        match = self.matcher.match(text, self.candidates())
        if not match.ok and self.settings.voice.only_loadout:
            # Explain "not in active loadout" instead of a bare "not recognised".
            wider = self.matcher.match(text, self.db.items)
            if wider.stratagem is not None:
                match.outside_loadout = wider.stratagem
                match.score = wider.score
                match.alias = wider.alias
                match.alternatives = wider.alternatives
        self.voice_match.emit(match)
        if execute and match.ok:
            if match.stratagem is not None:
                self.execute(match.stratagem, "voice")
            elif match.slot is not None:
                self.trigger_slot(match.slot - 1)
        return match

    # ------------------------------------------------------------------
    # shutdown
    # ------------------------------------------------------------------
    def shutdown(self) -> None:
        """Remove global hooks before the interpreter exits.

        The ``keyboard`` listener runs a daemon thread inside a low-level
        Windows hook; letting Python finalize while it is still active ends in
        an access violation on exit.  Unhook everything first.
        """
        try:
            self.hotkeys.clear()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.ptt.unbind()
        except Exception:  # noqa: BLE001
            pass
        try:
            from .core import hotkeys as hotkey_backend

            hotkey_backend.shutdown()
        except Exception:  # noqa: BLE001
            pass
