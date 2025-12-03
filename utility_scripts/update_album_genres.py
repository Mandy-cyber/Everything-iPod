"""
Manually update albums missing genre information
TODO: eventually add this functionality to the UI
"""

import sqlite3
from typing import List, Optional, Tuple

# make sure there are no spelling mistakes and that genres match those in ipod_wrapped/backend/constants.py
ALBUMS_WITH_GENRES = [
    # album_name, artist, [genre1, genre2, ..., genreN]
    ('The Summer That Saved Me (Explicit)', 'Odeal', ['rap', 'hip-hop', 'rnb', 'afrobeats']),
]

GENRE_MAPPINGS = {
    'hip hop': 'hip-hop',
    'hiphop': 'hip-hop',
    'r and b': 'rnb',
    'r&b': 'rnb',
    'rhythm and blues': 'rnb',
    'afrobeats': 'afrobeat',
}

def normalize_genre(genre: str) -> Optional[str]:
    """Normalize genre name using the genre mappings."""
    genre_lower = genre.lower().strip()
    return GENRE_MAPPINGS.get(genre_lower, genre_lower)

def process_genres(genres: List[str], max_genres: int = 5) -> str:
    """
    Process and normalize genres, limiting to max_genres.
    Returns comma-separated string of normalized genres.
    """
    normalized = []
    for g in genres:
        norm = normalize_genre(g)
        if norm not in normalized:
            normalized.append(norm)

    # feel free to remove the max logic tbh
    normalized = normalized[:max_genres]
    return ','.join(normalized)

def update_database(db_path: str):
    """Update the database with genre information."""
    # connect to db
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Starting database update...")
    print("="*60)

    total_updated = 0

    for album, artist, genres in ALBUMS_WITH_GENRES:
        genres_str = process_genres(genres)

        print(f"\n{album} by {artist}")
        print(f"  Genres: {genres_str}")

        # update all songs from this album by this artist
        cursor.execute('''
            UPDATE songs
            SET genres = ?
            WHERE album = ? AND artist = ?
        ''', (genres_str, album, artist))

        rows_affected = cursor.rowcount
        total_updated += rows_affected
        print(f"  Updated {rows_affected} song(s)")

    conn.commit()

    # show updated records
    print("\n" + "="*60)
    print("Updated albums:")
    print("="*60)

    for album, artist, _ in ALBUMS_WITH_GENRES:
        cursor.execute('''
            SELECT DISTINCT album, artist, genres
            FROM songs
            WHERE album = ? AND artist = ?
        ''', (album, artist))

        result = cursor.fetchone()
        if result:
            print(f"\n{result[0]}")
            print(f"  Artist: {result[1]}")
            print(f"  Genres: {result[2]}")
        else:
            print(f"\n{album} by {artist}")
            print(f"  WARNING: No songs found in database!")

    conn.close()

    print("\n" + "="*60)
    print(f"Manual genre update complete. Updated {total_updated} song(s) across {len(ALBUMS_WITH_GENRES)} album(s)")

def main():
    db_path = '../ipod_wrapped/storage/ipod_wrapped.db'

    print("Album Genre Update Script")
    print(f"Database: {db_path}")
    print(f"Albums to process: {len(ALBUMS_WITH_GENRES)}\n")

    update_database(db_path)

if __name__ == '__main__':
    main()
