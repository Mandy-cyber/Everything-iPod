"""
Runtime hook for PyInstaller to set up GObject Introspection environment
"""
import os
import sys

# Set up GI typelib search path
if hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller bundle
    gi_typelib_path = os.path.join(sys._MEIPASS, 'gi_typelibs')
    if os.path.exists(gi_typelib_path):
        os.environ['GI_TYPELIB_PATH'] = gi_typelib_path

    # Set XDG data dirs for GLib schemas and GtkSourceView
    share_path = os.path.join(sys._MEIPASS, 'share')
    if os.path.exists(share_path):
        # Preserve existing XDG_DATA_DIRS if any, append our bundled share
        existing = os.environ.get('XDG_DATA_DIRS', '')
        if existing:
            os.environ['XDG_DATA_DIRS'] = f"{share_path}{os.pathsep}{existing}"
        else:
            os.environ['XDG_DATA_DIRS'] = share_path

    # Set GSETTINGS_SCHEMA_DIR for GLib schemas
    glib_schemas = os.path.join(sys._MEIPASS, 'share', 'glib-2.0', 'schemas')
    if os.path.exists(glib_schemas):
        os.environ['GSETTINGS_SCHEMA_DIR'] = glib_schemas
