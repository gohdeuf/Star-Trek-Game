"""
world/planet_textures.py
=========================
Prozedurale Texturgenerierung für Planeten mittels fraktalem Value-Noise
(Perlin-ähnlich). Erzeugt pro Planetentyp (siehe entities.planets.PLANET_CLASSES
bzw. world/generator.py PLANET_WEIGHTS) eine farbige Equirectangular-Textur
(2:1 Seitenverhältnis), die horizontal nahtlos (seamless) ist, sodass sie
ohne sichtbare Naht auf eine Sphere gemappt werden kann.

Erdähnliche Planeten bekommen Ozeane/Kontinente/Polkappen, Gasriesen
horizontale Bänder mit Turbulenz, Wüsten-/Gesteinsplaneten entsprechende
Farbverläufe.

Texturen werden deterministisch über (planet_type, seed) erzeugt und als
PNG in assets/generated_textures/ zwischengespeichert, damit sie nicht bei
jedem Neuladen eines Sektors erneut berechnet werden müssen.
"""

import os
import random
import hashlib

import numpy as np
from PIL import Image

from ursina import Texture


# ---------------------------------------------------------------------------
# Cache-Verzeichnis
# ---------------------------------------------------------------------------

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTURE_DIR = os.path.join(_PROJECT_ROOT, "assets", "generated_textures")


# ---------------------------------------------------------------------------
# Noise-Grundlagen (fraktales Value-Noise, horizontal seamless)
# ---------------------------------------------------------------------------

def _fade(t):
    """Smoothstep-Interpolationskurve (wie beim klassischen Perlin-Noise)."""
    return t * t * t * (t * (t * 6 - 15) + 10)


def _value_noise_2d(width, height, cell_size, rng, tile_x=True):
    """
    Erzeugt ein (height, width)-Array mit Werten in [0, 1] via bilinear
    interpoliertem Value-Noise. Wenn tile_x=True, ist das Ergebnis entlang
    der x-Achse nahtlos wiederholbar (wichtig für die Kugel-Projektion).
    """
    cell_size = max(int(cell_size), 1)
    gx = int(np.ceil(width / cell_size)) + 1
    gy = int(np.ceil(height / cell_size)) + 1

    grid = rng.random((gy, gx))
    if tile_x:
        grid[:, -1] = grid[:, 0]

    xs = np.arange(width) / cell_size
    ys = np.arange(height) / cell_size

    x0 = np.clip(np.floor(xs).astype(int), 0, gx - 1)
    y0 = np.clip(np.floor(ys).astype(int), 0, gy - 1)
    x1 = np.clip(x0 + 1, 0, gx - 1)
    y1 = np.clip(y0 + 1, 0, gy - 1)

    tx = _fade(xs - np.floor(xs))[None, :]
    ty = _fade(ys - np.floor(ys))[:, None]

    g00 = grid[np.ix_(y0, x0)]
    g01 = grid[np.ix_(y0, x1)]
    g10 = grid[np.ix_(y1, x0)]
    g11 = grid[np.ix_(y1, x1)]

    top = g00 * (1 - tx) + g01 * tx
    bottom = g10 * (1 - tx) + g11 * tx
    return top * (1 - ty) + bottom * ty


