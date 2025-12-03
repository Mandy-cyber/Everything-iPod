import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

def create_curr_song_and_queue_view() -> Gtk.Box:
    """"""
    # will show:
    # - cover art
    # - song name, artist, album, genres
    #   - option to edit the above
    # - song stats
    # - back, play/pause, forward, shuffle, repeat icons
    # - list of songs coming up in queue
    pass