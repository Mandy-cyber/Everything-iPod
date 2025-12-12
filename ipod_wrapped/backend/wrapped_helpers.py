import os
import re
import glob
import json
import psutil
import shutil
import sqlite3
import platform
from pathlib import Path
from typing import Optional, List
from pymongo import MongoClient
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv

from .album_art_fixer import process_images, organize_music_files, clear_temp_directory
from .constants import DEFAULT_DB_PATH, DEFAULT_ALBUM_ART_DIR, SONG_EXTENSIONS

load_dotenv()

# TODO:
# - abstract some more :sob:
# - round up total_elapsed_ms sum

def extract_song_path(full_path: str) -> str:
    """Extract the path starting from /Music directory

    Args:
        full_path (str): The full file path from the log

    Returns:
        str: Path starting from /Music/. Empty string otherwise.
    """
    if "/Music/" in full_path:
        return "/Music/" + full_path.split("/Music/", 1)[1]
    return ""


def list_dir_song_paths(music_dir: str) -> List[str]:
    """Returns a list of song paths starting from the given music directory"""
    song_paths = []
    for root, _, files in os.walk(music_dir):
        for file in files:
            for ext in SONG_EXTENSIONS:
                if file.endswith(ext):
                    song_paths.append(os.path.join(root, file))
                    break
                
    return song_paths


