import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib, Gio

from backend import has_data, grab_all_songs, ms_to_mmss
from ..widgets.songs_table import create_song_store, create_song_selection_model, create_songs_table, Song
from ..widgets.song_info import display_song_info

# TODO: fix 'sorter' not bringing user back to top of table.
# TODO: fix wonky resizing

class SongsPage(Gtk.Box):
    """Page displaying songs list"""
    def __init__(self, db_type: str, db_path: str, album_art_dir: str, toggle_bottom_bar_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # setup
        self.toggle_bottom_bar = toggle_bottom_bar_callback
        self.db_type = db_type
        self.db_path = db_path
        self.album_art_dir = album_art_dir
        self.selected_song_index = None

        self.add_css_class('page-area')
        self.add_css_class('songs-page')
        self.set_vexpand(True)
        self.set_hexpand(True)

        # song info display (initially hidden)
        self.song_info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.song_info_box.add_css_class('song-info-container')
        self.song_info_box.set_visible(False)
        self.append(self.song_info_box)

        # setup store + models
        self.store: Gio.ListStore = create_song_store()
        self.selection, self.sort_model = create_song_selection_model(self.store)

        # scrolled window for table
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(
            Gtk.PolicyType.NEVER,
            Gtk.PolicyType.AUTOMATIC
        )
        self.scrolled_window.set_vexpand(True)

        # create table
        self.songs_table: Gtk.ColumnView = create_songs_table(
            self.selection,
            self.sort_model,
            scroll_to_top_callback=self._scroll_to_top
        )
        self.scrolled_window.set_child(self.songs_table)
        self.append(self.scrolled_window)

        # selection changed signal
        self.selection.connect('selection-changed', self._on_selection_changed)

        # load songs
        self._load_songs()
    
    def _load_songs(self) -> None:
        """Load songs into the songs store"""
        songs = []
        if has_data(self.db_type, self.db_path):
            songs = grab_all_songs(
                db_type=self.db_type,
                db_path=self.db_path,
                album_art_dir=self.album_art_dir
            )

        if len(songs) == 0 and self.toggle_bottom_bar:
            # wait to toggle
            GLib.idle_add(self.toggle_bottom_bar)
        else:
            self.songs = songs
            # populate with songs
            for song in songs:
                song_obj = Song(
                    title=song['title'],
                    artist=song['artist'],
                    album=song['album'],
                    duration=ms_to_mmss(song['duration'])
                )
                self.store.append(song_obj)

            # auto-select first song
            if len(songs) > 0:
                GLib.idle_add(self._select_first_song)

    def _select_first_song(self) -> bool:
        """Selects the first song in the table and retriggers display"""
        if self.store.get_n_items() > 0:
            self.selection.set_selected(0)
            self._update_song_display()
        return False

    def _update_song_display(self) -> None:
        """Update the song info display based on current selection"""
        selected = self.selection.get_selected_item()
        if selected is None:
            # no selection, hide song info
            self.song_info_box.set_visible(False)
            self.selected_song_index = None
            return

        # get position
        selected_pos = self.selection.get_selected()

        # find song data
        song_data = None
        if isinstance(selected, Song):
            for song in self.songs:
                if (song['title'] == selected.title and
                    song['artist'] == selected.artist and
                    song['album'] == selected.album):
                    song_data = song
                    self.selected_song_index = selected_pos
                    break

        if song_data:
            # clear box
            child = self.song_info_box.get_first_child()
            while child:
                self.song_info_box.remove(child)
                child = self.song_info_box.get_first_child()

            # rebuild
            song_info_widget = display_song_info(song_data)
            self.song_info_box.append(song_info_widget)
            self.song_info_box.set_visible(True)

    def _on_selection_changed(self, selection: Gtk.SingleSelection, position: int, n_items: int) -> None:
        """Handle selection change in the table"""
        self._update_song_display()

    def _scroll_to_top(self) -> None:
        """Scroll to the top of the table"""
        vadj = self.scrolled_window.get_vadjustment()
        if vadj:
            vadj.set_value(0)

    def refresh(self) -> None:
        """Refresh the page by reloading songs from database"""
        self.store.remove_all()
        self.song_info_box.set_visible(False)
        self.selected_song_index = None
        self._load_songs()