from panda3d.core import loadPrcFileData
# Schaltet V-Sync auf Engine-Ebene hart aus!
loadPrcFileData("", "sync-video #f")

from ursina import *

app = Ursina()
application.target_frame_rate = 144

cube = Entity(model="cube", color=color.red)

def update():
    cube.rotation_y += time.dt * 30  

app.run()
