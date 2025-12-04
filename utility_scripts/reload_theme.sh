#!/bin/bash

# dir locations
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

THEME_DIR="${THEME_DIR:-$PROJECT_ROOT/rockbox_themes/the_letter/.rockbox}"
ROCKBOX_DIR="${ROCKBOX_DIR:-$HOME/Coding/rockbox/build-dir/simdisk/.rockbox}"

# kill current rockboxui instance(s)
pkill -f rockboxui

# copy over theme
cp -r "$THEME_DIR/." "$ROCKBOX_DIR/"

# wait & restart
sleep 0.5
cd "$(dirname "$ROCKBOX_DIR")" && cd .. && ./rockboxui