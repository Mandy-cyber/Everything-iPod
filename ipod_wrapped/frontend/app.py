import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw

from .pages import AlbumsPage, SongsPage, WrappedPage, GenresPage
from .widgets.bottom_bar import create_bottom_bar
from .widgets.banner import create_banner
from .widgets.menu_nav import create_menu_nav

class MainWindow(Adw.ApplicationWindow):
    """Main application window with navigation"""
    def __init__(self, app, db_type="local", db_path="storage/ipod_wrapped.db", album_art_dir="storage/album-art"):
        super().__init__(application=app)
        
        # setup css
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("gtk_style.css")
        display = Gdk.Display.get_default()
        if display is not None:
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
        self.genres_page = GenresPage(db_type, db_path, album_art_dir, self.toggle_bottom_bar)
        self.albums_page = AlbumsPage(db_type, db_path, album_art_dir, self.toggle_bottom_bar)
        self.songs_page = SongsPage(db_type, db_path, album_art_dir, self.toggle_bottom_bar)
        self.wrapped_page = WrappedPage()
        
        # page titles w/icons
        self.stack.add_titled_with_icon(self.genres_page, "genres", "Genres", "org.gnome.Nautilus-symbolic")
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

        # wrap stack in overlay for floating menu button
        self.overlay = Gtk.Overlay()
        self.overlay.set_child(self.stack)

        # create banner placeholders
        self.error_banner = create_banner("", "error")
        self.success_banner = create_banner("", "success")

        # create menu nav button
        self.menu_btn = create_menu_nav(self.overlay, self, self.error_banner,
                                        self.success_banner, self.refresh_all_pages)
        self.overlay.add_overlay(self.menu_btn)

        # add overlay to main box
        main_box.append(self.overlay)

        # create bottom bar
        self.bottom_bar_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.bottom_bar_container.set_hexpand(True)
        self.collapsed_bar, self.expanded_bar = create_bottom_bar(self.toggle_bottom_bar)
        self.bottom_bar_container.append(self.collapsed_bar)
        self.bottom_bar_container.append(self.expanded_bar)

        self.bottom_bar_expanded = False

        # add bar to main box
        main_box.append(self.bottom_bar_container)

        # place banners (flush with bottom of window)
        main_box.append(self.error_banner)
        main_box.append(self.success_banner)
            
    
    def refresh_all_pages(self) -> None:
        """Refresh all pages after data has been updated"""
        # refresh albums page
        if hasattr(self.albums_page, 'refresh'):
            self.albums_page.refresh()

        # refresh songs page
        if hasattr(self.songs_page, 'refresh'):
            self.songs_page.refresh()

        # refresh wrapped page
        if hasattr(self.wrapped_page, 'refresh'):
            self.wrapped_page.refresh()  # type: ignore

    def toggle_bottom_bar(self) -> None:
        """Toggle between collapsed and expanded bottom bar"""
        self.bottom_bar_expanded = not self.bottom_bar_expanded

        if self.bottom_bar_expanded:
            # hide pages and mini bar, show full view
            self.stack.set_visible(False)
            self.collapsed_bar.set_visible(False)
            self.expanded_bar.set_visible(True)
            self.expanded_bar.set_vexpand(True)
        else:
            # show pages and mini bar, hide full view
            self.stack.set_visible(True)
            self.collapsed_bar.set_visible(True)
            self.expanded_bar.set_visible(False)
            self.expanded_bar.set_vexpand(False)


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