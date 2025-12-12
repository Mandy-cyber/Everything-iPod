#!/usr/bin/env bash
set -e

# -----------------------
# Configuration
# -----------------------
APP_NAME="iPodWrapped"
APPDIR="AppDir"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LINUXDEPLOY="$SCRIPT_DIR/linuxdeploy-x86_64.AppImage"
ICON_SRC="$PROJECT_ROOT/frontend/widgets/icon.png"
DESKTOP_FILE="$APPDIR/usr/share/applications/$APP_NAME.desktop"
ARCH=${ARCH:-x86_64}  # default architecture hint
VENV_NAME="$PROJECT_ROOT/build-venv"

# -----------------------
# Check for virtual environment
# -----------------------
if [ ! -d "$VENV_NAME" ]; then
    echo "Error: Virtual environment 'build-venv' not found in project root!"
    echo "Please create it first: python3 -m venv $VENV_NAME"
    echo "Then activate and install dependencies: source $VENV_NAME/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# -----------------------
# Cleanup previous builds
# -----------------------
echo "Cleaning previous AppImage builds..."
cd "$SCRIPT_DIR"
rm -rf "$APPDIR" "${APP_NAME}-${ARCH}.AppImage"

# -----------------------
# Create AppDir structure
# -----------------------
echo "Creating AppDir structure..."
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/$APP_NAME"
mkdir -p "$APPDIR/usr/share/applications"
mkdir -p "$APPDIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$APPDIR/usr/lib"

# -----------------------
# Copy Python app and resources
# -----------------------
echo "Copying Python app and resources..."
cp "$PROJECT_ROOT/main.py" "$APPDIR/usr/bin/$APP_NAME.py"
cp -r "$PROJECT_ROOT/frontend" "$APPDIR/usr/share/$APP_NAME/"
cp -r "$PROJECT_ROOT/backend" "$APPDIR/usr/share/$APP_NAME/"
cp -r "$PROJECT_ROOT/storage" "$APPDIR/usr/share/$APP_NAME/"
cp "$PROJECT_ROOT/gtk_style.css" "$APPDIR/usr/share/$APP_NAME/"

# -----------------------
# Bundle Python runtime and dependencies
# -----------------------
echo "Bundling Python runtime and dependencies..."
# Copy the entire virtual environment
cp -r "$VENV_NAME" "$APPDIR/usr/share/$APP_NAME/venv"

# Remove unnecessary files to reduce size
echo "Cleaning up bundled Python environment..."
find "$APPDIR/usr/share/$APP_NAME/venv" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APPDIR/usr/share/$APP_NAME/venv" -type f -name "*.pyc" -delete 2>/dev/null || true
find "$APPDIR/usr/share/$APP_NAME/venv" -type f -name "*.pyo" -delete 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/test 2>/dev/null || true

# Remove problematic shared libraries that conflict with system libraries
# We want to use system SSL, crypto, and other system libraries
echo "Removing conflicting shared libraries..."
find "$APPDIR/usr/share/$APP_NAME/venv" -name "libssl.so*" -delete 2>/dev/null || true
find "$APPDIR/usr/share/$APP_NAME/venv" -name "libcrypto.so*" -delete 2>/dev/null || true
find "$APPDIR/usr/share/$APP_NAME/venv" -name "libcurl.so*" -delete 2>/dev/null || true

# Remove packages with compiled extensions - must use system versions
# These have C extensions that are Python-version-specific
echo "Removing packages with compiled extensions (will use system versions)..."
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/gi 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/PyGObject* 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/pycairo* 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/cairo 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/pandas 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/pandas-* 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/numpy 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/numpy-* 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/PIL 2>/dev/null || true
rm -rf "$APPDIR/usr/share/$APP_NAME/venv/lib/python3."*/site-packages/Pillow-* 2>/dev/null || true

# -----------------------
# Create launcher script
# -----------------------
echo "Creating launcher..."
cat > "$APPDIR/usr/bin/$APP_NAME" << 'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "$0")")"
APPDIR="$(dirname "$HERE")"

# Use system Python (not bundled)
PYTHON_BIN="python3"

# Detect Python version
PYTHON_VERSION=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "3.12")

# Bundled packages location
VENV_SITE_PACKAGES="$APPDIR/share/iPodWrapped/venv/lib/python${PYTHON_VERSION}/site-packages"

# Also try python3.13 packages if system is older
VENV_SITE_PACKAGES_313="$APPDIR/share/iPodWrapped/venv/lib/python3.13/site-packages"

# Set PYTHONPATH to include bundled packages and app directories
export PYTHONPATH="$VENV_SITE_PACKAGES:$VENV_SITE_PACKAGES_313:$APPDIR/share/iPodWrapped:$PYTHONPATH"

# Add system library paths for GObject and GTK
SYSTEM_LIB_PATHS="/usr/lib/x86_64-linux-gnu:/usr/lib64:/usr/lib"
export LD_LIBRARY_PATH="$SYSTEM_LIB_PATHS:$LD_LIBRARY_PATH"

# GObject introspection typelib path
export GI_TYPELIB_PATH="/usr/lib/girepository-1.0:/usr/lib/x86_64-linux-gnu/girepository-1.0:/usr/lib64/girepository-1.0:$GI_TYPELIB_PATH"

# Persistent storage path
export STORAGE_DIR="$HOME/.iPodWrapped/storage"
mkdir -p "$STORAGE_DIR"

# Run main Python app
exec "$PYTHON_BIN" "$HERE/iPodWrapped.py" "$@"
EOF
chmod +x "$APPDIR/usr/bin/$APP_NAME"
echo "Launcher created."

# -----------------------
# Create .desktop file
# -----------------------
echo "Creating .desktop file..."
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=$APP_NAME
Comment=Your iPod management app
Exec=$APP_NAME
Icon=$APP_NAME
Terminal=false
Type=Application
Categories=AudioVideo;Utility;
EOF

# -----------------------
# Copy icon
# -----------------------
echo "Copying icon..."
cp "$ICON_SRC" "$APPDIR/usr/share/icons/hicolor/128x128/apps/$APP_NAME.png"

# -----------------------
# Build AppImage
# -----------------------
echo "Building AppImage for architecture: $ARCH..."
chmod +x "$LINUXDEPLOY"
ARCH=$ARCH "$LINUXDEPLOY" \
    --appdir "$APPDIR" \
    --output appimage \
    --desktop-file "$DESKTOP_FILE" \
    --icon-file "$APPDIR/usr/share/icons/hicolor/128x128/apps/$APP_NAME.png"

echo "AppImage build complete: $SCRIPT_DIR/${APP_NAME}-${ARCH}.AppImage"
