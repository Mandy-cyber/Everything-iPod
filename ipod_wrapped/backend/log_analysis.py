import os
import re
import glob
import json
import shutil
import sqlite3
import polars as pl
from dotenv import load_dotenv
import requests
from time import sleep
from pymongo import MongoClient, UpdateOne
from typing import Optional, List
from datetime import datetime

from .constants import *
from .constants import DEFAULT_DB_PATH
from .creds_manager import get_credentials
from .wrapped_helpers import (
    find_ipod, fix_filenames_in_db, extract_song_path,
    find_top_genres, find_top_artists, find_top_albums, find_top_songs,
    list_dir_song_paths, extract_metadata_from_path, find_music_directory
)
from .schema import (
    SQLITE_SONGS_TABLE, SQLITE_PLAYS_TABLE,
    SQLITE_PLAYS_TIMESTAMP_INDEX, SQLITE_PLAYS_SONG_ARTIST_INDEX,
    MONGO_SONGS_COLLECTION, MONGO_PLAYS_COLLECTION, MONGO_PLAYS_INDEXES
)

load_dotenv()

# TODO:
# - display albums missing genre info

class LogAnalyser:

    def __init__(self, db_type: str = 'mongo', db_path: str = DEFAULT_DB_PATH):
        """Initialize LogAnalyser with chosen database type

        Args:
            db_type (str): Either 'mongo' or 'local'. Defaults to 'mongo'.
            db_path (str): Path to local SQLite db file. Defaults to DEFAULT_DB_PATH.
        """
        self.db_type = db_type
        self.db_path = db_path

        # setup database connection
        if self.db_type == 'mongo':
            self._setup_mongo()
        else:
            self._setup_local_db()

        self.failed_albums = dict()
        self.batch_entries = []
        self.genre_data = dict()
        self.seen_songs = set()

        # load existing data from db
        raw_data = self._fetch_all_songs()
        for entry in raw_data:
            self.genre_data[f"{entry['album']}:{entry['artist']}"] = entry['genres']
            self.seen_songs.add(f"{entry['song']}:{entry['artist']}")

        # setup lastfm
        creds = get_credentials()
        if not creds or not creds.get('last_fm'):
            raise ValueError('Last.fm credentials are missing. Add them in Settings or in your local .env file')

        self.api_key = creds['last_fm'].get('api_key')
        self.shared_secret = creds['last_fm'].get('shared_secret')

        if not self.api_key or not self.shared_secret:
            raise ValueError('Last.fm API credentials not configured. Please add them in Settings.')


    def _setup_mongo(self):
        """Setup MongoDB connection"""
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        self.song_collection = db[MONGO_SONGS_COLLECTION]
        self.plays_collection = db[MONGO_PLAYS_COLLECTION]

        # create indexes on plays collection
        self.plays_collection.create_index(MONGO_PLAYS_INDEXES[0])
        self.plays_collection.create_index(MONGO_PLAYS_INDEXES[1])


    def _setup_local_db(self):
        """Setup SQLite local database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # create tables and indexes from schema
        self.cursor.execute(SQLITE_SONGS_TABLE)
        self.cursor.execute(SQLITE_PLAYS_TABLE)
        self.cursor.execute(SQLITE_PLAYS_TIMESTAMP_INDEX)
        self.cursor.execute(SQLITE_PLAYS_SONG_ARTIST_INDEX)

        self.conn.commit()


    def _fetch_all_songs(self) -> list:
        """Fetch all songs from database (abstracted for both db types)"""
        if self.db_type == 'mongo':
            return list(self.song_collection.find({}, projection={
                '_id': 0, 'album': 1, 'artist': 1, 'song': 1, 'genres': 1
            }))
        else:
            self.cursor.execute('SELECT song, artist, album, genres FROM songs')
            rows = self.cursor.fetchall()
            return [{'song': row[0], 'artist': row[1], 'album': row[2], 'genres': row[3]}
                    for row in rows]
    
    
    @staticmethod
    def find_playback_log() -> Optional[str]:
        """Finds the location of the playback log on the iPod

        Returns:
            str: The location of the log file
        """
        # find ipod
        ipod_location = find_ipod()
        if not ipod_location:
            return None
        
        # look for `playback.log`
        full_pattern = os.path.join(f"{ipod_location}/.rockbox", '**', "playback.log")
        found_files = glob.glob(full_pattern, recursive=True)
        if not found_files or len(found_files) == 0:
            return None
        return found_files[0]
        
        
    @staticmethod
    def load_logs(file_loc: str) -> list:
        """Loads the logs from the given file location

        Args:
            file_loc (str): the location of the log file

        Returns:
            list: a list of each line in the log file
        """
        log_lines = []
        with open(file_loc, 'r', encoding='utf-8', errors='ignore') as file:
            for line in file:
                try:
                    if not line.startswith('#'):
                        log_lines.append(line)
                except:
                    continue
        return log_lines
    

    def is_valid_track_filename(self, filename: str) -> bool:
        """Checks if the filename has a valid audio extension

        Args:
            filename (str): the filename to check

        Returns:
            bool: True if valid, False otherwise
        """
        return any(filename.endswith(ext) for ext in SONG_EXTENSIONS)


    def is_corrupted_metadata(self, text: str) -> bool:
        """Checks if text looks like corrupted log data

        Args:
            text (str): the text to check

        Returns:
            bool: True if corrupted, False otherwise
        """
        return ':' in text or text.isdigit() or len(text) == 0


    def extract_song_from_filename(self, track_filename: str) -> str:
        """Extracts song title from track filename

        Args:
            track_filename (str): the full track filename

        Returns:
            str: the extracted song title
        """
        if ' - ' in track_filename:
            # (e.g., "Artist - Song" or "Artist - Album - 01 Song")
            parts = track_filename.split(' - ')
            if len(parts) >= 3:
                # assume "Artist - Album - Song" format
                song = self.clean_song(' - '.join(parts[2:]))
            else:
                song = self.clean_song(parts[1])
        elif '-' in track_filename:
            song = self.clean_song(track_filename.split('-', 1)[1])
        elif '_' in track_filename:
            song = self.clean_song(track_filename.split('_', 1)[1])
        else:
            # no separator, use whole filename
            song = self.clean_song(track_filename)
        return song


    def parse_track_info(self, path: str) -> tuple:
        """Parses track info from the given path.

        Args:
            path (str): a path in the iPod log

        Returns:
            tuple: (album, artist, song) found from the path
        """
        path_sections = path.split('/')[1:]

        # find the "Music" directory index
        music_idx = -1
        for i in range(len(path_sections) - 1, -1, -1):
            if path_sections[i] == 'Music':
                music_idx = i
                break

        # if we found "Music", adjust indexing
        if music_idx >= 0:
            adjusted_sections = path_sections[music_idx + 1:]

            # need at least Artist/Album/Track
            if len(adjusted_sections) < 3:
                raise ValueError(f"Not enough sections after Music: {path}")

            artist = adjusted_sections[0].strip()
            album = self.fix_explicit_label(adjusted_sections[1].strip())
            track_filename = adjusted_sections[2]

            # check track extension
            if not self.is_valid_track_filename(track_filename):
                raise ValueError(f"Track filename missing valid extension: {track_filename}")

            # check artist/album corruption
            if self.is_corrupted_metadata(artist):
                raise ValueError(f"Artist looks corrupted: {artist}")

            song = self.extract_song_from_filename(track_filename)

            # ensure song title is valid
            if not song or song.lower() in ['flac', 'mp3', 'ogg', 'wav', 'm4a']:
                raise ValueError(f"Invalid song title: {song}")

            return album, artist, song

        # fallback to original logic if no Music directory found
        if len(path_sections) < 5:
            raise ValueError(f"Path doesn't have enough sections: {path}")

        artist = path_sections[2].strip()
        album = self.fix_explicit_label(path_sections[3].strip())
        song = self.clean_song(path_sections[4].split('-')[1])
        return album, artist, song
    

    def fix_explicit_label(self, file: str) -> str:
        """Removes the 'Explicit' tag and re-adds it neatly to the
        given string. This is because sometimes (often) the rockbox
        log cuts it off...
        
        EDIT: nevermind, i just had bad file names LOL. Keeping here
        just in case others have this problem though

        Args:
            file (str): the file name to be fixed

        Returns:
            str: the fixed string
        """
        if '(Exp' in file:
            new_name = file.split(' (Exp')[0]
            file = f"{new_name} (Explicit)"
        return file


    def clean_song(self, song: str) -> str:
        """Attempts to properly format the song title, removing
        unnecessary info

        Args:
            song (str): the song name to clean

        Returns:
            str: the 'cleaned' song name
        """
        # remove file extension first
        song_wout_ext = song
        for ext in SONG_EXTENSIONS:
            if song.endswith(ext):
                song_wout_ext = song[:-len(ext)]
                break

        # remove track number prefix (e.g., "01. " or "1 ")
        parts = song_wout_ext.split('.', 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            song_wout_ext = parts[1]

        return self.fix_explicit_label(song_wout_ext.strip())


    def logs_to_df(self) -> pl.DataFrame:
        """Creates a dataframe of all info found in the iPod
        log file

        Returns:
            pl.DataFrame: A dataframe of the iPod log data
        """
        entries = []
        failed = []

        for log_entry in self.log_data:
            match = re.match(IPOD_LOG_PATTERN, log_entry.strip())
            if match:
                try:
                    album, artist, song = self.parse_track_info(str(match.group(4)))

                    # find genre info based on album
                    album_key = f"{album}:{artist}"
                    if album_key in self.genre_data:
                        genres = self.genre_data[album_key]
                    else:
                        genres = self.find_album_genres((artist, album))
                        self.genre_data[album_key] = genres

                    # extract data from log entry
                    timestamp = int(match.group(1))
                    elapsed_ms = int(match.group(2))
                    length_ms = int(match.group(3))

                    # add song to database if not already seen
                    song_key = f"{song}:{artist}"
                    if song_key not in self.seen_songs:
                        # extract path
                        song_path = extract_song_path(str(match.group(4)))

                        self.batch_add_to_db({
                            "song": song,
                            "album": album,
                            "artist": artist,
                            "genres": genres,
                            "song_length_ms": length_ms,
                            "path": song_path
                        })
                        self.seen_songs.add(song_key)

                    # create full entry for play events
                    entries.append({
                        'timestamp': timestamp,
                        'elapsed_ms': elapsed_ms,
                        'length_ms': length_ms,
                        'file_path': str(match.group(4)),
                        'album': album,
                        'genres': genres,
                        'artist': artist,
                        'song': song
                    })
                except Exception as e:
                    failed.append(log_entry)
                    print(log_entry, e)

        df = pl.DataFrame(entries)
        if len(failed) > 0:
            print(f"Failed to parse {len(failed)} entries")

        return df
    
    
    def batch_add_to_db(self, entry: dict, final_add: bool = False) -> bool:
        """Adds song metadata to the songs table/collection"""
        if entry and entry != {}:
            self.batch_entries.append(entry)

        if len(self.batch_entries) == BATCH_SIZE or final_add:
            try:
                if self.db_type == 'mongo':
                    # add last_updated timestamp to each entry
                    now = datetime.now()
                    for entry in self.batch_entries:
                        entry['last_updated'] = now
                    result = self.song_collection.insert_many(self.batch_entries)
                    print(f"Inserted {len(result.inserted_ids)} songs to MongoDB")
                else:
                    # sqlite batch insert
                    now = datetime.now().isoformat()
                    self.cursor.executemany('''
                        INSERT OR IGNORE INTO songs (song, artist, album, genres, song_length_ms, path, last_updated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', [(e['song'], e['artist'], e['album'], e.get('genres', ''),
                           e.get('song_length_ms'), e.get('path', ''), now)
                          for e in self.batch_entries])
                    self.conn.commit()
                    print(f"Inserted {self.cursor.rowcount} songs to SQLite")

                self.batch_entries.clear()
            except Exception as e:
                print(f"Failed to batch add song metadata: {e}")
                return False
            
        return True


    def add_plays_from_dataframe(self, df: pl.DataFrame):
        """Insert individual play events from the log dataframe into plays table/collection

        Args:
            df (pl.DataFrame): Dataframe containing parsed log entries with columns:
                              timestamp, elapsed_ms, song, artist
        """
        if df.is_empty():
            print("No plays to insert")
            return

        print(f"Inserting {len(df)} play events...")

        try:
            if self.db_type == 'mongo':
                # convert dataframe to list of dicts
                plays_data = []
                for row in df.iter_rows(named=True):
                    plays_data.append({
                        'song': row['song'],
                        'artist': row['artist'],
                        'timestamp': datetime.fromtimestamp(row['timestamp']),
                        'elapsed_ms': row['elapsed_ms']
                    })

                # batch insert all plays
                if plays_data:
                    result = self.plays_collection.insert_many(plays_data)
                    print(f"Inserted {len(result.inserted_ids)} plays to MongoDB")
            else:
                # sqlite batch insert
                plays_data = []
                for row in df.iter_rows(named=True):
                    plays_data.append((
                        row['song'],
                        row['artist'],
                        datetime.fromtimestamp(row['timestamp']).isoformat(),
                        row['elapsed_ms']
                    ))

                self.cursor.executemany('''
                    INSERT OR IGNORE INTO plays (song, artist, timestamp, elapsed_ms)
                    VALUES (?, ?, ?, ?)
                ''', plays_data)
                self.conn.commit()
                print(f"Inserted {self.cursor.rowcount} new plays to SQLite")

        except Exception as e:
            print(f"Failed to insert play events: {e}")
        

    def find_album_genres(self, entry: tuple) -> str:
        """Finds the genres associated with the given album

        Args:
            entry (tuple): (artist, album) to find the genres for

        Returns:
            str: the genres associated with the given album
        """
        artist, album = entry
        genre_str = ""
        album_key = f"{album}:{artist}"

        if album_key in self.failed_albums:
            return ""

        # make request to last.fm for album info
        album_genres = []
        req_str = '{}/2.0/?method=album.getInfo&api_key={}&artist={}&album={}&autocorrect=1&format=json'.format(
            lastfm_root, self.api_key, artist, album.replace(" (Explicit)", "")
        )
        resp = requests.get(req_str)

        try:
            # grab valid genre tags
            album_data = json.loads(resp.text).get('album', {})
            toptags = album_data.get('tags', {})

            # handle both 'tags' and 'tag' structures from API
            tag_list = toptags.get('tag', [])
            if not isinstance(tag_list, list):
                tag_list = [tag_list] if tag_list else []

            for tag in tag_list:
                tag_name = tag['name'].lower().strip()
                if tag_name in all_genres:
                    album_genres.append(tag_name)

            genre_str = ','.join(album_genres)
        except Exception as e:
            print(f"Failed to find genres for album '{album}' by {artist}")
            self.failed_albums[album_key] = True

        sleep(0.5) # TODO: add proper rate limiting logic
        return genre_str


    def df_to_file(self, df: Optional[pl.DataFrame] = None,
                   output_file: str = 'sample_files/ipod_log.csv') -> None:
        """Writes the given dataframe, or the log dataframe, to the given
        output file.

        Args:
            df (pl.DataFrame, optional): The dataframe to write. Defaults to None.
            output_file (str, optional): Where to write the df to.
                                        Defaults to 'sample_files/ipod_log.csv'.
        """
        if df is None:
            df = self.log_df
        df.write_csv(output_file)
        
        
    def load_stats_from_db(self) -> pl.DataFrame:
        """Loads song statistics aggregated from plays table into a polars DataFrame"""
        if self.db_type == 'mongo':
            # aggregate from plays collection
            pipeline = [
                {'$group': {
                    '_id': {'song': '$song', 'artist': '$artist'},
                    'total_plays': {'$sum': 1},
                    'total_elapsed_ms': {'$sum': '$elapsed_ms'}
                }}
            ]
            play_stats = list(self.plays_collection.aggregate(pipeline))

            # get song metadata
            all_songs = list(self.song_collection.find({}, projection={'_id': 0}))
            songs_metadata = {(s['song'], s['artist']): s for s in all_songs}

            # combine stats with metadata
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
            # aggregate from plays table
            self.cursor.execute('''
                SELECT
                    s.song,
                    s.artist,
                    s.album,
                    s.genres,
                    COUNT(p.id) as total_plays,
                    s.song_length_ms,
                    SUM(p.elapsed_ms) as total_elapsed_ms
                FROM songs s
                LEFT JOIN plays p ON s.song = p.song AND s.artist = p.artist
                GROUP BY s.song, s.artist
            ''')
            rows = self.cursor.fetchall()
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

        if not all_docs:
            return pl.DataFrame()

        return pl.DataFrame(all_docs)


    def merge_duplicate_genres(self) -> None:
        """Merges any duplicate genres (e.g. hip-hop vs hip hop) in the db.
        Fixes with a batch update if necessary."""

        if self.db_type == 'mongo':
            bulk_operations = []

            # fetch all songs with genres
            all_docs = self.song_collection.find({'genres': {'$exists': True, '$ne': ''}})

            for doc in all_docs:
                genres = doc.get('genres', '')
                if not genres:
                    continue

                # split, normalize, rejoin
                genre_list = [g.strip() for g in genres.split(',')]
                normalized_genres = [genre_mappings.get(g.lower(), g) for g in genre_list]

                # remove duplicates
                seen = set()
                unique_genres = []
                for g in normalized_genres:
                    if g.lower() not in seen:
                        seen.add(g.lower())
                        unique_genres.append(g)

                new_genre_str = ','.join(unique_genres)

                # only update if genres changed
                if new_genre_str != genres:
                    bulk_operations.append(
                        UpdateOne(
                            {'_id': doc['_id']},
                            {'$set': {'genres': new_genre_str}}
                        )
                    )

            # batch update
            if bulk_operations:
                result = self.song_collection.bulk_write(bulk_operations)
                print(f"Genre normalization: {result.modified_count} documents updated")
            else:
                print("No genre duplicates found")
        else:
            # sqlite genre normalization
            self.cursor.execute("SELECT song, artist, genres FROM songs WHERE genres IS NOT NULL AND genres != ''")
            rows = self.cursor.fetchall()
            updates = []

            for row in rows:
                song, artist, genres = row
                if not genres:
                    continue

                # split, normalize, rejoin
                genre_list = [g.strip() for g in genres.split(',')]
                normalized_genres = [genre_mappings.get(g.lower(), g) for g in genre_list]

                # remove duplicates
                seen = set()
                unique_genres = []
                for g in normalized_genres:
                    if g.lower() not in seen:
                        seen.add(g.lower())
                        unique_genres.append(g)

                new_genre_str = ','.join(unique_genres)

                # only update if genres changed
                if new_genre_str != genres:
                    updates.append((new_genre_str, song, artist))

            # batch update
            if updates:
                self.cursor.executemany('''
                    UPDATE songs SET genres = ? WHERE song = ? AND artist = ?
                ''', updates)
                self.conn.commit()
                print(f"Genre normalization: {len(updates)} songs updated")
            else:
                print("No genre duplicates found")


    def find_most_listened_to(self) -> Optional[tuple]:
        """Finds the song most listened to by total_plays_count.

        Returns:
            Optional[tuple]: (song, artist, album)
        """
        # load stats from db
        stats_df = self.load_stats_from_db()

        if stats_df.is_empty():
            return None

        # filter out rows without total_plays
        stats_df = stats_df.filter(pl.col('total_plays').is_not_null())

        # sort by total_plays and get top song
        top_song = stats_df.sort('total_plays', descending=True).head(1)

        if len(top_song) == 0:
            return None

        row = top_song.row(0, named=True)
        return (row['song'], row['artist'], row['album'])


    def calc_total_play_time(self) -> int:
        """Calculates the total amount of time listened in minutes.
        An aggregation of total_elapsed_ms."""
        # load stats from db
        stats_df = self.load_stats_from_db()

        if stats_df.is_empty():
            return 0

        # filter out rows without total_elapsed_ms
        stats_df = stats_df.filter(pl.col('total_elapsed_ms').is_not_null())

        # sum elapsed time + convert to minutes
        total_ms = stats_df['total_elapsed_ms'].sum()
        total_minutes = total_ms // 60000
        return int(total_minutes)
    
    
    def calc_all_stats(self) -> dict:
        """Calculates all the relevant iPod Wrapped Stats"""
        # calculations
        top_genres = find_top_genres(self.db_type, self.db_path)
        top_artists = find_top_artists(self.db_type, self.db_path, 5)
        top_albums = find_top_albums(self.db_type, self.db_path)
        top_songs = find_top_songs(self.db_type, self.db_path, 5)

        # setup
        stats = {
            "top_genres": top_genres,
            "top_artists": top_artists,
            "top_albums": top_albums,
            "top_songs": top_songs,
            "most_listened_song": self.find_most_listened_to(),
            "total_play_time_mins": self.calc_total_play_time()
        }
        return stats


    def process_filesystem_songs(self, music_dir: str):
        """Process all songs from filesystem and add to database

        Args:
            music_dir (str): path to the Music directory on iPod
        """
        print("Processing all songs from filesystem...")
        all_song_paths = list_dir_song_paths(music_dir)
        added_count = 0

        for song_path in all_song_paths:
            # grab metadata
            metadata = extract_metadata_from_path(song_path)
            if not metadata:
                continue

            song_key = f"{metadata['song']}:{metadata['artist']}"

            # skip if already seen in logs
            if song_key in self.seen_songs:
                continue

            # find genre info based on album
            album_key = f"{metadata['album']}:{metadata['artist']}"
            if album_key in self.genre_data:
                genres = self.genre_data[album_key]
            else:
                genres = self.find_album_genres((metadata['artist'], metadata['album']))
                self.genre_data[album_key] = genres

            # add to db
            self.batch_add_to_db({
                "song": metadata['song'],
                "album": metadata['album'],
                "artist": metadata['artist'],
                "genres": genres,
                "song_length_ms": None,  # no length info from filesystem
                "path": metadata['path']
            })
            self.seen_songs.add(song_key)
            added_count += 1

        # add remaining batch
        self.batch_add_to_db({}, final_add=True)
        print(f"Added {added_count} songs from filesystem that weren't in playback.log")


    def close(self):
        """Close database connection (for SQLite)"""
        if self.db_type == 'local' and hasattr(self, 'conn'):
            self.conn.close()
            print("Database connection closed")


    def run(self) -> dict:
        """Runs the log analyser from start to finish"""
        # find logs
        log_location = self.find_playback_log()
        if not log_location:
            print("Could not find the iPod. Make sure it is connected via USB")
            return {"error": "Could not find iPod. Make sure it is connected & mounted."}
        
        
        try:
            # copy log to local storage
            shutil.copy2(log_location, STORAGE_DIR)

            # read and analyse logs
            self.log_data = self.load_logs(log_location)
            self.log_df = self.logs_to_df()
            print(f"Loaded {len(self.log_df)} log entries")

            # finish updating db with logged songs
            self.batch_add_to_db({}, final_add=True)
            self.add_plays_from_dataframe(self.log_df)

            # add songs from ipod fs not in logs
            music_dir = find_music_directory()
            if music_dir:
                self.process_filesystem_songs(music_dir)
            else:
                print("Could not find Music directory, skipping unplayed songs")

            # fix truncated album names
            print("Fixing truncated album names in database...")
            fix_filenames_in_db(db_type=self.db_type, db_path=self.db_path)

            # consolidate genre names
            self.merge_duplicate_genres()
            
            # run stats
            self.stats = self.calc_all_stats()
        except Exception as e:
            print(f"ERROR: {e}")
            return {"error": "Something went wrong. Please try again later"}

        # cleanup
        self.close()
        return {"success": "Successfully synced & analysed your listening history!"}



if __name__ == "__main__":
    analyser = LogAnalyser(db_type='local')
    analyser.run()