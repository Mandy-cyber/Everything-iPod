import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio, GObject

# TODO: paginate table

class Song(GObject.Object):
    """Represents a song in the table """
    __gtype_name__ = 'Song'
    
    is_playing = GObject.Property(type=bool, default=False)
    title = GObject.Property(type=str, default='')
    artist = GObject.Property(type=str, default='')
    album = GObject.Property(type=str, default='')
    duration = GObject.Property(type=str, default='')
    
    def __init__(self, title: str, artist: str, album: str, duration: str) -> None:
        """Initialize with song data"""
        super().__init__()
        self.is_playing = False
        self.title = title
        self.artist = artist
        self.album = album
        self.duration = duration

def create_song_store() -> Gio.ListStore:
    """Creates a list store for songs."""
    return Gio.ListStore(item_type=Song)
    
def create_song_selection_model(store: Gio.ListStore) -> tuple[Gtk.SingleSelection, Gtk.SortListModel]:
    """Wraps the given store in a sort model and single selection model.

    Returns:
        tuple: (selection_model, sort_model)
    """
    # wrap store in sort model
    sort_model = Gtk.SortListModel(model=store)
    # wrap sort model in selection model
    selection_model = Gtk.SingleSelection(model=sort_model, can_unselect=True)
    return selection_model, sort_model

def _setup_title_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """Setup callback for title column."""
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
    box.add_css_class('song-row')

    play_icon = Gtk.Label()
    box.append(play_icon)
    title_label = Gtk.Label(xalign=0)
    box.append(title_label)

    list_item.set_child(box)

def _bind_title_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """Bind callback for title column."""
    box = list_item.get_child()
    song_obj: Song = list_item.get_item()
    
    play_icon: Gtk.Label = box.get_first_child()
    play_icon_content = "▶" if song_obj.is_playing else ""
    play_icon.set_label(play_icon_content)
    
    title_label: Gtk.Label = box.get_last_child()
    title_label.set_label(song_obj.title)

def _setup_artist_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """ Setup callback for artist column."""
    artist_label = Gtk.Label(xalign=0)
    list_item.set_child(artist_label)

def _bind_artist_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """Bind callback for artist column."""
    song_obj: Song = list_item.get_item()
    artist_label: Gtk.Label = list_item.get_child()
    artist_label.set_label(song_obj.artist)

def _setup_album_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """Setup callback for album column."""
    album_label = Gtk.Label(xalign=0)
    list_item.set_child(album_label)

def _bind_album_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """Bind callback for album column."""
    song_obj: Song = list_item.get_item()
    album_label: Gtk.Label = list_item.get_child()
    album_label.set_label(song_obj.album)

def _setup_duration_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """ Setup callback for duration column."""
    duration_label = Gtk.Label(xalign=1)
    list_item.set_child(duration_label)

def _bind_duration_column(factory: Gtk.SignalListItemFactory, list_item: Gtk.ListItem) -> None:
    """Bind callback for duration column."""
    song_obj: Song = list_item.get_item()
    duration_label: Gtk.Label = list_item.get_child()
    duration_label.set_label(song_obj.duration)

def _create_column_sorter(column: Gtk.ColumnViewColumn, prop_name: str):
    """Creates a sorter for the given column"""
    # create expression
    prop_exp = Gtk.PropertyExpression.new(Song, None, prop_name)
    
    # create sorter
    property_type = Song.find_property(prop_name).value_type.fundamental
    if property_type == GObject.TYPE_STRING:
        sorter = Gtk.StringSorter.new(prop_exp)
    elif property_type == GObject.TYPE_BOOLEAN:
        sorter = Gtk.NumericSorter.new(prop_exp)
    
    # set the sorter on the column
    column.set_sorter(sorter)

def create_songs_table(selection_model: Gtk.SelectionModel, sort_model: Gtk.SortListModel, scroll_to_top_callback=None) -> Gtk.ColumnView:
    """Creates the ColumnView (i.e. songs table)."""
    # setup table
    column_view = Gtk.ColumnView(model=selection_model)
    column_view.set_show_row_separators(True)
    column_view.set_show_column_separators(False)
    column_view.add_css_class('songs-table')

    # title column
    title_factory = Gtk.SignalListItemFactory()
    title_factory.connect("setup", _setup_title_column)
    title_factory.connect("bind", _bind_title_column)
    title_column = Gtk.ColumnViewColumn(title="Title", factory=title_factory)
    title_column.set_resizable(True)
    title_column.set_fixed_width(180)
    title_column.set_expand(True)
    _create_column_sorter(title_column, 'title')
    column_view.append_column(title_column)

    # artist column
    artist_factory = Gtk.SignalListItemFactory()
    artist_factory.connect("setup", _setup_artist_column)
    artist_factory.connect("bind", _bind_artist_column)
    artist_column = Gtk.ColumnViewColumn(title="Artist", factory=artist_factory)
    artist_column.set_resizable(True)
    artist_column.set_fixed_width(150)
    artist_column.set_expand(True)
    _create_column_sorter(artist_column, 'artist')
    column_view.append_column(artist_column)

    # album column
    album_factory = Gtk.SignalListItemFactory()
    album_factory.connect("setup", _setup_album_column)
    album_factory.connect("bind", _bind_album_column)
    album_column = Gtk.ColumnViewColumn(title="Album", factory=album_factory)
    album_column.set_resizable(True)
    album_column.set_fixed_width(180)
    album_column.set_expand(True)
    _create_column_sorter(album_column, 'album')
    column_view.append_column(album_column)

    # duration column
    duration_factory = Gtk.SignalListItemFactory()
    duration_factory.connect("setup", _setup_duration_column)
    duration_factory.connect("bind", _bind_duration_column)
    duration_column = Gtk.ColumnViewColumn(title="Duration", factory=duration_factory)
    duration_column.set_resizable(True)
    duration_column.set_fixed_width(70)
    _create_column_sorter(duration_column, 'duration')
    column_view.append_column(duration_column)

    sort_model.set_sorter(column_view.get_sorter())

    if scroll_to_top_callback:
        sort_model.connect('items-changed', lambda *args: scroll_to_top_callback())

    return column_view