#!/bin/bash
# Windows Build Script for iPod Wrapped (runs on GitHub Actions Windows runner)
# This script is called by the GitHub Actions workflow

set -e

echo "=========================================="
echo "iPod Wrapped - Windows Build Script"
echo "=========================================="

# Install PyInstaller
echo "Installing build dependencies..."
python -m pip install pyinstaller

# Clean old builds
echo "Cleaning old build directories..."
rm -rf build dist

# Run PyInstaller
echo "Building with PyInstaller..."
pyinstaller ipod_wrapped.spec --clean

# Create storage directory
echo "Setting up portable package structure..."
mkdir -p dist/iPodWrapped/storage

# Copy README if exists
if [ -f "README_WINDOWS.txt" ]; then
    cp README_WINDOWS.txt dist/iPodWrapped/README.txt
    echo "Copied README.txt"
fi

# Create ZIP archive
echo "Creating ZIP archive..."
cd dist
7z a -tzip ipod-wrapped-windows-portable.zip iPodWrapped/
cd ..

echo ""
echo "=========================================="
echo "BUILD COMPLETE!"
echo "=========================================="
echo "Package: dist/ipod-wrapped-windows-portable.zip"
ls -lh dist/ipod-wrapped-windows-portable.zip
