"""
ui/minimap.py
=============
3D-Minimap – Heading-Up, orthografische Panda3D-Kamera

Änderungen gegenüber der 2D-Version:
  • Echte Panda3D-Kamera (orthografisch, leicht geneigt) im eigenen
    Display-Region – kein Offscreen-Buffer nötig
  • Sonnensysteme = goldene 3D-Kugeln + Billboard-Labels
  • Spieler-Marker = cyane Kugel + Richtungszeiger (Pfeil entlang Y)
  • Entfernungsringe als räumliche Referenz
  • Y-Höhe der Systeme wird jetzt ebenfalls dargestellt
  • Spielwelt bleibt für Minimap-Kamera unsichtbar (Kamera-Masken)
  • Toggle mit TAB → minimap.toggle()

Koordinatensystem-Konvention:
  Ursina  : x=rechts, y=oben,  z=hinten   (linkshändig)
  Panda3D : x=rechts, y=vorne, z=oben     (rechtshändig)
  Umrechnung: _u2p(x, y, z) = (x, -z, y)
"""

import math
from ursina import Entity, Text, camera, color, window
from panda3d.core import (
    Camera as P3DCamera,
    OrthographicLens,
    BitMask32,
    TextNode,
    LineSegs,
)


# ── Kamera-Masken ──────────────────────────────────────────────────────────
_MM_BIT  = BitMask32.bit(8)   # Minimap-Kamera rendert dieses Bit
_DEF_BIT = BitMask32.bit(0)   # Standard-Kamera (Panda3D-Default)


def _u2p(x, y, z):
    """Ursina (x, y, z) → Panda3D (x, -z, y)."""
    return x, -z, y


