import os
import re
import glob
import subprocess
import shutil
from typing import Optional
from album_art_fixer import process_images, organize_music_files, clear_temp_directory


def find_ipod() -> Optional[str]:
    """Find the device path for a connected iPod"""
    ipod_found = False

    # check for USB connection
    lsusb_output = subprocess.run(['lsusb'], capture_output=True, text=True)

    for line in lsusb_output.stdout.split('\n'):
        if 'iPod' in line or '05ac:' in line:  # 05ac = Apple's vendor ID
            ipod_found = True
            break

    if not ipod_found:
        print("No iPod found. Make sure it is connected via USB")
        return None

    # search for mount point
    mount_output = subprocess.run(['mount'], capture_output=True, text=True)

    ipod_mounts = []
    for line in mount_output.stdout.split('\n'):
        if any(keyword in line.lower() for keyword in ['ipod', 'apple']):
            ipod_mounts.append(line)

    if ipod_mounts:
        for mount in ipod_mounts:
            # parse mount point
            match = re.search(r'on (.+?) type', mount)
            if match:
                return match.group(1)

    # also check /proc/mounts
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                if 'ipod' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
    except Exception as e:
        pass

    return None


def find_music_directory() -> Optional[str]:
    """Finds the location of the 'Music' directory"""
    # find ipod
    ipod_location = find_ipod()
    if not ipod_location:
        return None
    
    # look for Music directory
    full_pattern = os.path.join(ipod_location, '**', "Music")
    found_files = glob.glob(full_pattern, recursive=True)
    if not found_files or len(found_files) == 0:
        return None
    return found_files[0]


def fix_and_store_album_art(album_art_storage: str) -> bool:
    """Generates a cover.jpg for each album, and copies them locally

    Args:
        album_art_storage (str): Where to store the generated album art

    Returns:
        bool: True if successful, false otherwise
    """
    # locate "Music" dir
    music_dir = find_music_directory()
    if not music_dir:
        print("Could not find Music directory on iPod")
        return False

    print(f"Found music directory: {music_dir}")

    try:
        # organize albums
        print("Organizing music files by album...")
        organize_music_files(music_dir)

        # check if covers already exist
        existing_covers = 0
        needs_extraction = 0

        for root, dirs, files in os.walk(music_dir):
            if '.rockbox' in dirs:
                dirs.remove('.rockbox')

            cover_path = os.path.join(root, 'cover.jpg')
            if os.path.exists(cover_path) and os.path.getsize(cover_path) > 0:
                existing_covers += 1
            else:
                needs_extraction += 1

        # extract art only if needed
        if needs_extraction > 0:
            process_images(music_dir)
        else:
            print("All albums already have cover art, skipping extraction")

        clear_temp_directory()

        # copy art to local storage
        print(f"Copying album art to {album_art_storage}...")
        os.makedirs(album_art_storage, exist_ok=True)

        copied_count = 0
        for root, dirs, files in os.walk(music_dir):
            # skip .rockbox directory
            if '.rockbox' in dirs:
                dirs.remove('.rockbox')

            # look for cover.jpg files
            if 'cover.jpg' in files:
                cover_path = os.path.join(root, 'cover.jpg')

                # create destination
                album_folder = os.path.basename(root)
                dest_filename = f"{album_folder}_cover.jpg"
                dest_path = os.path.join(album_art_storage, dest_filename)

                # copy to local storage
                shutil.copy2(cover_path, dest_path)
                copied_count += 1

        print(f"Successfully copied {copied_count} album covers to {album_art_storage}")
        return True

    except Exception as e:
        print(f"Error processing album art: {e}")
        return False
    