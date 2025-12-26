# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for iPod Wrapped Windows portable executable
"""

import os
import sys
from pathlib import Path
import subprocess

# Get the project root directory
block_cipher = None
# Get the directory where this spec file is located (windows_installer/)
spec_dir = Path(SPECPATH)
# Go up one level to project root
project_root = spec_dir.parent
ipod_wrapped_dir = project_root / 'ipod_wrapped'

# Find GTK installation path in MSYS2
mingw_prefix = Path(os.environ.get('MINGW_PREFIX', 'D:/a/_temp/msys64/mingw64'))

# Data files to include
datas = [
    (str(ipod_wrapped_dir / 'gtk_style.css'), '.'),
    (str(ipod_wrapped_dir / '.env.example'), '.'),
    (str(ipod_wrapped_dir / 'frontend' / 'desktop_icon.png'), 'frontend'),
    (str(ipod_wrapped_dir / 'storage' / 'album_art' / 'missing_album_cover.jpg'), 'storage/album_art'),
]

# Add GTK typelibs and GI data
gi_typelibs = mingw_prefix / 'lib' / 'girepository-1.0'
if gi_typelibs.exists():
    datas.append((str(gi_typelibs / '*.typelib'), 'gi_typelibs'))

# Add GLib schemas
glib_schemas = mingw_prefix / 'share' / 'glib-2.0' / 'schemas'
if glib_schemas.exists():
    datas.append((str(glib_schemas), 'share/glib-2.0/schemas'))

# Add GTK icons and themes
gtk_icons = mingw_prefix / 'share' / 'icons'
if gtk_icons.exists():
    datas.append((str(gtk_icons / 'Adwaita'), 'share/icons/Adwaita'))

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
    runtime_hooks=[str(spec_dir / 'hook-gi.py')],
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
