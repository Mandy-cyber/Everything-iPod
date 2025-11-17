import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

def create_bottom_bar(toggle_callback) -> tuple[Gtk.Box, Gtk.Box]:
    """Creates the bottom bar with collapsed and expanded views.
    
    Collapsed = currently playing song
    Expanded = queue UI and expanded 'currently playing'

    Args:
        toggle_callback: Function to call when toggling the bar
    """
    # collapsed view (horizontal bar)
    collapsed_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    collapsed_bar.set_hexpand(True)
    collapsed_bar.add_css_class('bottom-bar-collapsed')

    # expand button + spacers
    # TODO: on bottom bar click show expanded
    # TODO: add currently playing UI elements here

    # expanded view
    expanded_bar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    expanded_bar.set_vexpand(True)
    expanded_bar.set_hexpand(True)
    expanded_bar.add_css_class('bottom-bar-expanded')
    expanded_bar.set_visible(False)

    collapse_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    collapse_container.set_hexpand(True)

    # collapse button + spacers
    collapse_spacer_left = Gtk.Box()
    collapse_spacer_left.set_hexpand(True)
    collapse_container.append(collapse_spacer_left)

    collapse_button = create_toggle_button('pan-down-symbolic', 'bottom-bar-collapse-btn', toggle_callback)
    collapse_container.append(collapse_button)

    collapse_spacer_right = Gtk.Box()
    collapse_spacer_right.set_hexpand(True)
    collapse_container.append(collapse_spacer_right)
    expanded_bar.append(collapse_container)

    # add queue ui widgets to expanded view
    widgets = []
    [expanded_bar.append(widget) for widget in widgets]

    return collapsed_bar, expanded_bar

def create_toggle_button(icon_name: str, css_class: str, toggle_callback) -> Gtk.Button:
    """Creates a toggle button with given icon, styling, and
    callback functionality.
    
    Args:
        icon_name (str): the button's icon
        css_class (str): the name of the css class to apply
        toggle_callback: Function to call when the button is clicked
    
    Return:
        Gtk.Button: the toggleable button
    """
    toggle_button = Gtk.Button()
    toggle_button.set_icon_name(icon_name)
    toggle_button.add_css_class(css_class)
    toggle_button.set_halign(Gtk.Align.CENTER)
    toggle_button.set_valign(Gtk.Align.START)
    toggle_button.connect("clicked", lambda btn: toggle_callback())
    return toggle_button


# TODO: these stubs will be implemented later
def update_now_playing(song_metadata: dict) -> None:
    """Update the bottom bar with currently playing song info

    Args:
        song_metadata (dict): Metadata including song, artist, album, art_path
    """
    pass


def update_playback_state(is_playing: bool, is_paused: bool) -> None:
    """Update play/pause button state

    Args:
        is_playing (bool): Whether music is currently playing
        is_paused (bool): Whether playback is paused
    """
    pass


def update_position(position_ms: int, duration_ms: int) -> None:
    """Update progress bar and time display

    Args:
        position_ms (int): Current position in milliseconds
        duration_ms (int): Total duration in milliseconds
    """
    pass


def update_queue_display(queue: list) -> None:
    """Update the expanded queue view

    Args:
        queue (list): List of queued songs with metadata
    """
    pass