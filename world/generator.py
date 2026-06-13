"""
world/generator.py
===================
Prozedurale, deterministische Generierung neuer Sektoren.

Wird aufgerufen, sobald der WorldManager einen Sektor lädt, für den noch
KEIN Eintrag in `sectors` existiert. Erzeugt dann:
- einen sectors-Eintrag
- 0..N solar_systems mit Stern-Position (rel_x/y/z), SOI-Radius und
  planets_data (Planetenliste inkl. Ressourcen)

Determinismus:
Der Zufallsgenerator wird mit einem aus der sector_id abgeleiteten Seed
initialisiert. Dadurch erzeugt derselbe Sektor bei jedem Spielstart
exakt die gleichen Inhalte (kein Speichern nötig, bis der Spieler etwas
verändert -> dann wird der veränderte Zustand in der DB persistiert und
hat Vorrang vor der Neugenerierung).
"""

import hashlib
import random

from . import database as db


# ---------------------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------------------

# Wahrscheinlichkeit, dass ein Sektor überhaupt ein Sonnensystem enthält
SYSTEM_SPAWN_CHANCE = 0.35

# Wertebereiche für generierte Systeme
# (halbiert ggü. ursprünglichem Wert, damit ein System inkl. SOI bequem
# innerhalb eines einzelnen Sektors (SECTOR_SIZE=2000) Platz hat)
SOI_MIN, SOI_MAX = 300.0, 750.0
PLANETS_MIN, PLANETS_MAX = 0, 5

# Planeten-Klassen mit Gewichtung für die Zufallsauswahl (höher = häufiger).
# Klassencodes entsprechen entities.planets.PLANET_CLASSES.
# Häufige, "normale" Klassen (D, H, K, L, M) sind häufiger als seltene
# Gasriesen-Subklassen (6, 7, 9) und exotische Klassen (N, T, Y).
PLANET_WEIGHTS = {
    "M": 18,   # erdähnlich (Minshara)
    "K": 16,   # fast lebensermöglichend
    "L": 14,   # geologisch inaktiv
    "H": 14,   # Wüstenplanet, geologisch aktiv
    "D": 16,   # Asteroid/Mond, ressourcenreich
    "J": 8,    # Gasriese (Standard)
    "N": 4,    # selten klassifiziert
    "Y": 4,    # Dämon-Klasse, extreme Bedingungen
    "T": 3,    # Gasriese (allgemein)
    "6": 1,    # Gasriese, Klasse-7-ähnlich
    "7": 1,    # Gasriese, Cyclohexan/Phosphor
    "9": 1,    # Gasriese "Q'tahL"
}

PLANET_TYPES = list(PLANET_WEIGHTS.keys())
PLANET_WEIGHT_VALUES = list(PLANET_WEIGHTS.values())

RESOURCE_RANGES = {
    "M": (500, 1500),
    "K": (800, 2000),
    "L": (300, 1000),
    "H": (1000, 2500),
    "D": (2000, 5000),  # Asteroiden/Monde: viele Rohstoffe
    "J": (0, 0),        # Gasriesen: keine festen Ressourcen
    "N": (0, 500),
    "Y": (0, 800),
    "T": (0, 0),
    "6": (0, 0),
    "7": (0, 0),
    "9": (0, 0),
}

STAR_NAME_PREFIXES = [
    "Vulcan", "Andor", "Tellar", "Rigel", "Cait", "Bolarus",
    "Risa", "Bajor", "Ferenginar", "Cardassia", "Romulus",
    "Qo'noS", "Trill", "Betazed", "Deneva", "Tau",
]

STAR_NAME_SUFFIXES = ["Prime", "Major", "Minor", "I", "II", "III", "IV", "Outpost", "Belt"]


# ---------------------------------------------------------------------------
# Seed-Ableitung
# ---------------------------------------------------------------------------

def _seed_for_sector(sector_id):
    """
    Erzeugt einen deterministischen Integer-Seed aus der sector_id,
    damit jeder Sektor bei jedem Spielstart identisch generiert wird.
    """
    digest = hashlib.sha256(sector_id.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


# ---------------------------------------------------------------------------
# Sektor-Koordinaten -> Welt-Ursprung
# ---------------------------------------------------------------------------

def _sector_world_origin(sector_id, sector_size):
    """
    Berechnet die Weltkoordinate der "unteren" Ecke (Ursprung) des durch
    sector_id beschriebenen Sektor-Würfels.

    Erwartet sector_id im Format 'Sector_Alpha_<sx>_<sy>_<sz>'.
    Bei unbekanntem Format wird (0,0,0) als Fallback verwendet.
    """
    parts = sector_id.split("_")
    try:
        sx, sy, sz = int(parts[-3]), int(parts[-2]), int(parts[-1])
    except (ValueError, IndexError):
        sx, sy, sz = 0, 0, 0
    return sx * sector_size, sy * sector_size, sz * sector_size


# ---------------------------------------------------------------------------
# Hauptfunktion: Sektor bei Bedarf generieren
# ---------------------------------------------------------------------------

def ensure_sector_generated(sector_id):
    """
    Prüft, ob `sector_id` bereits in der Datenbank existiert.
    Falls nicht: generiert deterministisch ein neues Sonnensystem
    (oder lässt den Sektor leer) und schreibt alles in die DB.

    Idempotent: Wenn der Sektor bereits existiert (egal ob durch
    vorherige Generierung oder durch den Spieler verändert), passiert
    nichts.
    """
    if db.sector_exists(sector_id):
        return False  # bereits generiert/vorhanden -> nichts tun

    rng = random.Random(_seed_for_sector(sector_id))

    # 1) Sektor-Eintrag anlegen
    sector_name = _generate_sector_name(sector_id, rng)
    db.ensure_sector(sector_id, name=sector_name)

    # 2) Entscheiden, ob ein Sonnensystem generiert wird
    if rng.random() <= SYSTEM_SPAWN_CHANCE:
        system = _generate_solar_system(sector_id, rng)
        db.save_solar_system(system)

    return True


# ---------------------------------------------------------------------------
# Generierungs-Helfer
# ---------------------------------------------------------------------------

def _generate_sector_name(sector_id, rng):
    """Erzeugt einen lesbaren Namen für den Sektor, z.B. 'Sector_Beta_2_-1_0'."""
    greek_letters = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]
    letter = rng.choice(greek_letters)
    parts = sector_id.split("_")
    coords = "_".join(parts[-3:]) if len(parts) >= 3 else sector_id
    return f"Sector_{letter}_{coords}"


