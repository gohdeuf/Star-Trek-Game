# ============================================================================
# Schiffe-Modul: Hier sind alle verfügbaren Schiffe registriert
# ============================================================================
from entities.ships.enterprise import Enterprise

# Schiffs-Typ-Register: Name -> Klasse
SHIPS = {
	'enterprise': Enterprise,
	# Später mehr Schiffe hier hinzufügen:
	# 'warbird': Warbird,
	# 'klingon': KlingonCruiser,
	# ...
}

__all__ = ['Enterprise', 'SHIPS']
