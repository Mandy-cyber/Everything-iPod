#!/bin/bash
# Linux AppImage Build Script for iPod Wrapped
# This script creates a portable AppImage using PyInstaller + appimagetool

set -e

echo "=========================================="
echo "iPod Wrapped - Linux AppImage Build"
echo "=========================================="

# Clean old builds
echo "Cleaning old build directories..."
rm -rf build dist AppDir *.AppImage

# Run PyInstaller
echo "Building with PyInstaller..."
pyinstaller ipod_wrapped.spec --clean

# Create AppDir structure for AppImage
echo "Creating AppDir structure..."
mkdir -p AppDir/usr/bin
mkdir -p AppDir/usr/share/applications
mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps

# Copy PyInstaller output to AppDir
echo "Copying application files..."
cp -r dist/iPodWrapped/* AppDir/usr/bin/

# Create desktop entry
echo "Creating desktop entry..."
mkdir -p AppDir/usr/share/applications
cat > AppDir/usr/share/applications/ipod-wrapped.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=iPod Wrapped
Comment=Spotify Wrapped for your iPod
Exec=iPodWrapped
Icon=ipod-wrapped
Categories=AudioVideo;Audio;Player;
Terminal=false
EOF

# Also create desktop file in AppDir root (required by appimagetool)
cp AppDir/usr/share/applications/ipod-wrapped.desktop AppDir/ipod-wrapped.desktop

# Copy icon
echo "Copying icon..."
cp ../../ipod_wrapped/frontend/desktop_icon.png AppDir/usr/share/icons/hicolor/256x256/apps/ipod-wrapped.png
cp ../../ipod_wrapped/frontend/desktop_icon.png AppDir/ipod-wrapped.png
cp ../../ipod_wrapped/frontend/desktop_icon.png AppDir/.DirIcon

# Create AppRun script
echo "Creating AppRun script..."
cat > AppDir/AppRun << 'EOF'
#!/bin/bash
# AppRun script for iPod Wrapped

HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Set XDG data dirs to find bundled resources
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"

# Run the application
exec "${HERE}/usr/bin/iPodWrapped" "$@"
EOF

chmod +x AppDir/AppRun

# Download appimagetool if not present
if [ ! -f "appimagetool-x86_64.AppImage" ]; then
    echo "Downloading appimagetool..."
    wget -q https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool-x86_64.AppImage
fi

# Create AppImage
echo "Creating AppImage..."
ARCH=x86_64 ./appimagetool-x86_64.AppImage AppDir iPod-Wrapped-x86_64.AppImage

echo ""
echo "=========================================="
echo "BUILD COMPLETE!"
echo "=========================================="
echo "AppImage: iPod-Wrapped-x86_64.AppImage"
ls -lh iPod-Wrapped-x86_64.AppImage

echo ""
echo "To test:"
echo "  chmod +x iPod-Wrapped-x86_64.AppImage"
echo "  ./iPod-Wrapped-x86_64.AppImage"
