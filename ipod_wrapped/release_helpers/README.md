# Release Helpers
> Claude-generated because I have no desire to know how this installer stuff works deep down right now. All it has been is pain and suffering. Will learn it another day.

This directory contains scripts for building and packaging iPod Wrapped for Linux distribution.

## Prerequisites

1. System Python 3.13+
2. Build dependencies:
   ```bash
   sudo apt install libgtk-4-dev libadwaita-1-dev  # Ubuntu/Debian
   # or
   sudo dnf install gtk4-devel libadwaita-devel  # Fedora
   # or
   sudo pacman -S gtk4 libadwaita  # Arch
   ```

3. Create and activate virtual environment (from project root):
   ```bash
   cd /path/to/ipod_wrapped
   python3 -m venv build-venv
   source build-venv/bin/activate
   pip install -r requirements.txt
   ```

## Building the AppImage

```bash
cd release_helpers
./build_appimage.sh
```

This will:
- Check for build-venv in project root
- Bundle Python runtime and dependencies
- Remove conflicting system libraries
- Create iPodWrapped-x86_64.AppImage

## Creating the Release Package

```bash
./package_release.sh
```

This will create `ipod-wrapped-linux-x86_64.tar.gz` containing:
- iPodWrapped-x86_64.AppImage
- install.sh (installs AppImage + dependencies)
- uninstall.sh (removes AppImage + optionally data)
- README.md (user-facing release notes)

## Files in this Directory

**Build Scripts:**
- `build_appimage.sh` - builds the AppImage
- `package_release.sh` - packages everything for distribution
- `verify_appimage.sh` - verifies Python imports work
- `test_install.sh` - tests installer in Docker

**User-Facing Files (bundled in release):**
- `install.sh` - installer script with dependency detection
- `uninstall.sh` - uninstaller script
- `README.md` - user-facing release notes

**Build Artifacts (gitignored):**
- `linuxdeploy-x86_64.AppImage` - AppImage packaging tool (downloaded)
- `AppDir/` - temporary build directory (auto-generated)
- `*.AppImage` - generated AppImage files
- `*.tar.gz` - release tarballs

## Release Workflow

### Manual Release
1. Make code changes in the main project
2. Update version numbers if needed
3. Build AppImage: `./build_appimage.sh`
4. Test the AppImage: `./iPodWrapped-x86_64.AppImage`
5. Package for release: `./package_release.sh`
6. Upload `ipod-wrapped-linux-x86_64.tar.gz` to GitHub Releases

### Automated Release (GitHub Actions)
1. Make code changes and commit
2. Push a version tag: `git tag v1.0.0 && git push origin v1.0.0`
3. GitHub Actions automatically builds and creates a release

## Notes

- The build script expects build-venv to exist in the project root (../build-venv)
- All project files are copied from the parent directory
- The AppImage is self-contained except for GTK4/libadwaita system libraries
- Users' data is stored in ~/.iPodWrapped/storage/
