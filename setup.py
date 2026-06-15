from setuptools import setup

setup(
    name="Bindoj",
    options={
        "build_apps": {
            "platforms": ["win_amd64"],
            
            # Hier wird der Name der ausführbaren Datei festgelegt (erzeugt Bindoj.exe)
            "gui_apps": {
                "Bindoj": "main.py",
            },
            
            # WICHTIG: Diese Module müssen für die Windows-.exe geladen werden
            "include_modules": [
                "panda3d",
                "direct"
            ],
            
            "plugins": [
                "pandagl",
                "p3openal_audio",
            ],
            
            "requirements_path": "requirements.txt",
            
            "include_patterns": [
                "world/**/*",
                "models/**/*",
                "entities/**/*",
                "ui/**/*",
                "**/*.png",
                "**/*.jpg",
                "**/*.mp3",
                "**/*.wav",
                "**/*.ursina"
            ],
            
            # Verhindert Fehler mit unpassenden, vorkompilierten Binärdateien
            "use_optimized_wheels": False
        }
    }
)
