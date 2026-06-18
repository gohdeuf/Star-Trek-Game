"""
ui/minimap.py – Galaxy Map (2D Overlay)
=========================================
Keine eigene Panda3D-Kamera mehr.
Alles läuft als Ursina camera.ui-Entities → garantiert sichtbar.

Tab : Karte öffnen / schließen
Scroll : Zoom
LMB-Drag : Schwenken
"""

import math
from ursina import Entity, Text, camera, color, window, mouse, destroy

# ─── DB-Helfer ───────────────────────────────────────────────────────────────

def _load_systems():
    try:
        from world import database as db
        conn = db.get_connection()
        try:
            return [dict(r) for r in conn.execute(
                "SELECT system_id, name, rel_x, rel_y, rel_z FROM solar_systems"
            ).fetchall()]
        finally:
            conn.close()
    except Exception as e:
        print(f"[MAP] {e}")
        return []


def _load_planets(sid):
    try:
        import json
        from world import database as db
        conn = db.get_connection()
        try:
            r = conn.execute(
                "SELECT planets_data FROM solar_systems WHERE system_id=?", (sid,)
            ).fetchone()
            return json.loads(r['planets_data'] or '[]') if r else []
        finally:
            conn.close()
    except:
        return []


# ─── Input / Update-Controller ───────────────────────────────────────────────

class _MapCtrl(Entity):
    def __init__(self, m):
        super().__init__()
        self._m = m

    def input(self, key):
        if not self._m._active:
            return
        if   key == 'scroll up':   self._m._fh = max(self._m.FH_MIN, self._m._fh * 0.80)
        elif key == 'scroll down': self._m._fh = min(self._m.FH_MAX, self._m._fh * 1.25)

    def update(self):
        # LMB-Drag → Karte schwenken
        if self._m._active and mouse.left:
            vx, vy = mouse.velocity[0], mouse.velocity[1]
            if vx or vy:
                ar = window.aspect_ratio or 1.778
                self._m._pan_x -= vx * self._m._fh * ar
                self._m._pan_z -= vy * self._m._fh
        self._m.update()


# ─── Galaxie-Karte ────────────────────────────────────────────────────────────

