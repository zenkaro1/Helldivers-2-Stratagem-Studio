# Logo — Stratagem Studio

Entworfen in **VectorCraft 0.21** über den MCP-Server (`vectorcraft-cli mcp --headless`),
jede Form als echte Vektor-Operation (Polygone/Pfade), keine Rastervorlage.

## Idee

Das Zeichen ist ein **Stratagem-Kompass**: ein hexagonales Panzerplatten-Badge (Super
Destroyer / Hellpod-Anmutung) mit vier Pfeil-Chevrons, die nach außen zeigen — die
Eingaberichtungen eines Stratagem-Codes — und einem gelben Diamant-Kern.

- **Hexagon** = Schiffspanzerung, klar abgegrenztes App-Icon.
- **Vier Chevrons** = ↑ → ↓ ← , die Sprache der Stratagems.
- **Diamant-Kern** = das Stratagem selbst, das „Ziel“ des Codes.

## Farben

| Rolle | Wert |
| --- | --- |
| Platte | `#12140F` |
| Platte dunkel (Icon) | `#0B0C08` |
| Rand | `#3D4231` |
| Innenring | `#2B2F22` |
| Akzent (Chevrons, Kern) | `#F5D13F` |
| Wortmarke | `#EAE8DD` |
| Unterzeile | `#8F9484` |

Schrift: **Bahnschrift** (Bold für die Wortmarke, SemiBold für die Unterzeile) —
dieselbe Schrift wie in der App.

## Dateien

| Datei | Inhalt |
| --- | --- |
| `logo-mark.png` / `.svg` | Zeichen allein, 1024 × 1024, transparent |
| `logo-mark-512.png` | Zeichen, 512 × 512 |
| `logo-icon.png` / `.svg` | App-Icon (abgerundete Platte + Zeichen), 1024 × 1024 |
| `logo-icon-256.png` | App-Icon, 256 × 256 (auch als `app/assets/logo.png`) |
| `logo-lockup.png` / `.svg` | Zeichen + Wortmarke „STRATAGEM STUDIO“ + Unterzeile, 1800 × 560 |

## Neu bauen

```bat
.venv\Scripts\python.exe tools\build_logo.py
```

Das Skript verbindet sich mit VectorCraft (headless), baut drei Dokumente
(Zeichen, Lockup, Icon) und exportiert PNG + SVG nach `design/exports/logo/`.

## Verwendung

- **App-Icon**: `app/assets/logo.png` wird für Fenster- und Tray-Icon geladen.
- **Wortmarke**: als SVG frei skalierbar, z. B. für Startbildschirm, README, Installer.
- Mindestgröße für das Zeichen: 24 px (dann nur noch Hexagon + Kern lesbar).
