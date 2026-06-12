from ursina import *
import math
from entities import GameEntity
from config import SHIP_DEFAULT_SPEED, SHIP_DEFAULT_ROTATION_SPEED


class Enterprise(GameEntity):
	"""
	Enterprise-ähnliches Raumschiff (Klasse D).
	
	Diese Klasse wird später leicht mit einem Blender-Modell ersetzt:
	  statt self._build_ship() -> nur ein .glb/.obj laden
	
	Bewegung:
	- W/A/S/D: Vorwärts/Links/Zurück/Rechts
	- Pfeiltasten: Pitch (hoch/runter) und Yaw (links/rechts drehen)
	- Space/Ctrl: Hoch/Runter
	- Q/E: Roll
	"""
	
	def __init__(self, position=(0, 0, 0), use_builtin_model=False, **kwargs):
		super().__init__(name="Enterprise", position=position, **kwargs)
		
		# Bewegungs-Parameter
		self.speed = SHIP_DEFAULT_SPEED
		self.rotation_speed = SHIP_DEFAULT_ROTATION_SPEED
		self.velocity = Vec3(0, 0, 0)
		
		# Richtungs-Vektoren für Bewegung
		self.forward = Vec3(0, 0, -1)
		self.right = Vec3(1, 0, 0)
		self.up = Vec3(0, 1, 0)
		
		# Nutze eingebaute Geometrie oder später ein Blender-Modell
		if use_builtin_model:
			self._build_ship_builtin()
		else:
			self._load_ship_model()
	
	def _load_ship_model(self):
		"""Lade 3D-Modell aus Blender-Export (.glb mit Texturen)"""
		import os
		import time
		
		# Nutze ABSOLUTEN Pfad für maximale Zuverlässigkeit
		base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
		model_path_rel = "models/ships/enterprise.glb"
		model_path_abs = os.path.join(base_dir, model_path_rel)
		
		print(f"\n[DEBUG] ========== Modell-Lade-Debug ==========")
		print(f"[DEBUG] Basis-Verzeichnis: {base_dir}")
		print(f"[DEBUG] Relativer Pfad: {model_path_rel}")
		print(f"[DEBUG] Absoluter Pfad: {model_path_abs}")
		
		# Prüfe ob die Datei existiert
		if not os.path.exists(model_path_abs):
			print(f"[ERROR] Datei NICHT gefunden: {model_path_abs}")
			print(f"[ERROR] Aktuelles Verzeichnis: {os.getcwd()}")
			return
		
		# Zeige Datei-Infos
		file_size = os.path.getsize(model_path_abs)
		file_mtime = os.path.getmtime(model_path_abs)
		file_time = time.ctime(file_mtime)
		print(f"[OK] Modell-Datei gefunden!")
		print(f"[OK] Datei-Größe: {file_size} bytes")
		print(f"[OK] Letzte Änderung: {file_time}")
		print(f"[DEBUG] ========================================\n")
		
		# Lade mit relativem Pfad (ursina funktioniert besser damit)
		self.model = model_path_rel
		self.scale = 1.0  # Anpassen je nach Modell-Größe
		print(f"[OK] Modell erfolgreich geladen: {model_path_rel}")
	
	def _build_ship_builtin(self):
		"""Baue das Schiff aus primitiven Formen (cube, sphere, cylinder)"""
		
		# -------- Saucer Section (Untertasse/Brücke) --------
		self.saucer = Entity(
			parent=self,
			model='sphere',
			color=color.light_gray,
			scale=(2.5, 0.4, 2.5),
			position=(0, 1.5, 0),
		)
		
		# Fenster/Brücke
		bridge_light = Entity(
			parent=self.saucer,
			model='sphere',
			color=color.red,
			scale=(0.3, 0.2, 0.3),
			position=(0, 0.3, -0.8),
		)
		
		# -------- Rumpf (Main Body) --------
		self.hull = Entity(
			parent=self,
			model='cube',
			color=color.dark_gray,
			scale=(1.2, 4, 5),
			position=(0, -1, 0),
		)
		
		# -------- Nacelles (Warpflugwerk) --------
		self.nacelle_left = Entity(
			parent=self,
			model='cylinder',
			color=color.light_gray,
			scale=(0.5, 3, 1),
			position=(-2.2, -2, -0.5),
		)
		
		left_glow = Entity(
			parent=self.nacelle_left,
			model='sphere',
			color=color.cyan,
			scale=(0.7, 0.6, 0.6),
			position=(0, 0.5, 0.3),
			transparency=0.3,
		)
		
		self.nacelle_right = Entity(
			parent=self,
			model='cylinder',
			color=color.light_gray,
			scale=(0.5, 3, 1),
			position=(2.2, -2, -0.5),
		)
		
		right_glow = Entity(
			parent=self.nacelle_right,
			model='sphere',
			color=color.cyan,
			scale=(0.7, 0.6, 0.6),
			position=(0, 0.5, 0.3),
			transparency=0.3,
		)
		
		# -------- Deflector Dish --------
		self.deflector = Entity(
			parent=self,
			model='sphere',
			color=color.yellow,
			scale=(0.8, 0.4, 0.8),
			position=(0, -0.5, 3.5),
			transparency=0.4,
		)
	
	def update(self):
		"""Pro Frame: Input verarbeiten, Position aktualisieren"""
		super().update()
		dt = time.dt
		
		# -------- Input-Verarbeitung --------
		if held_keys['w']:
			self.position += self.forward * self.speed * dt
		if held_keys['s']:
			self.position -= self.forward * self.speed * dt
		if held_keys['d']:
			self.position += self.right * self.speed * dt
		if held_keys['a']:
			self.position -= self.right * self.speed * dt
		
		if held_keys['space']:
			self.position += self.up * self.speed * dt
		if held_keys['left ctrl'] or held_keys['right ctrl']:
			self.position -= self.up * self.speed * dt
		
		# Pfeiltasten für Drehung
		if held_keys['up arrow']:
			self.rotation_x -= self.rotation_speed * dt
		if held_keys['down arrow']:
			self.rotation_x += self.rotation_speed * dt
		if held_keys['left arrow']:
			self.rotation_y -= self.rotation_speed * dt
		if held_keys['right arrow']:
			self.rotation_y += self.rotation_speed * dt
		
		if held_keys['q']:
			self.rotation_z -= self.rotation_speed * dt
		if held_keys['e']:
			self.rotation_z += self.rotation_speed * dt
		
		self._update_direction_vectors()
	
	def _update_direction_vectors(self):
		"""Berechne Richtungs-Vektoren basierend auf Rotation"""
		angle_rad = math.radians(self.rotation_y)
		self.forward = Vec3(
			-math.sin(angle_rad),
			0,
			-math.cos(angle_rad)
		)
		
		self.right = Vec3(
			math.cos(angle_rad),
			0,
			-math.sin(angle_rad)
		)
