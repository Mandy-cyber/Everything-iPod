import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from backend.constants import DEFAULT_SCALE_TIER
from ..widgets.stats_filters import StatsFilters


class WrappedPage(Gtk.ScrolledWindow):
    """Page displaying wrapped statistics"""

    def __init__(self, db_type: str, db_path: str, album_art_dir: str, toggle_bottom_bar_callback=None):
        super().__init__()

        # setup
        self.toggle_bottom_bar = toggle_bottom_bar_callback
        self.db_type = db_type
        self.db_path = db_path
        self.album_art_dir = album_art_dir
        self.tier = DEFAULT_SCALE_TIER
        self.stats_filter = StatsFilters()

        self.add_css_class('page-area')
        self.add_css_class('wrapped-page')
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        
        # paned - right
        sw_right = Gtk.ScrolledWindow()
        sw_right.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        sw_right.add_css_class('generated-stats-scrolled')
        sw_right.set_hexpand(True)
        sw_right.set_vexpand(True)

        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.right_box.add_css_class('generated-stats-pane')
        sw_right.set_child(self.right_box)
        
        # paned - left
        sw_left = Gtk.ScrolledWindow()
        sw_left.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        sw_left.set_hexpand(True)
        sw_left.set_vexpand(True)
        sw_left.set_child(self.stats_filter.create_wrapped_box(
            self.right_box, {'db_type': self.db_type, 'db_path': self.db_path}
        ))

        # finish paned setup
        paned.set_start_child(sw_left)
        paned.set_end_child(sw_right)
        paned.set_position(400)
        paned.set_resize_start_child(True)
        paned.set_resize_end_child(True)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        
        self.set_child(paned)
        
        
    def rescale(self, tier: str) -> None:
        """Store the current tier for when stats visuals are generated"""
        self.tier = tier
        self.stats_filter.tier = tier

    def refresh(self) -> None:
        """Refresh the page by reloading data from database"""
        pass
        
        
        
        
