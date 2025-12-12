# iPod Wrapped - Linux Release
> Claude-generated because I have no desire to know how this installer stuff works deep down right now. All it has been is pain and suffering. Will learn it another day.

A GTK4 application to view your iPod library, listening history, and generate your "iPod Wrapped" statistics.

## System Requirements

- Linux kernel 3.2+
- x86_64 architecture
- GTK4 and libadwaita-1

## Quick Start (Recommended)

The easiest way to install iPod Wrapped with all dependencies:

```bash
# download and extract the release
tar -xzf ipod-wrapped-linux-x86_64.tar.gz
cd ipod-wrapped-linux

# run the installer
./install.sh
```

The installer will:
- Detect your Linux distribution
- Check for required dependencies (GTK4, libadwaita)
- Offer to install missing dependencies (requires sudo)
- Install the AppImage to ~/Applications/
- Create a desktop entry for your application menu
- Extract and install the app icon

After installation, launch from your application menu or run:
```bash
~/Applications/iPodWrapped.AppImage
```

## Manual Installation

If you prefer to install manually:

### 1. Install Dependencies

**Ubuntu/Debian/Pop!_OS:**
```bash
sudo apt install libgtk-4-1 libadwaita-1-0
```

**Fedora:**
```bash
sudo dnf install gtk4 libadwaita
```

**Arch/Manjaro:**
```bash
sudo pacman -S gtk4 libadwaita
```

**openSUSE:**
```bash
sudo zypper install gtk4 libadwaita
```

### 2. Install the AppImage

```bash
# make executable
chmod +x iPodWrapped-x86_64.AppImage

# move to preferred location
mkdir -p ~/Applications
mv iPodWrapped-x86_64.AppImage ~/Applications/

# run it
~/Applications/iPodWrapped-x86_64.AppImage
```

## Data Storage

All data is stored in: ~/.iPodWrapped/storage/
- Database: ipod_wrapped.db
- Album art: album_art/

## Uninstallation

To remove iPod Wrapped, run the uninstaller:

```bash
./uninstall.sh
```

Or manually:

```bash
# remove appimage
rm ~/Applications/iPodWrapped.AppImage

# remove desktop entry
rm ~/.local/share/applications/ipod-wrapped.desktop

# remove icon
rm ~/.local/share/icons/hicolor/128x128/apps/ipod-wrapped.png

# remove data (optional)
rm -rf ~/.iPodWrapped/
```

## Troubleshooting

**App won't start:**
- Ensure GTK4 and libadwaita are installed
- Check if AppImage has execute permissions: chmod +x iPodWrapped-x86_64.AppImage
- Try running from terminal to see error messages

**Missing dependencies:**
- Run the installer script again: ./install.sh
- Or manually install GTK4 and libadwaita using your package manager

**Database errors:**
- The app will create ~/.iPodWrapped/storage/ automatically
- Ensure you have write permissions in your home directory

## Support

Report issues: https://github.com/Mandy-cyber/Everything-iPod/issues
