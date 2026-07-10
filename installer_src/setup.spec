# -*- mode: python ; coding: utf-8 -*-
# Spec dla instalatora – buduj PO zbudowaniu głównej apki (dist/Moddy/)
from PyInstaller.utils.hooks import collect_data_files
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

datas = collect_data_files('customtkinter')
# Osadź całą aplikację w instalatorze
datas += [(os.path.join(ROOT, 'dist', 'Moddy'), 'app_files')]

a = Analysis(
    [os.path.join(SPECPATH, 'setup.py')],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=['PIL._tkinter_finder', 'winreg'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Moddy_Beta_1.0_Setup',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)
