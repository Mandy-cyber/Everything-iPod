import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from backend import grab_all_metadata, has_data
from ..widgets.album_button import create_album_button


class AlbumsPage(Gtk.ScrolledWindow):
    """Page displaying album grid"""

    def __init__(self, db_type: str, db_path: str, album_art_dir: str, toggle_bottom_bar_callback=None):
        super().__init__()

        # setup
        self.IMAGE_SIZE = 120
        self.toggle_bottom_bar = toggle_bottom_bar_callback
        self.db_type = db_type
        self.db_path = db_path
        self.album_art_dir = album_art_dir

        # setup scrollable window
        self.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )
        self.add_css_class('page-area')

        # setup flowbox for responsive layout
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(30)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_homogeneous(True)
        self.set_child(self.flowbox)

        # load albums
        self._load_albums()

    def _load_albums(self):
        """Load and display albums from database"""
        # check if data exists in database
        albums = []
        if has_data(self.db_type, self.db_path):
            albums = grab_all_metadata(
                db_type=self.db_type,
                db_path=self.db_path,
                album_art_dir=self.album_art_dir
            )

        if len(albums) == 0 and self.toggle_bottom_bar:
            # wait to toggle
            GLib.idle_add(self.toggle_bottom_bar)
        else:
            self.albums = albums
            # populate with album buttons
            for album in albums:
                button = create_album_button(album, self.IMAGE_SIZE)
                self.flowbox.append(button)

    def refresh(self):
        """Refresh the page by reloading albums from database"""
        # clear existing album buttons
        while True:
            child = self.flowbox.get_first_child()
            if child is None:
                break
            self.flowbox.remove(child)

        # reload albums
        self._load_albums()
