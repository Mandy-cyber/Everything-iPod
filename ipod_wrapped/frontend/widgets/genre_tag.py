import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango

def create_genre_tag(genre_info: dict, tag_size: int, content_box: Gtk.Box) -> Gtk.Button:
    """Creates a button with the name of a genre.

    Args:
        genre (dict): The genre and its associated songs
        tag_size (int): Max size of the tag to make.
        content_box (Gtk.Box): The box where the genre' songs & metadata will go

    Returns:
        Gtk.Button: The button/'tag' with the genre name
    """
    BUTTON_SIZE = tag_size + 5
    
    button = Gtk.Button()
    button.set_label(genre_info["genre"])
    button.set_size_request(BUTTON_SIZE, BUTTON_SIZE)
    button.set_hexpand(False)
    button.set_vexpand(False)
    button.add_css_class('genre-tag')
    
    button.connect("clicked", lambda btn: display_genre_songs(genre_info, content_box)) 
    return button
    
def display_genre_songs(genre_info: dict, content_box: Gtk.Box) -> None:
    """Displays the genre's songs and basic stats

    Args:
        genre_info (dict): The genre to display info/songs for
        content_box (Gtk.Box): The box where the display will go
    """
    # clean
    clear_content_box(content_box)
    
    # setup
    genre = genre_info["genre"]
    total_elapsed_ms = genre_info["total_elapsed_ms"]
    total_plays = genre_info("total_plays")
    
    # title + basic stats
    title = Gtk.Label(label=genre)
    title.set_justify(Gtk.Justification.CENTER)
    title.add_css_class('genre-title-label')
    
    
    
    # songs in this genre
    # song_listing = create_song_list(genre["songs"]) # TODO: come back and create


def clear_content_box(content_box: Gtk.Box) -> None:
    """Clears existing content from the given box"""
    pass # TODO: come back and complete