from setuptools import setup

setup(
    name="Bindoj",
    options={
        "build_apps": {
            # HIER DIE LÖSUNG: Nur für Windows (64-Bit) bauen
            "platforms": ["win_amd64"],
            
            # Deine Hauptdatei, die das Spiel startet
            "gui_apps": {
                "Bindoj": "main.py",
            },
            # Erzwingt das Einpacken der Grafik- und Soundtreiber
            "plugins": [
                "pandagl",
                "p3openal_audio",
            ],
            # Bindet alle Bibliotheken aus deiner requirements.txt ein
            "requirements_path": "requirements.txt",
            
            # Importiert all deine spezifischen Spiele-Ordner
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
        }
    }
)
