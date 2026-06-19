from setuptools import setup

setup(
    name="Bindoj",
    options={
        "build_apps": {
        "platforms": ["win_amd64"],

        # TEMPORÄR zum Debuggen: zeigt ein CMD-Fenster mit allen Ausgaben/Tracebacks
        "console_apps": {
            "Bindoj": "main.py",
        },
        # "gui_apps": {
        #     "Bindoj": "main.py",
        # },

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
            "**/*.glb",
            "**/*.ursinamesh",
            "**/*.ttf",
            "**/*.otf",
        ],
        "use_optimized_wheels": False
    }
}
)