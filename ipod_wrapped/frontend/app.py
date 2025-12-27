import sys
import os
import pathlib
import shutil
import traceback
import time
from datetime import datetime
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Adw

from .pages import AlbumsPage, SongsPage, WrappedPage, GenresPage
from .widgets.bottom_bar import create_bottom_bar
from .widgets.banner import create_banner
from .widgets.menu_nav import create_menu_nav
from backend.constants import DEFAULT_DB_PATH, DEFAULT_ALBUM_ART_DIR, STORAGE_DIR

class MainWindow(Adw.ApplicationWindow):
    """Main application window with navigation"""
    def __init__(self, app, db_type="local", db_path=DEFAULT_DB_PATH, album_art_dir=DEFAULT_ALBUM_ART_DIR):
        super().__init__(application=app)

        # check storage dir exists
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        DEFAULT_ALBUM_ART_DIR.mkdir(parents=True, exist_ok=True)

        # include missing_album_cover.jpg in storage
        missing_cover_dest = DEFAULT_ALBUM_ART_DIR / "missing_album_cover.jpg"
        if not missing_cover_dest.exists():
            missing_cover_src = pathlib.Path(__file__).parent.parent / "storage" / "album_art" / "missing_album_cover.jpg"
            if missing_cover_src.exists():
                shutil.copy2(missing_cover_src, missing_cover_dest)

        # setup css
        css_provider = Gtk.CssProvider()
        # find css file location
        css_path = pathlib.Path(__file__).parent.parent / "gtk_style.css"
        if css_path.exists():
            css_provider.load_from_path(str(css_path))
        else:
            print(f"warning: css file not found at {css_path}")
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
        self.wrapped_page = WrappedPage(db_type, db_path, album_art_dir, self.toggle_bottom_bar)
        
        # page titles w/icons
        self.stack.add_titled_with_icon(self.genres_page, "genres", "Genres", "view-list-symbolic")
        self.stack.add_titled_with_icon(self.albums_page, "albums", "Albums", "media-optical-symbolic")
        self.stack.add_titled_with_icon(self.songs_page, "songs", "Songs", "audio-x-generic-symbolic")
        self.stack.add_titled_with_icon(self.wrapped_page, "wrapped", "Wrapped", "starred-symbolic")
        
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

        # create menu nav button + 'Start Wrapped' dialog
        self.menu_btn, self.open_start_wrapped_dialog = create_menu_nav(
            self.overlay, self, self.error_banner,
            self.success_banner, self.refresh_all_pages
        )
        self.overlay.add_overlay(self.menu_btn)
        self.genres_page.set_start_wrapped_callback(self.open_start_wrapped_dialog)

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
        # refresh genres page
        if hasattr(self.genres_page, 'refresh'):
            self.genres_page.refresh()

        # refresh albums page
        if hasattr(self.albums_page, 'refresh'):
            self.albums_page.refresh()

        # refresh songs page
        if hasattr(self.songs_page, 'refresh'):
            self.songs_page.refresh()

        # refresh wrapped page
        if hasattr(self.wrapped_page, 'refresh'):
            self.wrapped_page.refresh()

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
        # force dark mode
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        win = MainWindow(self)
        win.present()


def setup_logging():
    """redirect stdout/stderr to log file"""
    try:
        # determine log file location
        if hasattr(sys, '_MEIPASS'):
            # running as pyinstaller bundle - log next to exe
            log_dir = pathlib.Path(sys.executable).parent
        else:
            # running from source - log in storage
            log_dir = pathlib.Path(__file__).parent.parent / "storage"

        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "ipod_wrapped.log"

        # append to existing log
        log_handle = open(log_file, 'a', buffering=1)
        sys.stdout = log_handle
        sys.stderr = log_handle

        print(f"\n\n{'='*60}")
        print(f"log session started at {datetime.now()}")
        print(f"python version: {sys.version}")
        print(f"executable: {sys.executable}")
        print(f"{'='*60}\n")

    except Exception as e:
        # if logging setup fails, just continue without it
        pass


def run():
    """Run the application"""
    try:
        setup_logging()
        app = iPodWrappedApp()
        app.run(sys.argv)
    except Exception as e:
        print(f"\nfatal error: {e}")
        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    run()