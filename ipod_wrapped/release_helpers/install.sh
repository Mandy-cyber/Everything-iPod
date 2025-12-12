#!/usr/bin/env bash
set -e

# =====================================================
# iPod Wrapped Installer
# =====================================================
# This script installs iPod Wrapped and its dependencies
# Supports: Ubuntu/Debian, Fedora, Arch Linux
# =====================================================

APP_NAME="iPodWrapped"
INSTALL_DIR="$HOME/Applications"
DESKTOP_FILE="$HOME/.local/share/applications/ipod-wrapped.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/128x128/apps/ipod-wrapped.png"

# colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# =====================================================
# helper functions
# =====================================================

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# =====================================================
# detect distribution
# =====================================================

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
    else
        print_error "Cannot detect Linux distribution"
        exit 1
    fi

    print_info "Detected: $PRETTY_NAME"
}

# =====================================================
# check dependencies
# =====================================================

check_gtk4() {
    if pkg-config --exists gtk4 2>/dev/null; then
        GTK4_VERSION=$(pkg-config --modversion gtk4)
        return 0
    else
        return 1
    fi
}

check_libadwaita() {
    if pkg-config --exists libadwaita-1 2>/dev/null; then
        LIBADWAITA_VERSION=$(pkg-config --modversion libadwaita-1)
        return 0
    else
        return 1
    fi
}

check_gtksourceview() {
    if pkg-config --exists gtksourceview-5 2>/dev/null; then
        GTKSOURCE_VERSION=$(pkg-config --modversion gtksourceview-5)
        return 0
    else
        return 1
    fi
}

check_python_package() {
    local package=$1
    if python3 -c "import $package" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# =====================================================
# install dependencies
# =====================================================

install_dependencies() {
    print_header "Checking Dependencies"

    NEEDS_INSTALL=false

    # check gtk4
    if check_gtk4; then
        print_success "GTK4 is installed (version $GTK4_VERSION)"
    else
        print_warning "GTK4 is not installed"
        NEEDS_INSTALL=true
    fi

    # check libadwaita
    if check_libadwaita; then
        print_success "libadwaita is installed (version $LIBADWAITA_VERSION)"
    else
        print_warning "libadwaita is not installed"
        NEEDS_INSTALL=true
    fi

    # check gtksourceview
    if check_gtksourceview; then
        print_success "GtkSourceView is installed (version $GTKSOURCE_VERSION)"
    else
        print_warning "GtkSourceView is not installed"
        NEEDS_INSTALL=true
    fi

    # check python packages
    if check_python_package "gi"; then
        print_success "PyGObject is installed"
    else
        print_warning "PyGObject is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "pandas"; then
        print_success "pandas is installed"
    else
        print_warning "pandas is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "dotenv"; then
        print_success "python-dotenv is installed"
    else
        print_warning "python-dotenv is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "requests"; then
        print_success "requests is installed"
    else
        print_warning "requests is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "pymongo"; then
        print_success "pymongo is installed"
    else
        print_warning "pymongo is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "PIL"; then
        print_success "Pillow is installed"
    else
        print_warning "Pillow is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "mutagen"; then
        print_success "mutagen is installed"
    else
        print_warning "mutagen is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "typer"; then
        print_success "typer is installed"
    else
        print_warning "typer is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "keyring"; then
        print_success "keyring is installed"
    else
        print_warning "keyring is not installed"
        NEEDS_INSTALL=true
    fi

    if check_python_package "psutil"; then
        print_success "psutil is installed"
    else
        print_warning "psutil is not installed"
        NEEDS_INSTALL=true
    fi

    # if nothing needed, return
    if [ "$NEEDS_INSTALL" = false ]; then
        print_success "All dependencies are already installed!"
        return 0
    fi

    # ask user if they want to install
    echo ""
    print_info "Missing dependencies need to be installed."
    echo -e "This will require sudo privileges.\n"
    read -p "Do you want to install missing dependencies? (y/n) " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Skipping dependency installation."
        print_warning "App may not work without these dependencies!"
        return 0
    fi

    # install based on distro
    case "$DISTRO" in
        ubuntu|debian|pop|linuxmint)
            print_info "Installing dependencies via apt..."
            sudo apt update || { print_error "Failed to update package list"; exit 1; }
            sudo apt install -y python3 python3-pandas python3-pil python3-requests \
                python3-dotenv python3-pymongo python3-mutagen python3-typer python3-keyring python3-psutil \
                pkg-config libgtk-4-1 libadwaita-1-0 libgtksourceview-5-0 \
                python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gtksource-5 || {
                print_warning "Some packages may have failed to install"
            }
            ;;
        fedora|rhel|centos)
            print_info "Installing dependencies via dnf..."
            sudo dnf install -y python3 python3-pandas python3-pillow python3-requests \
                python3-dotenv python3-pymongo python3-mutagen python3-typer python3-keyring python3-psutil \
                pkgconfig gtk4 libadwaita gtksourceview5 \
                python3-gobject python3-cairo || {
                print_warning "Some packages may have failed to install"
            }
            ;;
        arch|manjaro|endeavouros)
            print_info "Installing dependencies via pacman..."
            sudo pacman -S --needed --noconfirm python python-pandas python-pillow python-requests \
                python-dotenv python-pymongo python-mutagen python-typer python-keyring python-psutil \
                pkgconf gtk4 libadwaita gtksourceview5 \
                python-gobject python-cairo || {
                print_warning "Some packages may have failed to install"
            }
            ;;
        opensuse*)
            print_info "Installing dependencies via zypper..."
            sudo zypper install -y python3 python3-pandas python3-Pillow python3-requests \
                python3-dotenv python3-pymongo python3-mutagen python3-typer python3-keyring python3-psutil \
                pkg-config gtk4 libadwaita gtksourceview5 \
                python3-gobject python3-cairo || {
                print_warning "Some packages may have failed to install"
            }
            ;;
        *)
            print_error "Unsupported distribution: $DISTRO"
            print_info "Please manually install: gtk4, libadwaita-1"
            print_info "Then re-run this installer."
            exit 1
            ;;
    esac

    # verify installation
    if check_gtk4 && check_libadwaita; then
        print_success "Dependencies installed successfully!"
    else
        print_warning "Could not verify dependencies with pkg-config"
        print_info "But packages were installed. The app should still work."
    fi
}

