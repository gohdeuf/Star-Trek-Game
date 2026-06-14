"""
ui/minimap.py
=============
HUD-Übersichtskarte (obere rechte Ecke).

- Heading-Up: Spieler-Vorwärtsrichtung zeigt immer nach oben auf der Karte
- Spieler ist immer in der Mitte (cyan Marker + Richtungsstrahl)
- Sonnensysteme = gold Punkte mit Kurzname
- Koordinaten + Heading-Anzeige am unteren Rand
- Umschalten mit TAB (minimap.toggle())
"""

import math
from ursina import Entity, Text, camera, color, destroy


class Minimap(Entity):
    # ---- Konfiguration ------------------------------------------------
    CX    = 0.63     # Kartenmitte X auf camera.ui
    CY    = 0.29     # Kartenmitte Y auf camera.ui
    SIZE  = 0.24     # Kantenlänge (screen units)
    RANGE = 4000.0   # Sichtradius in Welteinheiten (= 2 × SECTOR_SIZE)

    def __init__(self, player_ship, world_manager):
        super().__init__(parent=camera.ui)
        self.player_ship   = player_ship
        self.world_manager = world_manager
        self._dots         = {}    # system_id -> {'dot', 'label', 'system'}
        self._known_ids    = set()
        self._visible      = True
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        cx, cy, s = self.CX, self.CY, self.SIZE
        hs = s / 2

        # Rand (leicht größer -> sichtbarer Rahmen)
        self._border = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(30, 130, 220, 240),
            scale=(s + 0.008, s + 0.008),
            position=(cx, cy, 2.2),
        )
        # Hintergrund
        self._bg = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(0, 5, 20, 210),
            scale=(s, s),
            position=(cx, cy, 2.0),
        )
        # Fadenkreuz H
        self._ch = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(40, 100, 180, 80),
            scale=(s * 0.90, 0.0016),
            position=(cx, cy, 1.8),
        )
        # Fadenkreuz V
        self._cv = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(40, 100, 180, 80),
            scale=(0.0016, s * 0.90),
            position=(cx, cy, 1.8),
        )
        # Titel
        self._title = Text(
            parent=camera.ui,
            text='SEKTOR-ÜBERSICHT  [TAB]',
            position=(cx - hs + 0.005, cy + hs - 0.013),
            scale=0.50,
            color=color.rgba(80, 180, 255, 210),
        )
        # Spieler-Körper
        self._pm_body = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(0, 230, 255, 255),
            scale=(0.011, 0.016),
            position=(cx, cy, 0.5),
        )
        # Spieler-Richtungsstrahl (zeigt immer nach oben = Vorwärts)
        self._pm_ray = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(0, 230, 255, 160),
            scale=(0.0025, s * 0.065),
            position=(cx, cy + s * 0.032, 0.5),
        )
        # Koordinaten / Heading
        self._coords = Text(
            parent=camera.ui,
            text='',
            position=(cx - hs + 0.005, cy - hs + 0.010),
            scale=0.50,
            color=color.rgba(130, 200, 255, 200),
        )

        self._static = [
            self._border, self._bg, self._ch, self._cv,
            self._title, self._pm_body, self._pm_ray, self._coords,
        ]

    # ------------------------------------------------------------------ Mathe
    def _world_to_map(self, wx, wz):
        """
        Weltposition (wx, wz) -> Bildschirmkoordinaten (Heading-Up).
        Y-Rotation des Spielers wird herausgerechnet: Forward = Oben.
        """
        px, _, pz = self.player_ship.position
        dx, dz = wx - px, wz - pz
        h = math.radians(self.player_ship.rotation_y)
        rx =  dx * math.cos(h) + dz * math.sin(h)
        ry = -dx * math.sin(h) + dz * math.cos(h)
        scale = (self.SIZE / 2.0) / self.RANGE
        return self.CX + rx * scale, self.CY + ry * scale

    def _in_bounds(self, mx, my):
        hs = self.SIZE / 2.0 * 0.94
        return abs(mx - self.CX) <= hs and abs(my - self.CY) <= hs

    # ------------------------------------------------------------------ Toggle
    def toggle(self):
        self._visible = not self._visible
        for e in self._static:
            e.enabled = self._visible
        for entry in self._dots.values():
            entry['dot'].enabled   = self._visible
            entry['label'].enabled = self._visible

    # ------------------------------------------------------------------ Dots
    def _sync_dots(self, systems):
        """Erstellt fehlende und entfernt veraltete System-Dots."""
        new_ids = {s['system_id'] for s in systems if s.get('system_id') is not None}

        for sid in list(self._dots):
            if sid not in new_ids:
                destroy(self._dots[sid]['dot'])
                destroy(self._dots[sid]['label'])
                del self._dots[sid]

        for sys in systems:
            sid = sys.get('system_id')
            if sid is None or sid in self._dots:
                continue

            dot = Entity(
                parent=camera.ui, model='quad',
                color=color.rgba(255, 215, 0, 220),
                scale=0.010,
                position=(self.CX, self.CY, 0.4),
                enabled=self._visible,
            )
            label = Text(
                parent=camera.ui,
                text=sys.get('name', '?')[:14],
                position=(self.CX + 0.013, self.CY),
                scale=0.46,
                color=color.rgba(255, 240, 130, 185),
                enabled=self._visible,
            )
            self._dots[sid] = {'dot': dot, 'label': label, 'system': sys}

        self._known_ids = new_ids

    def _update_dot_positions(self, systems):
        by_id = {s['system_id']: s for s in systems if s.get('system_id')}
        for sid, entry in self._dots.items():
            sys_data = by_id.get(sid, entry['system'])
            mx, my = self._world_to_map(
                sys_data.get('rel_x', 0),
                sys_data.get('rel_z', 0),
            )
            vis = self._in_bounds(mx, my) and self._visible
            entry['dot'].position   = (mx, my, 0.4)
            entry['dot'].enabled    = vis
            entry['label'].position = (mx + 0.013, my - 0.003)
            entry['label'].enabled  = vis

    # ------------------------------------------------------------------ Loop
    def update(self):
        if not self._visible or not self.player_ship:
            return

        systems = getattr(self.world_manager, 'solar_systems', [])
        current_ids = {s['system_id'] for s in systems if s.get('system_id')}
        if current_ids != self._known_ids:
            self._sync_dots(systems)

        self._update_dot_positions(systems)

        px, py, pz = self.player_ship.position
        hdg = self.player_ship.rotation_y % 360
        self._coords.text = (
            f'X:{px:7.0f}  Y:{py:5.0f}  Z:{pz:7.0f}\n'
            f'HDG: {hdg:6.1f}\u00b0'
        )
