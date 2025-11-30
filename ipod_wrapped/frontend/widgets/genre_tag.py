import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from .genre_songs import display_genre_songs

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