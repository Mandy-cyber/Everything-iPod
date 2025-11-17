import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from .sync_box import create_sync_box_widgets

def create_menu_nav(overlay: Gtk.Overlay, window: Gtk.ApplicationWindow,
                    error_banner: Adw.Banner = None, success_banner: Adw.Banner = None,
                    refresh_callback = None) -> Gtk.Button:
    """Creates a floating nav icon/button to show:
    - About
    - Start Wrapped
    - _______
    
    Returns:
        Gtk.Button: The floating nav button
    """
    # main icon
    menu_btn = Gtk.Button()
    menu_btn.set_icon_name('document-properties-symbolic')
    menu_btn.add_css_class('flat')
    menu_btn.add_css_class('circular')
    menu_btn.add_css_class('nav-menu-icon')
    
    menu_btn.set_halign(Gtk.Align.END)
    menu_btn.set_valign(Gtk.Align.END)
    menu_btn.set_margin_end(10)
    menu_btn.set_margin_bottom(10)
    
    menu_btn.set_can_focus(False)
    
    # extended nav
    extended = _create_extended_menu_nav(window, error_banner, success_banner, refresh_callback)
    extended.set_reveal_child(False)
    overlay.add_overlay(extended)

    menu_btn.connect('clicked', lambda btn: _open_menu_nav(extended))
    return menu_btn
    
def _create_extended_menu_nav(window: Gtk.ApplicationWindow,
                              error_banner: Adw.Banner, success_banner: Adw.Banner,
                              refresh_callback) -> Gtk.Revealer:
    """Creates the menu nav, showing icons for other pages/overlays"""
    # setup
    revealer = Gtk.Revealer()
    revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_LEFT)
    revealer.set_transition_duration(100)

    btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
    btn_box.set_halign(Gtk.Align.END)
    btn_box.set_valign(Gtk.Align.END)
    btn_box.set_margin_end(10)
    btn_box.set_margin_bottom(50)

    revealer.set_child(btn_box)

    # start wrapped button
    start_btn = Gtk.Button()
    start_btn.set_icon_name('system-restart-symbolic')
    start_btn.add_css_class('flat')
    start_btn.add_css_class('circular')
    start_btn.add_css_class('nav-start-icon')
    start_btn.set_can_focus(False)
    start_btn.connect('clicked', lambda btn: _open_start_wrapped_dialogue(window, error_banner, success_banner, refresh_callback))
    btn_box.append(start_btn)

    # about button
    about_btn = Gtk.Button()
    about_btn.set_icon_name('help-about-symbolic')
    about_btn.add_css_class('flat')
    about_btn.add_css_class('circular')
    about_btn.add_css_class('nav-about-icon')
    about_btn.set_can_focus(False)
    about_btn.connect('clicked', lambda btn: _open_about_dialogue(window))
    btn_box.append(about_btn)

    return revealer


def _open_menu_nav(revealer: Gtk.Revealer) -> None:
    """Reveals the other floating navs"""
    revealer.set_reveal_child(not revealer.get_reveal_child())
    
def _open_about_dialogue(window: Gtk.ApplicationWindow):
    """Opens the 'About' dialogue"""
    # TODO: come back
    about_dialog = Adw.AboutDialog()
    # about_dialog.set_transient_for(window)
    # about_dialog.set_modal(True)

    # about_dialog.set_program_name("iPod Wrapped")
    about_dialog.set_version("1.0.0")
    about_dialog.set_comments("An all-in-one tool to view your iPod library, listening history, and 'iPod Wrapped' statistics")
    # about_dialog.set_authors(["Mandy-cyber"])
    about_dialog.set_website("https://github.com/Mandy-cyber/Everything-iPod")
    # about_dialog.set_website_label("Source Code")
    about_dialog.set_license_type(Gtk.License.GPL_3_0)

    about_dialog.present()

def _open_start_wrapped_dialogue(window: Gtk.ApplicationWindow,
                                 error_banner: Adw.Banner, success_banner: Adw.Banner,
                                 refresh_callback):
    """Opens the 'Start iPod Wrapped' dialogue"""
    # create dialog
    dialog = Adw.Dialog()
    dialog.set_title("iPod Wrapped")

    # create content box
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
    content.set_margin_top(20)
    content.set_margin_bottom(20)
    content.set_margin_start(20)
    content.set_margin_end(20)
    content.set_halign(Gtk.Align.CENTER)
    content.set_valign(Gtk.Align.CENTER)
    content.add_css_class('start-wrapped-box')

    # add sync box widgets
    widgets = create_sync_box_widgets(error_banner, success_banner, refresh_callback)
    for widget in widgets:
        content.append(widget)

    # create toolbar view + add content
    toolbar_view = Adw.ToolbarView()
    toolbar_view.set_content(content)
    toolbar_view.set_top_bar_style(Adw.ToolbarStyle.FLAT)

    dialog.set_child(toolbar_view)
    dialog.present(window)