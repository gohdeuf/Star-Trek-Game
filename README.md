# SpielPython — 3D-Weltraum-Spiel mit ursina

Eine modulare Projekt-Struktur für ein 3D-Spiel mit **ursina** (Python 3D-Engine).

## 📁 Projekt-Struktur

```
SpielPython/
├── main.py                 # Hauptdatei — nur App-Init & Szenen-Koordination
├── config.py              # Globale Einstellungen (anpassen hier)
├── enterprise_d.py        # Test-Datei (alte Version, kann gelöscht werden)
│
├── entities/              # 🎮 Spiel-Entities (Schiffe, Planeten, Monde)
│   ├── __init__.py        # Basis-Klasse + Fabrik-Funktionen (load_ship, load_planet)
│   ├── planets.py         # Planet, Earth, Mars, Moon Klassen
│   ├── ships/
│   │   ├── __init__.py    # Schiffs-Register (SHIPS dict)
│   │   └── enterprise.py  # Enterprise-Klasse
│   └── ...                # Später: enemy.py, asteroid.py, etc.
│
├── models/                # 🎨 3D-Modelle (Blender-Export)
│   ├── ships/
│   │   ├── enterprise.glb      # ← Später: Blender-Export
│   │   └── enterprise.obj      # ← Optional: OBJ-Format
│   ├── planets/
│   │   ├── earth.glb
│   │   └── mars.glb
│   └── ...
│
└── README.md              # Diese Datei
```

## ⚡ Quick Start

```bash
cd /home/username/Projekt/SpielPython
python3 main.py
```

Du solltest sehen:
- Eine Enterprise-Klasse D (aus Primitiven gebaut)
- Erde & Mars im Weltraum
- Mond um die Erde
- Sternenfeld als Hintergrund

### Steuerung
- **W/A/S/D** — Schiff bewegen (Vorwärts/Links/Zurück/Rechts)
- **Space/Ctrl** — Hoch/Runter
- **Pfeiltasten** — Pitch (hoch/runter) und Yaw (drehen)
- **Q/E** — Roll (Seitendrehung)
- **ESC** — Beenden

## 🛠️ Wie wird das Projekt erweitert?

### 1️⃣ Neues Schiff hinzufügen

1. Erstelle `entities/ships/warbird.py`:

```python
from ursina import *
from entities import GameEntity

class Warbird(GameEntity):
    def __init__(self, position=(0, 0, 0), **kwargs):
        super().__init__(name="Warbird", position=position, **kwargs)
        self.model = 'cone'
        self.color = color.red
        self.scale = 2
    
    def update(self):
        self.rotation_y += 10 * time.dt()
```

2. Registriere es in `entities/ships/__init__.py`:

```python
from entities.ships.warbird import Warbird

SHIPS = {
    'enterprise': Enterprise,
    'warbird': Warbird,  # ← Neu!
}
```

3. Nutze es in `main.py`:

```python
enemy = load_ship('warbird', position=(30, 0, 0))
```

### 2️⃣ Neuen Planeten hinzufügen

1. Erweiter `entities/planets.py`:

```python
class Jupiter(Planet):
    def __init__(self, position=(100, 0, 0), **kwargs):
        super().__init__(
            name="Jupiter",
            position=position,
            radius=5.0,
            color_val=color.orange,
            **kwargs
        )
```

2. Nutze es in `main.py`:

```python
jupiter = load_planet('jupiter', position=(100, 0, 0))
```

## 🎨 Blender-Modelle integrieren

Das ist später sehr einfach! So funktioniert es:

### Blender → Export (.glb)

1. Modell in Blender erstellen/öffnen (z.B. Enterprise)
2. **File → Export As → glTF Binary (.glb)**
3. Speichern in `models/ships/enterprise.glb`

### Code anpassen

In `entities/ships/enterprise.py`, ändere:

```python
def __init__(self, position=(0, 0, 0), use_builtin_model=True, **kwargs):
    # ...
    if use_builtin_model:
        self._build_ship_builtin()  # Alte Geometrie
    else:
        self._load_ship_model()     # Blender-Modell laden
```

Und implementiere `_load_ship_model()`:

```python
def _load_ship_model(self):
    """Lade 3D-Modell aus Blender-Export"""
    from config import MODELS_PATH
    model_path = f"{MODELS_PATH}/ships/enterprise.glb"
    self.model = model_path
    self.scale = 1.0  # Anpassen falls nötig
```

Dann in `main.py` nutzen:

```python
player_ship = load_ship('enterprise', position=(0, 0, 0), use_builtin_model=False)
```

## 📝 Wichtige Dateien kurz erklärt

| Datei | Zweck |
|-------|-------|
| `main.py` | App-Init, Szenen-Setup, nur 80 Zeilen reiner Code |
| `config.py` | Fenster, Kamera, Geschwindigkeit, Debug-Flags |
| `entities/__init__.py` | `GameEntity`-Basis + Fabrik-Funktionen |
| `entities/ships/enterprise.py` | Enterprise-Schiff mit Input-Handling |
| `entities/planets.py` | Planeten mit Rotation und Monde |

## 🎯 Nächste Schritte (Beispiel-Plan)

1. ✅ Modulstruktur erstellen (gemacht!)
2. ☐ Enterprise in Blender nachbauen + exportieren
3. ☐ Ein paar neue Schiffe/Gegner hinzufügen
4. ☐ Schussystem (Lazern) implementieren
5. ☐ Kollisionserkennung
6. ☐ HUD/UI (Radar, Gesundheit)
7. ☐ Missions/Level-System

## 📚 Ursina-Ressourcen

- **Ursina Doku:** https://github.com/pmp-library/pmp-library
- **Panda3D (Grundlage):** https://www.panda3d.org/

## ❓ Fehler/Fragen?

- `Font Arial nicht gefunden?` — ursina nutzt `courier`, `arial`, etc. Wenn nötig, siehe `config.py`
- `Modell lädt nicht?` — Prüfe den Pfad in `MODELS_PATH` und die Datei-Extension
- `Import-Fehler?` — Stelle sicher, dass alle `__init__.py`-Dateien in `entities/` vorhanden sind

---

**Viel Spaß beim Entwickeln! 🚀**
