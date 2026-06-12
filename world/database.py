"""
world/database.py
==================
SQLite3-Datenbankschicht für das persistente Sandbox-Universum.

Enthält:
- Tabellen-Definitionen (sectors, solar_systems, station_sector, space_ships_sector)
- Initialisierungsfunktion (CREATE TABLE IF NOT EXISTS)
- CRUD-Helper für On-Demand (Lazy Loading) Zugriffe
- JSON (de)serialisierung für planets_data / modules

Die Datenbank-Datei liegt standardmäßig unter ./universe.db relativ zum
main.py Arbeitsverzeichnis. Pfad kann über config.DB_PATH überschrieben werden.
"""

import sqlite3
import json
import os

try:
    import config
    DB_PATH = getattr(config, "DB_PATH", "universe.db")
except ImportError:
    DB_PATH = "universe.db"


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------

def get_connection():
    """Erstellt eine neue SQLite-Verbindung mit aktivierten Foreign Keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Schema-Initialisierung
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS sectors (
    sector_id TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE IF NOT EXISTS solar_systems (
    system_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id TEXT NOT NULL,
    name TEXT,
    rel_x REAL DEFAULT 0,
    rel_y REAL DEFAULT 0,
    rel_z REAL DEFAULT 0,
    rot_x REAL DEFAULT 0,
    rot_y REAL DEFAULT 0,
    rot_z REAL DEFAULT 0,
    sphere_of_influence REAL DEFAULT 1000,
    planets_data TEXT DEFAULT '[]',
    FOREIGN KEY (sector_id) REFERENCES sectors (sector_id)
);

CREATE TABLE IF NOT EXISTS station_sector (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    sector_id TEXT NOT NULL,
    name TEXT,
    x REAL DEFAULT 0,
    y REAL DEFAULT 0,
    z REAL DEFAULT 0,
    rot_x REAL DEFAULT 0,
    rot_y REAL DEFAULT 0,
    rot_z REAL DEFAULT 0,
    modules TEXT DEFAULT '{}',
    FOREIGN KEY (sector_id) REFERENCES sectors (sector_id)
);

CREATE TABLE IF NOT EXISTS space_ships_sector (
    ship_id TEXT PRIMARY KEY,
    sector_id TEXT NOT NULL,
    name TEXT,
    x REAL DEFAULT 0,
    y REAL DEFAULT 0,
    z REAL DEFAULT 0,
    warp_speed REAL DEFAULT 0,
    FOREIGN KEY (sector_id) REFERENCES sectors (sector_id)
);
"""


def init_db():
    """Erstellt alle Tabellen, falls sie noch nicht existieren."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Sector-Helper: Koordinaten -> sector_id ("Sector_Alpha_X_Y")
# Origin (0,0,0) = Zentrum des Sol-Systems (Erde)
# ---------------------------------------------------------------------------

SECTOR_SIZE = 2000.0  # Kantenlänge eines Sektor-Würfels in Welteinheiten


def world_to_sector_coords(x, y, z, sector_size=SECTOR_SIZE):
    """Wandelt Weltkoordinaten in ganzzahlige Sektor-Indizes (sx, sy, sz) um."""
    sx = int(x // sector_size)
    sy = int(y // sector_size)
    sz = int(z // sector_size)
    return sx, sy, sz


def sector_coords_to_id(sx, sy, sz):
    """Erzeugt eine sector_id im Format 'Sector_Alpha_<sx>_<sy>_<sz>'."""
    return f"Sector_Alpha_{sx}_{sy}_{sz}"


def neighbor_sector_ids(sector_id):
    """
    Gibt die sector_id selbst plus alle 26 Nachbarn (3x3x3-Würfel) zurück.
    Erwartet sector_id im Format 'Sector_Alpha_<sx>_<sy>_<sz>'.
    """
    parts = sector_id.split("_")
    try:
        sx, sy, sz = int(parts[-3]), int(parts[-2]), int(parts[-1])
    except (ValueError, IndexError):
        # Fallback: nur den Sektor selbst zurückgeben, falls Format unbekannt
        return [sector_id]

    ids = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                ids.append(sector_coords_to_id(sx + dx, sy + dy, sz + dz))
    return ids


# ---------------------------------------------------------------------------
# CRUD: sectors
# ---------------------------------------------------------------------------

def ensure_sector(sector_id, name=None):
    """Stellt sicher, dass ein Sektor-Eintrag existiert (legt ihn ggf. an)."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO sectors (sector_id, name) VALUES (?, ?)",
            (sector_id, name or sector_id),
        )
        conn.commit()
    finally:
        conn.close()


