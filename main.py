from ursina import *
import config
from entities import load_ship, load_planet
from entities.planets import Moon
from world import WorldManager
import os
import shutil
import random # Wichtig, da random unten im Star-Field genutzt wird
from world.environment import create_skybox
from ui.minimap import Minimap
from ui.free_cam import FreeCam

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
player_ship = None
camera_controller = None
world_manager = None

def setup_scene():
	"""Initialisiere die Spielwelt: Schiffe, Planeten, Monde"""
	global camera_mode, free_cam, player_ship, world_manager
	from world.database import get_ship_by_id  # Importiere deine DB-Funktion
	db_daten = get_ship_by_id("NCC-1701-D")
	if db_daten:
        	# Hier holen wir die echten Koordinaten aus der DB
		start_pos = (db_daten['x'], db_daten['y'], db_daten['z'])
		print(f"[LOAD] Schiff aus DB geladen bei: {start_pos}")
	else:
       	# Fallback, falls die DB leer ist
		start_pos = (0, 0, 0)

		
	# ============ Fenster & Rendering Setup ============
	window.size = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
	camera.background_color = config.BG_COLOR
	camera.clip_plane_far = 30000  # Große Sichtweite für das Weltall
	
	# Beleuchtung (Fest in der Szene verankert, NICHT mehr an der Kamera!)
	sun = DirectionalLight(parent=scene, shadows=True)
	sun.rotation = (45, -45, 0)
	
	# ============ Lade Schiffe ============
	# FIX: use_builtin_model auf True gesetzt, damit die primitive Enterprise gerendert wird!
	player_ship = load_ship('enterprise', position=start_pos, use_builtin_model=False)
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
	#for _ in range(100):
	#	star_pos = Vec3(
	#		random.uniform(-200, 200),
	#		random.uniform(-100, 100),
	#		random.uniform(-200, 0),
	#	)
	#	Entity(
	#		model='sphere',
	#		scale=0.1,
	#		color=color.white,
	#		position=star_pos,
	#	)
	
	# ============ Kamera Setup (Folgen & F10 Freiflug) ============
	class CameraController(Entity):
		def update(self):
			global camera_mode
        
        	# 1. SICHERHEITSBREMSE: Wenn Freecam aktiv ist, tu absolut nichts!
			if camera_mode == "free":
				return
            
			if camera_mode == "follow" and player_ship:
            	# Berechne die ideale Position hinter dem Heck des Schiffes
				target_pos = player_ship.position - player_ship.forward * config.CAMERA_DEFAULT_DISTANCE
				target_pos += player_ship.up * config.CAMERA_DEFAULT_HEIGHT
            
            # Geschmeidiges Folgen
			camera.position = lerp(camera.position, target_pos, time.dt * 6)
            
            # Kamera blickt stabil auf das Schiff
			camera.look_at(player_ship.position)
			camera.rotation_z = player_ship.rotation_z

	global camera_controller
	camera_controller = CameraController()

	# ============ Welt-Manager (Lazy Loading + SOI-Logik) ============
	global world_manager
	world_manager = WorldManager(player_ship=player_ship)

	# ============ UI/HUD ============
	if config.SHOW_HELP_TEXT:
		help_text = Text(
			parent=camera.ui,
			text=(
				"=== Steuerung ===\n"
				"W/A/S/D: Bewegen | Space/Ctrl: Hoch/Runter\n"
				"Pfeiltasten: Pitch/Yaw | Q/E: Roll\n"
				"F10: Freie Kamera umschalten\n"
				"F12: Cache löschen (beim nächsten Start)\n"
				"ESC: Beenden"
			),
			position=(-0.48, 0.45),
			color=color.white,
			scale=1.2,
		)

# Import EditorCamera hier (außerhalb von setup_scene)
from ursina.prefabs.first_person_controller import EditorCamera

# Oben in main.py, EditorCamera-Import ERSETZEN durch:
from ui.free_cam import FreeCam

# input()-Funktion – EditorCamera-Zeilen ersetzen:
def input(key):
    global camera_mode, free_cam, camera_controller
    if key == config.TOGGLE_CAMERA_KEY:
        if camera_mode == "follow":
            camera_mode = "free"
            if camera_controller:
                camera_controller.disable()
            free_cam = FreeCam(speed=config.CAMERA_FREE_SPEED)
            print("[KAMERA] Freier Flugmodus AKTIVIERT (RMB halten + WASD)")
        else:
            camera_mode = "follow"
            if free_cam:
                destroy(free_cam)
                free_cam = None
            if camera_controller:
                camera_controller.enable()
            camera.fov = 60
            print("[KAMERA] Verfolgungsmodus REAKTIVIERT")


def main():
	"""Haupteinstieg: Initialisiere App und starte das Spiel"""
	global player_ship, world_manager, minimap
	
	app = Ursina(
		title=config.WINDOW_TITLE,
		fullscreen=True,
	)
	
	setup_scene()
	minimap = Minimap(player_ship=player_ship, world_manager=world_manager)
	create_skybox(player_ship)
	
	def exit_game():
		if world_manager:
			world_manager._save_player_position()
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

		def input(self, key):
			if key == 'tab':
				minimap.toggle()
	
	input_handler = InputHandler()
	
	app.run()


if __name__ == "__main__":
	main()
