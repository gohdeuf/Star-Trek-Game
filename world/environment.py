# world/environment.py
from ursina import *

def create_skybox(target_ship):
    textur_pfad = application.asset_folder / 'models/planets' / 'Himmel8K.png'
    
    skybox = Entity(
        model='sphere',
        texture=str(textur_pfad),
        scale=2000, # Ruhig schön groß machen
        double_sided=True,
        unlit=True
    )
    
    # Diese Logik läuft jetzt automatisch in jedem Frame des Spiels
    def update_skybox():
        # Die Skybox folgt exakt der Position des Raumschiffs
        skybox.position = target_ship.world_position
        
    # Wir übergeben die Logik an die update-Funktion der Skybox-Entity
    skybox.update = update_skybox
    
    return skybox
