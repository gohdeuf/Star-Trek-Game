from ursina import *
import config
from entities import load_ship, load_planet
from entities.planets import Moon
from world import WorldManager
import os
import shutil
import random # Wichtig, da random unten im Star-Field genutzt wird

# ============ KRITISCH: Aggressive Cache-Bereinigung VOR allem anderen ============
def aggressive_cache_clear():
	"""MAXIMALE Cache-Löschung - wird ganz am Anfang aufgerufen"""
	import os
	
	cache_clear_flag = ".cache_reset_on_next_start"
	should_clear_cache = os.path.exists(cache_clear_flag)
	
	if not should_clear_cache:
		print("[INFO] Cache-Clearing deaktiviert (schneller Start)")
		print("[INFO] Drücke den Button 'Clear Cache' um beim nächsten Start zu leeren")
		return
	
	print("[STARTUP] Starte aggressive Cache-Bereinigung...")
	
	try:
		cache_dirs = [
			os.path.expanduser("~/.panda3d"),
			os.path.expanduser("~/.ursina"),
			os.path.expanduser("~/.cache/panda3d"),
			os.path.expanduser("~/.cache/ursina"),
			"/tmp/panda3d*",
		]
		
		for cache_dir in cache_dirs:
			if "*" not in cache_dir and os.path.exists(cache_dir):
				try:
					shutil.rmtree(cache_dir)
					print(f"[OK] Gelöscht: {cache_dir}")
				except Exception as e:
					print(f"[WARN] Konnte nicht löschen {cache_dir}: {e}")
		
		for root, dirs, files in os.walk(os.path.expanduser("~")):
			for file in files:
				if file.endswith(".bam"):
					try:
						os.remove(os.path.join(root, file))
					except:
						pass
		
		print("[OK] Cache-Bereinigung abgeschlossen!")
		
		try:
			os.remove(cache_clear_flag)
			print("[OK] Cache-Reset-Flag gelöscht!")
		except:
			pass
		
	except Exception as e:
		print(f"[WARN] Aggressive Cache-Löschung fehlgeschlagen: {e}")

# Rufe SOFORT auf, BEVOR ursina window initialisiert wird
aggressive_cache_clear()


# ============ Globale Variablen für die F10-Kamera ============
camera_mode = "follow" # Kann "follow" oder "free" sein
free_cam = None