def _generate_star_name(rng):
    prefix = rng.choice(STAR_NAME_PREFIXES)
    suffix = rng.choice(STAR_NAME_SUFFIXES)
    return f"{prefix} {suffix}"


ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _generate_solar_system(sector_id, rng):
    """
    Erzeugt ein vollständiges solar_systems-Dict (ohne system_id, wird beim
    Insert von SQLite vergeben) inkl. planets_data mit Ressourcen.

    WICHTIG (BUGFIX): rel_x/rel_y/rel_z sind ABSOLUTE Weltkoordinaten und
    liegen garantiert innerhalb des durch sector_id beschriebenen
    Sektor-Würfels (also world_to_sector_coords(rel_x, rel_y, rel_z) ergibt
    wieder genau sector_id). Vorher wurden hier nur lokale Offsets im
    Bereich -1000..1000 erzeugt, die überall im Code (Spawn-Positionen,
    SOI-Distanzberechnung) als absolute Weltkoordinaten interpretiert
    wurden -> dadurch landeten ALLE generierten Systeme physisch in der
    Nähe von (0,0,0), unabhängig von ihrem sector_id-Tag. Das Lazy-Loading
    (Laden/Entladen anhand von sector_id) lief dadurch komplett an der
    tatsächlichen Position der Objekte vorbei, was zu fehlerhaftem
    Chunk-Loading und verschwindenden Planeten bei Annäherung führte.
    """
    soi = rng.uniform(SOI_MIN, SOI_MAX)

    size = db.SECTOR_SIZE
    ox, oy, oz = _sector_world_origin(sector_id, size)

    # Stern-Position: absolute Weltkoordinate, gleichverteilt innerhalb
    # des Sektor-Würfels [o, o + size) entlang jeder Achse.
    rel_x = ox + rng.uniform(0, size)
    rel_y = oy + rng.uniform(0, size)
    rel_z = oz + rng.uniform(0, size)

    rot_x = rng.uniform(0, 360)
    rot_y = rng.uniform(0, 360)
    rot_z = rng.uniform(0, 360)

    system_name = _generate_star_name(rng)
    # Erstes Wort des Systemnamens als Basis für Planetennamen,
    # z.B. "Vulcan Prime" -> "Vulcan"
    system_prefix = system_name.split()[0]

    num_planets = rng.randint(PLANETS_MIN, PLANETS_MAX)
    planets_data = []
    orbit_radius = soi * 0.1  # erster Planet startet bei 10% der SOI

    for i in range(num_planets):
        planet_type = rng.choices(PLANET_TYPES, weights=PLANET_WEIGHT_VALUES, k=1)[0]
        res_min, res_max = RESOURCE_RANGES[planet_type]
        max_resources = rng.randint(res_min, res_max) if res_max > 0 else 0

        # Orbit-Position (vereinfachte Kreisbahn in der xz-Ebene)
        angle = rng.uniform(0, 360)

        # Eindeutiger Name pro System: "<SystemPräfix> <Römische Ziffer>"
        # z.B. "Vulcan I", "Vulcan II", ... -> garantiert kollisionsfrei
        numeral = ROMAN_NUMERALS[i] if i < len(ROMAN_NUMERALS) else str(i + 1)
        planet_name = f"{system_prefix} {numeral}"

        planets_data.append({
            "name": planet_name,
            "type": planet_type,
            "orbit_radius": round(orbit_radius, 2),
            "orbit_angle": round(angle, 2),
            "resources": {
                "max": max_resources,
                "current": max_resources,
            },
        })

        # nächster Planet weiter draußen
        orbit_radius += soi * rng.uniform(0.08, 0.18)

    return {
        "sector_id": sector_id,
        "name": system_name,
        "rel_x": round(rel_x, 2),
        "rel_y": round(rel_y, 2),
        "rel_z": round(rel_z, 2),
        "rot_x": round(rot_x, 2),
        "rot_y": round(rot_y, 2),
        "rot_z": round(rot_z, 2),
        "sphere_of_influence": round(soi, 2),
        "planets_data": planets_data,
    }
