# ============================================================================
# Globale Konfiguration — Einstellungen hier anpassen
# ============================================================================
import os

# Modelle-Verzeichnis (ABSOLUTER PFAD)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_PATH: str = os.path.join(_PROJECT_ROOT, "SpielPython", "models")

# Fenster-Einstellungen
WINDOW_WIDTH: int = 1920
WINDOW_HEIGHT: int = 1080
WINDOW_TITLE: str = "Star Trek Space Battle Simulator"

# Render-Einstellungen
BG_COLOR: tuple = (0.05, 0.05, 0.1)  # Tiefes Blau
VSYNC: bool = True  # Vertical Sync für smooth gameplay

# Kamera-Standard
CAMERA_DEFAULT_DISTANCE: float = 15
CAMERA_DEFAULT_HEIGHT: float = 5

# Schiffe-Standard (Scale, Speed etc.)
SHIP_DEFAULT_SPEED: float = 15  # Einheiten/Sekunde
SHIP_DEFAULT_ROTATION_SPEED: float = 100  # Grad/Sekunde

# DEBUG-Modus (für Tests)
DEBUG: bool = True
SHOW_FPS: bool = True
SHOW_HELP_TEXT: bool = True
