"""
world/soi.py
============
Sphere-of-Influence (SOI) Mathematik gemäß Spezifikation Punkt 4.

- 3D-euklidische Distanzberechnung Schiff <-> Stern
- Zustandsübergang zwischen "Interstellar State" (Sektorraum,
  station_sector/space_ships_sector) und "System State" (lokales
  Sonnensystem, relative Koordinaten zum Stern, Planetenorbits aktiv)
"""

import math
from enum import Enum


class FlightState(Enum):
    INTERSTELLAR = "interstellar"  # außerhalb jeder SOI -> Sektor-Ansicht
    SYSTEM = "system"               # innerhalb einer SOI -> System-Ansicht


def distance_3d(pos1, pos2):
    """
    Berechnet die 3D-euklidische Distanz zwischen zwei Punkten.

    pos1, pos2: Tupel/Listen/Vec3 mit (x, y, z)
    """
    x1, y1, z1 = pos1[0], pos1[1], pos1[2]
    x2, y2, z2 = pos2[0], pos2[1], pos2[2]
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def find_active_system(ship_pos, solar_systems):
    """
    Prüft für eine Schiffsposition (Sektorkoordinaten), ob sie sich innerhalb
    der sphere_of_influence eines der übergebenen Sonnensysteme befindet.

    solar_systems: Liste von dicts mit Keys
        rel_x, rel_y, rel_z (Sternposition relativ zum Sektor)
        sphere_of_influence

    Returns:
        (system_dict, distance) wenn innerhalb einer SOI, sonst (None, None)
        Bei mehreren überlappenden SOIs wird das nächstgelegene System gewählt.
    """
    best_system = None
    best_distance = None

    for system in solar_systems:
        star_pos = (system.get("rel_x", 0), system.get("rel_y", 0), system.get("rel_z", 0))
        dist = distance_3d(ship_pos, star_pos)
        soi_radius = system.get("sphere_of_influence", 1000)

        if dist <= soi_radius:
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_system = system

    return best_system, best_distance


def world_to_system_relative(ship_pos, system):
    """
    Wandelt eine Schiffsposition (Sektorkoordinaten) in Koordinaten relativ
    zum Stern des Sonnensystems um (für den lokalen System-Modus).
    """
    star_pos = (system.get("rel_x", 0), system.get("rel_y", 0), system.get("rel_z", 0))
    return (
        ship_pos[0] - star_pos[0],
        ship_pos[1] - star_pos[1],
        ship_pos[2] - star_pos[2],
    )


def system_relative_to_world(local_pos, system):
    """Kehrfunktion zu world_to_system_relative."""
    star_pos = (system.get("rel_x", 0), system.get("rel_y", 0), system.get("rel_z", 0))
    return (
        local_pos[0] + star_pos[0],
        local_pos[1] + star_pos[1],
        local_pos[2] + star_pos[2],
    )


class SOITracker:
    """
    Hält den aktuellen Flugzustand (Sektor- oder Systemansicht) und löst
    bei Übergängen Callbacks aus.

    Nutzung im Spiel-Loop:
        tracker = SOITracker(on_enter_system=cb1, on_exit_system=cb2)
        tracker.update(ship.position, solar_systems_in_range)
    """

    def __init__(self, on_enter_system=None, on_exit_system=None):
        self.state = FlightState.INTERSTELLAR
        self.current_system = None
        self.on_enter_system = on_enter_system
        self.on_exit_system = on_exit_system

    def update(self, ship_pos, solar_systems):
        """
        Aktualisiert den Zustand basierend auf der aktuellen Schiffsposition
        und den im aktuellen 3x3x3-Sektorblock geladenen Sonnensystemen.
        """
        system, dist = find_active_system(ship_pos, solar_systems)

        if system is not None and self.state == FlightState.INTERSTELLAR:
            # Interstellar -> System
            self.state = FlightState.SYSTEM
            self.current_system = system
            if self.on_enter_system:
                self.on_enter_system(system, dist)

        elif system is None and self.state == FlightState.SYSTEM:
            # System -> Interstellar
            old_system = self.current_system
            self.state = FlightState.INTERSTELLAR
            self.current_system = None
            if self.on_exit_system:
                self.on_exit_system(old_system)

        elif system is not None and self.state == FlightState.SYSTEM:
            # Wechsel zwischen zwei überlappenden Systemen
            if system is not self.current_system and system.get("system_id") != (
                self.current_system.get("system_id") if self.current_system else None
            ):
                old_system = self.current_system
                self.current_system = system
                if self.on_exit_system:
                    self.on_exit_system(old_system)
                if self.on_enter_system:
                    self.on_enter_system(system, dist)

        return self.state, self.current_system, dist
