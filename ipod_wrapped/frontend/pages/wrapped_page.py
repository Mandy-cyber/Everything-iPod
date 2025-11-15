import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk


class WrappedPage(Gtk.Box):
    """Page displaying wrapped statistics"""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        # Placeholder label
        label = Gtk.Label(label="Wrapped Stats Page - Coming Soon")
        label.set_margin_top(50)
        label.set_margin_bottom(50)
        self.append(label)
