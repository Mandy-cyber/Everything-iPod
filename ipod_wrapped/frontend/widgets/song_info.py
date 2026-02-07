import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from backend.constants import DEFAULT_SONG_INFO_IMAGE_SIZE

def display_song_info(song_info: dict, image_size: int = DEFAULT_SONG_INFO_IMAGE_SIZE) -> Gtk.Box:
    """Displays info and the cover art for the song

    Args:
        song_info (dict): The info to display about the song
        image_size (int): Pixel size for the cover art image

    Returns:
        Gtk.Box: The box with the display
    """
    # setup
    title, artist, album, duration, metadata = song_info.values()
    genres, art_path, total_elapsed_ms, total_plays = metadata.values()
    total_mins = total_elapsed_ms // 60000
    
    # header box: image on left, text on right
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    header_box.set_halign(Gtk.Align.START)
    header_box.add_css_class('song-header-box')
    
    # left side: cover image
    image = Gtk.Image()
    image.set_from_file(art_path)
    image.set_pixel_size(image_size)
    image.add_css_class('song-page-image')
    header_box.append(image)
    
    # right side: text
    text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    text_box.set_valign(Gtk.Align.CENTER)
    header_box.append(text_box)
    
    # title, album, artist, genres
    items = {
        'title': GLib.markup_escape_text(title),
        'album': GLib.markup_escape_text(album),
        'artist': GLib.markup_escape_text(artist),
        'genres': f"<b>Genres:</b> <i>{GLib.markup_escape_text(genres)}</i>"
    }
    for name, val in items.items():
        label = Gtk.Label()
        label.set_use_markup(True)
        label.set_markup(val)
        label.set_halign(Gtk.Align.START)
        label.set_ellipsize(3)
        label.set_hexpand(True)
        label.set_tooltip_markup(val)
        label.add_css_class(f'song-page-{name}-label')
        text_box.append(label)
    
    # stats
    mins_text = f"{total_mins:,} {'min' if total_mins == 1 else 'mins'}"
    times_text = "time" if total_plays == 1 else "times"
    stats_text = f"<b>Info:</b> You've played this song <b>{total_plays}</b> {times_text}, for a total of <b>{mins_text}</b>"
    stats_label = Gtk.Label()
    stats_label.set_use_markup(True)
    stats_label.set_markup(stats_text)
    stats_label.set_halign(Gtk.Align.START)
    stats_label.set_ellipsize(3)
    stats_label.set_hexpand(True)
    stats_label.add_css_class('song-page-stats-label')
    text_box.append(stats_label)
    
    return header_box