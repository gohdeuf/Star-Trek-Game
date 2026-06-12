# ============================================================================
# Planeten-Klassen (Star Trek Planetenklassifizierung)
# ============================================================================
#
# Jede Star-Trek-Planetenklasse (D, H, J, K, L, M, N, T, Y sowie die
# Gasriesen-Subklassen 6, 7, 9) ist eine eigene Klasse mit charakteristischem
# Aussehen (Radius/Farbe) und Standard-Ressourcenbereich.
#
# Alle Klassen erben von `Planet` und teilen sich:
#   - resources: dict {"max": ..., "current": ...} für Ressourcenabbau
#   - planet_class: Kurzcode (z.B. "M", "J", "6") -> für Speicherung/Anzeige
#
# `Earth` und `Mars` sind konkrete, handplatzierte Beispiele und erben von
# ClassM bzw. ClassK.
# ============================================================================

from ursina import *
from entities import GameEntity
import random


class Planet(GameEntity):
	"""Basis-Klasse für alle Planeten."""

	# Wird in Subklassen überschrieben
	planet_class = "?"
	default_radius = 2.0
	default_color = color.white
	# (min, max) für zufällig generierte Ressourcenmenge, falls keine
	# `resources` übergeben werden. (0, 0) bedeutet: keine festen Ressourcen.
	resource_range = (0, 0)

	def __init__(self, name: str = None, position=(0, 0, 0), radius: float = None,
				 color_val=None, resources: dict = None, **kwargs):
		name = name or f"{self.__class__.__name__}"
		super().__init__(name=name, position=position, **kwargs)

		self.radius = radius if radius is not None else self.default_radius
		self.rotation_speed = 10  # Grad pro Sekunde

		# Lade Modell (später Blender-Export)
		self.model = 'sphere'
		self.color = color_val if color_val is not None else self.default_color
		self.scale = self.radius

		# Ressourcen: explizit übergeben, sonst zufällig im Klassen-Bereich,
		# sonst (0,0) für Klassen ohne feste Ressourcen (z.B. Gasriesen).
		if resources is not None:
			self.resources = resources
		else:
			res_min, res_max = self.resource_range
			if res_max > 0:
				amount = random.randint(res_min, res_max)
			else:
				amount = 0
			self.resources = {"max": amount, "current": amount}

	def update(self):
		"""Rotiere den Planeten langsam."""
		super().update()
		self.rotation_y += self.rotation_speed * time.dt


# ----------------------------------------------------------------------------
# Erdähnliche / feste Planeten
# ----------------------------------------------------------------------------

class ClassD(Planet):
	"""
	Klasse D: Asteroid, Mond.
	Nickel-Eisen/Silikat, Kraterlandschaft, keine bzw. sehr dünne Atmosphäre.
	Ressourcenreich (Bergbau).
	"""
	planet_class = "D"
	default_radius = 0.8
	default_color = color.gray
	resource_range = (2000, 5000)


class ClassH(Planet):
	"""
	Klasse H: Geologisch aktiv, fast instabil; Wüstenplanet.
	Metalle/Silikat, heiß, trocken, kaum Oberflächenwasser.
	"""
	planet_class = "H"
	default_radius = 1.8
	default_color = color.orange
	resource_range = (1000, 2500)


class ClassK(Planet):
	"""
	Klasse K: Fast lebensermöglichend (Terraforming möglich).
	Silikat, wenig Oberflächenwasser, dünne Atmosphäre.
	"""
	planet_class = "K"
	default_radius = 1.5
	default_color = color.red
	resource_range = (800, 2000)


class ClassL(Planet):
	"""
	Klasse L: Geologisch inaktiv.
	Silikat und Wasser, oxidierende Atmosphäre (Sauerstoff/Argon, CO2).
	"""
	planet_class = "L"
	default_radius = 1.6
	default_color = color.violet
	resource_range = (300, 1000)


class ClassM(Planet):
	"""
	Klasse M ("Minshara"): Geologisch aktiv, Silikat und Wasser,
	viel Oberflächenwasser, Sauerstoff/Stickstoff-Atmosphäre.
	Beispiele: Erde, Talos IV.
	"""
	planet_class = "M"
	default_radius = 2.0
	default_color = color.blue
	resource_range = (500, 1500)


class ClassN(Planet):
	"""
	Klasse N: selten klassifiziert, schwer lebensfeindliche Bedingungen.
	Keine festen Ressourcen, eher geologisch/atmosphärisch von Interesse.
	"""
	planet_class = "N"
	default_radius = 1.7
	default_color = color.yellow
	resource_range = (0, 500)


