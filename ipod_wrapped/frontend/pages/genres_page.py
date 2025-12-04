import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

from backend import has_data, create_genre_mappings
from ..widgets.genre_tag import create_genre_tag


class GenresPage(Gtk.ScrolledWindow):
    """Page displaying genres list"""

    def __init__(self, db_type: str, db_path: str, album_art_dir: str, toggle_bottom_bar_callback=None):
        super().__init__()

        # setup
        self.TAG_SIZE = 50
        self.toggle_bottom_bar = toggle_bottom_bar_callback
        self.open_start_wrapped = None
        self.db_type = db_type
        self.db_path = db_path
        self.album_art_dir = album_art_dir

        self.add_css_class('page-area')
        self.add_css_class('genres-page')
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)

        # paned - right
        sw_right = Gtk.ScrolledWindow()
        sw_right.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        sw_right.add_css_class('genre-breakdown-scrolled')

        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right_box.set_size_request(215, -1)
        self.right_box.add_css_class('genre-breakdown-pane')
        sw_right.set_child(self.right_box)
        
        # paned - left
        sw_left = Gtk.ScrolledWindow()
        sw_left.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(30)
        self.flowbox.set_min_children_per_line(1)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flowbox.set_column_spacing(0)
        self.flowbox.set_row_spacing(0)
        self.flowbox.set_homogeneous(True)

        sw_left.set_child(self.flowbox)
        
        # finish paned setup
        paned.set_start_child(sw_left)
        paned.set_end_child(sw_right)
        paned.set_position(400)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(False)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        
        self.set_child(paned)
        
    def _load_genre_tags(self) -> None:
        """Load and display genres from database"""
        # check if data exists in database
        genre_mappings = []
        if has_data(self.db_type, self.db_path):
            genre_mappings = create_genre_mappings(
                db_type=self.db_type,
                db_path=self.db_path,
                album_art_dir=self.album_art_dir
            )
            
        if len(genre_mappings) == 0 and self.open_start_wrapped:
            # open 'Start Wrapped' popup
            GLib.idle_add(self.open_start_wrapped)
        else:
            self.genre_mappings = sorted(genre_mappings, key=lambda d: d['genre'])
            # populate with genre tags
            first_tag = None
            for genre in self.genre_mappings:
                tag = create_genre_tag(genre, self.TAG_SIZE, self.right_box)
                self.flowbox.append(tag)
                if first_tag is None:
                    first_tag = tag

            # auto-click first genre tag
            if first_tag:
                first_tag.emit('clicked')
                
    def set_start_wrapped_callback(self, callback) -> None:
        """Set the callback to open the 'Start Wrapped' popup"""
        self.open_start_wrapped = callback
        self._load_genre_tags()

    def refresh(self) -> None:
        """Refresh the page by reloading genres from database"""
        # clear existing genre tags
        while True:
            child = self.flowbox.get_first_child()
            if child is None:
                break
            self.flowbox.remove(child)

        # reload tags
        self._load_genre_tags()