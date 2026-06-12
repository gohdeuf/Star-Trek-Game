# ============================================================================
# Entity-Basis und Exporte
# ============================================================================
from ursina import Entity, Vec3

class GameEntity(Entity):
	"""
	Basis-Klasse für alle Spiel-Entities (Schiffe, Planeten, Monde etc.).
	Bietet gemeinsame Funktionalität wie Bewegung, Update-Zyklen.
	"""
	
	def __init__(self, name: str = "Entity", **kwargs):
		super().__init__(**kwargs)
		self.name = name
		self.velocity = Vec3(0, 0, 0)
		self.is_active = True
	
	def update(self):
		"""Wird jeden Frame aufgerufen. Überschreibe in Subklassen."""
		if self.is_active:
			self.position += self.velocity
	
	def destroy_entity(self):
		"""Entferne die Entity aus der Szene."""
		self.is_active = False
		self.visible = False


# ============================================================================
# Import-Fabrik: Schiffe, Planeten etc. von hier laden
# ============================================================================

def load_ship(ship_type: str, position=(0, 0, 0), **kwargs):
	"""
	Lade ein Schiff nach Typ-Name.
	
	Beispiel:
	  ship = load_ship('enterprise', position=(0, 0, 0))
	
	Später kannst du hier Blender-Modelle (.glb/.obj) laden:
	  if use_3d_models:
	      return Entity(model='models/ships/enterprise.glb', ...)
	"""
	from entities.ships import SHIPS
	
	if ship_type not in SHIPS:
		raise ValueError(f"Schiff-Typ '{ship_type}' nicht bekannt. Verfügbar: {list(SHIPS.keys())}")
	
	ship_class = SHIPS[ship_type]
	return ship_class(position=position, **kwargs)


def load_planet(planet_type: str, position=(0, 0, 0), **kwargs):
	"""
	Lade einen Planeten nach Typ-Name.

	Unterstützte Werte für `planet_type`:
	  - 'earth', 'mars'  -> konkrete Beispiel-Planeten (Klasse M / K)
	  - Star-Trek-Klassencode: 'D', 'H', 'J', 'K', 'L', 'M', 'N', 'T', 'Y',
	    '6', '7', '9'    -> entsprechende Planet-Subklasse aus entities.planets

	kwargs (optional, für Klassencode-Varianten):
	  - name (str)       -> Anzeigename (Standard: Klassenname)
	  - resources (dict) -> {"max": ..., "current": ...}
	  - radius (float), color_val -> Aussehen überschreiben

	Beispiele:
	  earth = load_planet('earth', position=(10, 0, 0))
	  planet = load_planet('M', position=(50, 0, 0), name="Vulcan I",
	                        resources={"max": 1000, "current": 1000})
	"""
	from entities import planets

	if planet_type == 'earth':
		kwargs.pop('name', None)
		return planets.Earth(position=position, **kwargs)
	elif planet_type == 'mars':
		kwargs.pop('name', None)
		return planets.Mars(position=position, **kwargs)

	planet_class = planets.PLANET_CLASSES.get(planet_type)
	if planet_class is None:
		raise ValueError(
			f"Planet-Typ '{planet_type}' nicht bekannt. "
			f"Verfügbar: 'earth', 'mars', {list(planets.PLANET_CLASSES.keys())}"
		)

	return planet_class(position=position, **kwargs)


__all__ = ['GameEntity', 'load_ship', 'load_planet']