def sector_exists(sector_id):
    """Prüft, ob ein Sektor-Eintrag bereits in der DB existiert."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM sectors WHERE sector_id = ?", (sector_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD: solar_systems
# ---------------------------------------------------------------------------

def get_solar_systems_in_sectors(sector_ids):
    """Lädt alle Sonnensysteme, deren sector_id in sector_ids enthalten ist."""
    if not sector_ids:
        return []
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in sector_ids)
        rows = conn.execute(
            f"SELECT * FROM solar_systems WHERE sector_id IN ({placeholders})",
            tuple(sector_ids),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["planets_data"] = json.loads(d.get("planets_data") or "[]")
            result.append(d)
        return result
    finally:
        conn.close()


def save_solar_system(system):
    """
    Legt ein Sonnensystem an oder aktualisiert es.
    `system` ist ein dict mit den Spalten der solar_systems-Tabelle.
    planets_data wird automatisch nach JSON serialisiert, falls es eine
    Python-Liste/dict ist.
    """
    conn = get_connection()
    try:
        planets_data = system.get("planets_data", [])
        if not isinstance(planets_data, str):
            planets_data = json.dumps(planets_data)

        if system.get("system_id") is not None:
            conn.execute(
                """
                UPDATE solar_systems
                SET sector_id=?, name=?, rel_x=?, rel_y=?, rel_z=?,
                    rot_x=?, rot_y=?, rot_z=?, sphere_of_influence=?,
                    planets_data=?
                WHERE system_id=?
                """,
                (
                    system["sector_id"], system.get("name"),
                    system.get("rel_x", 0), system.get("rel_y", 0), system.get("rel_z", 0),
                    system.get("rot_x", 0), system.get("rot_y", 0), system.get("rot_z", 0),
                    system.get("sphere_of_influence", 1000),
                    planets_data, system["system_id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO solar_systems
                    (sector_id, name, rel_x, rel_y, rel_z, rot_x, rot_y, rot_z,
                     sphere_of_influence, planets_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    system["sector_id"], system.get("name"),
                    system.get("rel_x", 0), system.get("rel_y", 0), system.get("rel_z", 0),
                    system.get("rot_x", 0), system.get("rot_y", 0), system.get("rot_z", 0),
                    system.get("sphere_of_influence", 1000),
                    planets_data,
                ),
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD: station_sector
# ---------------------------------------------------------------------------

def get_stations_in_sectors(sector_ids):
    """Lädt alle Stationen aus den angegebenen Sektoren."""
    if not sector_ids:
        return []
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in sector_ids)
        rows = conn.execute(
            f"SELECT * FROM station_sector WHERE sector_id IN ({placeholders})",
            tuple(sector_ids),
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            d["modules"] = json.loads(d.get("modules") or "{}")
            result.append(d)
        return result
    finally:
        conn.close()


def save_station(station):
    """
    Legt eine Station an oder aktualisiert sie (z.B. vom Spieler gebauter Outpost).
    `modules` wird als JSON-String gespeichert.
    """
    conn = get_connection()
    try:
        modules = station.get("modules", {})
        if not isinstance(modules, str):
            modules = json.dumps(modules)

        if station.get("station_id") is not None:
            conn.execute(
                """
                UPDATE station_sector
                SET sector_id=?, name=?, x=?, y=?, z=?, rot_x=?, rot_y=?, rot_z=?, modules=?
                WHERE station_id=?
                """,
                (
                    station["sector_id"], station.get("name"),
                    station.get("x", 0), station.get("y", 0), station.get("z", 0),
                    station.get("rot_x", 0), station.get("rot_y", 0), station.get("rot_z", 0),
                    modules, station["station_id"],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO station_sector
                    (sector_id, name, x, y, z, rot_x, rot_y, rot_z, modules)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    station["sector_id"], station.get("name"),
                    station.get("x", 0), station.get("y", 0), station.get("z", 0),
                    station.get("rot_x", 0), station.get("rot_y", 0), station.get("rot_z", 0),
                    modules,
                ),
            )
        conn.commit()
    finally:
        conn.close()


def delete_station(station_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM station_sector WHERE station_id=?", (station_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CRUD: space_ships_sector
# ---------------------------------------------------------------------------

def get_ships_in_sectors(sector_ids, exclude_ship_id=None):
    """Lädt alle NPC-/anderen Schiffe in den angegebenen Sektoren."""
    if not sector_ids:
        return []
    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in sector_ids)
        query = f"SELECT * FROM space_ships_sector WHERE sector_id IN ({placeholders})"
        params = list(sector_ids)
        if exclude_ship_id is not None:
            query += " AND ship_id != ?"
            params.append(exclude_ship_id)
        rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def save_ship_position(ship_id, sector_id, name, x, y, z, warp_speed=0.0):
    """Erstellt/aktualisiert die Position eines Schiffes (Upsert)."""
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO space_ships_sector (ship_id, sector_id, name, x, y, z, warp_speed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ship_id) DO UPDATE SET
                sector_id=excluded.sector_id,
                name=excluded.name,
                x=excluded.x, y=excluded.y, z=excluded.z,
                warp_speed=excluded.warp_speed
            """,
            (ship_id, sector_id, name, x, y, z, warp_speed),
        )
        conn.commit()
    finally:
        conn.close()


def delete_ship(ship_id):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM space_ships_sector WHERE ship_id=?", (ship_id,))
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Seed-Daten: legt das Sol-System an, falls die DB leer ist
# ---------------------------------------------------------------------------

def seed_default_universe():
    """
    Legt einen minimalen Startzustand an (Sol-Sektor + Sol-System bei (0,0,0)),
    falls die Datenbank noch keine Sonnensysteme enthält.
    """
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) AS c FROM solar_systems").fetchone()["c"]
    finally:
        conn.close()

    if count > 0:
        return

    sol_sector_id = sector_coords_to_id(*world_to_sector_coords(0, 0, 0))
    ensure_sector(sol_sector_id, name="Sol Sector")

    save_solar_system({
        "sector_id": sol_sector_id,
        "name": "Sol-System",
        "rel_x": 0.0, "rel_y": 0.0, "rel_z": 0.0,
        "rot_x": 0.0, "rot_y": 0.0, "rot_z": 0.0,
        "sphere_of_influence": 1000.0,
        "planets_data": [
            {
                "name": "earth",
                "type": "earth",  # konkrete Klasse (entities.planets.Earth, Klasse M)
                "orbit_radius": 50.0,
                "orbit_angle": 0.0,
                "resources": {"max": 1000, "current": 1000},
            },
            {
                "name": "mars",
                "type": "mars",  # konkrete Klasse (entities.planets.Mars, Klasse K)
                "orbit_radius": 80.0,
                "orbit_angle": 0.0,
                "resources": {"max": 800, "current": 800},
            },
        ],
    })
