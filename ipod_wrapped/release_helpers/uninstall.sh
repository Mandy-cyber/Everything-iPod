#!/usr/bin/env bash

# =====================================================
# iPod Wrapped Uninstaller
# =====================================================

APP_NAME="iPodWrapped"
INSTALL_DIR="$HOME/Applications"
DESKTOP_FILE="$HOME/.local/share/applications/ipod-wrapped.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/128x128/apps/ipod-wrapped.png"
DATA_DIR="$HOME/.iPodWrapped"

# colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # no color

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}iPod Wrapped Uninstaller${NC}"
echo -e "${BLUE}========================================${NC}\n"

# remove appimage
if [ -f "$INSTALL_DIR/${APP_NAME}.AppImage" ]; then
    rm "$INSTALL_DIR/${APP_NAME}.AppImage"
    print_success "Removed AppImage"
else
    print_warning "AppImage not found (may already be removed)"
fi

# remove desktop entry
if [ -f "$DESKTOP_FILE" ]; then
    rm "$DESKTOP_FILE"
    print_success "Removed desktop entry"
fi

# remove icon
if [ -f "$ICON_FILE" ]; then
    rm "$ICON_FILE"
    print_success "Removed icon"
fi

# update desktop database
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

# ask about data
if [ -d "$DATA_DIR" ]; then
    echo ""
    print_info "Your data is stored in: $DATA_DIR"
    read -p "Do you want to delete your data? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        print_success "Removed data directory"
    else
        print_info "Data preserved in: $DATA_DIR"
    fi
fi

echo ""
print_success "iPod Wrapped has been uninstalled"
echo ""