def extract_metadata_from_path(file_path: str) -> Optional[dict]:
    """Extract song metadata from filesystem path

    Args:
        file_path (str): full path to the song file

    Returns:
        Optional[dict]: dict with song, artist, album, or None if invalid
    """
    try:
        # check if it's in the Music directory
        if "/Music/" not in file_path:
            return None

        path_sections = file_path.split('/Music/', 1)[1].split('/')

        # need Artist, Album, & Track 
        if len(path_sections) < 3:
            return None

        artist = path_sections[0].strip()
        album = path_sections[1].strip()
        track_filename = path_sections[2]

        # check for valid extension
        valid_ext = False
        song_name = track_filename
        for ext in SONG_EXTENSIONS:
            if track_filename.endswith(ext):
                valid_ext = True
                song_name = track_filename[:-len(ext)]
                break

        if not valid_ext:
            return None

        # handle separator patterns (e.g., "Artist - Song" or "Artist - Album - 01 Song")
        if ' - ' in song_name:
            parts = song_name.split(' - ')
            # if 3+ parts, assume "Artist - Album - Song" format
            if len(parts) >= 3:
                song_name = ' - '.join(parts[2:])
            else:
                song_name = parts[1]
        elif '-' in song_name:
            song_name = song_name.split('-', 1)[1]
        elif '_' in song_name:
            song_name = song_name.split('_', 1)[1]

        # remove track number prefix (e.g., "01. Song")
        parts = song_name.split('.', 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            song_name = parts[1]

        song_name = song_name.strip()

        # fix explicit label
        if '(Exp' in album:
            album = album.split(' (Exp')[0] + ' (Explicit)'
        if '(Exp' in song_name:
            song_name = song_name.split(' (Exp')[0] + ' (Explicit)'

        return {
            'song': song_name.strip(),
            'artist': artist,
            'album': album,
            'path': extract_song_path(file_path)
        }
    except Exception as e:
        print(f"Failed to extract metadata from {file_path}: {e}")
        return None

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


def find_rockbox_device() -> Optional[str]:
    """Find the mounted device with a .rockbox folder in it"""
    for partition in psutil.disk_partitions(all=False):
        # skip sys partitions on Windows
        if partition.device.startswith('C:\\') and platform.system() == "Windows":
            continue

        # found mount point
        mount_point = partition.mountpoint
        rockbox_path = Path(mount_point) / '.rockbox'
        
        try:
            # check if rockbox folder present
            if rockbox_path.exists() and rockbox_path.is_dir():
                print(f"Found Rockbox device at: {mount_point}")
                return mount_point
        except (PermissionError, OSError):
            # mount can't be accessed
            continue
    
    print("No Rockbox device found")
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


def fix_filenames_in_db(db_type: str = 'local', db_path: str = DEFAULT_DB_PATH) -> bool:
    """Fixes the album and song names saved in the mongo or local db to match
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

    # scan music directory for actual album and song names
    actual_albums = {}  # {artist: {truncated_album: full_album}}
    actual_songs = {}   # {(artist, album): {truncated_song: full_song}}

    for artist_dir in os.listdir(music_dir):
        artist_path = os.path.join(music_dir, artist_dir)
        if not os.path.isdir(artist_path) or artist_dir == '.rockbox':
            continue

        actual_albums[artist_dir] = {}

        for album_dir in os.listdir(artist_path):
            album_path = os.path.join(artist_path, album_dir)
            if not os.path.isdir(album_path):
                continue

            # store album name mappings
            actual_albums[artist_dir][album_dir] = album_dir
            if len(album_dir) > 40:
                truncated = album_dir[:40]
                actual_albums[artist_dir][truncated] = album_dir

            # scan songs in this album
            song_key = (artist_dir, album_dir)
            actual_songs[song_key] = {}

            for song_file in os.listdir(album_path):
                song_path = os.path.join(album_path, song_file)
                if not os.path.isfile(song_path):
                    continue

                # remove extension and track number to get song name
                song_name = song_file
                for ext in ['.mp3', '.flac', '.ogg', '.m4a', '.wav']:
                    if song_name.lower().endswith(ext):
                        song_name = song_name[:-len(ext)]
                        break

                # remove track number prefix (e.g., "01. " or "1 ")
                parts = song_name.split('.', 1)
                if len(parts) == 2 and parts[0].strip().isdigit():
                    song_name = parts[1].strip()

                # store song name mappings
                actual_songs[song_key][song_name] = song_name
                if len(song_name) > 40:
                    truncated_song = song_name[:40]
                    actual_songs[song_key][truncated_song] = song_name

    # fix database entries
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs

        album_updates = []
        song_updates = []

        # get all songs
        all_songs = song_collection.find({})

        for doc in all_songs:
            song = doc.get('song')
            album = doc.get('album')
            artist = doc.get('artist')

            if not all([song, album, artist]):
                continue

            update_fields = {}

            # check if album needs fixing
            if artist in actual_albums and album in actual_albums[artist]:
                full_album = actual_albums[artist][album]
                if full_album != album:
                    update_fields['album'] = full_album

            # check if song needs fixing (using original or fixed album)
            album_to_check = update_fields.get('album', album)
            song_key = (artist, album_to_check)
            if song_key in actual_songs and song in actual_songs[song_key]:
                full_song = actual_songs[song_key][song]
                if full_song != song:
                    update_fields['song'] = full_song

            # perform update if needed
            if update_fields:
                song_collection.update_one(
                    {'_id': doc['_id']},
                    {'$set': update_fields}
                )
                if 'album' in update_fields:
                    album_updates.append(update_fields['album'])
                if 'song' in update_fields:
                    song_updates.append(update_fields['song'])

        # print results
        if album_updates or song_updates:
            print(f"Fixed {len(album_updates)} album names and {len(song_updates)} song names in MongoDB")
        else:
            print("No truncated names found in MongoDB")

    else:
        # local sqlite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        album_updates = []
        song_updates = []

        # get all songs
        cursor.execute('SELECT song, artist, album FROM songs WHERE song IS NOT NULL AND artist IS NOT NULL')

        for row in cursor.fetchall():
            song, artist, album = row

            update_fields = {}
            where_clause = []
            params = []

            # check if album needs fixing
            if artist in actual_albums and album in actual_albums[artist]:
                full_album = actual_albums[artist][album]
                if full_album != album:
                    update_fields['album'] = full_album

            # check if song needs fixing (using original or fixed album)
            album_to_check = update_fields.get('album', album)
            song_key = (artist, album_to_check)
            if song_key in actual_songs and song in actual_songs[song_key]:
                full_song = actual_songs[song_key][song]
                if full_song != song:
                    update_fields['song'] = full_song

            # perform update if needed
            if update_fields:
                set_clause = ', '.join([f"{k} = ?" for k in update_fields.keys()])
                params = list(update_fields.values())

                # add where clause params
                params.extend([song, artist, album])

                cursor.execute(
                    f'UPDATE songs SET {set_clause} WHERE song = ? AND artist = ? AND album = ?',
                    params
                )

                if 'album' in update_fields:
                    album_updates.append(update_fields['album'])
                if 'song' in update_fields:
                    song_updates.append(update_fields['song'])

        conn.commit()
        conn.close()

        # print results
        if album_updates or song_updates:
            print(f"Fixed {len(album_updates)} album names and {len(song_updates)} song names in local database")
        else:
            print("No truncated names found in local database")

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


def find_album_art(album: str, album_art_storage: str = DEFAULT_ALBUM_ART_DIR) -> str:
    """Finds the art associated with the given album. Logic from Claude.

    Args:
        album (str): The album to search for
        album_art_storage (str): The location of album covers. Defaults to
        DEFAULT_ALBUM_ART_DIR

    Returns:
        str: The location of the album's specific cover art, or path to missing_album_cover.jpg if not found
    """
    # build available art dictionary
    available_art = {}
    for filename in os.listdir(album_art_storage):
        if filename.endswith('_cover.jpg'):
            album_from_file = filename.replace('_cover.jpg', '')
            available_art[album_from_file] = os.path.join(album_art_storage, filename)

    # try exact match first
    if album in available_art:
        return available_art[album]

    # try fuzzy match for truncated filenames or slight variations
    for file_album, file_art_path in available_art.items():
        # check if one is a prefix of the other (handles truncation)
        if file_album.startswith(album) or album.startswith(file_album):
            return file_art_path

        # check if only difference is version info like (Explicit) vs (Expanded Edition)
        # strip common version suffixes and compare
        album_base = re.sub(r' \((Explicit|Expanded Edition|Deluxe|Deluxe Version)\)$', '', album)
        file_base = re.sub(r' \((Explicit|Expanded Edition|Deluxe|Deluxe Version)\)$', '', file_album)

        if album_base == file_base and album_base != album:
            return file_art_path

    # no art found, return missing cover placeholder
    return os.path.join(album_art_storage, "missing_album_cover.jpg")


def fix_and_store_album_art(album_art_storage: str, db_type: str = 'local', db_path: str = DEFAULT_DB_PATH, force: bool = False) -> bool:
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
    
    
def grab_all_metadata(db_type: str, db_path: str, album_art_dir: str,
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      filters: Optional[dict] = None) -> List[dict]:
    """Grabs all metadata about all albums stored in the db

    Args:
        db_type (str): The type of db ('mongo' or 'local')
        db_path (str): The location of the db if 'local'
        album_art_dir (str): The directory where album art is stored
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        filters (Optional[dict]): Optional filters for the query. Supported keys:
            - 'album': Filter by specific album name
            - 'artist': Filter by specific artist name
            - 'genre': Filter by specific genre (case-insensitive, partial match)
            - 'song': Filter by specific song name

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
                        'song_length_ms': int,
                        'total_elapsed_ms': int,
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

    # fix truncated album names before fetching metadata
    fix_filenames_in_db(db_type=db_type, db_path=db_path)

    # process filters
    if filters is None:
        filters = {}

    albums_dict = {}
    songs_metadata = {}  # {(song, artist): {album, genres, song_length_ms}}

    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs
        plays_collection = db.plays

        # build song filter query
        song_filter = {'album': {'$ne': None}, 'artist': {'$ne': None}}
        if 'album' in filters and filters['album']:
            song_filter['album'] = filters['album']
        if 'artist' in filters and filters['artist']:
            song_filter['artist'] = filters['artist']
        if 'song' in filters and filters['song']:
            song_filter['song'] = filters['song']

        # get song metadata
        all_songs = song_collection.find(
            song_filter,
            projection={'_id': 0, 'song': 1, 'album': 1, 'artist': 1,
                       'genres': 1, 'song_length_ms': 1}
        )

        for song_doc in all_songs:
            # apply genre filter if specified
            if 'genre' in filters and filters['genre']:
                genres = song_doc.get('genres', '').lower()
                if filters['genre'].lower() not in genres:
                    continue

            song_key = (song_doc['song'], song_doc['artist'])
            songs_metadata[song_key] = {
                'album': song_doc['album'],
                'artist': song_doc['artist'],
                'genres': song_doc.get('genres', ''),
                'song_length_ms': song_doc.get('song_length_ms', 0) or 0
            }

        # build date filter for plays
        plays_filter = {}
        if start_date or end_date:
            plays_filter['timestamp'] = {}
            if start_date:
                plays_filter['timestamp']['$gte'] = start_date
            if end_date:
                plays_filter['timestamp']['$lte'] = end_date

        # aggregate play stats
        pipeline = [
            {'$match': plays_filter} if plays_filter else {'$match': {}},
            {'$group': {
                '_id': {'song': '$song', 'artist': '$artist'},
                'total_plays': {'$sum': 1},
                'total_elapsed_ms': {'$sum': '$elapsed_ms'}
            }}
        ]

        play_stats = list(plays_collection.aggregate(pipeline))

        # create play stats lookup dict
        play_stats_dict = {}
        for stat in play_stats:
            song_key = (stat['_id']['song'], stat['_id']['artist'])
            play_stats_dict[song_key] = {
                'total_plays': stat['total_plays'],
                'total_elapsed_ms': stat['total_elapsed_ms']
            }

        # combine metadata with play stats (even songs w/0 songs)
        for song_key, metadata in songs_metadata.items():
            song, artist = song_key
            album_key = (metadata['album'], artist)

            if album_key not in albums_dict:
                albums_dict[album_key] = {
                    'album_name': metadata['album'],
                    'artist': artist,
                    'genres': metadata['genres'],
                    'songs': []
                }

            # get play stats if they exist, otherwise use 0
            stats = play_stats_dict.get(song_key, {'total_plays': 0, 'total_elapsed_ms': 0})

            albums_dict[album_key]['songs'].append({
                'song': song,
                'song_length': ms_to_mmss(metadata['song_length_ms']),
                'total_elapsed': ms_to_mmss(stats['total_elapsed_ms']),
                'total_plays': stats['total_plays']
            })

    else:
        # local sqlite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # build SQL filter query
        conditions = ['album IS NOT NULL', 'artist IS NOT NULL']
        params = []
        if 'album' in filters and filters['album']:
            conditions.append('album = ?')
            params.append(filters['album'])
        if 'artist' in filters and filters['artist']:
            conditions.append('artist = ?')
            params.append(filters['artist'])
        if 'song' in filters and filters['song']:
            conditions.append('song = ?')
            params.append(filters['song'])

        where_clause = ' AND '.join(conditions)

        # get song metadata
        cursor.execute(f'''
            SELECT song, artist, album, genres, song_length_ms
            FROM songs
            WHERE {where_clause}
        ''', params)

        for row in cursor.fetchall():
            # apply genre filter if specified
            if 'genre' in filters and filters['genre']:
                genres = (row[3] or '').lower()
                if filters['genre'].lower() not in genres:
                    continue

            song_key = (row[0], row[1])
            songs_metadata[song_key] = {
                'album': row[2],
                'artist': row[1],
                'genres': row[3] or '',
                'song_length_ms': row[4] or 0
            }

        # build date filter for plays
        date_filter = ''
        params = []
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append('timestamp >= ?')
                params.append(start_date.isoformat())
            if end_date:
                conditions.append('timestamp <= ?')
                params.append(end_date.isoformat())
            date_filter = 'WHERE ' + ' AND '.join(conditions)

        # aggregate play stats from plays table
        query = f'''
            SELECT
                song,
                artist,
                COUNT(*) as total_plays,
                COALESCE(SUM(elapsed_ms), 0) as total_elapsed_ms
            FROM plays
            {date_filter}
            GROUP BY song, artist
        '''

        cursor.execute(query, params)

        play_stats_dict = {}
        for row in cursor.fetchall():
            song_key = (row[0], row[1])
            play_stats_dict[song_key] = {
                'total_plays': row[2],
                'total_elapsed_ms': row[3]
            }

        # iter through songs
        for song_key, metadata in songs_metadata.items():
            song, artist = song_key
            album_key = (metadata['album'], artist)

            if album_key not in albums_dict:
                # format metadata
                albums_dict[album_key] = {
                    'album_name': metadata['album'],
                    'artist': artist,
                    'genres': metadata['genres'],
                    'songs': []
                }

            stats = play_stats_dict.get(song_key, {'total_plays': 0, 'total_elapsed_ms': 0})

            # add metadata to songs
            albums_dict[album_key]['songs'].append({
                'song': song,
                'song_length': metadata['song_length_ms'],
                'total_elapsed': stats['total_elapsed_ms'],
                'total_plays': stats['total_plays']
            })

        conn.close()

    # get album art files
    fix_and_store_album_art(album_art_dir, db_type, db_path)

    # match metadata with album art
    results = []
    for album_key, album_data in albums_dict.items():
        # find album art
        album_name = album_data['album_name']
        album_artist = album_data['artist']
        art_path = find_album_art(album_name, album_art_dir)

        results.append({
            'art_path': art_path,
            'album_name': album_name,
            'artist': album_artist,
            'genres': album_data['genres'],
            'songs': album_data['songs']
        })

    return results
    

def create_genre_mappings(db_type: str, db_path: str, album_art_dir: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        filters: Optional[dict] = None) -> List[dict]:
    """Creates a mapping of genre to songs (using data in the given db).

    Args:
        db_type (str): The type of db ('mongo' or 'local')
        db_path (str): The location of the db if 'local'
        album_art_dir (str): The location of album covers
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        filters (Optional[dict]): Optional filters for the query. Supported keys:
            - 'album': Filter by specific album name
            - 'artist': Filter by specific artist name
            - 'genre': Filter by specific genre (case-insensitive, partial match)
            - 'song': Filter by specific song name

    Returns:
        List[dict]: [
            {
                "genre": str,
                "total_elapsed_ms": int,
                "total_plays": int,
                "songs": [
                    {
                        "song": str,
                        "artist": str,
                        "art_path": str,
                    }
                    ...
                ]
            },
            ...
        ]
    """
    # check for bad params
    if db_type != 'mongo' and db_type != 'local':
        return []

    if db_type == 'local' and (not db_path or len(db_path) == 0):
        return []

    # process filters
    if filters is None:
        filters = {}

    # setup
    mappings = []
    genres = set()
    songs_dict = {}

    # mongo search
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs
        plays_collection = db.plays

        # build song filter query
        song_filter = {'album': {'$ne': None}, 'artist': {'$ne': None}}
        if 'album' in filters and filters['album']:
            song_filter['album'] = filters['album']
        if 'artist' in filters and filters['artist']:
            song_filter['artist'] = filters['artist']
        if 'song' in filters and filters['song']:
            song_filter['song'] = filters['song']

        # get song album + genres
        all_songs = song_collection.find(
            song_filter,
            projection={'_id': 0, 'song': 1, 'artist': 1, 'album': 1, 'genres': 1}
        )

        for song_doc in all_songs:
            # apply genre filter if specified
            song_genres = song_doc.get('genres', '')
            if 'genre' in filters and filters['genre']:
                if filters['genre'].lower() not in song_genres.lower():
                    continue

            song_key = (song_doc['song'], song_doc['artist'])
            album_art = find_album_art(song_doc['album'], album_art_dir)
            songs_dict[song_key] = {
                'song': song_doc['song'],
                'artist': song_doc['artist'],
                'art_path': album_art,
                'total_elapsed_ms': 0,  # added later
                'total_plays': 0,       # added later
                'genres': song_genres
            }

            # parse out genres
            if song_genres:
                genres.update(song_genres.split(','))

        # build date filter for plays
        plays_filter = {}
        if start_date or end_date:
            plays_filter['timestamp'] = {}
            if start_date:
                plays_filter['timestamp']['$gte'] = start_date
            if end_date:
                plays_filter['timestamp']['$lte'] = end_date

        # aggregate play stats
        pipeline = [
            {'$match': plays_filter} if plays_filter else {'$match': {}},
            {'$group': {
                '_id': {'song': '$song', 'artist': '$artist'},
                'total_plays': {'$sum': 1},
                'total_elapsed_ms': {'$sum': '$elapsed_ms'}
            }}
        ]

        play_stats = list(plays_collection.aggregate(pipeline))

        # iter through songs
        for stat in play_stats:
            song = stat['_id']['song']
            artist = stat['_id']['artist']
            song_key = (song, artist)

            if song_key not in songs_dict:
                continue

            # finish adding info to songs
            songs_dict[song_key]['total_elapsed_ms'] = stat['total_elapsed_ms']
            songs_dict[song_key]['total_plays'] = stat['total_plays']

        # create temp genre dict
        temp_dict = {}
        for genre in genres:
            g = genre if len(genre) > 0 else "unknown"
            genre = g.lower()
            temp_dict[genre] = {
                "genre": genre,
                "total_elapsed_ms": 0,
                "total_plays": 0,
                "songs": []
            }

        # add songs
        for key, song_info in songs_dict.items():
            song, artist = key
            song_genres = song_info["genres"].split(",")
            elapsed = song_info["total_elapsed_ms"]
            plays = song_info["total_plays"]

            for g in song_genres:
                g_lower = g.strip().lower() if g.strip() else "unknown"
                if g_lower in temp_dict:
                    song_info_copy = {
                        'song': song_info['song'],
                        'artist': song_info['artist'],
                        'art_path': song_info['art_path']
                    }
                    temp_dict[g_lower]["songs"].append(song_info_copy)
                    temp_dict[g_lower]["total_elapsed_ms"] += elapsed
                    temp_dict[g_lower]["total_plays"] += plays

        # finalize mappings
        for val in temp_dict.values():
            mappings.append(val)

        return mappings
    else:
        # local sqlite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # build SQL filter query
        conditions = ['album IS NOT NULL', 'artist IS NOT NULL']
        params = []
        if 'album' in filters and filters['album']:
            conditions.append('album = ?')
            params.append(filters['album'])
        if 'artist' in filters and filters['artist']:
            conditions.append('artist = ?')
            params.append(filters['artist'])
        if 'song' in filters and filters['song']:
            conditions.append('song = ?')
            params.append(filters['song'])

        where_clause = ' AND '.join(conditions)

        # get song album + genres
        cursor.execute(f'''
            SELECT song, artist, album, genres
            FROM songs
            WHERE {where_clause}
        ''', params)
        
        for row in cursor.fetchall():
            # apply genre filter if specified
            song_genres = row[3] or ''
            if 'genre' in filters and filters['genre']:
                if filters['genre'].lower() not in song_genres.lower():
                    continue

            # store song info for later
            song_key = (row[0], row[1])
            album_art = find_album_art(row[2], album_art_dir)
            songs_dict[song_key] = {
                'song': row[0],
                'artist': row[1],
                'art_path': album_art,
                'total_elapsed_ms': 0,  # added later
                'total_plays': 0,       # added later
                'genres': song_genres
            }

            # parse out genres
            if song_genres:
                genres.update(song_genres.split(","))
            
        # build date filters for plays
        date_filter = ''
        params = []
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append('timestamp >= ?')
                params.append(start_date.isoformat())
            if end_date:
                conditions.append('timestamp <= ?')
                params.append(end_date.isoformat())
            date_filter = 'WHERE ' + ' AND '.join(conditions)

        # aggregate play stats from plays table
        query = f'''
            SELECT
                song,
                artist,
                COUNT(*) as total_plays,
                SUM(elapsed_ms) as total_elapsed_ms
            FROM plays
            {date_filter}
            GROUP BY song, artist
        '''
        cursor.execute(query, params)
        
        # iter through songs
        for row in cursor.fetchall():
            song = row[0]
            artist = row[1]
            song_key = (song, artist)
            
            if song_key not in songs_dict:
                continue
            
            # finish adding info to songs
            songs_dict[song_key]['total_elapsed_ms'] = row[3]
            songs_dict[song_key]['total_plays'] = row[2]
            
        conn.close()
        
        # create temp genre dict
        temp_dict = dict()
        for genre in genres:
            g = genre if len(genre) > 0 else "unknown"
            genre = g.lower()
            temp_dict[genre] = {
                "genre": genre,
                "total_elapsed_ms": 0,
                "total_plays": 0,
                "songs": []
            }
            
        # add songs
        for key, song_info in songs_dict.items():
            song, artist = key
            song_genres = song_info["genres"].split(",")
            elapsed = song_info["total_elapsed_ms"]
            plays = song_info["total_plays"]

            for g in song_genres:
                g_lower = g.strip().lower() if g.strip() else "unknown"
                if g_lower in temp_dict:
                    song_info_copy = {
                        'song': song_info['song'],
                        'artist': song_info['artist'],
                        'art_path': song_info['art_path']
                    }
                    temp_dict[g_lower]["songs"].append(song_info_copy)
                    temp_dict[g_lower]["total_elapsed_ms"] += elapsed
                    temp_dict[g_lower]["total_plays"] += plays
            

        # finalize mappings
        for val in temp_dict.values():
            mappings.append(val)

        return mappings
    
    
def grab_all_songs(db_type: str, db_path: str, album_art_dir: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        filters: Optional[dict] = None) -> List[dict]:
    """Grabs all songs, and relevant metadata, from the given db.

    Args:
        db_type (str): The type of db ('mongo' or 'local')
        db_path (str): The location of the db if 'local'
        album_art_dir (str): The location of album covers
        start_date (Optional[datetime]): Filter songs from this date onwards
        end_date (Optional[datetime]): Filter songs up to this date
        filters (Optional[dict]): Optional filters for the query. Supported keys:
            - 'album': Filter by specific album name
            - 'artist': Filter by specific artist name
            - 'genre': Filter by specific genre (case-insensitive, partial match)
            - 'song': Filter by specific song name

    Returns:
        List[dict]: [
            {
                "title": str,
                "artist": str,
                "album": str,
                "duration": int,
                "metadata": {
                    "genres": str,
                    "art_path": str,
                    "total_elapsed_ms": int,
                    "total_plays": int,
                }
            },
            ...
        ]
    """
    # check for bad params
    if db_type != 'mongo' and db_type != 'local':
        return []

    if db_type == 'local' and (not db_path or len(db_path) == 0):
        return []

    # process filters
    if filters is None:
        filters = {}

    # setup
    all_songs = []
    songs_dict = {}

    # mongo search
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs
        plays_collection = db.plays

        # build song filter query
        song_filter = {'song': {'$ne': None}, 'artist': {'$ne': None}}
        if 'album' in filters and filters['album']:
            song_filter['album'] = filters['album']
        if 'artist' in filters and filters['artist']:
            song_filter['artist'] = filters['artist']
        if 'song' in filters and filters['song']:
            song_filter['song'] = filters['song']

        # get song metadata
        all_songs_cursor = song_collection.find(
            song_filter,
            projection={'_id': 0, 'song': 1, 'artist': 1, 'album': 1, 'genres': 1, 'song_length_ms': 1}
        )

        for song_doc in all_songs_cursor:
            # apply genre filter if specified
            song_genres = song_doc.get('genres', '')
            if 'genre' in filters and filters['genre']:
                if filters['genre'].lower() not in song_genres.lower():
                    continue

            song_key = (song_doc['song'], song_doc['artist'])
            album_art = find_album_art(song_doc['album'], album_art_dir)
            songs_dict[song_key] = {
                'title': song_doc['song'],
                'artist': song_doc['artist'],
                'album': song_doc['album'],
                'duration': song_doc.get('song_length_ms', 0) or 0,
                'metadata': {
                    'genres': song_genres,
                    'art_path': album_art,
                    'total_elapsed_ms': 0,  # added later
                    'total_plays': 0,       # added later
                }
            }

        # build date filter for plays
        plays_filter = {}
        if start_date or end_date:
            plays_filter['timestamp'] = {}
            if start_date:
                plays_filter['timestamp']['$gte'] = start_date
            if end_date:
                plays_filter['timestamp']['$lte'] = end_date

        # aggregate play stats
        pipeline = [
            {'$match': plays_filter} if plays_filter else {'$match': {}},
            {'$group': {
                '_id': {'song': '$song', 'artist': '$artist'},
                'total_plays': {'$sum': 1},
                'total_elapsed_ms': {'$sum': '$elapsed_ms'}
            }}
        ]

        play_stats = list(plays_collection.aggregate(pipeline))

        # update songs with play stats
        for stat in play_stats:
            song = stat['_id']['song']
            artist = stat['_id']['artist']
            song_key = (song, artist)

            if song_key not in songs_dict:
                continue

            songs_dict[song_key]['metadata']['total_elapsed_ms'] = stat['total_elapsed_ms']
            songs_dict[song_key]['metadata']['total_plays'] = stat['total_plays']

        # finish up
        for val in songs_dict.values():
            all_songs.append(val)

        return all_songs
    else:
        # local sqlite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # build SQL filter query
        conditions = ['song IS NOT NULL', 'artist IS NOT NULL']
        params = []
        if 'album' in filters and filters['album']:
            conditions.append('album = ?')
            params.append(filters['album'])
        if 'artist' in filters and filters['artist']:
            conditions.append('artist = ?')
            params.append(filters['artist'])
        if 'song' in filters and filters['song']:
            conditions.append('song = ?')
            params.append(filters['song'])

        where_clause = ' AND '.join(conditions)

        # get most info
        cursor.execute(f'''
            SELECT song, artist, album, genres, song_length_ms
            FROM songs
            WHERE {where_clause}
        ''', params)
        
        for row in cursor.fetchall():
            # apply genre filter if specified
            song_genres = row[3] or ''
            if 'genre' in filters and filters['genre']:
                if filters['genre'].lower() not in song_genres.lower():
                    continue

            # store for later
            song_key = (row[0], row[1])
            album_art = find_album_art(row[2], album_art_dir)
            songs_dict[song_key] = {
                'title': row[0],
                'artist': row[1],
                'album': row[2],
                'duration': row[4],
                'metadata': {
                    'genres': song_genres,
                    'art_path': album_art,
                    'total_elapsed_ms': 0,  # added later
                    'total_plays': 0,       # added later
                }
            }
            
        # build date filters for plays
        date_filter = ''
        params = []
        if start_date or end_date:
            conditions = []
            if start_date:
                conditions.append('timestamp >= ?')
                params.append(start_date.isoformat())
            if end_date:
                conditions.append('timestamp <= ?')
                params.append(end_date.isoformat())
            date_filter = 'WHERE ' + ' AND '.join(conditions)

        # aggregate play stats from plays table
        query = f'''
            SELECT
                song,
                artist,
                COUNT(*) as total_plays,
                SUM(elapsed_ms) as total_elapsed_ms
            FROM plays
            {date_filter}
            GROUP BY song, artist
        '''
        cursor.execute(query, params)
        
        # iter through songs
        for row in cursor.fetchall():
            song = row[0]
            artist = row[1]
            song_key = (song, artist)
            
            if song_key not in songs_dict:
                continue
            
            # finish adding info to songs
            songs_dict[song_key]['metadata']['total_elapsed_ms'] = row[3]
            songs_dict[song_key]['metadata']['total_plays'] = row[2]

        conn.close()
        
        # finish up
        for val in songs_dict.values():
            all_songs.append(val)
        
        # print(json.dumps(all_songs, indent=4))
        return all_songs


def load_stats_from_db(db_type: str, db_path: str,
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None) -> List[dict]:
    """Loads song statistics aggregated from plays table

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date

    Returns:
        List[dict]: List of dicts with keys: song, artist, album, genres, total_plays,
                   song_length_ms, total_elapsed_ms
    """
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs
        plays_collection = db.plays

        # build date filter for plays
        plays_filter = {}
        if start_date or end_date:
            plays_filter['timestamp'] = {}
            if start_date:
                plays_filter['timestamp']['$gte'] = start_date
            if end_date:
                plays_filter['timestamp']['$lte'] = end_date

        # aggregate from plays collection
        pipeline = [
            {'$match': plays_filter} if plays_filter else {'$match': {}},
            {'$group': {
                '_id': {'song': '$song', 'artist': '$artist'},
                'total_plays': {'$sum': 1},
                'total_elapsed_ms': {'$sum': '$elapsed_ms'}
            }}
        ]
        play_stats = list(plays_collection.aggregate(pipeline))

        # get song metadata
        all_songs = list(song_collection.find({}, projection={'_id': 0}))
        songs_metadata = {(s['song'], s['artist']): s for s in all_songs}

        # combine stats with metadata (even songs w/0 plays)
        all_docs = []
        for stat in play_stats:
            song_key = (stat['_id']['song'], stat['_id']['artist'])
            if song_key in songs_metadata:
                metadata = songs_metadata[song_key]
                all_docs.append({
                    'song': stat['_id']['song'],
                    'artist': stat['_id']['artist'],
                    'album': metadata.get('album', ''),
                    'genres': metadata.get('genres', ''),
                    'total_plays': stat['total_plays'],
                    'song_length_ms': metadata.get('song_length_ms', 0) or 0,
                    'total_elapsed_ms': stat['total_elapsed_ms']
                })
    else:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # build date filter for plays
        date_conditions = []
        params = []
        if start_date:
            date_conditions.append('p.timestamp >= ?')
            params.append(start_date.isoformat())
        if end_date:
            date_conditions.append('p.timestamp <= ?')
            params.append(end_date.isoformat())

        date_filter = ''
        if date_conditions:
            date_filter = ' AND ' + ' AND '.join(date_conditions)

        # aggregate from plays table
        query = f'''
            SELECT
                s.song,
                s.artist,
                s.album,
                s.genres,
                COUNT(p.id) as total_plays,
                s.song_length_ms,
                COALESCE(SUM(p.elapsed_ms), 0) as total_elapsed_ms
            FROM songs s
            LEFT JOIN plays p ON s.song = p.song AND s.artist = p.artist{date_filter}
            GROUP BY s.song, s.artist
        '''
        cursor.execute(query, params)
        rows = cursor.fetchall()
        all_docs = [
            {
                'song': row[0],
                'artist': row[1],
                'album': row[2] or '',
                'genres': row[3] or '',
                'total_plays': row[4] or 0,
                'song_length_ms': row[5] or 0,
                'total_elapsed_ms': row[6] or 0
            }
            for row in rows
        ]
        conn.close()

    return all_docs


def find_top_genres(db_type: str, db_path: str, n: int = 3,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   stats_data: Optional[List[dict]] = None) -> List[dict]:
    """Finds the top n genres listened to based on total_elapsed_ms stats.

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        n (int): The number of top genres to show. Defaults to 3.
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        stats_data (Optional[List[dict]]): Pre-loaded stats data. If not provided,
                                          will load from database.

    Returns:
        List[dict]: [
            {
                'genre': str,
                'total_elapsed_mins': int
                'album_art': str,
            },
            ...
        ]
    """
    stats = stats_data if stats_data is not None else load_stats_from_db(db_type, db_path, start_date, end_date)

    if not stats:
        return []

    # aggregate by genre
    genre_stats = defaultdict(list)
    for song in stats:
        genres_str = song.get('genres', '')
        if not genres_str:
            continue

        elapsed = song.get('total_elapsed_ms', 0)
        album_art = find_album_art(song.get('album', ''))
        for genre in genres_str.split(','):
            genre = genre.strip()
            if genre:
                if genre not in genre_stats:
                    # add elapsed time
                    genre_stats[genre] = [0]
                genre_stats[genre][0] += elapsed
                
                if len(genre_stats[genre]) == 2:
                    continue
                # add album art
                genre_stats[genre].append(album_art)

    # sort and get top n
    sorted_genres = sorted(genre_stats.items(), key=lambda x: x[1], reverse=True)[:n]
    
    # build dict
    return [{'genre': genre, 'total_elapsed_mins': metadata[0] // 60000, 'album_art': metadata[1]} for genre, metadata in sorted_genres]


def find_top_artists(db_type: str, db_path: str, n: int = 3,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None,
                    stats_data: Optional[List[dict]] = None) -> List[dict]:
    """Finds the top n artists listened to based on total_elapsed_ms stats.

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        n (int): The number of top artists to show. Defaults to 3.
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        stats_data (Optional[List[dict]]): Pre-loaded stats data. If not provided,
                                          will load from database.

    Returns:
        List[dict]: [
            {
                'artist': str,
                'total_elapsed_mins': int
                'album_art': str,
            },
            ...
        ]
    """
    stats = stats_data if stats_data is not None else load_stats_from_db(db_type, db_path, start_date, end_date)

    if not stats:
        return []

    # aggregate by artist
    artist_stats = defaultdict(list)
    for song in stats:
        artist = song.get('artist', '')
        if not artist:
            continue

        elapsed = song.get('total_elapsed_ms', 0)
        album_art = find_album_art(song.get('album', ''))
        if artist not in artist_stats:
            # add elapsed time
            artist_stats[artist] = [0]
        artist_stats[artist][0] += elapsed
        
        if len(artist_stats[artist]) == 2:
            continue
        # add album art
        artist_stats[artist].append(album_art)

    # sort and get top n
    sorted_artists = sorted(artist_stats.items(), key=lambda x: x[1], reverse=True)[:n]

    return [{'artist': artist, 'total_elapsed_mins': metadata[0] // 60000, 'album_art': metadata[1]} for artist, metadata in sorted_artists]


def find_top_albums(db_type: str, db_path: str, n: int = 3,
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   stats_data: Optional[List[dict]] = None) -> List[dict]:
    """Finds the top n albums listened to based on total_elapsed_ms stats.

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        n (int): The number of top albums to show. Defaults to 3.
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        stats_data (Optional[List[dict]]): Pre-loaded stats data. If not provided,
                                          will load from database.

    Returns:
        List[dict]: [
            {
                'album': str,
                'artist': str,
                'total_elapsed_mins': int
                'album_art': str,
            },
            ...
        ]
    """
    stats = stats_data if stats_data is not None else load_stats_from_db(db_type, db_path, start_date, end_date)

    if not stats:
        return []

    # aggregate by album and artist
    album_stats = defaultdict(list)
    for song in stats:
        album = song.get('album', '')
        artist = song.get('artist', '')
        album_art = find_album_art(song.get('album', ''))
        if not album or not artist:
            continue

        elapsed = song.get('total_elapsed_ms', 0)
        album_key = (album, artist)
        if album_key not in album_stats:
            # add elapsed time
            album_stats[album_key] = [0]
        album_stats[album_key][0] += elapsed
        
        if len(album_stats[album_key]) == 2:
            continue
        # add album art
        album_stats[album_key].append(album_art)

    # sort and get top n
    sorted_albums = sorted(album_stats.items(), key=lambda x: x[1], reverse=True)[:n]

    return [{'album': album, 'artist': artist, 'total_elapsed_mins': metadata[0] // 60000, 'album_art': metadata[1]}
            for (album, artist), metadata in sorted_albums]


def find_top_songs(db_type: str, db_path: str, n: int = 3,
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None,
                  stats_data: Optional[List[dict]] = None) -> List[dict]:
    """Finds the top n songs listened to based on total_plays stats.

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        n (int): The number of top songs to show. Defaults to 3.
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        stats_data (Optional[List[dict]]): Pre-loaded stats data. If not provided,
                                          will load from database.

    Returns:
        List[dict]: [
            {
                'song': str,
                'artist': str,
                'total_plays': int,
                'album_art': str,
            },
            ...
        ]
    """
    stats = stats_data if stats_data is not None else load_stats_from_db(db_type, db_path, start_date, end_date)

    if not stats:
        return []

    # sort by total_plays and get top n
    sorted_songs = sorted(stats, key=lambda x: x.get('total_plays', 0), reverse=True)[:n]
    for song_obj in sorted_songs:
        album_art = find_album_art(song_obj['album'])
        song_obj['album_art'] = album_art

    return [{'song': song['song'], 'artist': song['artist'], 'total_plays': song['total_plays'], 'album_art': song['album_art']}
            for song in sorted_songs]


def get_total_listening_time(db_type: str, db_path: str,
                             start_date: Optional[datetime] = None,
                             end_date: Optional[datetime] = None,
                             stats_data: Optional[List[dict]] = None) -> int:
    """Calculates total listening time in minutes.

    Args:
        db_type (str): Type of database ('mongo' or 'local')
        db_path (str): Path to local db file
        start_date (Optional[datetime]): Filter plays from this date onwards
        end_date (Optional[datetime]): Filter plays up to this date
        stats_data (Optional[List[dict]]): Pre-loaded stats data. If not provided,
                                          will load from database.

    Returns:
        int: Total listening time in minutes
    """
    stats = stats_data if stats_data is not None else load_stats_from_db(db_type, db_path, start_date, end_date)

    if not stats:
        return 0

    # sum all total_elapsed_ms
    total_ms = sum(song.get('total_elapsed_ms', 0) for song in stats)

    return total_ms // 60000
