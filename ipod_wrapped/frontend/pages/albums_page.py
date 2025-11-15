import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from backend import grab_all_metadata
from ..widgets.album_button import create_album_button


class AlbumsPage(Gtk.ScrolledWindow):
    """Page displaying album grid"""

    def __init__(self, db_type: str, db_path: str, album_art_dir: str):
        super().__init__()

        self.IMAGE_SIZE = 120

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

        # load and create album buttons
        albums = grab_all_metadata(
            db_type=db_type,
            db_path=db_path,
            album_art_dir=album_art_dir
        )

        for album in albums:
            button = create_album_button(album, self.IMAGE_SIZE)
            self.flowbox.append(button)
            
        #
