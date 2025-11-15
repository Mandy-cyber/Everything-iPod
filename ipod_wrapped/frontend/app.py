import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw
from .pages import AlbumsPage, SongsPage, WrappedPage

class MainWindow(Adw.ApplicationWindow):
    """Main application window with navigation"""
    def __init__(self, app, db_type="local", db_path="../sample-files/ipod_wrapped.db", album_art_dir="../sample-files/album-art"):
        super().__init__(application=app)
        
        # setup css
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("gtk_style.css")
        display = Gdk.Display.get_default()
        Gtk.StyleContext.add_provider_for_display(
            display,
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # window params
        self.set_default_size(650, 500)
        self.set_title("iPod Wrapped")
        
        # store config
        self.db_type = db_type
        self.db_path = db_path
        self.album_art_dir = album_art_dir
        
        # main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)
        
        # setup view stack
        self.stack = Adw.ViewStack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        
        # add pages to stack
        self.albums_page = AlbumsPage(db_type, db_path, album_art_dir)
        self.songs_page = SongsPage()
        self.wrapped_page = WrappedPage()
        
        # Replace these lines:
        self.stack.add_titled_with_icon(self.albums_page, "albums", "Albums", "media-optical-symbolic")
        self.stack.add_titled_with_icon(self.songs_page, "songs", "Songs", "audio-x-generic-symbolic")
        self.stack.add_titled_with_icon(self.wrapped_page, "wrapped", "Wrapped", "emblem-favorite-symbolic")
        
        # create view switcher
        view_switcher = Adw.ViewSwitcher()
        view_switcher.set_stack(self.stack)
        view_switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        
        # create header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(view_switcher)
        main_box.append(header_bar)
        
        # add stack to main box
        main_box.append(self.stack)
        
        # create bottom bar
        self.bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.bottom_bar.set_hexpand(True)
        self.bottom_bar.add_css_class('bottom-bar')
        main_box.append(self.bottom_bar)
        
        # Track visibility state
        self.bottom_bar_visible = True
    
    def toggle_bottom_bar(self):
        """Toggle bottom bar visibility"""
        self.bottom_bar_visible = not self.bottom_bar_visible
        self.bottom_bar.set_visible(self.bottom_bar_visible)
    
    def show_bottom_bar(self):
        """Show the bottom bar"""
        self.bottom_bar_visible = True
        self.bottom_bar.set_visible(True)
    
    def hide_bottom_bar(self):
        """Hide the bottom bar"""
        self.bottom_bar_visible = False
        self.bottom_bar.set_visible(False)


class iPodWrappedApp(Adw.Application):
    """GTK Application wrapper"""
    def __init__(self):
        super().__init__(application_id="com.mandycyber.iPodWrapped")
    
    def do_activate(self):
        win = MainWindow(self)
        win.present()


def run():
    """Run the application"""
    app = iPodWrappedApp()
    app.run(sys.argv)


if __name__ == "__main__":
    run()