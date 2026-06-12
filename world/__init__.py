"""
world package
=============
Enthält die Datenbank- und Sandbox-Welt-Logik gemäß
"Technical Specification: Hyper-Realistic Star Trek Sandbox Universe in Python".

Module:
- database.py     -> SQLite3-Schema & CRUD (sectors, solar_systems, station_sector, space_ships_sector)
- soi.py          -> Sphere-of-Influence Mathematik & Zustandsübergänge
- world_manager.py -> Lazy-Loading-Manager (3x3x3-Sektor-Tracking, Spawn/Despawn)
"""

from .world_manager import WorldManager
from .soi import FlightState, SOITracker, distance_3d
from . import database

__all__ = [
    "WorldManager",
    "FlightState",
    "SOITracker",
    "distance_3d",
    "database",
]