class Minimap:
    """
    Vollbild-Sternenkarte als 2D camera.ui-Overlay.

    Koordinaten:
      Ursina X  →  screen X  (rechts = rechts)
      Ursina Z  →  screen Y  (Ursina-vorwärts = Karte-oben)

    Kein Panda3D-Kamera-Aufwand, keine BitMasks, keine Display-Regions.
    """

    FH_DEF  =  3_000.0   # Start: ~3 Sektoren sichtbar
    FH_MIN  =     60.0   # maximaler Zoom-in
    FH_MAX  = 80_000.0   # maximaler Zoom-out
    PLN_THR =    800.0   # Planeten zeigen wenn _fh < dieser Wert
    DBREF   =    240     # Frames zwischen DB-Neuladen

    def __init__(self, player_ship, world_manager):
        self.player  = player_ship
        self.world   = world_manager
        self._active = False
        self._fh     = self.FH_DEF   # aktueller Zoom (Welt-Halb-Höhe)
        self._pan_x  = 0.0
        self._pan_z  = 0.0
        self._systems    = []
        self._star_ents  = {}   # sid → dot Entity
        self._lbl_ents   = {}   # sid → Text
        self._planet_ents= {}   # sid → [Entity, ...]  (lazy erstellt)
        self._frame      = 0

        # ── Hintergrund-Overlay ──────────────────────────────────────────────
        ar = window.aspect_ratio or 1.778
        self._bg = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(2, 5, 20, 252),
            scale=(ar, 1), z=0.9,
            enabled=False,
        )

        # ── Spieler-Marker ───────────────────────────────────────────────────
        self._ply = Entity(
            parent=camera.ui, model='quad',
            color=color.cyan, scale=0.018,
            z=0.0, enabled=False,
        )
        self._ply_lbl = Text(
            parent=camera.ui, text='◀ Spieler',
            color=color.rgba(50, 255, 255, 220),
            scale=0.6, z=0.0, enabled=False,
        )

        # ── HUD-Texte ────────────────────────────────────────────────────────
        self._hint = Text(
            parent=camera.ui, enabled=False,
            text='GALAXIE-KARTE  ·  Scroll: Zoom  ·  LMB: Schwenken  ·  Tab: Schließen',
            position=(0, 0.46), origin=(0, 0),
            scale=0.55, color=color.rgba(100, 190, 255, 210), z=-0.5,
        )
        self._info = Text(
            parent=camera.ui, text='', enabled=False,
            position=(-0.85, -0.46), scale=0.45,
            color=color.rgba(130, 200, 255, 180), z=-0.5,
        )
        self._hud_elems = [self._bg, self._ply, self._ply_lbl, self._hint, self._info]

        self._reload()
        self._ctrl = _MapCtrl(self)
        print(f"[MAP] Bereit – {len(self._systems)} Systeme | Tab zum Öffnen")

    # ── Koordinaten-Helfer ────────────────────────────────────────────────────

    def _to_ui(self, wx, wz):
        """Weltkoordinaten → camera.ui (x, y)."""
        s = 0.5 / self._fh   # 0.5 = halbe Bildschirmhöhe
        return (wx - self._pan_x) * s, (wz - self._pan_z) * s

    def _dot_px(self):
        """Dot-Größe in screen-units: immer ~12 px bei 1080p."""
        return 12.0 / (window.size[1] or 1080)

    # ── Systemliste ───────────────────────────────────────────────────────────

    def _reload(self):
        self._systems = _load_systems()
        self._sync()

    def _sync(self):
        cur = {s['system_id'] for s in self._systems if s.get('system_id')}

        # Veraltete Einträge entfernen
        for sid in list(self._star_ents):
            if sid not in cur:
                destroy(self._star_ents.pop(sid))
                if sid in self._lbl_ents:
                    destroy(self._lbl_ents.pop(sid))
                for e in self._planet_ents.pop(sid, []):
                    destroy(e)

        # Neue Systeme hinzufügen
        for s in self._systems:
            sid = s.get('system_id')
            if sid and sid not in self._star_ents:
                self._add_star(sid, s.get('name', '?'))

    def _add_star(self, sid, name):
        """Erstellt Dot + Label für ein Sonnensystem (versteckt bis Karte offen)."""
        dot = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(255, 220, 50, 230),
            scale=self._dot_px(),
            z=0.0, enabled=self._active,
        )
        lbl = Text(
            parent=camera.ui,
            text=name,
            color=color.rgba(255, 240, 100, 220),
            scale=0.55, z=-0.1,
            enabled=self._active,
        )
        self._star_ents[sid]  = dot
        self._lbl_ents[sid]   = lbl
        self._planet_ents[sid] = []

    # ── Planeten ──────────────────────────────────────────────────────────────

    def _build_planets(self, sid, star_wx, star_wz):
        """Lazy: Erstellt Planet-Dots für ein System."""
        for e in self._planet_ents.get(sid, []):
            destroy(e)
        ents = []
        for p in _load_planets(sid):
            orb   = p.get('orbit_radius', 0)
            angle = math.radians(p.get('orbit_angle', 0))
            pwx   = star_wx + orb * math.cos(angle)
            pwz   = star_wz + orb * math.sin(angle)
            ux, uz = self._to_ui(pwx, pwz)

            dot = Entity(
                parent=camera.ui, model='quad',
                color=color.rgba(140, 200, 255, 210),
                scale=self._dot_px() * 0.55,
                position=(ux, uz), z=-0.1,
            )
            lbl = Text(
                parent=camera.ui,
                text=p.get('name', '?')[:12],
                color=color.rgba(140, 200, 255, 180),
                scale=0.38, z=-0.2,
                x=ux + self._dot_px() * 1.4, y=uz,
            )
            ents.extend([dot, lbl])
        self._planet_ents[sid] = ents

    def _clear_all_planets(self):
        for sid in list(self._planet_ents):
            for e in self._planet_ents[sid]:
                destroy(e)
            self._planet_ents[sid] = []

    # ── Pro-Frame-Platzierung ─────────────────────────────────────────────────

    def _place_all(self):
        dp = self._dot_px()
        show_planets = self._fh < self.PLN_THR

        for s in self._systems:
            sid = s.get('system_id')
            if sid not in self._star_ents:
                continue

            wx  = s.get('rel_x', 0)
            wz  = s.get('rel_z', 0)
            ux, uz = self._to_ui(wx, wz)

            # Dot
            dot = self._star_ents[sid]
            dot.x = ux; dot.y = uz; dot.scale = dp

            # Label: leicht rechts vom Dot
            lbl = self._lbl_ents[sid]
            lbl.x = ux + dp * 1.4; lbl.y = uz

            # Planeten
            dist = math.sqrt((wx - self._pan_x)**2 + (wz - self._pan_z)**2)
            if show_planets and dist < self._fh * 1.2:
                if not self._planet_ents.get(sid):
                    self._build_planets(sid, wx, wz)
                else:
                    # Positionen aktualisieren
                    planets = _load_planets(sid)
                    ents    = self._planet_ents[sid]
                    for i, p in enumerate(planets):
                        orb   = p.get('orbit_radius', 0)
                        angle = math.radians(p.get('orbit_angle', 0))
                        pwx   = wx + orb * math.cos(angle)
                        pwz   = wz + orb * math.sin(angle)
                        eux, euz = self._to_ui(pwx, pwz)
                        j = i * 2
                        if j < len(ents):
                            ents[j].x = eux; ents[j].y = euz
                            ents[j].scale = dp * 0.55
                        if j + 1 < len(ents):
                            ents[j+1].x = eux + dp * 1.4; ents[j+1].y = euz
            else:
                for e in self._planet_ents.get(sid, []):
                    destroy(e)
                self._planet_ents[sid] = []

        # Spieler-Marker
        if self.player:
            px, pz = self.player.position.x, self.player.position.z
            ux, uz = self._to_ui(px, pz)
            self._ply.x = ux;   self._ply.y = uz
            self._ply.scale = dp * 1.5
            self._ply.rotation_z = -self.player.rotation_y
            self._ply_lbl.x = ux + dp * 2.0
            self._ply_lbl.y = uz

    # ── Toggle ────────────────────────────────────────────────────────────────

    def toggle(self):
        self._active = not self._active

        for e in self._hud_elems:
            e.enabled = self._active
        for dot in self._star_ents.values():
            dot.enabled = self._active
        for lbl in self._lbl_ents.values():
            lbl.enabled = self._active

        if self._active:
            if self.player:
                self._pan_x = self.player.position.x
                self._pan_z = self.player.position.z
            self._fh = self.FH_DEF
            self._reload()
        else:
            self._clear_all_planets()

    # ── Update (von _MapCtrl aufgerufen) ──────────────────────────────────────

    def update(self):
        if not self._active:
            return

        self._frame += 1
        if self._frame % self.DBREF == 0:
            self._reload()

        self._place_all()

        if self.player:
            px = self.player.position.x
            pz = self.player.position.z
            self._info.text = (
                f'Spieler ({px:,.0f} | {pz:,.0f})  ·  '
                f'Zoom {self.FH_DEF / self._fh:.1f}×  ·  '
                f'{len(self._systems)} Systeme'
            )
