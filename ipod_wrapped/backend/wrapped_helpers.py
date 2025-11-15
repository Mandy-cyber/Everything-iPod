import os
import re
import glob
import json
import subprocess
import shutil
import sqlite3
import math
from typing import Optional, List
from pymongo import MongoClient
from datetime import datetime

from .album_art_fixer import process_images, organize_music_files, clear_temp_directory


def ms_to_mmss(milliseconds: int) -> str:
    """Convert milliseconds to mm:ss format

    Args:
        milliseconds (int): Time in milliseconds

    Returns:
        str: Time in mm:ss format
    """
    if not milliseconds:
        return "0:00"

    total_seconds = milliseconds // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return f"{minutes}:{seconds:02d}"


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


def has_data(db_type: str, db_path: str) -> bool:
    """Check if database contains data

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to the database file (for local db)

    Returns:
        bool: True if database has song data, False otherwise
    """
    if db_type == 'local':
        # check if database exists
        if not os.path.exists(db_path):
            return False

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM songs')
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception:
            return False
    else:
        # check mongo database
        try:
            client = MongoClient(os.getenv('MONGODB_URI'))
            db = client.song_db
            song_collection = db.songs
            count = song_collection.count_documents({})
            return count > 0
        except Exception:
            return False


def fix_filenames_in_db(db_type: str = 'local', db_path: str = 'storage/ipod_wrapped.db') -> bool:
    """Fixes the album names saved in the mongo or local db to match
    the names found in the Music directory. This is because often the
    log file truncates or otherwise messes them up.

    Args:
        db_type (str): Either 'mongo' or 'local'
        db_path (str): Path to local SQLite db file

    Returns:
        bool: True if successful, False otherwise
    """
    # get music directory
    music_dir = find_music_directory()
    if not music_dir:
        print("Could not find Music directory on iPod")
        return False

    # get all album folders from Music directory
    actual_albums = {}  # {artist: {truncated_album: full_album}}

    for artist_dir in os.listdir(music_dir):
        artist_path = os.path.join(music_dir, artist_dir)
        if not os.path.isdir(artist_path) or artist_dir == '.rockbox':
            continue

        actual_albums[artist_dir] = {}

        for album_dir in os.listdir(artist_path):
            album_path = os.path.join(artist_path, album_dir)
            if not os.path.isdir(album_path):
                continue

            # store both full name and potential truncated versions
            actual_albums[artist_dir][album_dir] = album_dir

            # also store truncated version (first 40 chars) as key
            if len(album_dir) > 40:
                truncated = album_dir[:40]
                actual_albums[artist_dir][truncated] = album_dir

    # fix database entries
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs

        # get all unique album/artist pairs
        pipeline = [
            {'$group': {'_id': {'album': '$album', 'artist': '$artist'}}}
        ]

        updates = []
        for doc in song_collection.aggregate(pipeline):
            album = doc['_id']['album']
            artist = doc['_id']['artist']

            # check if this artist exists and if album needs fixing
            if artist in actual_albums:
                if album in actual_albums[artist]:
                    full_album = actual_albums[artist][album]

                    # only update if truncated
                    if full_album != album:
                        updates.append({
                            'filter': {'album': album, 'artist': artist},
                            'update': {'$set': {'album': full_album}}
                        })

        # perform updates
        if updates:
            from pymongo import UpdateMany
            for update in updates:
                song_collection.update_many(update['filter'], update['update'])
            print(f"Fixed {len(updates)} truncated album names in MongoDB")
        else:
            print("No truncated album names found in MongoDB")

    else:  
        # local sqlite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # get all unique album/artist pairs
        cursor.execute('SELECT DISTINCT album, artist FROM songs WHERE album IS NOT NULL AND artist IS NOT NULL')

        updates = []
        for row in cursor.fetchall():
            album, artist = row

            # check if this artist exists and if album needs fixing
            if artist in actual_albums:
                if album in actual_albums[artist]:
                    full_album = actual_albums[artist][album]

                    # only update if truncated
                    if full_album != album:
                        updates.append((full_album, album, artist))

        # perform updates
        if updates:
            cursor.executemany(
                'UPDATE songs SET album = ? WHERE album = ? AND artist = ?',
                updates
            )
            conn.commit()
            print(f"Fixed {len(updates)} truncated album names in local database")
        else:
            print("No truncated album names found in local database")

        conn.close()

    return True


