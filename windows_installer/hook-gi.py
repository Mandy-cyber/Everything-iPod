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

    # Set XDG data dirs for GLib schemas
    share_path = os.path.join(sys._MEIPASS, 'share')
    if os.path.exists(share_path):
        os.environ['XDG_DATA_DIRS'] = share_path
