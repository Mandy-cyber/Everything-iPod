# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for iPod Wrapped (Linux)
Creates a standalone bundle with all GTK4/Libadwaita dependencies
"""

from pathlib import Path
import os

block_cipher = None

# Get paths
# Get the directory where this spec file is located (installers/linux/)
spec_dir = Path(SPECPATH)
# Go up two levels to project root
project_root = spec_dir.parent.parent
ipod_wrapped_dir = project_root / 'ipod_wrapped'

# Data files to include
datas = [
    (str(ipod_wrapped_dir / 'gtk_style.css'), '.'),
    (str(ipod_wrapped_dir / '.env.example'), '.'),
    (str(ipod_wrapped_dir / 'frontend' / 'desktop_icon.png'), 'frontend'),
    (str(ipod_wrapped_dir / 'storage' / 'album_art' / 'missing_album_cover.jpg'), 'storage/album_art'),
]

# Collect GtkSourceView shared libraries
binaries = []

# Find GTK libraries (system installation)
# On Linux, PyInstaller's default hooks should catch most libraries,
# but we'll explicitly add GtkSourceView if needed
import subprocess
try:
    # Find libgtksourceview
    result = subprocess.run(['pkg-config', '--variable=libdir', 'gtksourceview-5'],
                          capture_output=True, text=True, check=True)
    lib_dir = Path(result.stdout.strip())
    gtksource_so = lib_dir / 'libgtksourceview-5.so.0'
    if gtksource_so.exists():
        binaries.append((str(gtksource_so), '.'))
except:
    pass

# Add GTK typelibs and GI data
# Find typelib directory
try:
    result = subprocess.run(['pkg-config', '--variable=typelibdir', 'gobject-introspection-1.0'],
                          capture_output=True, text=True, check=True)
    gi_typelibs = Path(result.stdout.strip())
    if gi_typelibs.exists():
        datas.append((str(gi_typelibs), 'gi_typelibs'))
except:
    # Fallback to common locations
    for typelib_path in ['/usr/lib/x86_64-linux-gnu/girepository-1.0', '/usr/lib/girepository-1.0']:
        if Path(typelib_path).exists():
            datas.append((typelib_path, 'gi_typelibs'))
            break

# Add GLib schemas
glib_schemas = Path('/usr/share/glib-2.0/schemas')
if glib_schemas.exists():
    datas.append((str(glib_schemas), 'share/glib-2.0/schemas'))

# Add Adwaita icons (subset - the full set is huge)
adwaita_icons = Path('/usr/share/icons/Adwaita')
if adwaita_icons.exists():
    # Only include scalable symbolic icons to keep size down
    symbolic_icons = adwaita_icons / 'scalable'
    if symbolic_icons.exists():
        datas.append((str(symbolic_icons), 'share/icons/Adwaita/scalable'))
    # Include icon theme index
    icon_theme = adwaita_icons / 'index.theme'
    if icon_theme.exists():
        datas.append((str(icon_theme), 'share/icons/Adwaita'))

# Add GtkSourceView language specs and style schemes
gtksourceview_data = Path('/usr/share/gtksourceview-5')
if gtksourceview_data.exists():
    datas.append((str(gtksourceview_data), 'share/gtksourceview-5'))

# Hidden imports needed for GTK4/GI
hiddenimports = [
    'gi._gi_cairo',  # Critical for cairo Context support
    'gi._gi',
    'gi.repository.Gtk',
    'gi.repository.Gdk',
    'gi.repository.GLib',
    'gi.repository.GObject',
    'gi.repository.Gio',
    'gi.repository.Adw',
    'gi.repository.GdkPixbuf',
    'gi.repository.Pango',
    'gi.repository.GtkSource',
    'cairo',
    'PIL._imaging',
    'PIL.Image',
    'pandas',
    'numpy',
    'mutagen',
    'requests',
    'dotenv',
    'typer',
    'keyring',
    'keyring.backends.SecretService',
    'psutil',
]

a = Analysis(
    [str(ipod_wrapped_dir / 'main.py')],
    pathex=[str(ipod_wrapped_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(spec_dir / 'hook-gi.py')],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
    ],
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
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
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