class ClassY(Planet):
	"""
	Klasse Y ("Demon-Class"): Extreme Temperaturschwankungen (bis >500K),
	toxische/hochgiftige Atmosphäre mit thermionischer Strahlung.
	Beispiel: Ha'Dara.
	"""
	planet_class = "Y"
	default_radius = 1.9
	default_color = color.lime
	resource_range = (0, 800)


# ----------------------------------------------------------------------------
# Gasriesen
# ----------------------------------------------------------------------------

class GasGiant(Planet):
	"""
	Basis-Klasse für Gasriesen (Klassen 6, 7, 9, J, T).
	Generell: kein fester Boden, keine Bergbau-Ressourcen, dichte Atmosphäre.
	"""
	planet_class = "GasGiant"
	default_radius = 4.0
	default_color = color.orange
	resource_range = (0, 0)


class ClassJ(GasGiant):
	"""
	Klasse J: Gasriese mit dichter, hoch-Fluor-haltiger Atmosphäre,
	Windgeschwindigkeiten über 10.000 km/h.
	"""
	planet_class = "J"
	default_radius = 4.0
	default_color = color.orange


class ClassT(GasGiant):
	"""
	Klasse T: Gasriese mit dichter Atmosphäre (allgemeiner Typ).
	"""
	planet_class = "T"
	default_radius = 4.2
	default_color = color.brown


class Class6(GasGiant):
	"""
	Klasse 6: Gasriese, äußerlich Klasse 7 ähnlich, dichte Atmosphäre.
	"""
	planet_class = "6"
	default_radius = 3.8
	default_color = color.azure


class Class7(GasGiant):
	"""
	Klasse 7: Gasriese mit dichter Atmosphäre aus Cyclohexanschicht
	und flüssigem Phosphor.
	"""
	planet_class = "7"
	default_radius = 4.0
	default_color = color.cyan


class Class9(GasGiant):
	"""
	Klasse 9 ("Q'tahL"): Gasriese mit dichter Atmosphäre.
	"""
	planet_class = "9"
	default_radius = 4.5
	default_color = color.magenta


# ----------------------------------------------------------------------------
# Konkrete, handplatzierte Beispiele
# ----------------------------------------------------------------------------

class Earth(ClassM):
	"""Erde – konkretes Beispiel für Klasse M."""

	def __init__(self, position=(10, 0, 0), **kwargs):
		kwargs.pop("name", None)
		super().__init__(
			name="Earth",
			position=position,
			**kwargs
		)
		# SPÄTER: Lade Blender-Modell mit Textur
		# self.texture = 'models/planets/earth.png'


class Mars(ClassK):
	"""Mars – konkretes Beispiel für Klasse K."""

	def __init__(self, position=(15, 0, 5), **kwargs):
		kwargs.pop("name", None)
		super().__init__(
			name="Mars",
			position=position,
			radius=1.5,
			**kwargs
		)


# ----------------------------------------------------------------------------
# Registry: Kurzcode -> Klasse (für load_planet / generator)
# ----------------------------------------------------------------------------

PLANET_CLASSES = {
	"D": ClassD,
	"H": ClassH,
	"J": ClassJ,
	"K": ClassK,
	"L": ClassL,
	"M": ClassM,
	"N": ClassN,
	"T": ClassT,
	"Y": ClassY,
	"6": Class6,
	"7": Class7,
	"9": Class9,
}


# ----------------------------------------------------------------------------
# Monde
# ----------------------------------------------------------------------------

class Moon(GameEntity):
	"""Mond — orbitet um einen Planeten."""

	def __init__(self, name: str, parent_planet: Planet, orbit_radius: float, **kwargs):
		super().__init__(name=name, **kwargs)

		self.parent_planet = parent_planet
		self.orbit_radius = orbit_radius
		self.orbital_speed = 30  # Grad pro Sekunde
		self.angle = 0

		self.model = 'sphere'
		self.color = color.gray
		self.scale = 0.5

		# Update Position basierend auf Umlaufbahn
		self._update_orbit()

	def update(self):
		super().update()
		self.angle += self.orbital_speed * time.dt
		self._update_orbit()

	def _update_orbit(self):
		"""Positioniere den Mond im Orbit um seinen Planeten."""
		import math
		angle_rad = math.radians(self.angle)
		self.position = self.parent_planet.position + Vec3(
			math.cos(angle_rad) * self.orbit_radius,
			0,
			math.sin(angle_rad) * self.orbit_radius,
		)
