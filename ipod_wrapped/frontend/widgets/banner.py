from typing import Optional, Any
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib

def create_banner(message: str, banner_type: str = "info") -> Adw.Banner:
    """Creates a banner widget for displaying messages

    Args:
        message (str): The message to display
        banner_type (str): Type of banner - "info", "error", or "success"

    Returns:
        Adw.Banner: The configured banner widget
    """
    # setup
    banner = Adw.Banner(title=message)
    banner.set_revealed(False)
    banner.set_button_label("")
    banner.set_use_markup(False)

    # add styling
    if banner_type == "error":
        banner.add_css_class('banner-error')
    elif banner_type == "success":
        banner.add_css_class('banner-success')
    else:
        banner.add_css_class('banner-info')

    return banner


def show_banner(banner: Adw.Banner, message: Optional[str] = None, auto_dismiss: bool = True) -> None:
    """Shows the banner with an optional new message

    Args:
        banner (Adw.Banner): The banner to show
        message (str, optional): A different message to display
        auto_dismiss (bool, optional): Auto-hide banner after 5 seconds. Defaults to True.
    """
    if message:
        banner.set_title(message)
    banner.set_revealed(True)

    # auto-dismiss after 5 seconds (logic from claude)
    if auto_dismiss:
        timeout_id: Any = getattr(banner, '_timeout_id', None)
        if timeout_id:
            GLib.source_remove(timeout_id)

        setattr(banner, '_timeout_id', GLib.timeout_add_seconds(5, lambda: _auto_hide_banner(banner)))


def hide_banner(banner: Adw.Banner) -> None:
    """Hides the banner

    Args:
        banner (Adw.Banner): The banner to hide
    """
    # cancel any pending auto-dismiss timeout (logic from claude)
    timeout_id: Any = getattr(banner, '_timeout_id', None)
    if timeout_id:
        GLib.source_remove(timeout_id)
        setattr(banner, '_timeout_id', None)

    banner.set_revealed(False)


def _auto_hide_banner(banner: Adw.Banner) -> bool:
    """Internal function to auto-hide banner after timeout

    Args:
        banner (Adw.Banner): The banner to hide

    Returns:
        bool: False to prevent GLib from calling this again
    """
    # (logic from claude)
    banner.set_revealed(False)
    setattr(banner, '_timeout_id', None)
    return False