def _get_max_last_updated(db_type: str, db_path: str) -> Optional[datetime]:
    """Get the most recent last_updated timestamp from the database

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file

    Returns:
        Optional[datetime]: Most recent update time or None if not available
    """
    if db_type == 'mongo':
        try:
            client = MongoClient(os.getenv('MONGODB_URI'))
            db = client.song_db
            song_collection = db.songs

            # find document with most recent last_updated
            result = song_collection.find_one(
                {'last_updated': {'$exists': True}},
                sort=[('last_updated', -1)]
            )
            if result and 'last_updated' in result:
                return result['last_updated']
        except Exception:
            pass
    else:
        # local sqlite
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT MAX(last_updated) FROM songs WHERE last_updated IS NOT NULL')
            result = cursor.fetchone()
            conn.close()

            if result and result[0]:
                return datetime.fromisoformat(result[0])
        except Exception:
            pass

    return None


def _get_album_art_last_processed(album_art_storage: str) -> Optional[datetime]:
    """Get the timestamp when album art was last processed

    Args:
        album_art_storage (str): Album art storage directory

    Returns:
        Optional[datetime]: Last processed time or None if never processed
    """
    cache_file = os.path.join(album_art_storage, '.last_processed')

    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, 'r') as f:
            timestamp_str = f.read().strip()
            return datetime.fromisoformat(timestamp_str)
    except Exception:
        return None


def _set_album_art_last_processed(album_art_storage: str):
    """Set the album art last processed timestamp to now

    Args:
        album_art_storage (str): Album art storage directory
    """
    cache_file = os.path.join(album_art_storage, '.last_processed')

    try:
        os.makedirs(album_art_storage, exist_ok=True)
        with open(cache_file, 'w') as f:
            f.write(datetime.now().isoformat())
    except Exception as e:
        print(f"Warning: could not update album art cache: {e}")


def _should_process_album_art(album_art_storage: str, db_type: str, db_path: str) -> bool:
    """Check if album art processing is needed based on db last_updated

    Args:
        album_art_storage (str): Album art storage directory
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file

    Returns:
        bool: True if processing is needed, False otherwise
    """
    # check when last processed
    last_processed = _get_album_art_last_processed(album_art_storage)
    if last_processed is None:
        return True

    # get most recent db update
    db_last_updated = _get_max_last_updated(db_type, db_path)
    if db_last_updated is None:
        return True

    return db_last_updated > last_processed


def fix_and_store_album_art(album_art_storage: str, db_type: str = 'local', db_path: str = 'storage/ipod_wrapped.db', force: bool = False) -> bool:
    """Generates a cover.jpg for each album, and copies them locally

    Args:
        album_art_storage (str): Where to store the generated album art
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        force (bool): Force reprocessing even if not needed

    Returns:
        bool: True if successful, false otherwise
    """
    # check if processing is needed
    if not force and not _should_process_album_art(album_art_storage, db_type, db_path):
        print("Album art is up to date, skipping processing")
        return True

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

        # update cache timestamp
        _set_album_art_last_processed(album_art_storage)

        return True

    except Exception as e:
        print(f"Error processing album art: {e}")
        return False
    
    
