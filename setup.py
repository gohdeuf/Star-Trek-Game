from setuptools import setup

setup(
    name="Bindoj",
    options={
        "build_apps": {
            "platforms": ["win_amd64"],

            "console_apps": {
                "Bindoj": "main.py",
            },

            # Damit du bei künftigen Abstürzen einen Log siehst statt nichts:
            "log_filename": "$USER_APPDATA/Bindoj/output.log",
            "log_append": False,

            "include_modules": {
                "*": [
                    "panda3d",
                    "direct",
                    "numpy._core._exceptions",
                ]
            },

            "plugins": [
                "pandagl",
                "p3tinydisplay",
                "p3openal_audio",
            ],
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
