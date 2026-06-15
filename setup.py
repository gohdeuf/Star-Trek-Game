from setuptools import setup

setup(
    name="Bindoj",
    options={
        "build_apps": {
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
            
            # HIER WERDEN DEINE ORDNER UND DATEIEN IMPORTIERT:
            # Die Angabe '**/*' sorgt dafür, dass alle Unterordner und Dateien mitgenommen werden
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
