"""Database schema definitions for iPod Wrapped"""

# SQLite schema
SQLITE_SONGS_TABLE = '''
    CREATE TABLE IF NOT EXISTS songs (
        song TEXT NOT NULL,
        artist TEXT NOT NULL,
        album TEXT NOT NULL,
        genres TEXT,
        song_length_ms INTEGER,
        last_updated TEXT,
        PRIMARY KEY (song, artist)
    )
'''

SQLITE_PLAYS_TABLE = '''
    CREATE TABLE IF NOT EXISTS plays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        song TEXT NOT NULL,
        artist TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        elapsed_ms INTEGER NOT NULL,
        UNIQUE(song, artist, timestamp, elapsed_ms)
    )
'''

SQLITE_PLAYS_TIMESTAMP_INDEX = '''
    CREATE INDEX IF NOT EXISTS idx_plays_timestamp
    ON plays(timestamp)
'''

SQLITE_PLAYS_SONG_ARTIST_INDEX = '''
    CREATE INDEX IF NOT EXISTS idx_plays_song_artist
    ON plays(song, artist)
'''

SQLITE_UI_PLAYS_TABLE = '''
    CREATE TABLE IF NOT EXISTS ui_plays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        song TEXT NOT NULL,
        artist TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        elapsed_ms INTEGER NOT NULL,
        source TEXT DEFAULT 'ui'
    )
'''

SQLITE_UI_PLAYS_TIMESTAMP_INDEX = '''
    CREATE INDEX IF NOT EXISTS idx_ui_plays_timestamp
    ON ui_plays(timestamp)
'''

SQLITE_UI_PLAYS_SONG_ARTIST_INDEX = '''
    CREATE INDEX IF NOT EXISTS idx_ui_plays_song_artist
    ON ui_plays(song, artist)
'''

# MongoDB
MONGO_SONGS_COLLECTION = 'songs'
MONGO_PLAYS_COLLECTION = 'plays'
MONGO_UI_PLAYS_COLLECTION = 'ui_plays'
MONGO_PLAYS_INDEXES = [
    ('timestamp', 1),  # ascending index on timestamp
    [('song', 1), ('artist', 1)]  # compound index
]
