import cairo
import math
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Gio, Pango, GdkPixbuf, Adw, GLib

from backend import grab_all_songs, ms_to_mmss
from .songs_table import create_song_store, create_song_selection_model, create_songs_table, Song
from .song_info import display_song_info

def create_album_button(db_type: str, db_path: str, album_art_dir: str, album_info: dict, nav_view: Adw.NavigationView, image_size: int = 120) -> Gtk.Button:
    """Creates a button with Album Art, Name, and Artist.

    Args:
        db_type (str):
        db_path (str):
        album_art_dir (str):
        album_info (dict): Album metadata containing art, name, artist, genres, songs
        nav_view (Adw.NavigationView): Navigation view to push detail page onto
        image_size (int): Size of the album art image

    Returns:
        Gtk.Button: The button with album art and info
    """
    art, name, artist, _, _ = album_info.values()
    button = Gtk.Button()

    # setup
    BUTTON_SIZE = image_size + 5
    button.set_size_request(BUTTON_SIZE, BUTTON_SIZE)
    button.set_hexpand(False)
    button.set_vexpand(False)
    button.add_css_class('album-button')

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.set_spacing(5)

    # setup rounded image
    texture = __round_image(art, image_size, 2)
    picture = Gtk.Picture.new_for_paintable(texture)
    picture.set_size_request(image_size, image_size)

    # setup labels (will truncate with '...')
    name_label = Gtk.Label(label=name)
    name_label.set_ellipsize(Pango.EllipsizeMode.END)
    name_label.set_max_width_chars(12)
    name_label.set_justify(Gtk.Justification.CENTER)
    name_label.add_css_class('album-name-label')

    artist_label = Gtk.Label(label=artist)
    artist_label.set_ellipsize(Pango.EllipsizeMode.END)
    artist_label.set_max_width_chars(12)
    artist_label.set_justify(Gtk.Justification.CENTER)
    artist_label.add_css_class('album-artist-label')

    # add widgets to box
    box.append(picture)
    box.append(name_label)
    box.append(artist_label)

    button.set_child(box)
    button.connect("clicked", lambda btn: _show_album_info(album_info, db_type, db_path, album_art_dir, nav_view))
    return button

def _show_album_info(album_info: dict, db_type: str, db_path: str, album_art_dir: str, nav_view: Adw.NavigationView) -> None:
    """Shows the given album info when an album cover is clicked
    Absolutely insanity how chunky this function got. TODO: come back and make better
    """
    # setup
    _, album_name, artist, _, _ = album_info.values()

    # create store + models
    store: Gio.ListStore = create_song_store()
    selection, sort_model = create_song_selection_model(store)

    # main content box (song info + table)
    content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    content_box.set_vexpand(True)
    content_box.set_hexpand(True)

    # song info display (initially hidden)
    song_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    song_info_box.add_css_class('song-info-container')
    song_info_box.add_css_class('album-pg-song-info-container')
    song_info_box.set_visible(False)
    content_box.append(song_info_box)

    # scrolled window for table
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(
        Gtk.PolicyType.NEVER,
        Gtk.PolicyType.AUTOMATIC
    )
    scrolled_window.set_vexpand(True)

    # create table
    songs_table: Gtk.ColumnView = create_songs_table(selection, sort_model, show_columns={'title': True, 'artist': False, 'album': False, 'duration': True})
    scrolled_window.set_child(songs_table)
    content_box.append(scrolled_window)

    # header bar
    toolbar_view = Adw.ToolbarView()
    toolbar_view.set_content(content_box)
    header_bar = Adw.HeaderBar()
    header_bar.set_show_end_title_buttons(False)
    header_bar.set_show_start_title_buttons(False)
    toolbar_view.add_top_bar(header_bar)

    # navigation page on top of main page
    detail_page = Adw.NavigationPage()
    detail_page.set_title(f"{album_name} - {artist}")
    detail_page.set_child(toolbar_view)

    # load songs
    songs_data = _load_album_songs(
        album_name, store, db_type,
        db_path, album_art_dir
    )

    # setup selection handler
    def on_selection_changed(sel, position, n_items):
        selected = sel.get_selected_item()
        if selected is None:
            song_info_box.set_visible(False)
            return

        # find song data
        song_data = None
        for song in songs_data:
            if song['title'] == selected.title:
                song_data = song
                break

        if song_data:
            # clear box
            child = song_info_box.get_first_child()
            while child:
                song_info_box.remove(child)
                child = song_info_box.get_first_child()

            # rebuild
            song_info_widget = display_song_info(song_data)
            song_info_box.append(song_info_widget)
            song_info_box.set_visible(True)

    selection.connect('selection-changed', on_selection_changed)

    # auto-select first song
    if len(songs_data) > 0 and store.get_n_items() > 0:
        def select_first():
            selection.set_selected(0)
            # manually trigger display
            song_info_widget = display_song_info(songs_data[0])
            song_info_box.append(song_info_widget)
            song_info_box.set_visible(True)
            return False
        GLib.idle_add(select_first)

    # push onto navigation stack
    nav_view.push(detail_page)
    
def _load_album_songs(album_name: str, store: Gio.ListStore, db_type: str, db_path: str, album_art_dir: str):
    """Load songs of the given album into the songs store

    Returns:
        list: The songs data loaded from the database
    """
    songs = grab_all_songs(
        db_type=db_type,
        db_path=db_path,
        album_art_dir=album_art_dir,
        filters={'album': album_name}
    )
    for song in songs:
        song_obj = Song(
            title=song['title'],
            duration=ms_to_mmss(song['duration'])
        )
        store.append(song_obj)
    return songs


def __round_image(filename, size, radius=15, shadow=True):
    """Round image corners using Cairo"""
    # load image
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        filename=filename,
        width=size,
        height=size,
        preserve_aspect_ratio=True
    )
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    
    # shadow config
    shadow_offset = 1
    shadow_blur = 3
    
    if shadow:
        canvas_width = width + shadow_blur
        canvas_height = height + shadow_blur
    else:
        canvas_width = width
        canvas_height = height
    
    # setup cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, canvas_width, canvas_height)
    ctx = cairo.Context(surface)
    
    # draw shadow
    if shadow:
        ctx.new_sub_path()
        ctx.arc(width - radius + shadow_offset, radius + shadow_offset, radius, -math.pi/2, 0)
        ctx.arc(width - radius + shadow_offset, height - radius + shadow_offset, radius, 0, math.pi/2)
        ctx.arc(radius + shadow_offset, height - radius + shadow_offset, radius, math.pi/2, math.pi)
        ctx.arc(radius + shadow_offset, radius + shadow_offset, radius, math.pi, 3*math.pi/2)
        ctx.close_path()
        ctx.set_source_rgba(0, 0, 0, 0.15)
        ctx.fill()
    
    # draw rounded rectangle
    ctx.new_sub_path()
    ctx.arc(width - radius, radius, radius, -math.pi/2, 0)
    ctx.arc(width - radius, height - radius, radius, 0, math.pi/2)
    ctx.arc(radius, height - radius, radius, math.pi/2, math.pi)
    ctx.arc(radius, radius, radius, math.pi, 3*math.pi/2)
    ctx.close_path()
    ctx.clip()
    
    # draw pixbuf
    Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
    ctx.paint()
    
    # convert to texture
    rounded_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, canvas_width, canvas_height)
    texture = Gdk.Texture.new_for_pixbuf(rounded_pixbuf)
    return texture