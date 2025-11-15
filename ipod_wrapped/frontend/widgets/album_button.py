import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, Pango, GdkPixbuf
import cairo
import math


def create_album_button(album_info: dict, image_size: int = 120) -> Gtk.Button:
    """Creates a button with Album Art, Name, and Artist.

    Args:
        album_info (dict): Album metadata containing art, name, artist, genres, songs
        image_size (int): Size of the album art image

    Returns:
        Gtk.Button: The button with album art and info
    """
    art, name, artist, genres, songs = album_info.values()
    button = Gtk.Button()

    # setup
    BUTTON_SIZE = image_size + 5
    button.set_size_request(BUTTON_SIZE, BUTTON_SIZE)
    button.set_hexpand(False)
    button.set_vexpand(False)
    button.add_css_class('album-button')

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.set_spacing(5)

    # setup rounded image
    texture = round_image(art, image_size, 2)
    picture = Gtk.Picture.new_for_paintable(texture)
    picture.set_size_request(image_size, image_size)

    # setup labels (will truncate with '...')
    name_label = Gtk.Label(label=name)
    name_label.set_ellipsize(Pango.EllipsizeMode.END)
    name_label.set_max_width_chars(12)
    name_label.set_justify(Gtk.Justification.CENTER)
    name_label.add_css_class('album-name-label')

    artist_label = Gtk.Label(label=artist)
    artist_label.set_ellipsize(Pango.EllipsizeMode.END)
    artist_label.set_max_width_chars(12)
    artist_label.set_justify(Gtk.Justification.CENTER)
    artist_label.add_css_class('album-artist-label')

    # add widgets to box
    box.append(picture)
    box.append(name_label)
    box.append(artist_label)

    button.set_child(box)
    # TODO: come back and add open logic
    return button


def round_image(filename, size, radius=15, shadow=True):
    """Round image corners using Cairo"""
    # load image
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        filename=filename,
        width=size,
        height=size,
        preserve_aspect_ratio=True
    )
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    
    # shadow config
    shadow_offset = 1
    shadow_blur = 3
    
    if shadow:
        canvas_width = width + shadow_blur
        canvas_height = height + shadow_blur
    else:
        canvas_width = width
        canvas_height = height
    
    # setup cairo
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, canvas_width, canvas_height)
    ctx = cairo.Context(surface)
    
    # draw shadow
    if shadow:
        ctx.new_sub_path()
        ctx.arc(width - radius + shadow_offset, radius + shadow_offset, radius, -math.pi/2, 0)
        ctx.arc(width - radius + shadow_offset, height - radius + shadow_offset, radius, 0, math.pi/2)
        ctx.arc(radius + shadow_offset, height - radius + shadow_offset, radius, math.pi/2, math.pi)
        ctx.arc(radius + shadow_offset, radius + shadow_offset, radius, math.pi, 3*math.pi/2)
        ctx.close_path()
        ctx.set_source_rgba(0, 0, 0, 0.15)
        ctx.fill()
    
    # draw rounded rectangle
    ctx.new_sub_path()
    ctx.arc(width - radius, radius, radius, -math.pi/2, 0)
    ctx.arc(width - radius, height - radius, radius, 0, math.pi/2)
    ctx.arc(radius, height - radius, radius, math.pi/2, math.pi)
    ctx.arc(radius, radius, radius, math.pi, 3*math.pi/2)
    ctx.close_path()
    ctx.clip()
    
    # draw pixbuf
    Gdk.cairo_set_source_pixbuf(ctx, pixbuf, 0, 0)
    ctx.paint()
    
    # convert to texture
    rounded_pixbuf = Gdk.pixbuf_get_from_surface(surface, 0, 0, canvas_width, canvas_height)
    texture = Gdk.Texture.new_for_pixbuf(rounded_pixbuf)
    return texture