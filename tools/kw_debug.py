import sys

sys.path.insert(0, r"C:\Projekte\Website Design\hd2-stratagem-studio")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from app.context import AppContext  # noqa: E402
from app.core.database import StratagemDatabase  # noqa: E402
from app.core.models import AppSettings, Loadout  # noqa: E402
from app.core.storage import Storage  # noqa: E402
from app.paths import STRATAGEM_DB  # noqa: E402

settings = AppSettings()
settings.voice.only_loadout = True
loadouts = {"default": Loadout(slots=["eagle_500kg_bomb", "orbital_380mm_he_barrage", None, None])}
ctx = AppContext(StratagemDatabase(STRATAGEM_DB), Storage(), settings, loadouts)

ctx.add_custom_keyword("eagle_500kg_bomb", "5kg")
ctx.add_custom_keyword("orbital_380mm_he_barrage", "380")
ctx.add_custom_keyword("orbital_120mm_he_barrage", "120")

for text in ("5kg", "380", "120", "380mm", "dreihundertachtzig", "120mm"):
    match = ctx.submit_text(text, execute=False)
    print(f"{text!r:24} -> {match.stratagem.name if match.stratagem else None} "
          f"(score {match.score}, alias {match.alias!r}, alternatives {match.alternatives[:2]})")

print("candidates:", [s.name for s in ctx.candidates()])
print("380 in loadout?", "orbital_380mm_he_barrage" in ctx.loadout.slots)
print("120 in loadout?", "orbital_120mm_he_barrage" in ctx.loadout.slots)