def _fractal_noise(width, height, base_cell, octaves, seed, tile_x=True):
    """Summe mehrerer Value-Noise-Octaven (steigende Frequenz, fallende Amplitude)."""
    rng = np.random.default_rng(seed)
    total = np.zeros((height, width), dtype=np.float64)
    amplitude = 1.0
    max_amp = 0.0
    cell = max(int(base_cell), 2)

    for _ in range(octaves):
        total += _value_noise_2d(width, height, cell, rng, tile_x=tile_x) * amplitude
        max_amp += amplitude
        amplitude *= 0.5
        cell = max(cell // 2, 2)

    return total / max_amp


# ---------------------------------------------------------------------------
# Farbverlauf-Mapping
# ---------------------------------------------------------------------------

def _apply_colormap(values, stops):
    """
    Mappt ein (h, w)-Array mit Werten in [0, 1] über eine Liste von
    (schwelle, (r, g, b))-Stützpunkten auf ein (h, w, 3)-uint8-Array.
    """
    stops = sorted(stops, key=lambda s: s[0])
    h, w = values.shape
    rgb = np.zeros((h, w, 3), dtype=np.float64)

    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        mask = (values >= t0) & (values <= t1)
        if not np.any(mask):
            continue
        span = max(t1 - t0, 1e-6)
        local_t = np.clip((values[mask] - t0) / span, 0, 1)
        for ch in range(3):
            rgb[..., ch][mask] = c0[ch] + (c1[ch] - c0[ch]) * local_t

    rgb[values < stops[0][0]] = stops[0][1]
    rgb[values > stops[-1][0]] = stops[-1][1]

    return np.clip(rgb, 0, 255).astype(np.uint8)


def _apply_ice_caps(rgb, strength):
    """Blendet weiße Polkappen an oberem/unterem Bildrand ein (Breitengrad-basiert)."""
    if strength <= 0:
        return rgb

    h, w, _ = rgb.shape
    lat = np.abs(np.linspace(-1, 1, h))[:, None, None]  # 0 = Äquator, 1 = Pol
    cap = np.clip((lat - (1.0 - strength)) / strength, 0, 1)
    white = np.array([245.0, 248.0, 252.0])

    blended = rgb.astype(np.float64) * (1 - cap) + white * cap
    return np.clip(blended, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Farbpaletten pro Planetentyp
# ---------------------------------------------------------------------------
# "rocky" -> Noise wird direkt über Colormap auf Terrain gemappt (+ optionale
#            Polkappen)
# "gas"   -> Noise erzeugt Bänder + Turbulenz für Gasriesen

PLANET_PALETTES = {
    # --- Spezifische Sol-Planeten ---
    "earth": {
        "style": "rocky",
        "colors": [
            (0.00, (8, 28, 90)),
            (0.42, (20, 90, 165)),
            (0.47, (45, 130, 185)),
            (0.50, (195, 185, 130)),
            (0.55, (55, 125, 55)),
            (0.75, (125, 140, 70)),
            (0.90, (140, 110, 80)),
            (1.00, (255, 255, 255)),
        ],
        "ice_caps": 0.16,
    },
    "mars": {
        "style": "rocky",
        "colors": [
            (0.00, (90, 35, 20)),
            (0.35, (150, 65, 30)),
            (0.55, (190, 95, 45)),
            (0.75, (215, 140, 85)),
            (1.00, (240, 215, 195)),
        ],
        "ice_caps": 0.06,
    },

    # --- Star-Trek-Klassencodes (siehe generator.py PLANET_WEIGHTS) ---
    "M": {  # erdähnlich (Minshara)
        "style": "rocky",
        "colors": [
            (0.00, (12, 45, 100)),
            (0.42, (30, 105, 175)),
            (0.48, (205, 195, 145)),
            (0.55, (110, 145, 55)),
            (0.78, (175, 165, 75)),
            (1.00, (250, 250, 248)),
        ],
        "ice_caps": 0.14,
    },
    "K": {  # fast lebensermöglichend, trocken/felsig
        "style": "rocky",
        "colors": [
            (0.00, (95, 75, 55)),
            (0.40, (145, 115, 85)),
            (0.70, (185, 155, 115)),
            (1.00, (225, 205, 175)),
        ],
        "ice_caps": 0.0,
    },
    "L": {  # geologisch inaktiv, grau/braun
        "style": "rocky",
        "colors": [
            (0.00, (60, 55, 50)),
            (0.50, (110, 100, 90)),
            (1.00, (175, 165, 155)),
        ],
        "ice_caps": 0.0,
    },
    "H": {  # Wüstenplanet
        "style": "rocky",
        "colors": [
            (0.00, (120, 70, 20)),
            (0.40, (185, 125, 40)),
            (0.70, (225, 175, 85)),
            (1.00, (250, 220, 155)),
        ],
        "ice_caps": 0.0,
    },
    "D": {  # Asteroid/Mond, grau-kraterig
        "style": "rocky",
        "colors": [
            (0.00, (45, 45, 50)),
            (0.50, (110, 110, 115)),
            (1.00, (185, 185, 190)),
        ],
        "ice_caps": 0.0,
    },
    "N": {  # selten klassifiziert, violett/exotisch
        "style": "rocky",
        "colors": [
            (0.00, (40, 20, 60)),
            (0.50, (100, 50, 120)),
            (1.00, (185, 135, 205)),
        ],
        "ice_caps": 0.0,
    },
    "Y": {  # Dämon-Klasse, toxisch gelb-grün
        "style": "rocky",
        "colors": [
            (0.00, (50, 30, 10)),
            (0.35, (120, 90, 20)),
            (0.60, (170, 150, 30)),
            (0.85, (140, 190, 60)),
            (1.00, (230, 230, 120)),
        ],
        "ice_caps": 0.0,
    },

    # --- Gasriesen ---
    "J": {  # Standard-Gasriese (Jupiter-artig)
        "style": "gas",
        "bands": 9,
        "colors": [
            (0.00, (115, 75, 45)),
            (0.30, (180, 140, 90)),
            (0.50, (225, 205, 165)),
            (0.70, (195, 150, 100)),
            (1.00, (140, 90, 60)),
        ],
    },
    "T": {  # Gasriese, eisig (Uranus/Neptun-artig)
        "style": "gas",
        "bands": 7,
        "colors": [
            (0.00, (35, 80, 145)),
            (0.30, (70, 135, 195)),
            (0.50, (145, 205, 235)),
            (0.70, (90, 160, 210)),
            (1.00, (45, 95, 170)),
        ],
    },
    "6": {  # exotischer Gasriese, türkis
        "style": "gas",
        "bands": 8,
        "colors": [
            (0.00, (25, 90, 80)),
            (0.50, (80, 175, 150)),
            (1.00, (160, 225, 205)),
        ],
    },
    "7": {  # exotischer Gasriese, violett
        "style": "gas",
        "bands": 8,
        "colors": [
            (0.00, (55, 30, 80)),
            (0.50, (145, 70, 165)),
            (1.00, (215, 155, 225)),
        ],
    },
    "9": {  # exotischer Gasriese "Q'tahL", rot/orange
        "style": "gas",
        "bands": 10,
        "colors": [
            (0.00, (70, 20, 20)),
            (0.50, (165, 60, 40)),
            (1.00, (225, 125, 80)),
        ],
    },

    # --- Sonne (Bonus, optional in _spawn_star nutzbar) ---
    "sun": {
        "style": "gas",
        "bands": 3,
        "colors": [
            (0.00, (255, 140, 0)),
            (0.40, (255, 200, 60)),
            (0.70, (255, 240, 150)),
            (1.00, (255, 255, 230)),
        ],
    },
}

DEFAULT_PALETTE_KEY = "K"


# ---------------------------------------------------------------------------
# Hauptfunktionen
# ---------------------------------------------------------------------------

def seed_for_planet(name):
    """Erzeugt einen deterministischen Seed aus dem Planetennamen (für Caching)."""
    digest = hashlib.sha256(str(name).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _generate_planet_array(planet_type, resolution, seed):
    palette = PLANET_PALETTES.get(planet_type, PLANET_PALETTES[DEFAULT_PALETTE_KEY])

    width, height = resolution * 2, resolution  # Equirectangular 2:1

    if palette["style"] == "gas":
        base_cell = max(width // 16, 2)
        noise = _fractal_noise(width, height, base_cell, octaves=4, seed=seed, tile_x=True)

        lat = np.linspace(0, 1, height)[:, None]
        bands = (np.sin(lat * palette.get("bands", 8) * np.pi) + 1) / 2
        value = np.clip(bands * 0.55 + noise * 0.45, 0, 1)

        rgb = _apply_colormap(value, palette["colors"])
    else:
        base_cell = max(width // 20, 2)
        noise = _fractal_noise(width, height, base_cell, octaves=5, seed=seed, tile_x=True)

        rgb = _apply_colormap(noise, palette["colors"])
        rgb = _apply_ice_caps(rgb, palette.get("ice_caps", 0.0))

    return rgb


def generate_planet_texture(planet_type, resolution=128, seed=None):
    """
    Erzeugt (oder lädt aus dem Cache) eine prozedurale Equirectangular-Textur
    für den gegebenen Planetentyp und gibt ein ursina.Texture-Objekt zurück.

    planet_type: Klassencode (z.B. "M", "J", "earth", "mars", ...)
    resolution:  Höhe der Textur in Pixeln (Breite = 2x Höhe)
    seed:        Optionaler Integer-Seed für Determinismus (z.B. via
                 seed_for_planet(name)). Ohne Seed wird zufällig gewählt.
    """
    if seed is None:
        seed = random.randint(0, 2**31 - 1)

    cache_name = f"{planet_type}_{seed}_{resolution}.png"
    cache_path = os.path.join(TEXTURE_DIR, cache_name)

    if not os.path.exists(cache_path):
        os.makedirs(TEXTURE_DIR, exist_ok=True)
        rgb = _generate_planet_array(planet_type, resolution, seed)
        Image.fromarray(rgb, mode="RGB").save(cache_path)

    return Texture(cache_path)
