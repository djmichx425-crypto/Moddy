# -*- mode: python ; coding: utf-8 -*-
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))

datas = []
from PyInstaller.utils.hooks import collect_data_files
datas += collect_data_files('customtkinter')

a = Analysis(
    [os.path.join(SPECPATH, 'uninstall.py')],
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
    name='uninstall',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)
