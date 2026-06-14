"""
ui/free_cam.py
==============
Ersatz für Ursinas EditorCamera.

EditorCamera rotiert um ihren Ursprung (0,0,0). Ist die Kamera beim
Aktivieren weit vom Ursprung entfernt, entsteht ein riesiger Orbit-Radius:
jede Mausbewegung schickt die Kamera in einem kilometerlangen Bogen –
daher das "MACH 2000"-Phänomen.

FreeCam dreht sich stattdessen direkt um den eigenen Standpunkt (FPS-Stil):
- Rechte Maustaste halten + Mausbewegung = Kamera drehen
- WASD / Space / Ctrl = Fliegen
- Shift = 10× Geschwindigkeit
- Scrollrad = Grundgeschwindigkeit anpassen
"""

from ursina import Entity, camera, mouse, held_keys, scene, time, Vec3, clamp


class FreeCam(Entity):
    def __init__(self, speed=50):
        super().__init__()
        self.speed = speed

        # Aktuelle Kamera-Weltposition / -Rotation sichern
        self._prev_pos = Vec3(camera.world_position)
        self._prev_rot = Vec3(camera.world_rotation)

        # Kamera an diese Entity heften und lokale Transform zurücksetzen,
        # damit sich die Kamera genau an der Stelle befindet, an der sie
        # vorher war – kein Sprung, kein Orbit-Offset.
        self.world_position = self._prev_pos
        self.world_rotation = self._prev_rot
        camera.parent   = self
        camera.position = Vec3(0, 0, 0)
        camera.rotation = Vec3(0, 0, 0)

        mouse.locked = False   # Maus bleibt sichtbar; Drehen nur bei RMB

    # ------------------------------------------------------------------
    def input(self, key):
        """Scrollrad = Grundgeschwindigkeit anpassen."""
        if key == 'scroll up':
            self.speed = min(self.speed * 1.25, 10000)
        elif key == 'scroll down':
            self.speed = max(self.speed * 0.80, 1)

    # ------------------------------------------------------------------
    def update(self):
        # ---- Drehen (nur bei gehaltener rechter Maustaste) ----
        if mouse.right:
            self.rotation_y += mouse.velocity[0] * 80
            self.rotation_x  = clamp(
                self.rotation_x - mouse.velocity[1] * 80,
                -89, 89,
            )

        # ---- Scrollrad wird über input() abgefangen (siehe unten) ----

        # ---- Bewegung ----
        boost = 10 if held_keys['shift'] else 1
        spd   = self.speed * boost

        move = Vec3(
            held_keys['d']       - held_keys['a'],
            held_keys['space']   - held_keys['control'],
            held_keys['w']       - held_keys['s'],
        )
        if move.length() > 0:
            move = move.normalized()

        self.position += (
            self.forward * move.z
            + self.right * move.x
            + Vec3(0, move.y, 0)
        ) * spd * time.dt

    # ------------------------------------------------------------------
    def on_destroy(self):
        """Kamera beim Zerstören wieder in den Scene-Graph zurücksetzen."""
        mouse.locked  = False
        camera.parent = scene
