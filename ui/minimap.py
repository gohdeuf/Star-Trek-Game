"""
ui/minimap.py  –  v8 (Final Camera Fix)
==============================================
Kernfix: Wir modifizieren die BitMaske der Hauptkamera sicher, indem wir
das _MM_BIT mit einer binären UND-Verknüpfung (AND NOT) abziehen.
So wird das geschützte `overall_bit` nicht berührt (AssertionError behoben).
hide() erhält wieder korrekte Bitmasken (TypeError behoben).
"""

import math
from ursina import Entity, Text, camera, color, window
from panda3d.core import (
    Camera as P3DCamera,
    OrthographicLens,
    NodePath,
    PandaNode,
    BitMask32,
    TextNode,
    LineSegs,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    GeomTriangles,
    Geom,
    GeomNode,
)
import builtins


def _get_base():
    return builtins.__dict__.get('base')

# Wir definieren unser dediziertes Minimap-Bit
_MM_BIT = BitMask32.bit(8)


def _u2p(x, y, z):
    return x, -z, y


def _make_sphere(radius, r, g, b):
    stacks, slices = 12, 18
    fmt   = GeomVertexFormat.getV3()
    vdata = GeomVertexData('sp', fmt, Geom.UHStatic)
    vdata.setNumRows((stacks + 1) * (slices + 1))
    vw = GeomVertexWriter(vdata, 'vertex')

    for i in range(stacks + 1):
        phi = math.pi * i / stacks
        sp, cp = math.sin(phi), math.cos(phi)
        for j in range(slices + 1):
            theta = 2 * math.pi * j / slices
            vw.addData3(
                sp * math.cos(theta) * radius,
                sp * math.sin(theta) * radius,
                cp * radius,
            )

    tris = GeomTriangles(Geom.UHStatic)
    c = slices + 1
    for i in range(stacks):
        for j in range(slices):
            p0 = i * c + j
            tris.addVertices(p0,     p0 + c,     p0 + 1)
            tris.addVertices(p0 + 1, p0 + c,     p0 + c + 1)

    geom = Geom(vdata)
    geom.addPrimitive(tris)
    gn = GeomNode('sp')
    gn.addGeom(geom)
    np = NodePath(gn)
    np.setColor(r, g, b, 1.0)
    return np


