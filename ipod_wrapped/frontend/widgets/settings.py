import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from typing import Optional
from gi.repository import Gtk, Adw, GLib
import keyring as kr

from backend.constants import SERVICE_NAME
from backend.creds_manager import has_credentials, save_credentials, delete_credentials
from .banner import show_banner, hide_banner

def create_settings_dialog(
    window: Gtk.ApplicationWindow, error_banner: Optional[Adw.Banner] = None, 
    success_banner: Optional[Adw.Banner] = None) -> Adw.Dialog:
    """Creates the 'Settings' popup/dialog"""
    # create dialog
    dialog = Adw.Dialog()
    dialog.set_title('Settings')
    
    # create content box
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    content.set_margin_top(0)
    content.set_margin_bottom(20)
    content.set_margin_start(20)
    content.set_margin_end(20)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.START)
    content.add_css_class('settings-box')

    # text
    title = Gtk.Label(label="Settings")
    title.add_css_class('settings-title')
    title.set_margin_bottom(5)

    # status label
    status_label = Gtk.Label()
    status_label.add_css_class('settings-status')

    # subtitle = Gtk.Label(label="API Configuration")
    # subtitle.add_css_class('settings-subtitle')

    explainer = Gtk.Label(label="To fetch genre and album metadata, we need Last.fm API credentials. These are securely stored in your local keyring and never leave your device.")
    explainer.set_wrap(True)
    explainer.set_max_width_chars(50)
    explainer.set_justify(Gtk.Justification.CENTER)
    explainer.add_css_class('settings-explainer')

    # input field: api key
    apik_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    apik_label = Gtk.Label(label="API Key")
    apik_label.set_width_chars(15)
    apik_label.set_xalign(0)
    apik_entry = Gtk.PasswordEntry()
    apik_entry.set_show_peek_icon(True)
    apik_entry.set_hexpand(True)
    apik_container.append(apik_label)
    apik_container.append(apik_entry)

    # input field: shared secret
    ss_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    ss_label = Gtk.Label(label="Shared Secret")
    ss_label.set_width_chars(15)
    ss_label.set_xalign(0)
    ss_entry = Gtk.PasswordEntry()
    ss_entry.set_show_peek_icon(True)
    ss_entry.set_hexpand(True)
    ss_container.append(ss_label)
    ss_container.append(ss_entry)

    # help link
    help_link = Gtk.LinkButton(uri="https://www.last.fm/api/account/create")
    help_link.set_label("Don't have credentials? Get them here")
    help_link.set_halign(Gtk.Align.CENTER)

    # buttons
    button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    button_box.set_halign(Gtk.Align.CENTER)

    clear_btn = Gtk.Button(label="Clear Credentials")
    clear_btn.add_css_class('destructive-action')
    clear_btn.connect('clicked', lambda btn: _on_clear_clicked(
        btn, status_label, clear_btn, error_banner, success_banner, window
    ))

    save_btn = Gtk.Button(label="Save Credentials")
    save_btn.add_css_class('suggested-action')
    save_btn.connect('clicked', lambda btn: _on_save_clicked(
        btn, apik_entry, ss_entry, status_label, clear_btn, error_banner, success_banner, dialog
    ))

    button_box.append(clear_btn)
    button_box.append(save_btn)

    # add all widgets
    content.append(status_label)
    content.append(title)
    #content.append(subtitle)
    content.append(explainer)
    content.append(apik_container)
    content.append(ss_container)
    content.append(help_link)
    content.append(button_box)

    # toolbar view w/header
    toolbar_view = Adw.ToolbarView()
    toolbar_view.set_content(content)
    header_bar = Adw.HeaderBar()
    toolbar_view.add_top_bar(header_bar)

    dialog.set_child(toolbar_view)

    # update UI state
    dialog.connect('map', lambda d: _update_ui_state(status_label, clear_btn))
    return dialog

def _update_ui_state(status_label: Gtk.Label, clear_btn: Gtk.Button) -> None:
    """Updates the UI based on credential state"""
    if has_credentials():
        status_label.set_text("Credentials found")
        status_label.remove_css_class('warning')
        status_label.add_css_class('success')
        clear_btn.set_visible(True)
    else:
        status_label.set_text("No credentials found")
        status_label.remove_css_class('success')
        status_label.add_css_class('warning')
        clear_btn.set_visible(False)

def _on_save_clicked(
    button: Gtk.Button, api_key_entry: Gtk.PasswordEntry,
    shared_secret_entry: Gtk.PasswordEntry, status_label: Gtk.Label,
    clear_btn: Gtk.Button, error_banner: Optional[Adw.Banner],
    success_banner: Optional[Adw.Banner], dialog: Adw.Dialog) -> None:
    """Handles save credentials button click"""
    # hide previous banners
    if error_banner:
        hide_banner(error_banner)
    if success_banner:
        hide_banner(success_banner)

    # get values
    api_key = api_key_entry.get_text().strip()
    shared_secret = shared_secret_entry.get_text().strip()

    # validate
    if not api_key or not shared_secret:
        if error_banner:
            show_banner(error_banner, "Both an API key and Shared Secret are required")
        return

    # save credentials
    try:
        credentials = {
            'last_fm': {
                'api_key': api_key,
                'shared_secret': shared_secret
            }
        }
        success = save_credentials(credentials)

        if success:
            # clear entry fields
            api_key_entry.set_text("")
            shared_secret_entry.set_text("")

            # update UI
            _update_ui_state(status_label, clear_btn)

            # show success
            if success_banner:
                show_banner(success_banner, "Credentials saved successfully")

            # auto-close dialog
            GLib.timeout_add(1500, lambda: dialog.close() or False)
        else:
            if error_banner:
                show_banner(error_banner, "Failed to save credentials")

    except Exception as e:
        if error_banner:
            show_banner(error_banner, f"Failed to save credentials: {str(e)}")

def _on_clear_clicked(
    button: Gtk.Button, status_label: Gtk.Label, clear_btn: Gtk.Button,
    error_banner: Optional[Adw.Banner], success_banner: Optional[Adw.Banner],
    window: Gtk.ApplicationWindow) -> None:
    """Handles clear credentials button click"""
    # create confirmation dialog
    confirm = Adw.MessageDialog.new(window)
    confirm.set_heading("Delete Credentials?")
    confirm.set_body("This will remove your Last.fm API credentials from your keyring.")
    confirm.add_response("cancel", "Cancel")
    confirm.add_response("clear", "Clear")
    confirm.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
    confirm.connect('response', lambda dlg, response: _on_confirm_clear(
        dlg, response, status_label, clear_btn, error_banner, success_banner
    ))
    confirm.present()

def _on_confirm_clear(
    dialog: Adw.MessageDialog, response: str, status_label: Gtk.Label,
    clear_btn: Gtk.Button, error_banner: Optional[Adw.Banner],
    success_banner: Optional[Adw.Banner]) -> None:
    """Handles confirmation dialog response"""
    if response == "clear":
        # hide previous banners
        if error_banner:
            hide_banner(error_banner)
        if success_banner:
            hide_banner(success_banner)

        try:
            # delete creds + update UI
            delete_credentials()
            _update_ui_state(status_label, clear_btn)

            # show success
            if success_banner:
                show_banner(success_banner, "Credentials cleared")

        except Exception as e:
            if error_banner:
                show_banner(error_banner, f"Failed to delete credentials: {str(e)}")