#!/usr/bin/env bash
set -e

# =====================================================
# Package iPod Wrapped Release
# =====================================================
# Creates a tarball with AppImage and installer scripts
# =====================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="iPodWrapped"
RELEASE_NAME="ipod-wrapped-linux-x86_64"
RELEASE_DIR="$SCRIPT_DIR/$RELEASE_NAME"

echo "Packaging iPod Wrapped for release..."

# check for appimage
if [ ! -f "$SCRIPT_DIR/${APP_NAME}-x86_64.AppImage" ]; then
    echo "Error: ${APP_NAME}-x86_64.AppImage not found!"
    echo "Please build the AppImage first: ./build_appimage.sh"
    exit 1
fi

# create release directory
echo "Creating release directory..."
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# copy files
echo "Copying files..."
cp "$SCRIPT_DIR/${APP_NAME}-x86_64.AppImage" "$RELEASE_DIR/"
cp "$SCRIPT_DIR/install.sh" "$RELEASE_DIR/"
cp "$SCRIPT_DIR/uninstall.sh" "$RELEASE_DIR/"
cp "$SCRIPT_DIR/RELEASE_NOTES.md" "$RELEASE_DIR/README.md"

# create tarball
echo "Creating tarball..."
cd "$SCRIPT_DIR"
tar -czf "${RELEASE_NAME}.tar.gz" "$RELEASE_NAME"

# cleanup
rm -rf "$RELEASE_DIR"

# show results
echo ""
echo "Release package created successfully!"
echo "File: ${RELEASE_NAME}.tar.gz"
echo "Size: $(du -h "${RELEASE_NAME}.tar.gz" | cut -f1)"
echo ""
echo "Contents:"
echo "  - ${APP_NAME}-x86_64.AppImage"
echo "  - install.sh"
echo "  - uninstall.sh"
echo "  - README.md"
echo ""
echo "Upload this tarball to your GitHub release."