def _fetch_all_systems():
    try:
        from world import database as db
        conn = db.get_connection()
        try:
            rows = conn.execute(
                "SELECT system_id, name, rel_x, rel_y, rel_z "
                "FROM solar_systems"
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    except Exception as e:
        print(f"[MINIMAP] DB-Fehler: {e}")
        return []


class Minimap:
    RANGE     = 8_000.0
    TILT_DEG  = 20
    SYS_SCALE = 100
    PLY_SCALE = 70

    DR_L, DR_R = 0.74, 0.99
    DR_B, DR_T = 0.74, 0.99

    DB_REFRESH_INTERVAL = 120

    def __init__(self, player_ship, world_manager):
        self.player       = player_ship
        self.world        = world_manager
        self._dots        = {}
        self._all_systems = []
        self._visible     = True
        self._ok          = False
        self._frame_cnt   = 0

        self._base = _get_base()
        if self._base is None:
            print("[MINIMAP] 'base' nicht verfügbar")
            return

        # mm_root unter base.render erstellen
        self._mm_root = self._base.render.attachNewNode(PandaNode('mm_root'))
        self._mm_root.setLightOff()

        # 1. Wir verstecken den Node standardmäßig für alle Kameras
        self._mm_root.hide(BitMask32.allOn())
        
        # 2. Wir machen ihn EXKLUSIV für Kameras mit dem _MM_BIT sichtbar
        self._mm_root.showThrough(_MM_BIT)

        # 3. SICHERER FIX: Der Hauptkamera das _MM_BIT abziehen.
        #    Das schützt das interne 'overall_bit' und verhindert den AssertionError!
        if self._base.camNode:
            current_mask = self._base.camNode.getCameraMask()
            safe_mask = current_mask & ~_MM_BIT
            self._base.camNode.setCameraMask(safe_mask)

        self._ok = True
        self._make_camera()
        self._make_reference_rings()
        self._make_player_marker()
        self._make_hud()
        self._refresh_systems()
        print(f"[MINIMAP] OK – {len(self._all_systems)} Systeme geladen")

    # ── Kamera ─────────────────────────────────────────────────────────────
    def _make_camera(self):
        half = self.RANGE
        lens = OrthographicLens()
        lens.setFilmSize(half * 2.1, half * 2.1)
        lens.setNearFar(-half * 5, half * 5)

        cam_node = P3DCamera('mm_cam')
        cam_node.setLens(lens)
        
        # Minimap-Kamera bekommt das exklusive Bit zugewiesen
        cam_node.setCameraMask(_MM_BIT)
        
        self._cam = self._mm_root.attachNewNode(cam_node)
        tilt = math.radians(self.TILT_DEG)
        dist = self.RANGE * 1.6
        self._cam.setPos(0.0, -dist * math.sin(tilt), dist * math.cos(tilt))
        self._cam.setHpr(0.0, -(90.0 - self.TILT_DEG), 0.0)
        
        dr = self._base.win.makeDisplayRegion(
            self.DR_L, self.DR_R,
            self.DR_B, self.DR_T,
        )
        dr.setCamera(self._cam)
        dr.setClearColorActive(True)
        dr.setClearDepthActive(True)
        dr.setClearColor((0.01, 0.03, 0.15, 1.0))
        dr.setSort(20)
        self._dr = dr

    # ── Ringe ──────────────────────────────────────────────────────────────
    def _make_reference_rings(self):
        self._ring_root = self._mm_root.attachNewNode('mm_rings')
        segs = 80
        for frac, alpha in ((0.5, 0.55), (1.0, 0.85)):
            r  = self.RANGE * frac
            ls = LineSegs()
            ls.setColor(0.2, 0.5, 1.0, alpha)
            ls.setThickness(1.5)
            for i in range(segs + 1):
                a  = 2 * math.pi * i / segs
                pt = (r * math.cos(a), r * math.sin(a), 0.0)
                ls.moveTo(*pt) if i == 0 else ls.drawTo(*pt)
            self._ring_root.attachNewNode(ls.create())
        r   = self.RANGE
        ls2 = LineSegs()
        ls2.setColor(0.2, 0.35, 0.7, 0.4)
        ls2.moveTo(-r, 0, 0); ls2.drawTo(r, 0, 0)
        ls2.moveTo(0, -r, 0); ls2.drawTo(0, r, 0)
        self._ring_root.attachNewNode(ls2.create())

    # ── Spieler-Marker ─────────────────────────────────────────────────────
    def _make_player_marker(self):
        self._ply_root = self._mm_root.attachNewNode('mm_player')
        body = _make_sphere(self.PLY_SCALE, 0.0, 0.9, 1.0)
        body.reparentTo(self._ply_root)
        tip = _make_sphere(1.0, 0.0, 1.0, 0.7)
        tip.setScale(self.PLY_SCALE * 0.3,
                     self.PLY_SCALE * 2.5,
                     self.PLY_SCALE * 0.3)
        tip.setPos(0, self.PLY_SCALE * 1.5, 0)
        tip.reparentTo(self._ply_root)

    # ── HUD ────────────────────────────────────────────────────────────────
    def _make_hud(self):
        ar  = window.aspect_ratio or 1.778
        sx  = ((self.DR_L + self.DR_R) / 2 - 0.5) * ar
        sy  =  (self.DR_B + self.DR_T) / 2 - 0.5
        hx  = ((self.DR_R - self.DR_L) / 2) * ar
        hy  =  (self.DR_T - self.DR_B) / 2

        self._frame = Entity(
            parent=camera.ui, model='quad',
            color=color.rgba(20, 90, 200, 100),
            scale=(hx * 2 + 0.012, hy * 2 + 0.012),
            position=(sx, sy, 2.5),
        )
        self._title = Text(
            parent=camera.ui,
            text='MINIMAP  [TAB]',
            position=(sx - hx + 0.005, sy + hy - 0.013),
            scale=0.48,
            color=color.rgba(80, 180, 255, 220),
        )
        self._coords = Text(
            parent=camera.ui, text='',
            position=(sx - hx + 0.005, sy - hy + 0.010),
            scale=0.44,
            color=color.rgba(130, 200, 255, 200),
        )
        self._hud_elems = [self._frame, self._title, self._coords]

    # ── DB ─────────────────────────────────────────────────────────────────
    def _refresh_systems(self):
        self._all_systems = _fetch_all_systems()
        self._sync_dots(self._all_systems)

    # ── Dots ───────────────────────────────────────────────────────────────
    def _sync_dots(self, systems):
        new_ids = {s['system_id'] for s in systems if s.get('system_id') is not None}

        for sid in list(self._dots):
            if sid not in new_ids:
                self._dots[sid].removeNode()
                del self._dots[sid]

        for sys in systems:
            sid = sys.get('system_id')
            if sid is None or sid in self._dots:
                continue

            root = self._mm_root.attachNewNode(f'mm_sys_{sid}')



            tn = TextNode(f'lbl_{sid}')
            tn.setText(sys.get('name', '?')[:14])
            tn.setTextColor(1.0, 0.95, 0.5, 1.0)
            tn.setAlign(TextNode.ALeft)
            lbl = root.attachNewNode(tn)
            lbl.setScale(60)
            lbl.setPos(self.SYS_SCALE * 1.2, 0, 0)
            lbl.setBillboardPointEye(self._cam, 0.0, False)   # ← explizite MM-Kamera!

            self._dots[sid] = root

    def _place_dots(self):
        px = self.player.position.x
        py = self.player.position.y
        pz = self.player.position.z

        for sys in self._all_systems:
            sid = sys.get('system_id')
            if sid not in self._dots:
                continue
            dx = sys.get('rel_x', 0) - px
            dy = sys.get('rel_y', 0) - py
            dz = sys.get('rel_z', 0) - pz
            rx, ry, rz = _u2p(dx, dy, dz)
            self._dots[sid].setPos(rx, ry, rz)

    # ── Toggle ─────────────────────────────────────────────────────────────
    def toggle(self):
        if not self._ok:
            return
        self._visible = not self._visible
        self._dr.setActive(self._visible)
        for e in self._hud_elems:
            e.enabled = self._visible
        if self._visible:
            self._mm_root.showThrough(_MM_BIT)
        else:
            self._mm_root.hide(BitMask32.allOn())

    # ── Update ─────────────────────────────────────────────────────────────
    def update(self):
        if not self._ok or not self._visible or not self.player:
            return

        self._frame_cnt += 1
        if self._frame_cnt % self.DB_REFRESH_INTERVAL == 0:
            self._refresh_systems()

        px  = self.player.position.x
        py  = self.player.position.y
        pz  = self.player.position.z
        hdg = self.player.rotation_y

        self._ply_root.setPos(0, 0, 0)
        self._ply_root.setHpr(-hdg, 0, 0)
        self._ring_root.setPos(0, 0, 0)



        self._place_dots()

        self._coords.text = (
            f'X:{px:7.0f}  Y:{py:5.0f}  Z:{pz:7.0f}\n'
            f'HDG: {hdg % 360:6.1f}°'
        )