# =====================================================
# install appimage
# =====================================================

install_appimage() {
    print_header "Installing iPod Wrapped"

    # find appimage in current directory
    APPIMAGE_FILE=$(find . -maxdepth 1 -name "${APP_NAME}*.AppImage" -type f | head -n 1)

    if [ -z "$APPIMAGE_FILE" ]; then
        print_error "AppImage file not found in current directory"
        print_info "Expected: ${APP_NAME}-x86_64.AppImage"
        exit 1
    fi

    print_info "Found: $APPIMAGE_FILE"

    # create install directory
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$(dirname "$DESKTOP_FILE")"
    mkdir -p "$(dirname "$ICON_FILE")"

    # copy appimage
    INSTALLED_APPIMAGE="$INSTALL_DIR/${APP_NAME}.AppImage"
    cp "$APPIMAGE_FILE" "$INSTALLED_APPIMAGE"
    chmod +x "$INSTALLED_APPIMAGE"
    print_success "Installed to: $INSTALLED_APPIMAGE"

    # extract icon from appimage
    print_info "Extracting icon..."
    "$INSTALLED_APPIMAGE" --appimage-extract usr/share/icons/hicolor/128x128/apps/${APP_NAME}.png >/dev/null 2>&1 || true
    if [ -f "squashfs-root/usr/share/icons/hicolor/128x128/apps/${APP_NAME}.png" ]; then
        cp "squashfs-root/usr/share/icons/hicolor/128x128/apps/${APP_NAME}.png" "$ICON_FILE"
        rm -rf squashfs-root
        print_success "Icon extracted"
    else
        print_warning "Could not extract icon (app will still work)"
    fi

    # create desktop entry
    print_info "Creating desktop entry..."
    cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=iPod Wrapped
Comment=View your iPod library and listening statistics
Exec=$INSTALLED_APPIMAGE
Icon=ipod-wrapped
Terminal=false
Type=Application
Categories=AudioVideo;Audio;Music;Utility;
Keywords=ipod;music;wrapped;statistics;
StartupNotify=true
EOF

    chmod +x "$DESKTOP_FILE"
    print_success "Desktop entry created"

    # update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
    fi
}

# =====================================================
# main installation
# =====================================================

main() {
    print_header "iPod Wrapped Installer"

    # detect distro
    detect_distro

    # install dependencies
    install_dependencies

    # install appimage
    install_appimage

    # done
    print_header "Installation Complete!"
    print_success "iPod Wrapped has been installed successfully"
    echo ""
    print_info "You can now:"
    echo "  • Launch from your application menu"
    echo "  • Run directly: $INSTALL_DIR/${APP_NAME}.AppImage"
    echo ""
    print_info "Data will be stored in: ~/.iPodWrapped/storage/"
    echo ""
}

# run main
main
