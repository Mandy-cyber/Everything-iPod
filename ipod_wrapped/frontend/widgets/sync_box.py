from typing import Optional, Callable, List
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib
from backend import LogAnalyser
from .banner import show_banner, hide_banner
import threading

def create_sync_box_widgets(error_banner: Optional[Adw.Banner], success_banner: Optional[Adw.Banner], refresh_callback: Optional[Callable]) -> List[Gtk.Widget]:
    """Creates the widgets that go on the 'Start Wrapped'
    page/expanded view.

    Args:
        error_banner (Adw.Banner): Banner for error messages
        success_banner (Adw.Banner): Banner for success messages
        refresh_callback: Function to call to refresh all pages after sync

    Returns:
        list: A list of the widgets.
    """
    # text
    title = Gtk.Label(label="iPod Wrapped")
    title.add_css_class('start-wrapped-title')

    subtitle = Gtk.Label(label="Sync your Listening History")
    subtitle.add_css_class('start-wrapped-subtitle')

    explainer = Gtk.Label(label="Make sure your iPod is plugged in and accessible in your filesystem. Once confirmed, click below to pull your listening log and album covers. Only songs and albums you've listened to will populate here automatically. With this we will generate/update your iPod Wrapped!\n\nThe first run will take a while, but subsequent updates will be much faster. Have fun!")
    explainer.set_wrap(True)
    explainer.set_max_width_chars(50)
    explainer.add_css_class('start-wrapped-explainer')
    
    # spinner
    spinner = Gtk.Spinner()
    spinner.set_halign(Gtk.Align.CENTER)
    spinner.set_visible(False)
    spinner.add_css_class('start-wrapped-spinner')

    # start button box
    box = Gtk.Box(spacing=6)
    icon = Gtk.Image(icon_name="drive-removable-media-usb-pendrive-symbolic")
    label = Gtk.Label(label="Start Wrapped")
    box.append(icon)
    box.append(label)
    
    # start button button
    start_btn = Gtk.Button(child=box)
    start_btn.add_css_class('start-wrapped-btn')
    start_btn.set_halign(Gtk.Align.CENTER)
    start_btn.set_valign(Gtk.Align.START)
    start_btn.connect("clicked", lambda btn: start_wrapped(start_btn, spinner, error_banner, success_banner, refresh_callback))

    widgets = [
        title, subtitle, explainer, spinner, start_btn
    ]
    return widgets

def start_wrapped(button: Gtk.Button, spinner: Gtk.Spinner,
                  error_banner: Optional[Adw.Banner], success_banner: Optional[Adw.Banner], refresh_callback: Optional[Callable]) -> None:
    """Starts the log analyser

    Args:
        button (Gtk.Button): The start button to disable during processing
        spinner (Gtk.Spinner): The spinner to show during processing
        error_banner (Adw.Banner): Banner for error messages
        success_banner (Adw.Banner): Banner for success messages
        refresh_callback: Function to call to refresh all pages after sync
    """
    # hide any prev. banners
    if error_banner:
        hide_banner(error_banner)
    if success_banner:
        hide_banner(success_banner)

    # show loading icon + disable button
    button.set_sensitive(False)
    spinner.set_visible(True)
    spinner.start()

    def run_analysis():
        """Run the analysis in a background thread"""
        analyser = LogAnalyser("local")
        result = analyser.run()
        
        # update UI on main thread
        GLib.idle_add(analysis_complete, result, button, spinner,
                     error_banner, success_banner, refresh_callback)

    # start analyser in background thread
    thread = threading.Thread(target=run_analysis)
    thread.daemon = True
    thread.start()

def analysis_complete(result: dict, button: Gtk.Button,
                     spinner: Gtk.Spinner, error_banner: Optional[Adw.Banner],
                     success_banner: Optional[Adw.Banner], refresh_callback: Optional[Callable]) -> bool:
    """Called when analysis is complete to update UI

    Args:
        result (dict): Result from analyser.run()
        button (Gtk.Button): The start button to re-enable
        spinner (Gtk.Spinner): The spinner to hide
        error_banner (Adw.Banner): Banner for error messages
        success_banner (Adw.Banner): Banner for success messages
        refresh_callback: Function to call to refresh all pages after sync

    Returns:
        bool: False to prevent GLib from calling this again
    """
    # hide spinner and re-enable button
    spinner.stop()
    spinner.set_visible(False)
    button.set_sensitive(True)

    if "error" in result:
        if error_banner:
            show_banner(error_banner, result["error"])
    else:
        if success_banner:
            show_banner(success_banner, result["success"])
        # refresh all pages to show new data
        if refresh_callback:
            refresh_callback()

    return False