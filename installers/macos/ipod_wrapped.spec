# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for iPod Wrapped macOS .app bundle
"""

from pathlib import Path
import os
import subprocess

block_cipher = None

# Get paths
# Get the directory where this spec file is located (installers/macos/)
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

# Collect binaries
binaries = []

# Try to find GTK libraries via Homebrew
try:
    result = subprocess.run(['brew', '--prefix', 'gtk4'],
                          capture_output=True, text=True, check=True)
    gtk_prefix = Path(result.stdout.strip())

    # Add GtkSourceView library
    result = subprocess.run(['brew', '--prefix', 'gtksourceview5'],
                          capture_output=True, text=True, check=True)
    gtksourceview_prefix = Path(result.stdout.strip())
    gtksource_lib = gtksourceview_prefix / 'lib' / 'libgtksourceview-5.0.dylib'
    if gtksource_lib.exists():
        binaries.append((str(gtksource_lib), '.'))
except:
    print("Warning: Could not find GTK4 via Homebrew")
    gtk_prefix = Path('/opt/homebrew')  # Fallback for Apple Silicon

# Add GTK typelibs and GI data
try:
    result = subprocess.run(['pkg-config', '--variable=typelibdir', 'gobject-introspection-1.0'],
                          capture_output=True, text=True, check=True)
    gi_typelibs = Path(result.stdout.strip())
    if gi_typelibs.exists():
        datas.append((str(gi_typelibs), 'gi_typelibs'))
except:
    # Fallback to common Homebrew locations
    for typelib_path in [
        gtk_prefix / 'lib' / 'girepository-1.0',
        Path('/opt/homebrew/lib/girepository-1.0'),
        Path('/usr/local/lib/girepository-1.0')
    ]:
        if typelib_path.exists():
            datas.append((str(typelib_path), 'gi_typelibs'))
            break

# Add GLib schemas
glib_schemas = gtk_prefix / 'share' / 'glib-2.0' / 'schemas'
if glib_schemas.exists():
    datas.append((str(glib_schemas), 'share/glib-2.0/schemas'))

# Add Adwaita icons (subset)
adwaita_icons = gtk_prefix / 'share' / 'icons' / 'Adwaita'
if adwaita_icons.exists():
    symbolic_icons = adwaita_icons / 'scalable'
    if symbolic_icons.exists():
        datas.append((str(symbolic_icons), 'share/icons/Adwaita/scalable'))
    icon_theme = adwaita_icons / 'index.theme'
    if icon_theme.exists():
        datas.append((str(icon_theme), 'share/icons/Adwaita'))

# Add GtkSourceView language specs and style schemes
gtksourceview_data = gtk_prefix / 'share' / 'gtksourceview-5'
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
    'keyring.backends.OS_X',
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

app = BUNDLE(
    coll,
    name='iPod Wrapped.app',
    icon=str(ipod_wrapped_dir / 'frontend' / 'desktop_icon.icns') if (ipod_wrapped_dir / 'frontend' / 'desktop_icon.icns').exists() else None,
    bundle_identifier='com.mandycyber.ipodwrapped',
    info_plist={
        'CFBundleName': 'iPod Wrapped',
        'CFBundleDisplayName': 'iPod Wrapped',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '11.0',
        'NSPrincipalClass': 'NSApplication',
    },
)
