from ursina import *
import config
from entities import load_ship, load_planet
from entities.planets import Moon
from world import WorldManager
import os
import shutil

# ============ KRITISCH: Aggressive Cache-Bereinigung VOR allem anderen ============
def aggressive_cache_clear():
	"""MAXIMALE Cache-Löschung - wird ganz am Anfang aufgerufen"""
	import os
	
	# Prüfe ob eine Flag-Datei existiert, die Cache-Löschung erzwingt
	cache_clear_flag = ".cache_reset_on_next_start"
	
	should_clear_cache = os.path.exists(cache_clear_flag)
	
	if not should_clear_cache:
		print("[INFO] Cache-Clearing deaktiviert (schneller Start)")
		print("[INFO] Drücke den Button 'Clear Cache' um beim nächsten Start zu leeren")
		return
	
	print("[STARTUP] Starte aggressive Cache-Bereinigung...")
	
	try:
		# Lösche ALLE möglichen Cache-Verzeichnisse
		cache_dirs = [
			os.path.expanduser("~/.panda3d"),
			os.path.expanduser("~/.ursina"),
			os.path.expanduser("~/.cache/panda3d"),
			os.path.expanduser("~/.cache/ursina"),
			"/tmp/panda3d*",  # Temp-Dateien
		]
		
		for cache_dir in cache_dirs:
			if "*" not in cache_dir and os.path.exists(cache_dir):
				try:
					shutil.rmtree(cache_dir)
					print(f"[OK] Gelöscht: {cache_dir}")
				except Exception as e:
					print(f"[WARN] Konnte nicht löschen {cache_dir}: {e}")
		
		# Versuche auch BAM-Dateien (Panda3D binäre Cache-Dateien) zu löschen
		for root, dirs, files in os.walk(os.path.expanduser("~")):
			for file in files:
				if file.endswith(".bam"):
					try:
						os.remove(os.path.join(root, file))
					except:
						pass
		
		print("[OK] Cache-Bereinigung abgeschlossen!")
		
		# Lösche die Flag-Datei, damit nicht jedesmal gelöscht wird
		try:
			os.remove(cache_clear_flag)
			print("[OK] Cache-Reset-Flag gelöscht!")
		except:
			pass
		
	except Exception as e:
		print(f"[WARN] Aggressive Cache-Löschung fehlgeschlagen: {e}")

# Rufe SOFORT auf, BEVOR ursina window initialisiert wird
aggressive_cache_clear()


def setup_scene():
	"""Initialisiere die Spielwelt: Schiffe, Planeten, Monde"""
	
	# ============ Fenster & Rendering Setup ============
	window.size = (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
	camera.background_color = config.BG_COLOR
	
	# Beleuchtung
	sun = DirectionalLight(parent=camera, shadows=True)
	sun.rotation = (45, 45, 0)
	
	# ============ Lade Schiffe ============
	# Beispiel: Lade Enterprise mit load_ship()
	player_ship = load_ship('enterprise', position=(0, 0, 0), use_builtin_model=False)
	player_ship.ship_id = "NCC-1701-D"  # Eindeutige ID für die space_ships_sector Tabelle
	
	# Später mehr Schiffe:
	# enemy_ship = load_ship('warbird', position=(20, 0, 10))
	
	# ============ Lade Planeten & Monde ============
	earth = load_planet('earth', position=(50, 0, 0))
	mars = load_planet('mars', position=(80, 0, 0))
	
	# Mond um Erde
	moon_earth = Moon(
		name="Luna",
		parent_planet=earth,
		orbit_radius=5,
	)
	
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
	
	# ============ Kamera Setup (folgt dem Schiff) ============
	# Kamera-Offset vom Schiff (hinter und über dem Schiff)
	CAMERA_OFFSET = Vec3(0, 8, 15)
	
	# Erstelle eine kleine "Helfer-Entity" nur zum Updaten der Kamera
	class CameraController(Entity):
		def update(self):
			# Folge dem Schiff mit Offset
			camera.position = player_ship.position + CAMERA_OFFSET
			camera.look_at(player_ship.position)
	
	camera_controller = CameraController()

	# ============ Welt-Manager (Lazy Loading + SOI-Logik) ============
	# Lädt nur den aktuellen Sektor + 3x3x3 Nachbarsektoren aus der SQLite-DB,
	# spawnt/despawnt Stationen & Schiffe und schaltet zwischen
	# Sektor-Ansicht und lokaler System-Ansicht (siehe world/world_manager.py)
	world_manager = WorldManager(player_ship=player_ship)

	# ============ UI/HUD ============
	if config.SHOW_HELP_TEXT:
		help_text = Text(
			text=(
				"=== Steuerung ===\n"
				"W/A/S/D: Bewegen | Space/Ctrl: Hoch/Runter\n"
				"Pfeiltasten: Pitch/Yaw | Q/E: Roll\n"
				"Strg+AltGr+Entf: Cache löschen (nächster Start)\n"
				"ESC: Beenden"
			),
			position=(-0.48, 0.45),
			font='courier',
			color=color.white,
			scale=1.2,
		)
	
	# ============ Rückgabe der wichtigen Entities ============
	return {
		'player_ship': player_ship,
		'earth': earth,
		'mars': mars,
		'moon': moon_earth,
		'world_manager': world_manager,
	}


def main():
	"""Haupteinstieg: Initialisiere App und starte das Spiel"""
	
	# Ursina App erstellen
	app = Ursina(
		title=config.WINDOW_TITLE,
		fullscreen=False,
	)
	
	# Szene aufbauen
	scene = setup_scene()
	player_ship = scene['player_ship']
	
	# ESC zum Beenden
	def exit_game():
		application.quit()
	
	# ============ Cache-Reset Tastenkombination: Strg+AltGr+Entf ============
	cache_reset_triggered = False  # Flag um mehrfaches Auslösen zu verhindern
	
	def on_cache_reset_key():
		"""Erstelle Flag-Datei für Cache-Reset beim nächsten Start (F12)"""
		nonlocal cache_reset_triggered
		
		if cache_reset_triggered:
			return  # Verhindere mehrfaches Auslösen
		
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
	
	# Input-Handler registrieren
	class InputHandler(Entity):
		def update(self):
			# *** CHANGED TRIGGER TO F12 ***
			if held_keys['f12']: 
				on_cache_reset_key()
	
	input_handler = InputHandler()
	
	# In dieser Hauptdatei sind jetzt nur:
	# - App-Initialisierung
	# - Szenen-Setup (Laden von Entities)
	# - Globale Update-Loops
	#
	# Alle Spiel-Logik, Klassen, Bewegungen sind in:
	#   - entities/ships/enterprise.py (Schiff-Bewegung)
	#   - entities/planets.py (Planeten-Rotation)
	#
	# Das macht es leicht, später Blender-Modelle zu integrieren!
	# Einfach in den entsprechenden Klassen _load_ship_model() implementieren.
	#
	# ============================================
	
	# Hauptschleife starten
	app.run()


if __name__ == "__main__":
	main()

