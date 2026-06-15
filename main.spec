# -*- mode: python ; coding: utf-8 -*-
import os
import ursina

# Pfad zu den eingebauten Ursina-Dateien ermitteln
ursina_path = os.path.dirname(ursina.__file__)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('world/', 'world/'), 
        ('models/', 'models/'), 
        ('entities/', 'entities/'),
        ('ui/', 'ui/'),
        (ursina_path, 'ursina') # Wichtig, damit Ursina-eigene Texturen geladen werden
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MeinUrsinaSpiel', # Hier können Sie den Wunschnamen der .exe eintragen
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Auf 'False' ändern, wenn das schwarze CMD-Fenster beim Starten ausgeblendet sein soll
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
