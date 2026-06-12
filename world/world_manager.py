"""
world/world_manager.py
=======================
Lazy-Loading-Manager ("Minecraft-Style Slicing", Spezifikation Punkt 3).

Verantwortlichkeiten:
- Trackt den aktuellen Sektor des Spielerschiffs
- Lädt nur den aktuellen Sektor + 3x3x3 Nachbarsektoren aus der DB
- Spawnt/Despawnt 3D-Entities (Stationen, fremde Schiffe) beim Sektorwechsel
- Speichert Outposts/Stationen als JSON zurück in die DB, bevor sie
  beim Verlassen des Sektors aus dem Speicher entfernt werden
- Nutzt SOITracker für den Übergang Sektor-Ansicht <-> System-Ansicht
"""

from ursina import Entity, color, destroy, Vec3
import math

from . import database as db
from . import generator
from .soi import SOITracker, FlightState, world_to_system_relative

try:
    from entities import load_planet
except ImportError:
    load_planet = None


class WorldManager(Entity):
    """
    Wird als Ursina-Entity registriert, damit `update()` jeden Frame
    automatisch aufgerufen wird.
    """

    def __init__(self, player_ship, sector_size=None, **kwargs):
        super().__init__(**kwargs)

        self.player_ship = player_ship
        self.sector_size = sector_size or db.SECTOR_SIZE

        # DB initialisieren / Seed-Daten anlegen
        db.init_db()
        db.seed_default_universe()

        # Aktuell geladene Daten
        self.current_sector_id = None
        self.loaded_sector_ids = []
        self.solar_systems = []
        self.station_entities = {}   # station_id -> Ursina Entity
        self.ship_entities = {}      # ship_id -> Ursina Entity
        self.planet_entities = {}    # (system_id, planet_name) -> Ursina Entity

        # SOI-Übergangslogik
        self.soi_tracker = SOITracker(
            on_enter_system=self._on_enter_system,
            on_exit_system=self._on_exit_system,
        )

        # Initiales Laden basierend auf Startposition
        self._refresh_sector(force=True)

    # ------------------------------------------------------------------
    # Sektor-Bestimmung
    # ------------------------------------------------------------------

    def _ship_position(self):
        p = self.player_ship.position
        return (p.x, p.y, p.z)

    def _current_sector_id_for_position(self, pos):
        sx, sy, sz = db.world_to_sector_coords(pos[0], pos[1], pos[2], self.sector_size)
        return db.sector_coords_to_id(sx, sy, sz)

    # ------------------------------------------------------------------
    # Haupt-Update (von Ursina jeden Frame aufgerufen)
    # ------------------------------------------------------------------

    def update(self):
        pos = self._ship_position()
        new_sector_id = self._current_sector_id_for_position(pos)

        if new_sector_id != self.current_sector_id:
            self._refresh_sector(new_sector_id=new_sector_id)

        # SOI-Übergänge (Sektor- vs. System-Ansicht) prüfen
        self.soi_tracker.update(pos, self.solar_systems)

    # ------------------------------------------------------------------
    # Sektor-Refresh: Lazy Loading des 3x3x3-Blocks
    # ------------------------------------------------------------------

    def _refresh_sector(self, new_sector_id=None, force=False):
        if new_sector_id is None:
            new_sector_id = self._current_sector_id_for_position(self._ship_position())

        if not force and new_sector_id == self.current_sector_id:
            return

        old_sector_ids = set(self.loaded_sector_ids)

        self.current_sector_id = new_sector_id
        db.ensure_sector(new_sector_id)
        self.loaded_sector_ids = db.neighbor_sector_ids(new_sector_id)

        # ---- Autonome Generierung neuer Sektoren ----
        # Für jeden Sektor im aktuellen 3x3x3-Block, der noch nicht in der
        # DB existiert, wird deterministisch ein neues Sonnensystem
        # (inkl. Planeten & Ressourcen) generiert und gespeichert.
        for sid in self.loaded_sector_ids:
            generated = generator.ensure_sector_generated(sid)
            if generated:
                print(f"[GEN] Neuer Sektor generiert: {sid}")

        new_sector_ids = set(self.loaded_sector_ids)

        # Sektoren, die nicht mehr im 3x3x3-Block sind -> entladen
        sectors_to_unload = old_sector_ids - new_sector_ids
        if sectors_to_unload:
            self._unload_sectors(sectors_to_unload)

        # Sonnensysteme für den neuen Block laden (für SOI-Berechnung)
        self.solar_systems = db.get_solar_systems_in_sectors(self.loaded_sector_ids)

        # Stationen & Schiffe für neue Sektoren laden
        sectors_to_load = new_sector_ids - old_sector_ids if old_sector_ids else new_sector_ids
        if sectors_to_load:
            self._load_sectors(sectors_to_load)

    # ------------------------------------------------------------------
    # Laden: Entities aus DB spawnen
    # ------------------------------------------------------------------

    def _load_sectors(self, sector_ids):
        """Spawnt 3D-Entities für Stationen, Schiffe und Planeten in den gegebenen Sektoren."""
        stations = db.get_stations_in_sectors(list(sector_ids))
        for station in stations:
            self._spawn_station(station)

        ships = db.get_ships_in_sectors(
            list(sector_ids), exclude_ship_id=getattr(self.player_ship, "ship_id", None)
        )
        for ship in ships:
            self._spawn_ship(ship)

        systems = db.get_solar_systems_in_sectors(list(sector_ids))
        for system in systems:
            self._spawn_planets(system)

    def _spawn_planets(self, system):
        """
        Spawnt für jeden Eintrag in system['planets_data'] eine Planeten-
        Entity über load_planet(). Position = Sternposition (rel_x/y/z)
        + Orbit-Offset (orbit_radius, orbit_angle) in der xz-Ebene.
        """
        if load_planet is None:
            return  # entities-Modul nicht verfügbar

        star_x = system.get("rel_x", 0)
        star_y = system.get("rel_y", 0)
        star_z = system.get("rel_z", 0)
        system_id = system.get("system_id")

        for planet in system.get("planets_data", []):
            key = (system_id, planet["name"])
            if key in self.planet_entities:
                continue  # bereits gespawnt

            orbit_radius = planet.get("orbit_radius", 0)
            orbit_angle_deg = planet.get("orbit_angle", 0)
            angle_rad = math.radians(orbit_angle_deg)

            px = star_x + orbit_radius * math.cos(angle_rad)
            py = star_y
            pz = star_z + orbit_radius * math.sin(angle_rad)

            entity = self._try_load_planet(planet, position=(px, py, pz))
            if entity is not None:
                self.planet_entities[key] = {
                    "entity": entity,
                    "data": planet,
                    "system_id": system_id,
                    "sector_id": system.get("sector_id"),
                }

    def _try_load_planet(self, planet, position):
        """
        Erzeugt die Planeten-Entity über load_planet(<Klassencode>, ...).
        `planet` ist das dict aus planets_data (siehe world/generator.py):
            { "name": ..., "type": "M"/"D"/"J"/..., "resources": {...}, ... }

        `type` ist der Star-Trek-Klassencode (siehe entities.planets.PLANET_CLASSES)
        und bestimmt Aussehen (Radius/Farbe) sowie Standard-Ressourcenbereich.
        """
        if load_planet is None:
            # entities-Modul nicht verfügbar -> einfache Sphere als Fallback
            return Entity(model='sphere', color=color.white, position=position, scale=2)

        try:
            return load_planet(
                planet.get("type", "M"),
                position=position,
                name=planet.get("name", "Unknown Planet"),
                resources=planet.get("resources"),
            )
        except Exception as e:
            print(f"[WARN] Konnte Planet '{planet.get('name')}' (Typ {planet.get('type')}) nicht laden: {e}")
            return Entity(model='sphere', color=color.white, position=position, scale=2)

    def _spawn_station(self, station):
        entity = Entity(
            model='cube',
            color=color.azure,
            position=(station["x"], station["y"], station["z"]),
            rotation=(station["rot_x"], station["rot_y"], station["rot_z"]),
            scale=2,
        )
        self.station_entities[station["station_id"]] = {
            "entity": entity,
            "data": station,
        }

    def _spawn_ship(self, ship):
        entity = Entity(
            model='cube',
            color=color.orange,
            position=(ship["x"], ship["y"], ship["z"]),
            scale=1,
        )
        self.ship_entities[ship["ship_id"]] = {
            "entity": entity,
            "data": ship,
        }

    # ------------------------------------------------------------------
    # Entladen: Entities zerstören + Outposts/Stationen zurück in DB
    # ------------------------------------------------------------------

    def _unload_sectors(self, sector_ids):
        """
        Zerstört alle 3D-Entities aus den angegebenen Sektoren und schreibt
        Stationen (Outposts) als JSON-Modul-Strings in die DB zurück,
        bevor sie aus dem RAM/GPU entfernt werden.
        """
        # Stationen
        for station_id, info in list(self.station_entities.items()):
            station_data = info["data"]
            if station_data["sector_id"] in sector_ids:
                entity = info["entity"]
                # aktuelle Transform zurückschreiben (z.B. falls Spieler gebaut hat)
                station_data["x"] = entity.x
                station_data["y"] = entity.y
                station_data["z"] = entity.z
                station_data["rot_x"] = entity.rotation_x
                station_data["rot_y"] = entity.rotation_y
                station_data["rot_z"] = entity.rotation_z
                db.save_station(station_data)

                destroy(entity)
                del self.station_entities[station_id]

        # Schiffe
        for ship_id, info in list(self.ship_entities.items()):
            ship_data = info["data"]
            if ship_data["sector_id"] in sector_ids:
                entity = info["entity"]
                db.save_ship_position(
                    ship_id=ship_data["ship_id"],
                    sector_id=ship_data["sector_id"],
                    name=ship_data.get("name"),
                    x=entity.x, y=entity.y, z=entity.z,
                    warp_speed=ship_data.get("warp_speed", 0.0),
                )
                destroy(entity)
                del self.ship_entities[ship_id]

        # Planeten
        self._unload_planets(sector_ids)

    def _unload_planets(self, sector_ids):
        """
        Zerstört Planeten-Entities der gegebenen Sektoren und schreibt den
        aktuellen Ressourcenstand (z.B. nach Abbau durch den Spieler)
        zurück in die zugehörige solar_systems-Zeile.
        """
        affected_systems = {}  # system_id -> system dict (mit aktualisierten planets_data)

        for key, info in list(self.planet_entities.items()):
            if info["sector_id"] not in sector_ids:
                continue

            system_id, planet_name = key
            entity = info["entity"]

            # Aktuellen Ressourcenstand von der Entity übernehmen (falls
            # GenericPlanet.resources während des Spiels verändert wurde)
            current_resources = getattr(entity, "resources", None)
            if current_resources is not None:
                info["data"]["resources"] = current_resources

            destroy(entity)

            if system_id not in affected_systems:
                affected_systems[system_id] = {
                    "system_id": system_id,
                    "sector_id": info["sector_id"],
                    "planets_data": [],
                }
            affected_systems[system_id]["planets_data"].append(info["data"])

            del self.planet_entities[key]

        # Persistiere geänderte Ressourcenwerte zurück in die DB
        for system_id, partial in affected_systems.items():
            full_systems = db.get_solar_systems_in_sectors([partial["sector_id"]])
            full = next((s for s in full_systems if s["system_id"] == system_id), None)
            if full is None:
                continue

            # planets_data im vollen System-Datensatz mit den aktualisierten
            # Planeten-Dicts (gleiche Objekte, ggf. von außen verändert) abgleichen
            updated_by_name = {p["name"]: p for p in partial["planets_data"]}
            for p in full["planets_data"]:
                if p["name"] in updated_by_name:
                    p["resources"] = updated_by_name[p["name"]].get("resources", p.get("resources"))

            db.save_solar_system(full)

    # ------------------------------------------------------------------
    # SOI-Übergangs-Callbacks
    # ------------------------------------------------------------------

    def _on_enter_system(self, system, distance):
        """
        Wird ausgelöst, wenn das Schiff die SOI eines Sonnensystems betritt.
        Wechselt zur lokalen Systemansicht: Koordinaten relativ zum Stern,
        Planetenorbits/Ressourcen-Extraktion werden aktiv.
        """
        print(f"[SOI] Eintritt in System '{system.get('name')}' (Distanz: {distance:.1f})")
        # Hier könnte die UI umgeschaltet werden, z.B.:
        # ui_manager.switch_to_system_view(system)
        # Lokale Koordinaten relativ zum Stern berechnen:
        local_pos = world_to_system_relative(self._ship_position(), system)
        print(f"[SOI] Lokale Koordinaten relativ zum Stern: {local_pos}")

    def _on_exit_system(self, system):
        """
        Wird ausgelöst, wenn das Schiff die SOI eines Sonnensystems verlässt
        und in den interstellaren Sektorraum zurückkehrt.
        """
        if system:
            print(f"[SOI] Austritt aus System '{system.get('name')}' -> Sektoransicht")
        # ui_manager.switch_to_sector_view()

    # ------------------------------------------------------------------
    # Öffentliche Helfer
    # ------------------------------------------------------------------

    @property
    def flight_state(self):
        return self.soi_tracker.state

    @property
    def active_system(self):
        return self.soi_tracker.current_system