def setup_scene():
	"""Initialisiere die Spielwelt: Schiffe, Planeten, Monde"""
	global camera_mode, free_cam
	
	# ============ Fenster & Rendering Setup ============
	window.size = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
	camera.background_color = config.BG_COLOR
	camera.clip_plane_far = 30000  # Große Sichtweite für das Weltall
	
	# Beleuchtung (Fest in der Szene verankert, NICHT mehr an der Kamera!)
	sun = DirectionalLight(parent=scene, shadows=True)
	sun.rotation = (45, -45, 0)
	
	# ============ Lade Schiffe ============
	# FIX: use_builtin_model auf True gesetzt, damit die primitive Enterprise gerendert wird!
	player_ship = load_ship('enterprise', position=(0, 0, 0), use_builtin_model=False)
	player_ship.ship_id = "NCC-1701-D"
	
	# ============ Lade Planeten & Monde [DEPRECATED] ============
	# DEPRECATED: Planeten werden jetzt vom WorldManager (generator.py) procedural
	# generiert und geladen. Hardcodierte Planeten hier werden entfernt.
	# earth = load_planet('earth', position=(50, 0, 0))
	# mars = load_planet('mars', position=(80, 0, 0))
	# 
	# moon_earth = Moon(
	# 	name="Luna",
	# 	parent_planet=earth,
	# 	orbit_radius=5,
	# )
	
	# ============ Star-Field (Sterne im Hintergrund) ============
	for _ in range(100):
		star_pos = Vec3(
			random.uniform(-200, 200),
			random.uniform(-100, 100),
			random.uniform(-200, 0),
		)
		Entity(
			model='sphere',
			scale=0.1,
			color=color.white,
			position=star_pos,
		)
	
	# ============ Kamera Setup (Folgen & F10 Freiflug) ============
	class CameraController(Entity):
		def update(self):
			global camera_mode
			
			if camera_mode == "follow" and player_ship:
				# Berechne die ideale Position hinter dem Heck des Schiffes basierend auf dessen forward-Vektor
				target_pos = player_ship.position - player_ship.forward * config.CAMERA_DEFAULT_DISTANCE
				target_pos += player_ship.up * config.CAMERA_DEFAULT_HEIGHT

				
				# Geschmeidiges Folgen der Position mittels lerp (ohne Klammern bei time.dt)
				camera.position = lerp(camera.position, target_pos, time.dt * 6)
				
				# Kamera blickt stabil auf das Schiff und neigt sich beim Rollen (Q/E) mit
				camera.look_at(player_ship.position)
				camera.rotation_z = player_ship.rotation_z

	camera_controller = CameraController()

	# Integrierte Input-Funktion für den F10-Wechsel innerhalb der Szene
	from ursina.prefabs.first_person_controller import EditorCamera
	
	def input(key):
		global camera_mode, free_cam
		if key == config.TOGGLE_CAMERA_KEY:
			if camera_mode == "follow":
				camera_mode = "free"
				free_cam = EditorCamera()
				free_cam.speed = config.CAMERA_FREE_SPEED
				print("[KAMERA] Freier Flugmodus AKTIVIERT (Steuerung mit rechter Maustaste + WASD)")
			else:
				camera_mode = "follow"
				if free_cam:
					destroy(free_cam)
					free_cam = None
				
				# KRITISCHER FIX: Setzt Schieflagen der Editor-Kamera beim Zurückwechseln komplett zurück
				camera.rotation = (0, 0, 0)
				camera.fov = 60
				print("[KAMERA] Verfolgungsmodus REAKTIVIERT & ZURÜCKGESETZT")

	camera_controller.input = input

	# ============ Welt-Manager (Lazy Loading + SOI-Logik) ============
	world_manager = WorldManager(player_ship=player_ship)

	# ============ UI/HUD ============
	if config.SHOW_HELP_TEXT:
		help_text = Text(
			text=(
				"=== Steuerung ===\n"
				"W/A/S/D: Bewegen | Space/Ctrl: Hoch/Runter\n"
				"Pfeiltasten: Pitch/Yaw | Q/E: Roll\n"
				"F10: Freie Kamera umschalten\n"
				"F12: Cache löschen (beim nächsten Start)\n"
				"ESC: Beenden"
			),
			position=(-0.48, 0.45),
			font='courier',
			color=color.white,
			scale=1.2,
		)
	
	return {
		'player_ship': player_ship,
		'world_manager': world_manager,
	}

def main():
	"""Haupteinstieg: Initialisiere App und starte das Spiel"""
	
	app = Ursina(
		title=config.WINDOW_TITLE,
		fullscreen=False,
	)
	
	scene = setup_scene()
	player_ship = scene['player_ship']
	
	def exit_game():
		application.quit()
	
	cache_reset_triggered = False  
	
	def on_cache_reset_key():
		"""Erstelle Flag-Datei für Cache-Reset beim nächsten Start"""
		nonlocal cache_reset_triggered
		
		if cache_reset_triggered:
			return  
		
		cache_reset_triggered = True
		import os
		try:
			with open(".cache_reset_on_next_start", "w") as f:
				f.write("Cache will be cleared on next startup\n")
			print("\n" + "="*50)
			print("[OK] ✓ Cache-Reset für nächsten Start aktiviert! (Debug)")
			print("[OK] Starte das Spiel neu, um den Cache zu löschen.")
			print("="*50 + "\n")
		except Exception as e:
			print(f"[ERROR] Konnte Flag-Datei nicht erstellen: {e}")
	
	class InputHandler(Entity):
		def update(self):
			if held_keys['f12']: 
				on_cache_reset_key()
			if held_keys['escape']:
				exit_game()
	
	input_handler = InputHandler()
	
	app.run()


if __name__ == "__main__":
	main()
