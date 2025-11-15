import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw
from .sync_box import create_sync_box_widgets

def create_bottom_bar(toggle_callback, error_banner: Adw.Banner, success_banner: Adw.Banner, refresh_callback) -> tuple[Gtk.Box, Gtk.Box]:
    """Creates the bottom bar with collapsed and expanded views.

    Args:
        toggle_callback: Function to call when toggling the bar
        error_banner (Adw.Banner): Banner for error messages
        success_banner (Adw.Banner): Banner for success messages
        refresh_callback: Function to call to refresh all pages after sync
    """
    # collapsed view (horizontal bar)
    collapsed_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    collapsed_bar.set_hexpand(True)
    collapsed_bar.add_css_class('bottom-bar-collapsed')

    # expand button + spacers
    spacer_left = Gtk.Box()
    spacer_left.set_hexpand(True)
    collapsed_bar.append(spacer_left)

    expand_button = create_toggle_button('pan-up-symbolic', 'bottom-bar-expand-btn', toggle_callback)
    collapsed_bar.append(expand_button)

    spacer_right = Gtk.Box()
    spacer_right.set_hexpand(True)
    collapsed_bar.append(spacer_right)

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

    # add widgets to expand page
    widgets = create_sync_box_widgets(error_banner, success_banner, refresh_callback)
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