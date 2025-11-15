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
    has_data,
    create_genre_mappings
)
from .album_art_fixer import process_images, organize_music_files, clear_temp_directory
from .constants import *

__all__ = [
    'LogAnalyser',
    'grab_all_metadata',
    'find_ipod',
    'find_music_directory',
    'fix_filenames_in_db',
    'fix_and_store_album_art',
    'find_album_art',
    'ms_to_mmss',
    'process_images',
    'organize_music_files',
    'clear_temp_directory',
    'has_data',
    'create_genre_mappings',
]
