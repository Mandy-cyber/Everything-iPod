# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for iPod Wrapped Windows portable executable
"""

import os
import sys
from pathlib import Path

# Get the project root directory
block_cipher = None
project_root = Path('..').resolve()
ipod_wrapped_dir = project_root / 'ipod_wrapped'

# Data files to include
datas = [
    (str(ipod_wrapped_dir / 'gtk_style.css'), '.'),
    (str(ipod_wrapped_dir / '.env.example'), '.'),
    (str(ipod_wrapped_dir / 'frontend' / 'desktop_icon.png'), 'frontend'),
    (str(ipod_wrapped_dir / 'storage' / 'album_art' / 'missing_album_cover.jpg'), 'storage/album_art'),
]

# Hidden imports needed for GTK and dependencies
hiddenimports = [
    'gi',
    'gi.repository',
    'gi.repository.Gtk',
    'gi.repository.GLib',
    'gi.repository.Gio',
    'gi.repository.Adw',
    'gi.repository.GdkPixbuf',
    'gi.repository.Pango',
    'gi.repository.GtkSource',
    'cairo',
    'PIL',
    'PIL._imaging',
    'pandas',
    'requests',
    'pymongo',
    'mutagen',
    'keyring',
    'keyring.backends',
    'keyring.backends.Windows',
    'psutil',
]

a = Analysis(
    [str(ipod_wrapped_dir / 'main.py')],
    pathex=[str(ipod_wrapped_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='iPodWrapped',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ipod_wrapped_dir / 'frontend' / 'desktop_icon.png'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='iPodWrapped',
)
