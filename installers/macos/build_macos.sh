#!/bin/bash
# macOS .app Bundle Build Script for iPod Wrapped

set -e

echo "=========================================="
echo "iPod Wrapped - macOS .app Build"
echo "=========================================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script must be run on macOS"
    exit 1
fi

# Clean old builds
echo "Cleaning old build directories..."
rm -rf build dist

# Run PyInstaller
echo "Building with PyInstaller..."
pyinstaller ipod_wrapped.spec --clean

# Check if .app was created
if [ ! -d "dist/iPod Wrapped.app" ]; then
    echo "Error: .app bundle was not created!"
    exit 1
fi

# Create storage directory inside .app (for initial structure)
echo "Setting up .app bundle structure..."
mkdir -p "dist/iPod Wrapped.app/Contents/Resources/storage"

# Note: Actual user data will go to ~/Library/Application Support/iPod Wrapped/

echo ""
echo "=========================================="
echo "BUILD COMPLETE!"
echo "=========================================="
echo "App bundle: dist/iPod Wrapped.app"
ls -lh dist/

echo ""
echo "To test:"
echo "  open 'dist/iPod Wrapped.app'"
echo ""
echo "To create DMG for distribution:"
echo "  hdiutil create -volname 'iPod Wrapped' -srcfolder dist/ -ov -format UDZO iPod-Wrapped-macOS.dmg"
