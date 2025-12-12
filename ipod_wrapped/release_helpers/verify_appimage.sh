#!/usr/bin/env bash
# Quick verification that AppImage can import required modules

APPIMAGE="./iPodWrapped-x86_64.AppImage"

if [ ! -f "$APPIMAGE" ]; then
    echo "Error: AppImage not found"
    exit 1
fi

echo "Extracting AppImage..."
"$APPIMAGE" --appimage-extract >/dev/null 2>&1

echo "Testing Python imports..."
cd squashfs-root

# Get the python binary from AppRun
PYTHON_BIN="./usr/share/iPodWrapped/venv/bin/python3"
VENV_SITE_PACKAGES="./usr/share/iPodWrapped/venv/lib/python3.13/site-packages"
SYSTEM_SITE_PACKAGES="/usr/lib/python3.13/site-packages:/usr/lib64/python3.13/site-packages"
export PYTHONPATH="$SYSTEM_SITE_PACKAGES:$VENV_SITE_PACKAGES:./usr/share/iPodWrapped:$PYTHONPATH"
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:/usr/lib64:/usr/lib:$LD_LIBRARY_PATH"
export GI_TYPELIB_PATH="/usr/lib/girepository-1.0:/usr/lib/x86_64-linux-gnu/girepository-1.0:/usr/lib64/girepository-1.0"

# Test imports
$PYTHON_BIN -c "import gi; print('✓')" 2>&1 | grep -q "✓" && echo "✓ PyGObject works" || echo "✗ PyGObject failed"
$PYTHON_BIN -c "import pandas; print('✓')" 2>&1 | grep -q "✓" && echo "✓ pandas works" || echo "✗ pandas failed"
$PYTHON_BIN -c "import requests; print('✓')" 2>&1 | grep -q "✓" && echo "✓ requests works" || echo "✗ requests failed"

cd ..
rm -rf squashfs-root

echo "Verification complete"
