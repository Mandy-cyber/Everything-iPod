from typing import List, Optional, Callable
import gi
import random
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from backend.constants import DEFAULT_GENRE_HEADER_IMAGE_SIZE, DEFAULT_GENRE_SONG_IMAGE_SIZE

def display_genre_songs(
    genre_info: dict,
    content_box: Gtk.Box,
    play_song_callback: Optional[Callable] = None,
    header_image_size: int = DEFAULT_GENRE_HEADER_IMAGE_SIZE,
    song_image_size: int = DEFAULT_GENRE_SONG_IMAGE_SIZE,
) -> Gtk.Box:
    """Displays the genre's songs and basic stats

    Args:
        genre_info (dict): The genre to display info/songs for
        content_box (Gtk.Box): The box where the display will go
        play_song_callback: Optional callback function(song_path, metadata) to play songs
        header_image_size (int): Pixel size for the genre header image
        song_image_size (int): Pixel size for song listing thumbnails

    Returns:
        Gtk.Box: The box updated with the display
    """
    # clean
    clear_content_box(content_box)

    # setup
    genre: str = genre_info["genre"]
    songs: List[dict] = genre_info["songs"]
    total_plays: int = genre_info["total_plays"]
    total_elapsed_ms: int = genre_info["total_elapsed_ms"]
    total_mins = total_elapsed_ms // 60000

    # choose random cover art
    genre_art: str = ""
    while genre_art == "" or genre_art.endswith("missing_album_cover.jpg"):
        genre_art = random.choice(songs)["art_path"]

    # header box: image on left, text on right
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    header_box.set_halign(Gtk.Align.START)
    header_box.add_css_class('genre-header-box')
    content_box.append(header_box)

    # left side: cover image
    image = Gtk.Image()
    image.set_from_file(genre_art)
    image.set_pixel_size(header_image_size)
    image.add_css_class('genre-image')
    header_box.append(image)

    # right side: title and stats
    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    text_box.set_valign(Gtk.Align.CENTER)
    header_box.append(text_box)

    # title
    title = Gtk.Label(label=genre)
    title.set_halign(Gtk.Align.START)
    title.set_ellipsize(3)
    title.set_hexpand(True)
    title.add_css_class('genre-title-label')
    text_box.append(title)

    # total plays w/info icon
    plays_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    plays_box.set_halign(Gtk.Align.START)

    plays_info = Gtk.Button()
    plays_info.set_icon_name("dialog-information-symbolic")
    plays_info.add_css_class('flat')
    plays_info.add_css_class('circular')
    plays_info.add_css_class('genre-info-icon')
    plays_info.set_tooltip_text("The number of times you've played songs of this genre")
    plays_info.set_can_focus(False)
    plays_box.append(plays_info)

    plays_label = Gtk.Label()
    plays_label.set_use_markup(True)
    plays_label.set_markup(f"<b>Total Plays:</b> {total_plays}")
    plays_label.set_halign(Gtk.Align.START)
    plays_label.set_ellipsize(3)
    plays_label.set_hexpand(True)
    plays_label.add_css_class('genre-stats-label')
    plays_box.append(plays_label)

    text_box.append(plays_box)

    # total elapsed w/info icon
    elapsed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
    elapsed_box.set_halign(Gtk.Align.START)

    elapsed_info = Gtk.Button()
    elapsed_info.set_icon_name("dialog-information-symbolic")
    elapsed_info.add_css_class('flat')
    elapsed_info.add_css_class('circular')
    elapsed_info.add_css_class('genre-info-icon')
    elapsed_info.set_tooltip_text("The total minutes spent listening to songs of this genre")
    elapsed_info.set_can_focus(False)
    elapsed_box.append(elapsed_info)

    elapsed_label = Gtk.Label()
    elapsed_label.set_use_markup(True)
    elapsed_label.set_markup(f"<b>Total Elapsed:</b> {total_mins:,}{'min' if total_mins == 1 else 'mins'}")
    elapsed_label.set_halign(Gtk.Align.START)
    elapsed_label.set_ellipsize(3)
    elapsed_label.set_hexpand(True)
    elapsed_label.add_css_class('genre-stats-label')
    elapsed_box.append(elapsed_label)

    text_box.append(elapsed_box)

    # scrollable songs list
    songs_scroll = Gtk.ScrolledWindow()
    songs_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    songs_scroll.set_vexpand(True)
    content_box.append(songs_scroll)

    songs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    songs_scroll.set_child(songs_box)

    # load in songs
    for song_info in songs:
        listing = create_song_listing(song_info, play_song_callback, song_image_size)
        songs_box.append(listing)

    return content_box

def create_song_listing(
    song_info: dict,
    play_song_callback: Optional[Callable] = None,
    image_size: int = DEFAULT_GENRE_SONG_IMAGE_SIZE,
) -> Gtk.Box:
    song, artist, art_path = song_info.values()

    # listing box
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    box.set_halign(Gtk.Align.START)
    box.add_css_class('genre-song-row')

    # album art
    image = Gtk.Image()
    image.set_from_file(art_path)
    image.set_pixel_size(image_size)
    image.add_css_class('genre-song-art')
    box.append(image)
    
    # song and artist text
    text_label = Gtk.Label()
    full_text = f"{song} • {artist}"
    text_label.set_label(full_text)
    text_label.set_halign(Gtk.Align.START)
    text_label.set_ellipsize(3)
    text_label.set_xalign(0)
    text_label.set_hexpand(True)
    text_label.add_css_class('genre-song-text')
    box.append(text_label)
    
    # TODO: add right click with menu showing 'add to queue' 'play next'
    
    return box
    
def clear_content_box(box: Gtk.Box) -> None:
    """Clears existing content from the given box"""
    while True:
        child = box.get_first_child()
        if child is None:
            break
        box.remove(child)