class Minimap:
    """
    3D-Minimap mit separater orthografischer Panda3D-Kamera
    und eigenem Display-Region (oben rechts).
    """

    # ── Konfiguration ──────────────────────────────────────────────────────
    RANGE     = 4_000.0  # Sichtradius in Welteinheiten (= 2 × SECTOR_SIZE)
    TILT_DEG  = 20       # Kamera-Neigung: 0 = reine Draufsicht, 20 = leicht iso
    SYS_SCALE = 100      # Kugel-Radius Sonnensystem-Marker
    PLY_SCALE = 70       # Kugel-Radius Spieler-Marker

    # Display-Region (normiert 0 = links/unten … 1 = rechts/oben)
    DR_L, DR_R = 0.74, 0.99
    DR_B, DR_T = 0.74, 0.99

    # ── Initialisierung ────────────────────────────────────────────────────
    def __init__(self, player_ship, world_manager):
        self.player   = player_ship
        self.world    = world_manager
        self._dots    = {}     # system_id → NodePath (Kugel + Label)
        self._known   = set()
        self._visible = True

        self._make_camera()
        self._make_reference_rings()
        self._make_player_marker()
        self._make_hud()

        # Gesamte Spielwelt vor Minimap-Kamera (Bit 8) verstecken.
        # Individuelle Marker rufen danach .show(_MM_BIT) auf, um sich
        # dem Minimap-Renderer bekannt zu machen.
        base.render.hide(_MM_BIT)

    # ── Panda3D-Kamera + Display-Region ────────────────────────────────────
    def _make_camera(self):
        half = self.RANGE

        lens = OrthographicLens()
        lens.setFilmSize(half * 2.1, half * 2.1)
        lens.setNearFar(-half * 5, half * 5)

        node = P3DCamera('mm_cam')
        node.setLens(lens)
        node.setCameraMask(_MM_BIT)   # sieht nur Objekte mit Bit 8

        self._cam = base.render.attachNewNode(node)

        dr = base.win.makeDisplayRegion(
            self.DR_L, self.DR_R,
            self.DR_B, self.DR_T,
        )
        dr.setCamera(self._cam)
        dr.setClearColorActive(True)
        dr.setClearDepthActive(True)
        dr.setClearColor((0.01, 0.03, 0.12, 0.95))   # dunkler Weltraum-Hintergrund
        dr.setSort(20)   # über Haupt-DR zeichnen
        self._dr = dr

    # ── Entfernungsringe ───────────────────────────────────────────────────
    def _make_reference_rings(self):
        """Zwei Kreise (50 % / 100 % RANGE) als Entfernungsreferenz."""
        self._ring_root = base.render.attachNewNode('mm_rings')
        self._ring_root.show(_MM_BIT)

        segs = 80
        for frac, alpha in ((0.5, 0.35), (1.0, 0.55)):
            r  = self.RANGE * frac
            ls = LineSegs()
            ls.setColor(0.2, 0.45, 0.9, alpha)
            ls.setThickness(1.2)
            for i in range(segs + 1):
                a  = 2 * math.pi * i / segs
                pt = (r * math.cos(a), r * math.sin(a), 0)
                ls.moveTo(*pt) if i == 0 else ls.drawTo(*pt)
            self._ring_root.attachNewNode(ls.create())

        # Kreuzlinien (N/S- und O/W-Achse)
        r   = self.RANGE
        ls2 = LineSegs()
        ls2.setColor(0.15, 0.3, 0.65, 0.30)
        ls2.moveTo(-r, 0, 0); ls2.drawTo(r,  0, 0)
        ls2.moveTo(0, -r, 0); ls2.drawTo(0,  r, 0)
        self._ring_root.attachNewNode(ls2.create())

    # ── Spieler-Marker ─────────────────────────────────────────────────────
    def _make_player_marker(self):
        self._ply_np = base.render.attachNewNode('mm_player')
        self._ply_np.show(_MM_BIT)

        # Körper-Kugel (cyan)
        body = loader.loadModel('models/misc/sphere')
        body.setScale(self.PLY_SCALE)
        body.setColor(0.0, 0.85, 1.0, 1.0)
        body.reparentTo(self._ply_np)

        # Richtungspfeil (elongierte Kugel entlang +Y = Vorwärts in Panda3D)
        tip = loader.loadModel('models/misc/sphere')
        tip.setScale(self.PLY_SCALE * 0.28,
                     self.PLY_SCALE * 2.2,
                     self.PLY_SCALE * 0.28)
        tip.setPos(0, self.PLY_SCALE * 1.3, 0)
        tip.setColor(0.0, 1.0, 1.0, 1.0)
        tip.reparentTo(self._ply_np)

    # ── 2D-HUD-Overlay (Rahmen + Text) ────────────────────────────────────
    def _make_hud(self):
        ar = window.aspect_ratio or 1.778
        sx  = ((self.DR_L + self.DR_R) / 2 - 0.5) * ar
        sy  =  (self.DR_B + self.DR_T) / 2 - 0.5
        hx  = ((self.DR_R - self.DR_L) / 2) * ar
        hy  =  (self.DR_T - self.DR_B) / 2

        self._frame = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(20, 90, 200, 150),
            scale=(hx * 2 + 0.012, hy * 2 + 0.012),
            position=(sx, sy, 2.5),
        )
        self._title = Text(
            parent=camera.ui,
            text='MINIMAP 3D  [TAB]',
            position=(sx - hx + 0.005, sy + hy - 0.013),
            scale=0.48,
            color=color.rgba(80, 180, 255, 220),
        )
        self._coords = Text(
            parent=camera.ui,
            text='',
            position=(sx - hx + 0.005, sy - hy + 0.010),
            scale=0.44,
            color=color.rgba(130, 200, 255, 200),
        )
        self._hud_elems = [self._frame, self._title, self._coords]

    # ── Sonnensystem-Marker ────────────────────────────────────────────────
    def _sync_dots(self, systems):
        """Erstellt fehlende und entfernt veraltete System-Marker."""
        new_ids = {s['system_id'] for s in systems
                   if s.get('system_id') is not None}

        for sid in list(self._dots):
            if sid not in new_ids:
                self._dots[sid].removeNode()
                del self._dots[sid]

        for sys in systems:
            sid = sys.get('system_id')
            if sid is None or sid in self._dots:
                continue

            root = base.render.attachNewNode(f'mm_sys_{sid}')
            root.show(_MM_BIT)

            # Gold-Kugel
            sphere = loader.loadModel('models/misc/sphere')
            sphere.setScale(self.SYS_SCALE)
            sphere.setColor(1.0, 0.84, 0.0, 1.0)
            sphere.reparentTo(root)

            # Billboard-Label (dreht sich stets zur Minimap-Kamera)
            tn = TextNode(f'mm_lbl_{sid}')
            tn.setText(sys.get('name', '?')[:14])
            tn.setTextColor(1.0, 0.95, 0.5, 0.90)
            tn.setAlign(TextNode.ALeft)
            tn_np = root.attachNewNode(tn)
            tn_np.setScale(65)
            tn_np.setPos(self.SYS_SCALE * 1.2, 0, 0)
            tn_np.setBillboardPointEye()

            self._dots[sid] = root

        self._known = new_ids

    def _place_dots(self, systems):
        """Aktualisiert die 3D-Positionen aller System-Marker."""
        px, py, pz = (self.player.position.x,
                      self.player.position.y,
                      self.player.position.z)
        ppx, ppy, ppz = _u2p(px, py, pz)
        by_id = {s['system_id']: s for s in systems if s.get('system_id')}

        for sid, root in self._dots.items():
            s = by_id.get(sid)
            if not s:
                continue
            dx = s.get('rel_x', 0) - px
            dy = s.get('rel_y', 0) - py   # Höhe (war in 2D-Version ignoriert)
            dz = s.get('rel_z', 0) - pz
            rx, ry, rz = _u2p(dx, dy, dz)
            root.setPos(ppx + rx, ppy + ry, ppz + rz)

    # ── Toggle ─────────────────────────────────────────────────────────────
    def toggle(self):
        self._visible = not self._visible
        self._dr.setActive(self._visible)
        for e in self._hud_elems:
            e.enabled = self._visible

        fn = 'unstash' if self._visible else 'stash'
        for np in (self._ply_np, self._ring_root, *self._dots.values()):
            getattr(np, fn)()

    # ── Update (jeden Frame) ───────────────────────────────────────────────
    def update(self):
        if not self._visible or not self.player:
            return

        px  = self.player.position.x
        py  = self.player.position.y
        pz  = self.player.position.z
        hdg = self.player.rotation_y        # Ursina: Rotation um Y-Achse

        # Spieler-Position in Panda3D-Koordinaten
        ppx, ppy, ppz = _u2p(px, py, pz)

        # ── Kamera: Heading-Up + Neigung ──────────────────────────────────
        # Die Kamera sitzt über + leicht hinter dem Spieler, dreht sich mit
        # dessen Heading, sodass Vorwärts stets oben auf der Karte ist.
        #
        # HPR in Panda3D: H dreht um Z (Hochachse), P = Nicken nach unten
        # Tipp: Falls die Karte spiegelverkehrt dreht, ersetze -hdg durch hdg.
        tilt     = math.radians(self.TILT_DEG)
        dist     = self.RANGE * 1.6
        h_rad    = math.radians(-hdg)        # Vorzeichen: Ursina ↔ Panda3D

        # Kamera um TILT_DEG nach "hinten" versetzen, damit Spieler zentriert bleibt
        back_x = math.sin(h_rad) * dist * math.sin(tilt)
        back_y = -math.cos(h_rad) * dist * math.sin(tilt)

        self._cam.setPos(
            ppx + back_x,
            ppy + back_y,
            ppz + dist * math.cos(tilt),
        )
        self._cam.setHpr(-hdg, -(90 - self.TILT_DEG), 0)

        # ── Spieler-Marker ────────────────────────────────────────────────
        self._ply_np.setPos(ppx, ppy, ppz)
        self._ply_np.setHpr(-hdg, 0, 0)     # Pfeil zeigt Vorwärtsrichtung

        # ── Referenzringe mitfahren (immer um Spieler zentriert) ──────────
        self._ring_root.setPos(ppx, ppy, ppz)

        # ── Sonnensystem-Marker ───────────────────────────────────────────
        systems = getattr(self.world, 'solar_systems', [])
        cur_ids = {s['system_id'] for s in systems if s.get('system_id')}
        if cur_ids != self._known:
            self._sync_dots(systems)
        self._place_dots(systems)

        # ── Koordinaten-HUD ───────────────────────────────────────────────
        self._coords.text = (
            f'X:{px:7.0f}  Y:{py:5.0f}  Z:{pz:7.0f}\n'
            f'HDG: {hdg % 360:6.1f}°'
        )
