import os
import re
import glob
import json
import subprocess
import sqlite3
import polars as pl
from dotenv import load_dotenv
import requests
from time import sleep
from pymongo import MongoClient, UpdateOne
from typing import Optional, List

from constants import *

load_dotenv()

class LogAnalyser:

    def __init__(self, db_type: str = 'mongo', db_path: str = '../sample-files/ipod_wrapped.db'):
        """Initialize LogAnalyser with chosen database type

        Args:
            db_type (str): Either 'mongo' or 'local'. Defaults to 'mongo'.
            db_path (str): Path to local SQLite db file. Defaults to '../sample-files/ipod_wrapped.db'.
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
        try:
            self.api_key = os.getenv('LASTFM_API_KEY')
            self.shared_secret = os.getenv('LASTFM_SHARED_SECRET')
        except Exception as e:
            print(f"Could not analyze logs: {e}")
            return


    def _setup_mongo(self):
        """Setup MongoDB connection"""
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        self.song_collection = db.songs


    def _setup_local_db(self):
        """Setup SQLite local database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

        # create table if not exists
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                song TEXT NOT NULL,
                artist TEXT NOT NULL,
                album TEXT NOT NULL,
                genres TEXT,
                total_plays INTEGER DEFAULT 0,
                song_length_ms INTEGER,
                total_elapsed_ms INTEGER DEFAULT 0,
                PRIMARY KEY (song, artist)
            )
        ''')
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
        return any(filename.endswith(ext) for ext in song_extensions)


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
            song = self.clean_song(track_filename.split(' - ', 1)[1])
        else:
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
        for ext in song_extensions:
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
            match = re.match(ipod_log_pattern, log_entry.strip())
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

                    # add song to database if not already seen
                    song_key = f"{song}:{artist}"
                    if song_key not in self.seen_songs:
                        self.batch_add_to_db({"song": song, "album": album, "artist": artist, "genres": genres})
                        self.seen_songs.add(song_key)

                    # create full entry for calculations
                    entries.append({
                        'timestamp': int(match.group(1)),
                        'elapsed_ms': int(match.group(2)),
                        'length_ms': int(match.group(3)),
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
        """Adds the given entry to the database collection"""
        if entry and entry != {}:
            self.batch_entries.append(entry)

        if len(self.batch_entries) == BATCH_SIZE or final_add:
            try:
                if self.db_type == 'mongo':
                    result = self.song_collection.insert_many(self.batch_entries)
                    print(result.inserted_ids)
                else:
                    # sqlite batch insert
                    self.cursor.executemany('''
                        INSERT OR IGNORE INTO songs (song, artist, album, genres)
                        VALUES (?, ?, ?, ?)
                    ''', [(e['song'], e['artist'], e['album'], e.get('genres', ''))
                          for e in self.batch_entries])
                    self.conn.commit()
                    print(f"Inserted {self.cursor.rowcount} songs")

                self.batch_entries.clear()
            except Exception as e:
                print(f"Failed to batch add entries to db: {e}")
        

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
    

    def calc_total_plays(self) -> pl.DataFrame:
        """Calculates the total number of plays of each song in the
        log dataframe.

        Returns:
            pl.DataFrame: the dataframe with total plays calculated
        """
        summary = self.log_df.group_by(['artist', 'song', 'album', 'genres']).agg([
            pl.len().alias('total_plays'),
            pl.col('length_ms').first().alias('song_length_ms'),
            pl.col('elapsed_ms').sum().alias('total_elapsed_ms'),
        ]).sort('total_plays', descending=True)
        return summary


    def update_play_stats_in_db(self):
        """Updates play statistics in database"""
        # setup
        play_stats = self.calc_total_plays()
        print(f"Updating play stats for {len(play_stats)} songs...")

        if self.db_type == 'mongo':
            bulk_operations = []
            for row in play_stats.iter_rows(named=True):
                # replace with current stats from log
                updated_stats = {
                    'total_plays': row['total_plays'],
                    'song_length_ms': row['song_length_ms'],
                    'total_elapsed_ms': row['total_elapsed_ms']
                }

                # add to bulk operations
                bulk_operations.append(
                    UpdateOne(
                        {'song': row['song'], 'artist': row['artist']},
                        {'$set': updated_stats}
                    )
                )

            # execute batch update
            if bulk_operations:
                result = self.song_collection.bulk_write(bulk_operations)
                print(f"Play stats updated: {result.modified_count} documents modified")
            else:
                print("No play stats to update")
        else:
            # sqlite update
            for row in play_stats.iter_rows(named=True):
                self.cursor.execute('''
                    UPDATE songs
                    SET total_plays = ?,
                        song_length_ms = ?,
                        total_elapsed_ms = ?
                    WHERE song = ? AND artist = ?
                ''', (row['total_plays'], row['song_length_ms'], row['total_elapsed_ms'],
                      row['song'], row['artist']))

            self.conn.commit()
            print(f"Play stats updated: {self.cursor.rowcount} songs modified")


    def df_to_file(self, df: pl.DataFrame = None,
                   output_file: str = '../sample-files/ipod_log.csv') -> None:
        """Writes the given dataframe, or the log dataframe, to the given
        output file.

        Args:
            df (pl.DataFrame, optional): The dataframe to write. Defaults to None.
            output_file (str, optional): Where to write the df to.
                                        Defaults to '../sample-files/ipod_log.csv'.
        """
        if df is None:
            df = self.log_df
        df.write_csv(output_file)
        
        
    def load_stats_from_db(self) -> pl.DataFrame:
        """Loads song statistics from database into a polars DataFrame"""
        if self.db_type == 'mongo':
            # fetch all documents from mongo
            all_docs = list(self.song_collection.find({}, projection={'_id': 0}))
        else:
            # fetch all from sqlite
            self.cursor.execute('''
                SELECT song, artist, album, genres, total_plays,
                       song_length_ms, total_elapsed_ms
                FROM songs
            ''')
            rows = self.cursor.fetchall()
            all_docs = [
                {
                    'song': row[0],
                    'artist': row[1],
                    'album': row[2],
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


    def find_top_genres(self, n: int = 3) -> List[str]:
        """Finds the top n genres listened to based on
        total_elapsed_ms stats.

        Args:
            n (int, optional): The number of top genres to show. Defaults to 3.

        Returns:
            List[str]: [first, second, third, ..., N] top genres
        """
        # load stats from db
        stats_df = self.load_stats_from_db()

        if stats_df.is_empty():
            return []

        # filter out rows missing info
        stats_df = stats_df.filter(
            (pl.col('genres').is_not_null()) &
            (pl.col('genres') != '') &
            (pl.col('total_elapsed_ms').is_not_null())
        )

        # explode genres into separate rows
        genre_rows = []
        for row in stats_df.iter_rows(named=True):
            genres = row['genres'].split(',')
            elapsed = row['total_elapsed_ms']
            for genre in genres:
                genre = genre.strip()
                if genre:
                    genre_rows.append({'genre': genre, 'total_elapsed_ms': elapsed})

        if not genre_rows:
            return []

        genre_df = pl.DataFrame(genre_rows)

        # aggregate by genre
        top_genres = genre_df.group_by('genre').agg(
            pl.col('total_elapsed_ms').sum().alias('total_time')
        ).sort('total_time', descending=True).head(n)

        return top_genres['genre'].to_list()


    def find_top_artists(self, n: int = 3) -> List[str]:
        """Finds the top n artists listened to based on
        total_plays stats.

        Args:
            n (int, optional): The number of top artists to show. Defaults to 3.

        Returns:
            List[str]: [first, second, third, ..., N] top artists
        """
        # load stats from db
        stats_df = self.load_stats_from_db()

        if stats_df.is_empty():
            return []

        # filter out rows without total_plays
        stats_df = stats_df.filter(pl.col('total_plays').is_not_null())

        # aggregate by artist
        top_artists = stats_df.group_by('artist').agg(
            pl.col('total_plays').sum().alias('total_plays')
        ).sort('total_plays', descending=True).head(n)

        return top_artists['artist'].to_list()
    
    
    def find_top_albums(self, n: int = 3) -> List[str]:
        """Finds the top n albums listened to based on
        total_plays stats.

        Args:
            n (int, optional): The number of top albums to show. Defaults to 3.

        Returns:
            List[str]: [first, second, third, ..., N] top albums
        """
        # load stats from db
        stats_df = self.load_stats_from_db()

        if stats_df.is_empty():
            return []

        # filter out rows without total_plays
        stats_df = stats_df.filter(pl.col('total_plays').is_not_null())

        # aggregate by album (and artist in case of same-named albums)
        top_albums = stats_df.group_by(['album', 'artist']).agg(
            pl.col('total_plays').sum().alias('total_plays')
        ).sort('total_plays', descending=True).head(n)

        # return album names (w/artist for context)
        return [(row["album"], row["artist"]) for row in top_albums.iter_rows(named=True)]
       
    
    def find_top_songs(self, n: int = 3) -> List[tuple]:
        """Finds the top n songs listened to based on
        total_plays stats.

        Args:
            n (int, optional): The number of top songs to show. Defaults to 3.

        Returns:
            List[str]: [first, second, third, ..., N] top songs
        """
        # load stats from db
        stats_df = self.load_stats_from_db()

        if stats_df.is_empty():
            return []

        # filter out rows without total_plays
        stats_df = stats_df.filter(pl.col('total_plays').is_not_null())

        # aggregate by song (and artist in case of same-named songs)
        top_songs = stats_df.group_by(['song', 'artist']).agg(
            pl.col('total_plays').sum().alias('total_plays')
        ).sort('total_plays', descending=True).head(n)

        # return song names (w/artist for context)
        return [(row['song'],row['artist']) for row in top_songs.iter_rows(named=True)]
    
    
    def find_most_listened_to(self) -> tuple:
        """Finds the song most listened to by total_plays_count.

        Returns:
            tuple: (song, artist, album)
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
        return total_minutes
    
    
    def calc_all_stats(self) -> dict:
        """"""
        # calculations
        top_genres = self.find_top_genres()
        top_artists = self.find_top_artists(5)
        top_albums = self.find_top_albums()
        top_songs = self.find_top_songs(5)
        
        # setup
        stats = {
            "top_genres": [],
            "top_artists": [],
            "top_albums": [],
            "top_songs": [],
            "most_listened_song": self.find_most_listened_to(),
            "total_play_time_mins": self.calc_total_play_time()
        }
        
        # format genres
        for genre in top_genres:
            stats["top_genres"].append({"genre": genre})
        
        # format artists
        for artist in top_artists:
            stats["top_artists"].append({"artist": artist})
        
        # format albums
        for album in top_albums:
            stats["top_albums"].append({"album": album})
            
        # format songs
        for song in top_songs:
            stats["top_songs"].append({"song": song})
        
        print(json.dumps(stats, indent=4))
        return stats


    def close(self):
        """Close database connection (for SQLite)"""
        if self.db_type == 'local' and hasattr(self, 'conn'):
            self.conn.close()
            print("Database connection closed")


    def run(self) -> None:
        """Runs the log analyser from start to finish"""
        # find logs
        log_location = self.find_playback_log()
        if not log_location:
            print("Could not find the iPod. Make sure it is connected via USB")
            return

        # read and analyse logs
        self.log_data = self.load_logs(log_location)
        self.log_df = self.logs_to_df()
        print(f"Loaded {len(self.log_df)} log entries")

        # finish updating db
        self.batch_add_to_db({}, final_add=True)
        self.update_play_stats_in_db()

        # run stats
        self.stats = self.calc_all_stats()

        # cleanup
        self.close()


if __name__ == "__main__":
    analyser = LogAnalyser(db_type='local')
    analyser.run()