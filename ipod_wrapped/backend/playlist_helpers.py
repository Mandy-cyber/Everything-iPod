import os
import json
import sqlite3
from dotenv import load_dotenv
from typing import Optional, List
from pymongo import MongoClient

from .constants import DEFAULT_DB_PATH

load_dotenv()

def list_db_song_paths(
    db_type: str,
    db_path: str,
    filters: Optional[dict] = None,
) -> List[dict]:
    """Lists songs with their full paths from the db
    
    Args:
        db_type (str): The type of db ('mongo' or 'local')
        db_path (str): The location of the db if 'local'
        filters (Optional[dict]): Optional filters for the query. Supported keys:
            - 'album': Filter by specific album name
            - 'artist': Filter by specific artist name
            - 'genre': Filter by specific genre (case-insensitive, partial match)
            
    Returns:
        List[dict]: [
            {
                "song": str,
                "artist": str,
                "album": str,
                "path": str,
            },
            ...
        ]
    """
    # check for bad params
    if db_type != 'mongo' and db_type != 'local':
        return []

    if db_type == 'local' and not db_path:
        return []

    # process filters
    if filters is None:
        filters = {}

    # setup
    all_songs = []
    songs_dict =  dict()
    
    # mongo search
    if db_type == 'mongo':
        client = MongoClient(os.getenv('MONGODB_URI'))
        db = client.song_db
        song_collection = db.songs
        
        # build song filter query
        song_filter = {'song': {'$ne': None}, 'artist': {'$ne': None}}
        if 'album' in filters and filters['album']:
            song_filter['album'] = filters['album']
        if 'artist' in filters and filters['artist']:
            song_filter['artist'] = filters['artist']

        # get song metadata
        all_songs_cursor = song_collection.find(
            song_filter,
            projection={'_id':0, 'song': 1, 'artist': 1, 'album': 1, 'genres': 1, 'path': 1}
        )
        
        for song_doc in all_songs_cursor:
            # apply genre filter if specified
            song_genres = song_doc.get('genres', '')
            if 'genre' in filters and filters['genre']:
                if filters['genre'].lower() not in song_genres.lower():
                    continue
                
            song_key = (song_doc['song'], song_doc['artist'])
            songs_dict[song_key] = {
                'song': song_doc['song'],
                'artist': song_doc['artist'],
                'album': song_doc['album'],
                'path': song_doc['path'],
            }
            
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

        where_clause = ' AND '.join(conditions)
        
        # get info
        cursor.execute(f'''
            SELECT song, artist, album, genres, path
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
            songs_dict[song_key] = {
                'song': row[0],
                'artist': row[1],
                'album': row[2],
                'path': row[4],
            }
            
        conn.close()
        
        # finish up
        for val in songs_dict.values():
            all_songs.append(val)
        return all_songs
        
        