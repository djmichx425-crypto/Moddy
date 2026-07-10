# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas  = [('assets', 'assets')]
datas += collect_data_files('customtkinter')
datas += collect_data_files('minecraft_launcher_lib')

hiddenimports = [
    'uvicorn.loops.auto',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan.on',
    'sqlalchemy.dialects.sqlite',
    'PIL._tkinter_finder',
    'jose.jwt',
    'bcrypt',
    'psutil',
    'cryptography.fernet',
    'cryptography.hazmat.primitives.kdf.pbkdf2',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'tkinter.test'],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Moddy',
    debug=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3*.dll'],
    console=False,
    icon='assets\\icon.ico',
    version='assets\\version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Moddy',
)