def grab_all_metadata(db_type: str, db_path: str, album_art_dir: str) -> List[dict]:
    """Grabs all metadata about all albums stored in the db

    Args:
        db_type (str): The type of db ('mongo' or 'local')
        db_path (str): The location of the db if 'local'
        album_art_dir (str): The directory where album art is stored

    Returns:
        List[dict]: Each dict contains:
            {
                'art_path': str,
                'album_name': str,
                'artist': str,
                'genres': str,
                'songs': [
                    {
                        'song': str,
                        'song_length': str,  # format: "mm:ss"
                        'total_elapsed': str,  # format: "mm:ss"
                        'total_plays': int
                    },
                    ...
                ]
            }
    """
    # check for bad params
    if db_type != 'mongo' and db_type != 'local':
        return []

    if db_type == 'local' and (not db_path or len(db_path) == 0):
        return []

    albums_dict = {}

    # load song data from mongo
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs

        # get all songs grouped by album
        all_songs = song_collection.find(
            {'album': {'$ne': None}, 'artist': {'$ne': None}},
            projection={'_id': 0, 'song': 1, 'album': 1, 'artist': 1, 'genres': 1,
                       'song_length_ms': 1, 'total_elapsed_ms': 1, 'total_plays': 1}
        )

        # build result
        for song_doc in all_songs:
            album_key = (song_doc['album'], song_doc['artist'])
            if album_key not in albums_dict:
                albums_dict[album_key] = {
                    'album_name': song_doc['album'],
                    'artist': song_doc['artist'],
                    'genres': song_doc.get('genres', ''),
                    'songs': []
                }

            albums_dict[album_key]['songs'].append({
                'song': song_doc.get('song', ''),
                'song_length': ms_to_mmss(song_doc.get('song_length_ms', 0) or 0),
                'total_elapsed': ms_to_mmss(song_doc.get('total_elapsed_ms', 0) or 0),
                'total_plays': song_doc.get('total_plays', 0) or 0
            })

    # load song data from local
    else:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                album,
                artist,
                song,
                genres,
                song_length_ms,
                total_elapsed_ms,
                total_plays
            FROM songs
            WHERE album IS NOT NULL AND artist IS NOT NULL
            ORDER BY album, artist
        ''')

        for row in cursor.fetchall():
            album_key = (row[0], row[1])
            if album_key not in albums_dict:
                albums_dict[album_key] = {
                    'album_name': row[0],
                    'artist': row[1],
                    'genres': row[3] or '',
                    'songs': []
                }

            albums_dict[album_key]['songs'].append({
                'song': row[2],
                'song_length': ms_to_mmss(row[4] or 0),
                'total_elapsed': ms_to_mmss(row[5] or 0),
                'total_plays': row[6] or 0
            })

        conn.close()

    # get album art files
    fix_and_store_album_art(album_art_dir, db_type, db_path)
    available_art = {}
    for filename in os.listdir(album_art_dir):
        if filename.endswith('_cover.jpg'):
            album_from_file = filename.replace('_cover.jpg', '')
            available_art[album_from_file] = os.path.join(album_art_dir, filename)

    # match metadata with album art
    results = []
    for album_key, album_data in albums_dict.items():
        album_name = album_data['album_name']
        album_artist = album_data['artist']
        art_path = None

        # try exact match first
        if album_name in available_art:
            art_path = available_art[album_name]
        else:
            # below logic straight from Claude real talk
            # try fuzzy match for truncated filenames or slight variations
            for file_album, file_art_path in available_art.items():
                # check if one is a prefix of the other (handles truncation)
                if file_album.startswith(album_name) or album_name.startswith(file_album):
                    art_path = file_art_path
                    break

                # check if only difference is version info like (Explicit) vs (Expanded Edition)
                # strip common version suffixes and compare
                album_base = re.sub(r' \((Explicit|Expanded Edition|Deluxe|Deluxe Version)\)$', '', album_name)
                file_base = re.sub(r' \((Explicit|Expanded Edition|Deluxe|Deluxe Version)\)$', '', file_album)

                if album_base == file_base and album_base != album_name:
                    art_path = file_art_path
                    break

        # only include albums that have matching art
        if art_path:
            results.append({
                'art_path': art_path,
                'album_name': album_name,
                'artist': album_artist,
                'genres': album_data['genres'],
                'songs': album_data['songs']
            })

    print(json.dumps(results, indent=4))
    return results
    
    