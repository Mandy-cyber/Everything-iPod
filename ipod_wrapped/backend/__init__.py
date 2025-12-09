"""Backend module for iPod Wrapped - handles data processing and analysis"""

from .log_analysis import LogAnalyser
from .wrapped_helpers import (
    grab_all_metadata,
    find_ipod,
    find_music_directory,
    fix_filenames_in_db,
    fix_and_store_album_art,
    find_album_art,
    ms_to_mmss,
    extract_song_path,
    has_data,
    create_genre_mappings,
    grab_all_songs,
    find_top_genres,
    find_top_artists,
    find_top_albums,
    find_top_songs,
    load_stats_from_db,
    get_total_listening_time,
    list_dir_song_paths,
    extract_metadata_from_path
)
from .album_art_fixer import process_images, organize_music_files, clear_temp_directory
from .constants import *
from .creds_manager import save_credentials, get_credentials, has_credentials, delete_credentials

__all__ = [
    'LogAnalyser',
    'grab_all_metadata',
    'find_ipod',
    'find_music_directory',
    'fix_filenames_in_db',
    'fix_and_store_album_art',
    'find_album_art',
    'ms_to_mmss',
    'extract_song_path',
    'process_images',
    'organize_music_files',
    'clear_temp_directory',
    'has_data',
    'create_genre_mappings',
    'grab_all_songs',
    'find_top_genres',
    'find_top_artists',
    'find_top_albums',
    'find_top_songs',
    'load_stats_from_db',
    'get_total_listening_time',
    'save_credentials',
    'get_credentials',
    'has_credentials',
    'delete_credentials',
    'list_dir_song_paths',
    'extract_metadata_from_path'
]
