# SpielPython — A 3D space game with Ursina

A modular project structure for a 3D game using **ursina** (Python 3D engine).

## 📁 Projekt-Struktur

```
SpielPython/
├── main.py                 # Main file — only does app initialization & scene coordination
├── config.py              # Global settings (adjust them here)
├── enterprise_d.py        # Test file (old version, can be deleted)
│
├── entities/              # 🎮 Game entities (ships, planets, moons)
│   ├── __init__.py        # Base class + factory functions (load_ship, load_planet)
│   ├── planets.py         # Planet, Earth, Mars, Moon classes
│   ├── ships/
│   │   ├── __init__.py    # Ship Register (SHIPS dict)
│   │   └── enterprise.py  # Enterprise class
│   └── ...                # Later additions: enemy.py, asteroid.py, etc.
│
├── models/                # 🎨 3D models (Blender export)
│   ├── ships/
│   │   ├── enterprise.glb      # ← Later: Blender export
│   │   └── enterprise.obj      # ← Optional: OBJ-Format
│   ├── planets/
│   │   ├── earth.glb
│   │   └── mars.glb
│   └── ...
├── world/
|   ├── generator.py        # Generates the plants/sectors.
|   ├── soi.py              # This is used to calculate the area of ​​influence of objects, for example, the sun.
|   ├── database.py         # Database for sectors, suns, planets, etc.
|   ├── world_manager.py    # Reads the database from database.py and creates planets and suns as entities.
|   ├── __init__.py         # Contains the database and sandbox world logic
│
└── README.md              # This file
```

## ⚡ Quick Start

```bash
cd /home/username/Projekt/SpielPython
python3 main.py
```

You should see:
- An Enterprise-class D (built from primitives)
- The Sun and other planets

### Steuerung
- **W/A/S/D** — Move ship (forward/left/backward/right)
- **Space/Ctrl** — Up/Down
- **Arrow keys** — Pitch (up/down) and Yaw (rotate)
- **Q/E** — Roll (sideways rotation)
- **ESC** — Quit
- **F12** — Clear cache on next startup (Development Only)

## 🛠️ How can the project be expanded?

### 1️⃣ By adding new ships

1. Create `entities/ships/warbird.py`:

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

2. Register it in `entities/ships/__init__.py`:

```python
from entities.ships.warbird import Warbird

SHIPS = {
    'enterprise': Enterprise,
    'warbird': Warbird,  # ← New!
}
```

3. Use it in `main.py`:

```python
enemy = load_ship('warbird', position=(30, 0, 0))
```

## 🎨 Blender model integration

It will be very easy later on! Here's how it works:

### Blender → Export (.glb)

1. Create/open model in Blender (e.g. Enterprise)
2. **File → Export As → glTF Binary (.glb)**
3. Save in `models/ships/enterprise.glb`

### Adjust the code

In `entities/ships/enterprise.py`, Change:

```python
def __init__(self, position=(0, 0, 0), use_builtin_model=True, **kwargs):
    # ...
    if use_builtin_model:
        self._build_ship_builtin()  # Ancient geometry -- possibly an inaccurate translation
    else:
        self._load_ship_model()     # load Blender model
```

Und implementiere `_load_ship_model()`:

```python
def _load_ship_model(self):
    """Lade 3D-Modell aus Blender-Export"""
    from config import MODELS_PATH
    model_path = f"{MODELS_PATH}/ships/enterprise.glb"
    self.model = model_path
    self.scale = 1.0  # Adjust if necessary
```

Then use it in `main.py`:

```python
player_ship = load_ship('enterprise', position=(0, 0, 0), use_builtin_model=False)
```

## 📝 Important files explained briefly

| Datei | Zweck |
|-------|-------|
| `main.py` | App initialization, scene setup, only 80 lines of pure code |
| `config.py` | Window, camera, speed, debug flags |
| `entities/__init__.py` | `GameEntity`-Basic + Factory functions |
| `entities/ships/enterprise.py` | Enterprise ship with input handling |
| `entities/planets.py` | Rotating planets and moons |

## 🎯 Next steps (example plan)

1. ✅ Create a modular structure (done!)
2. ☐ Recreate and export Enterprise in Blender
3. ☐ Add a few new ships/enemies
4. ☐ Implement a firing system (lasers)
5. ☐ Collision detection
6. ☐ HUD/UI (radar, health)
7. ☐ Mission/level system

## 📚 Ursina resources

- **Ursina Docs:** https://github.com/pmp-library/pmp-library
- **Panda3D (Foundation):** https://www.panda3d.org/

## ❓ possible errors/questions

- `Font Arial not found?` — ursina uses `courier`, `arial`, etc. If necessary, see `config.py`
- `Model not loading?` — Check the path in `MODELS_PATH` and the file extension
- `Import error?` — Make sure all `__init__.py` files are present in `entities/`
