================================================================================
                        iPod Wrapped - Linux AppImage
================================================================================

Thank you for downloading iPod Wrapped!

WHAT IS THIS?
-------------
This is a portable AppImage - a single executable file that contains everything
needed to run iPod Wrapped on Linux. No installation required!

SYSTEM REQUIREMENTS
-------------------
- Linux x86_64 (64-bit)
- Tested on: Ubuntu 20.04+, Arch Linux, Fedora 35+
- FUSE2 or FUSE3 (usually pre-installed)

FIRST TIME SETUP
----------------
1. Make the AppImage executable:
   chmod +x iPod-Wrapped-x86_64.AppImage

2. Run it:
   ./iPod-Wrapped-x86_64.AppImage

That's it! The app is fully portable and self-contained.

WHERE IS MY DATA STORED?
------------------------
Your iPod data, album art, and statistics are stored in:
  ~/.iPodWrapped/storage/

This keeps your data separate from the app, so you can:
- Update the AppImage without losing data
- Move the AppImage anywhere
- Backup your data easily

UPDATING TO A NEW VERSION
-------------------------
1. Download the new AppImage
2. Replace the old file
3. Make it executable again: chmod +x iPod-Wrapped-x86_64.AppImage
4. Run it - your data is preserved!

UNINSTALLING
------------
1. Delete the AppImage file
2. Optionally delete your data: rm -rf ~/.iPodWrapped/

TROUBLESHOOTING
---------------
If the AppImage won't run:

1. Check if FUSE is installed:
   - Ubuntu/Debian: sudo apt install fuse libfuse2
   - Arch: sudo pacman -S fuse2
   - Fedora: sudo dnf install fuse

2. Try extracting and running manually:
   ./iPod-Wrapped-x86_64.AppImage --appimage-extract
   ./squashfs-root/AppRun

3. Check logs in: ~/.iPodWrapped/ipod_wrapped.log

SUPPORT
-------
Report issues at: https://github.com/Mandy-cyber/Everything-iPod/issues

================================================================================
