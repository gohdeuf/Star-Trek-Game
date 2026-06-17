"""
ui/minimap.py – Galaxy Map
===========================
Tab: Vollbild-Galaxie-Karte öffnen / schließen
  Scrollrad          → Zoom rein/raus
  Linke Maustaste    → Karte schwenken
  Tab / Escape       → Schließen

Koordinaten (Ursina → Panda3D Draufsicht):
  Ursina X  →  Panda3D X  (rechts  = rechts)
  Ursina Z  →  Panda3D Y  (vorwärts = oben auf der Karte)
  Kamera schaut senkrecht nach unten: HPR(0, -90, 0)
"""

import math
from ursina import Entity, Text, camera, color, window, mouse
from panda3d.core import (
    Camera as P3DCamera,
    OrthographicLens,
    PandaNode,
    BitMask32,
    TextNode,
    LineSegs,
)
import builtins


def _get_base():
    return builtins.__dict__.get('base')

_MM_BIT = BitMask32.bit(8)


# ─── Datenbank-Helfer ────────────────────────────────────────────────────────

def _load_systems():
    try:
        from world import database as db
        conn = db.get_connection()
        try:
            rows = conn.execute(
                "SELECT system_id, name, rel_x, rel_y, rel_z FROM solar_systems"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception as e:
        print(f"[MAP] DB-Fehler: {e}")
        return []


def _load_planets(system_id):
    try:
        import json
        from world import database as db
        conn = db.get_connection()
        try:
            row = conn.execute(
                "SELECT planets_data FROM solar_systems WHERE system_id=?",
                (system_id,)
            ).fetchone()
            if row:
                return json.loads(row['planets_data'] or '[]')
        finally:
            conn.close()
    except Exception as e:
        print(f"[MAP] Planet-Ladefehler: {e}")
    return []


# ─── Controller-Entity (treibt update-Loop an) ───────────────────────────────

class _MapController(Entity):
    """
    Winzige Entity, die ausschließlich Minimap.update() pro Frame aufruft
    und Scroll-/Drag-Input verarbeitet, wenn die Karte geöffnet ist.
    """

    def __init__(self, galaxy_map):
        super().__init__()
        self._gm = galaxy_map

    def input(self, key):
        if not self._gm._active:
            return
        if key == 'scroll up':
            self._gm._apply_zoom(0.80)    # rein
        elif key == 'scroll down':
            self._gm._apply_zoom(1.25)    # raus

    def update(self):
        # Maus-Drag für Schwenken (nur wenn Karte offen)
        if self._gm._active and mouse.left:
            vx, vy = mouse.velocity[0], mouse.velocity[1]
            if abs(vx) > 0 or abs(vy) > 0:
                ar  = window.aspect_ratio or 1.778
                spd = self._gm._film_h   # skaliert mit Zoom
                self._gm._pan_x -= vx * spd * ar
                self._gm._pan_z -= vy * spd

        # Haupt-Update der Karte
        self._gm.update()


# ─── Galaxie-Karte ───────────────────────────────────────────────────────────

class Minimap:
    """
    Interaktive Vollbild-Sternenkarte.

    Aufbau:
    - Separater Panda3D-Display-Region (Vollbild, Sort 50, deckend)
    - Eigene orthographische Kamera mit _MM_BIT-Maske
    - Alle Geometrien als LineSegs (Draw-Mask-sicher)
    - Sternenlabels immer sichtbar, skalieren adaptiv mit Zoom
    - Planeten werden lazy geladen und ab PLANET_THRESHOLD angezeigt
    """

    FILM_DEFAULT =  15_000.0   # Start-Halbhöhe in Welteinheiten
    FILM_MIN     =     120.0   # maximaler Zoom-in
    FILM_MAX     = 100_000.0   # maximaler Zoom-out

    PLANET_THRESHOLD = 1_200.0  # Planeten anzeigen wenn _film_h < Wert

    STAR_R   =  70.0   # Radius des Sternkreises (Welteinheiten)
    LBL_BASE = 100.0   # Basis-Textskalierung

    DB_REFRESH = 240   # Frames zwischen DB-Neulesungen

    def __init__(self, player_ship, world_manager):
        self.player = player_ship
        self.world  = world_manager

        self._dots    = {}   # system_id → root NodePath
        self._lbls    = {}   # system_id → Label-NodePath
        self._pnodes  = {}   # system_id → [NodePath, ...] | None (= noch nicht geladen)
        self._systems = []

        self._active    = False
        self._ok        = False
        self._frame_cnt = 0

        self._film_h = self.FILM_DEFAULT
        self._pan_x  = 0.0   # Kamera-Mittelpunkt Ursina-X
        self._pan_z  = 0.0   # Kamera-Mittelpunkt Ursina-Z (= Panda3D Y)

        self._base = _get_base()
        if self._base is None:
            print("[MAP] 'base' nicht verfügbar")
            return

        # Wurzel-Knoten für alle 3D-Kartenobjekte
        self._root = self._base.render.attachNewNode(PandaNode('galaxy_root'))
        self._root.setLightOff()
        self._root.hide(BitMask32.allOn())
        self._root.showThrough(_MM_BIT)

        # Hauptkamera: _MM_BIT entfernen → sieht keine Kartenobjekte
        if self._base.camNode:
            cur = self._base.camNode.getCameraMask()
            self._base.camNode.setCameraMask(cur & ~_MM_BIT)

        self._ok = True
        self._setup_camera()
        self._make_player_marker()
        self._make_hud()
        self._reload_systems()

        self._ctrl = _MapController(self)
        print(f"[MAP] Galaxie-Karte bereit – {len(self._systems)} Systeme | Tab zum Öffnen")

    # ── Kamera ───────────────────────────────────────────────────────────────

    def _setup_camera(self):
        self._lens = OrthographicLens()
        ar = window.aspect_ratio or 1.778
        self._lens.setFilmSize(self._film_h * 2 * ar, self._film_h * 2)
        self._lens.setNearFar(-1_000_000, 1_000_000)

        cam_node = P3DCamera('galaxy_cam')
        cam_node.setLens(self._lens)
        cam_node.setCameraMask(_MM_BIT)

        self._cam = self._root.attachNewNode(cam_node)
        self._cam.setPos(0.0, 0.0, 50_000.0)
        # Senkrecht nach unten schauen; Panda3D +Y = Karten-oben = Ursina +Z
        self._cam.setHpr(0.0, -90.0, 0.0)

        self._dr = self._base.win.makeDisplayRegion(0.0, 1.0, 0.0, 1.0)
        self._dr.setCamera(self._cam)
        self._dr.setClearColorActive(True)
        self._dr.setClearDepthActive(True)
        self._dr.setClearColor((0.01, 0.02, 0.08, 1.0))
        self._dr.setSort(50)    # über der Hauptszene (Sort 0)
        self._dr.setActive(False)

    def _apply_zoom(self, factor):
        self._film_h = max(self.FILM_MIN, min(self.FILM_MAX, self._film_h * factor))
        ar = window.aspect_ratio or 1.778
        self._lens.setFilmSize(self._film_h * 2 * ar, self._film_h * 2)
        self._rescale_labels()

    # ── Spieler-Marker ───────────────────────────────────────────────────────

    def _make_player_marker(self):
        self._ply = self._root.attachNewNode('map_player')
        r = self.STAR_R * 1.3
        ls = LineSegs()
        ls.setColor(0.2, 1.0, 1.0, 1.0)    # cyan
        ls.setThickness(3.0)
        # Pfeil: Spitze in +Y (Ursina vorwärts = Karte-oben)
        ls.moveTo(0, r * 1.6, 0)
        ls.drawTo(-r * 0.7, -r * 0.7, 0)
        ls.drawTo(r * 0.7, -r * 0.7, 0)
        ls.drawTo(0, r * 1.6, 0)
        self._ply.attachNewNode(ls.create())

        tn = TextNode('you')
        tn.setText('◀ Spieler')
        tn.setTextColor(0.2, 1.0, 1.0, 1.0)
        lbl = self._ply.attachNewNode(tn)
        lbl.setScale(self.LBL_BASE)
        lbl.setPos(r * 1.8, 0, 1)
        lbl.setP(-90)   # flach liegend → von Draufsicht lesbar
        self._ply_lbl = lbl

    # ── HUD ──────────────────────────────────────────────────────────────────

    def _make_hud(self):
        self._hint = Text(
            parent=camera.ui, enabled=False,
            text='GALAXIE-KARTE  ·  Scrollrad: Zoom  ·  Linke Maustaste: Schwenken  ·  Tab: Schließen',
            position=(0.0, 0.47), origin=(0, 0),
            scale=0.44, color=color.rgba(100, 190, 255, 210),
        )
        self._info = Text(
            parent=camera.ui, enabled=False, text='',
            position=(-0.85, -0.47), scale=0.42,
            color=color.rgba(130, 200, 255, 180),
        )
        self._hud = [self._hint, self._info]

    # ── Systemliste ──────────────────────────────────────────────────────────

    def _reload_systems(self):
        self._systems = _load_systems()
        self._sync_dots()

    def _sync_dots(self):
        cur_ids = {s['system_id'] for s in self._systems if s.get('system_id')}
        for sid in list(self._dots):
            if sid not in cur_ids:
                self._dots[sid].removeNode()
                del self._dots[sid]
                self._lbls.pop(sid, None)
                self._pnodes.pop(sid, None)
        for sys in self._systems:
            sid = sys.get('system_id')
            if sid and sid not in self._dots:
                self._add_star(sys)

    # ── Stern-Geometrie ──────────────────────────────────────────────────────

    def _add_star(self, sys_data):
        sid  = sys_data['system_id']
        name = sys_data.get('name', '?')
        r    = self.STAR_R

        root = self._root.attachNewNode(f'gm_{sid}')

        # Kreis + Kreuz
        ls = LineSegs()
        ls.setColor(1.0, 0.88, 0.2, 1.0)
        ls.setThickness(2.5)
        for i in range(15):
            a  = 2 * math.pi * i / 14
            pt = (r * math.cos(a), r * math.sin(a), 0.0)
            ls.moveTo(*pt) if i == 0 else ls.drawTo(*pt)
        cr = r * 0.6
        ls.moveTo(-cr, 0, 0); ls.drawTo(cr, 0, 0)
        ls.moveTo(0, -cr, 0); ls.drawTo(0, cr, 0)
        root.attachNewNode(ls.create())

        # Name-Label (immer sichtbar)
        tn = TextNode('lbl')
        tn.setText(name)
        tn.setTextColor(1.0, 0.95, 0.4, 1.0)
        tn.setAlign(TextNode.ALeft)
        lbl = root.attachNewNode(tn)
        lbl.setScale(self.LBL_BASE)
        lbl.setPos(r * 1.5, 0, 1.0)
        lbl.setP(-90)   # flach → von oben lesbar

        self._dots[sid]   = root
        self._lbls[sid]   = lbl
        self._pnodes[sid] = None   # Planeten lazy laden

        # Sofort platzieren
        root.setPos(sys_data.get('rel_x', 0), sys_data.get('rel_z', 0), 0.0)

    # ── Planeten-Geometrie (lazy) ─────────────────────────────────────────────

    def _build_planets(self, sid):
        """Erstellt Orbit-Ringe + Planet-Punkte + Labels für ein System."""
        root = self._dots.get(sid)
        if root is None:
            return
        nodes = []
        for p in _load_planets(sid):
            orb_r = p.get('orbit_radius', 0)
            angle = math.radians(p.get('orbit_angle', 0))
            px_l  = orb_r * math.cos(angle)
            py_l  = orb_r * math.sin(angle)

            # Orbit-Ring (XY-Ebene in Panda3D = horizontale Karte-Ebene)
            ls_o = LineSegs()
            ls_o.setColor(0.25, 0.45, 0.85, 0.5)
            ls_o.setThickness(1.0)
            for i in range(49):
                a  = 2 * math.pi * i / 48
                pt = (orb_r * math.cos(a), orb_r * math.sin(a), 0.2)
                ls_o.moveTo(*pt) if i == 0 else ls_o.drawTo(*pt)
            np_o = root.attachNewNode(ls_o.create())
            np_o.hide()
            nodes.append(np_o)

            # Planet-Punkt
            dr   = max(orb_r * 0.04, 3.0)
            ls_d = LineSegs()
            ls_d.setColor(0.55, 0.8, 1.0, 1.0)
            ls_d.setThickness(2.5)
            for i in range(9):
                a  = 2 * math.pi * i / 8
                pt = (px_l + dr * math.cos(a), py_l + dr * math.sin(a), 0.6)
                ls_d.moveTo(*pt) if i == 0 else ls_d.drawTo(*pt)
            np_d = root.attachNewNode(ls_d.create())
            np_d.hide()
            nodes.append(np_d)

            # Planet-Label
            ptn = TextNode('plbl')
            ptn.setText(p.get('name', '?')[:12])
            ptn.setTextColor(0.55, 0.8, 1.0, 1.0)
            ptn.setAlign(TextNode.ALeft)
            np_l = root.attachNewNode(ptn)
            np_l.setScale(self.LBL_BASE * 0.28)
            np_l.setPos(px_l + dr * 1.8, py_l, 1.0)
            np_l.setP(-90)
            np_l.hide()
            nodes.append(np_l)

        self._pnodes[sid] = nodes

    # ── Pro-Frame-Updates ────────────────────────────────────────────────────

    def _update_player(self):
        if not self.player:
            return
        self._ply.setPos(self.player.position.x, self.player.position.z, 1.0)
        self._ply.setH(-self.player.rotation_y)

    def _update_planet_visibility(self):
        show_mode = self._film_h < self.PLANET_THRESHOLD
        for sys in self._systems:
            sid = sys.get('system_id')
            if sid not in self._dots:
                continue

            if not show_mode:
                for np in (self._pnodes.get(sid) or []):
                    np.hide()
                continue

            # Nur Systeme nah am Karten-Mittelpunkt zeigen
            wx   = sys.get('rel_x', 0)
            wz   = sys.get('rel_z', 0)
            dist = math.sqrt((wx - self._pan_x)**2 + (wz - self._pan_z)**2)
            if dist > self._film_h * 1.0:
                for np in (self._pnodes.get(sid) or []):
                    np.hide()
                continue

            # Lazy-Load der Planetengeometrie
            if self._pnodes.get(sid) is None:
                self._build_planets(sid)

            for np in (self._pnodes.get(sid) or []):
                np.show()

    def _rescale_labels(self):
        """Labels immer in lesbarer Größe halten, egal wie weit gezoomt."""
        scale = max(18.0, min(280.0, self._film_h * 0.009))
        for lbl in self._lbls.values():
            lbl.setScale(scale)
        self._ply_lbl.setScale(scale)

    # ── Toggle ───────────────────────────────────────────────────────────────

    def toggle(self):
        if not self._ok:
            return
        self._active = not self._active
        self._dr.setActive(self._active)
        for e in self._hud:
            e.enabled = self._active

        if self._active:
            self._root.showThrough(_MM_BIT)
            # Beim Öffnen auf den Spieler zentrieren
            if self.player:
                self._pan_x = self.player.position.x
                self._pan_z = self.player.position.z
            self._film_h = self.FILM_DEFAULT
            ar = window.aspect_ratio or 1.778
            self._lens.setFilmSize(self._film_h * 2 * ar, self._film_h * 2)
            self._cam.setPos(self._pan_x, self._pan_z, 50_000.0)
            self._reload_systems()
            self._rescale_labels()
        else:
            self._root.hide(BitMask32.allOn())

    # ── Haupt-Update (von _MapController aufgerufen) ─────────────────────────

    def update(self):
        if not self._ok or not self._active:
            return

        self._frame_cnt += 1
        if self._frame_cnt % self.DB_REFRESH == 0:
            self._reload_systems()

        # Kamera auf Schwenk-Position setzen
        self._cam.setPos(self._pan_x, self._pan_z, 50_000.0)

        # Spieler-Marker
        self._update_player()

        # Planeten ein/ausblenden
        self._update_planet_visibility()

        # HUD-Text
        if self.player:
            px = self.player.position.x
            pz = self.player.position.z
            zoom = self.FILM_DEFAULT / self._film_h
            self._info.text = (
                f'Spieler ({px:,.0f} | {pz:,.0f})  ·  '
                f'Karte-Zentrum ({self._pan_x:,.0f} | {self._pan_z:,.0f})  ·  '
                f'Zoom {zoom:.1f}×  ·  {len(self._systems)} Systeme'
            )