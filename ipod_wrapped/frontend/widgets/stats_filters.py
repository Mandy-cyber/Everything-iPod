import os
import json
from datetime import datetime
from typing import List, Union
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version("GtkSource", "5")
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, GtkSource, Adw, Pango

from backend import find_top_genres, find_top_artists, find_top_albums, find_top_songs, load_stats_from_db, get_total_listening_time
from backend.constants import (
    DEFAULT_SCALE_TIER,
    DEFAULT_VISUAL_LIST_ART_SIZE, DEFAULT_VISUAL_LIST_ROW_HEIGHT,
    DEFAULT_VISUAL_LIST_NUM_WIDTH, DEFAULT_VISUAL_SUMMARY_ART_SIZE,
    DEFAULT_VISUAL_LIST_MAX_CHARS, DEFAULT_VISUAL_SUMMARY_MAX_CHARS,
    DEFAULT_VISUAL_PAGE_MARGIN,
    VISUAL_LIST_ART_SIZES, VISUAL_LIST_ROW_HEIGHTS,
    VISUAL_LIST_NUM_WIDTHS, VISUAL_SUMMARY_ART_SIZES,
    VISUAL_LIST_MAX_CHARS, VISUAL_SUMMARY_MAX_CHARS, VISUAL_PAGE_MARGINS,
)

# TODO:
# - add clear button to date range
# - change title entry to on-changed vs on-activated

class StatsFilters:
    """Represents a set of stats filters/entries to
    apply when running iPod Wrapped"""
    
    DEFAULT_MAX = 5
    
    def __init__(self) -> None:
        """Initialize default filters"""
        self.filters = {
            'mode': 'nerd',
            'start_date': None,
            'end_date': None,
            'wrapped_title': '',
            'max_artists': self.DEFAULT_MAX,
            'max_albums': self.DEFAULT_MAX,
            'max_songs': self.DEFAULT_MAX,
            'max_genres': self.DEFAULT_MAX,
        }
        self.stat_filter_box = None
        self.tier = DEFAULT_SCALE_TIER
        
    def _create_metadata_filter_box(self) -> Gtk.Box:
        """Creates the 'Mode', 'Date Range', and 'Title' filter boxes.

        Returns:
            Gtk.Box: A box with all the filter boxes/entry forms
        """
        # setup
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.add_css_class('stats-filter-box')

        # mode
        mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        mode_box.add_css_class('stats-mode-box')
        mode_label = Gtk.Label(label="Mode:")
        mode_label.set_xalign(0.0)
        mode_label.add_css_class('stats-filter-label')
        mode_entry = Gtk.DropDown.new_from_strings(['nerd', 'visual'])
        mode_entry.add_css_class('stats-mode-dropdown')
        mode_entry.connect("notify::selected-item", self._on_mode_dropdown_changed)
        mode_box.append(mode_label)
        mode_box.append(mode_entry)

        box.append(mode_box)

        # date range
        dates_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        dates_container.add_css_class('stats-dates-container')
        date_label = Gtk.Label(label="Date Range:")
        date_label.set_xalign(0.0)
        date_label.add_css_class('stats-filter-label')
        dates_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        dates_box.add_css_class('stats-date-box')

        # from/start
        from_date_button = Gtk.MenuButton()
        from_date_button.set_label("Start Date")
        from_date_button.add_css_class('stats-date-button')
        from_date_button.add_css_class('stats-from-date-button')

        from_calendar = Gtk.Calendar()
        from_calendar.add_css_class('stats-calendar')
        from_popover = Gtk.Popover()
        from_popover.set_child(from_calendar)
        from_date_button.set_popover(from_popover)
        from_calendar.connect('day-selected', self._on_from_date_selected, from_date_button, from_popover)

        dates_box.append(from_date_button)

        # to/end
        to_date_button = Gtk.MenuButton()
        to_date_button.set_label("End Date")
        to_date_button.add_css_class('stats-date-button')
        to_date_button.add_css_class('stats-to-date-button')

        to_calendar = Gtk.Calendar()
        to_calendar.add_css_class('stats-calendar')
        to_popover = Gtk.Popover()
        to_popover.set_child(to_calendar)
        to_date_button.set_popover(to_popover)
        to_calendar.connect('day-selected', self._on_to_date_selected, to_date_button, to_popover)

        dates_box.append(to_date_button)

        dates_container.append(date_label)
        dates_container.append(dates_box)
        box.append(dates_container)

        # title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        title_box.add_css_class('stats-title-box')
        title_label = Gtk.Label(label="Title:")
        title_label.set_xalign(0.0)
        title_label.add_css_class('stats-filter-label')
        title_entry = Gtk.Entry()
        title_entry.set_placeholder_text('"My 2025 iPod Wrapped"!')
        title_entry.add_css_class('stats-title-entry')
        title_entry.connect('activate', self._on_title_entry_activated)
        title_box.append(title_label)
        title_box.append(title_entry)
        
        box.append(title_box)

        return box
    
    def _create_stat_filter_box(self) -> Gtk.Box:
        """Creates the Top 'x' filter boxes.

        Returns:
            Gtk.Box: A box with all the filter boxes
        """
        # setup box
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.add_css_class('stats-stat-filter-box')

        # title
        title = Gtk.Label()
        title.set_label("Choose Your Stats")
        title.set_xalign(0.0)
        title.add_css_class('stats-filter-box-title')
        box.append(title)

        # subtitle
        # subtitle = Gtk.Label(label="N.B. In visual mode, can only select 2 stats")
        # subtitle.set_xalign(0.0)
        # subtitle.add_css_class('stats-filter-box-subtitle')
        # box.append(subtitle)

        # stat boxes
        stats = ['artists', 'albums', 'songs', 'genres']
        for stat in stats:
            stat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            stat_box.add_css_class('stats-indiv-stat-box')

            bullet = Gtk.Label(label="•")
            bullet.add_css_class('stats-bullet')
            adjustment = Gtk.Adjustment(value=self.DEFAULT_MAX, lower=0, upper=100, step_increment=1, page_increment=10)
            stat_entry = Gtk.SpinButton(adjustment=adjustment, digits=0, numeric=True)
            stat_entry.set_value(self.DEFAULT_MAX)
            stat_label = Gtk.Label()
            stat_label.set_use_markup(True)
            stat_label.set_markup(f"Top <u>{int(self.DEFAULT_MAX)}</u> {stat}")

            stat_entry.connect('value-changed', self._on_stat_entry_changed, stat_label, stat)

            stat_box.append(bullet)
            stat_box.append(stat_entry)
            stat_box.append(stat_label)
            box.append(stat_box)

        return box
        
    def _on_mode_dropdown_changed(self, dropdown: Gtk.DropDown, _pspec) -> None:
        # update filter
        selected = dropdown.get_selected()
        if selected == 0:
            self.filters["mode"] = "nerd"
            if self.stat_filter_box:
                self.stat_filter_box.set_sensitive(True)
        elif selected == 1:
            self.filters["mode"] = "visual"
            if self.stat_filter_box:
                self.stat_filter_box.set_sensitive(False)

    def _on_title_entry_activated(self, entry: Gtk.Entry) -> None:
        self.filters["wrapped_title"] = entry.get_text()
    
    def _on_stat_entry_changed(self, spin_button: Gtk.SpinButton, label: Gtk.Label, stat: str) -> None:
        # update label
        value = int(spin_button.get_value())
        stat_text = stat[:-1] if value == 1 else stat
        label.set_markup(f"Top <u>{value}</u> {stat_text}")
        # update stat
        self.filters[f"max_{stat}"] = value

    def _on_from_date_selected(self, calendar: Gtk.Calendar, button: Gtk.MenuButton, popover: Gtk.Popover) -> None:
        # update label
        date = calendar.get_date()
        button.set_label(f"{date.get_year()}-{date.get_month():02d}-{date.get_day_of_month():02d}")
        # update stat
        self.filters['start_date'] = date
        popover.popdown()

    def _on_to_date_selected(self, calendar: Gtk.Calendar, button: Gtk.MenuButton, popover: Gtk.Popover) -> None:
        # update label
        date = calendar.get_date()
        button.set_label(f"{date.get_year()}-{date.get_month():02d}-{date.get_day_of_month():02d}")
        # update stat
        self.filters['end_date'] = date
        popover.popdown()
    
    def _clear_pane(self, pane: Gtk.Box) -> None:
        """Clears the given pane of any widgets/elements"""
        while True:
            child = pane.get_first_child()
            if not child:
                break
            pane.remove(child)
    
    def _hide_album_art_field(self, results: Union[dict, list]) -> Union[dict, list]:
        """Removes all occurrences of the 'album_art' field from
        the given results. This field is really only used on
        the backend and is not for viewing."""
        if isinstance(results, dict):
            new_dict = {}
            for key, value in results.items():
                if key != 'album_art':
                    new_dict[key] = self._hide_album_art_field(value)
            return new_dict
        elif isinstance(results, list):
            return [self._hide_album_art_field(item) for item in results]
        else:
            return results
            
    def _nerd_mode_stats_view(self, results: dict) -> GtkSource.View:
        """Creates a JSON code block view of the given results"""
        # setup lang + syntax
        source_manager = GtkSource.LanguageManager.get_default()
        json_lang = source_manager.get_language("json")
        buffer = GtkSource.Buffer()
        if json_lang:
            buffer.set_language(json_lang)
            buffer.set_highlight_syntax(True)
        
        # add code
        cleaned_results = self._hide_album_art_field(results)
        text = json.dumps(cleaned_results, indent=4, ensure_ascii=False)
        buffer.set_text(text, len(text))
        
        # set light mode
        scheme_manager = GtkSource.StyleSchemeManager.get_default()
        dark_mode = scheme_manager.get_scheme("solarized-light")
        if dark_mode:
            buffer.set_style_scheme(dark_mode)          
        
        # finish code block setup
        source_view = GtkSource.View(buffer=buffer)
        source_view.set_show_line_numbers(True)
        source_view.set_editable(False)
        source_view.set_wrap_mode(Gtk.WrapMode.WORD)
        return source_view
    
    def _create_visual_mode_list_page(self, category: str, data: list) -> Gtk.Box:
        """Creates a Spotify Wrapped-esque view of the given data"""
        # tier-based sizes
        art_size = VISUAL_LIST_ART_SIZES.get(self.tier, DEFAULT_VISUAL_LIST_ART_SIZE)
        row_height = VISUAL_LIST_ROW_HEIGHTS.get(self.tier, DEFAULT_VISUAL_LIST_ROW_HEIGHT)
        num_width = VISUAL_LIST_NUM_WIDTHS.get(self.tier, DEFAULT_VISUAL_LIST_NUM_WIDTH)
        max_chars = VISUAL_LIST_MAX_CHARS.get(self.tier, DEFAULT_VISUAL_LIST_MAX_CHARS)
        margin = VISUAL_PAGE_MARGINS.get(self.tier, DEFAULT_VISUAL_PAGE_MARGIN)

        # setup page
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.set_halign(Gtk.Align.FILL)
        page.set_valign(Gtk.Align.CENTER)
        page.set_margin_start(margin)
        page.set_margin_end(margin)
        page.add_css_class('stats-visual-page-box')
        page.add_css_class(f'stats-visual-page-box-{category}s')

        # title
        page_title = Gtk.Label(label=f'Your top {category}s')
        page_title.add_css_class('stats-visual-page-title')
        page.append(page_title)

        # top x boxes
        for idx, itm in enumerate(data, start=1):
            val = itm.get(category, '')
            art = itm.get('album_art', '')
            artist = itm.get('artist', '')

            # item box
            item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            item_box.set_size_request(-1, row_height)
            item_box.set_halign(Gtk.Align.CENTER)
            item_box.set_valign(Gtk.Align.CENTER)
            item_box.add_css_class('top-x-item-box')

            # left: item number
            item_num = Gtk.Label(label=str(idx))
            item_num.set_size_request(num_width, -1)
            item_num.set_halign(Gtk.Align.CENTER)
            item_num.set_valign(Gtk.Align.CENTER)
            item_num.add_css_class('top-x-item-num')
            item_box.append(item_num)

            # middle: album cover
            art_container = Gtk.Box()
            art_container.set_size_request(art_size, art_size)
            art_container.set_halign(Gtk.Align.CENTER)
            art_container.set_valign(Gtk.Align.CENTER)

            if art and os.path.exists(art):
                album_art_img = Gtk.Picture.new_for_filename(art)
                album_art_img.set_content_fit(Gtk.ContentFit.COVER)
                album_art_img.add_css_class('top-x-album-art')
                art_container.append(album_art_img)
            else:
                art_container.add_css_class('top-x-album-art-missing')

            item_box.append(art_container)

            # right: val + artist
            text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            text_box.set_halign(Gtk.Align.START)
            text_box.set_valign(Gtk.Align.CENTER)

            val_label = Gtk.Label(label=val)
            val_label.set_xalign(0.0)
            val_label.set_ellipsize(Pango.EllipsizeMode.END)
            val_label.set_max_width_chars(max_chars)
            val_label.add_css_class('top-x-item-value')
            text_box.append(val_label)

            if artist and category != 'artist':
                artist_label = Gtk.Label(label=artist)
                artist_label.set_xalign(0.0)
                artist_label.set_ellipsize(Pango.EllipsizeMode.END)
                artist_label.set_max_width_chars(max_chars)
                artist_label.add_css_class('top-x-item-artist')
                text_box.append(artist_label)

            item_box.append(text_box)
            page.append(item_box)

        return page
          
    def _create_visual_mode_summary_page(self, data: dict) -> Gtk.Box:
        """Creates a Spotify Wrapped-esque summary page"""
        # tier-based sizes
        summary_art = VISUAL_SUMMARY_ART_SIZES.get(self.tier, DEFAULT_VISUAL_SUMMARY_ART_SIZE)
        summary_max_chars = VISUAL_SUMMARY_MAX_CHARS.get(self.tier, DEFAULT_VISUAL_SUMMARY_MAX_CHARS)

        # setup
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_halign(Gtk.Align.CENTER)
        page.set_valign(Gtk.Align.CENTER)
        page.add_css_class('stats-visual-page-box')
        page.add_css_class('stats-visual-page-box-summary')

        # cover art
        if 'top_albums' in data and len(data['top_albums']) > 0:
            cover_art = data['top_albums'][0]['album_art']

            if cover_art and os.path.exists(cover_art):
                album_art_img = Gtk.Picture.new_for_filename(cover_art)
                album_art_img.set_size_request(summary_art, summary_art)
                album_art_img.set_content_fit(Gtk.ContentFit.COVER)
                album_art_img.set_halign(Gtk.Align.CENTER)
                album_art_img.set_valign(Gtk.Align.CENTER)
                album_art_img.set_margin_bottom(20)
                album_art_img.add_css_class('summary-album-art')
                page.append(album_art_img)
            else:
                art_container = Gtk.Box()
                art_container.set_size_request(summary_art, summary_art)
                art_container.set_halign(Gtk.Align.CENTER)
                art_container.set_valign(Gtk.Align.CENTER)
                art_container.set_margin_bottom(20)
                art_container.add_css_class('summary-album-art-missing')
                page.append(art_container)

        # setup two-column layout
        columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        columns_box.set_halign(Gtk.Align.CENTER)
        columns_box.set_valign(Gtk.Align.CENTER)

        # left column: top artists
        if 'top_artists' in data and len(data['top_artists']) > 0:
            artists_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            artists_box.set_halign(Gtk.Align.START)

            artists_title = Gtk.Label(label="Top Artists")
            artists_title.set_xalign(0.0)
            artists_title.add_css_class('summary-column-title')
            artists_box.append(artists_title)

            for idx, artist_data in enumerate(data['top_artists'], start=1):
                artist_name = artist_data.get('artist', '')
                artist_label = Gtk.Label(label=f"{idx} {artist_name}")
                artist_label.set_xalign(0.0)
                artist_label.set_ellipsize(Pango.EllipsizeMode.END)
                artist_label.set_max_width_chars(summary_max_chars)
                artist_label.add_css_class('summary-list-item')
                artists_box.append(artist_label)

            columns_box.append(artists_box)

        # right column: top songs
        if 'top_songs' in data and len(data['top_songs']) > 0:
            songs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            songs_box.set_halign(Gtk.Align.START)

            songs_title = Gtk.Label(label="Top Songs")
            songs_title.set_xalign(0.0)
            songs_title.add_css_class('summary-column-title')
            songs_box.append(songs_title)

            for idx, song_data in enumerate(data['top_songs'], start=1):
                song_name = song_data.get('song', '')
                song_label = Gtk.Label(label=f"{idx} {song_name}")
                song_label.set_xalign(0.0)
                song_label.set_ellipsize(Pango.EllipsizeMode.END)
                song_label.set_max_width_chars(summary_max_chars)
                song_label.add_css_class('summary-list-item')
                songs_box.append(song_label)

            columns_box.append(songs_box)

        page.append(columns_box)

        # minutes listened
        if 'total_listened_mins' in data:
            mins_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            mins_box.set_halign(Gtk.Align.START)
            mins_box.set_margin_top(15)

            mins_label = Gtk.Label(label="Minutes Listened")
            mins_label.set_xalign(0.0)
            mins_label.add_css_class('summary-mins-label')
            mins_box.append(mins_label)

            mins_value = Gtk.Label(label=f"{data['total_listened_mins']:,}")
            mins_value.set_xalign(0.0)
            mins_value.add_css_class('summary-mins-value')
            mins_box.append(mins_value)

            page.append(mins_box)

        return page      
            
    def _create_visual_mode_pages(self, results: dict) -> List[Gtk.Box]:
        """Creates Spotify Wrapped-esque views of the given stats."""
        # setup + reformat results
        pages = []
        data = {}
        for category, res in results['data'].items():
            if category == 'total_listened_mins':
                data[category] = res
                continue
            
            data[category] = results['data'][category][:self.DEFAULT_MAX]
                       
        # summary page
        pages.append(
            self._create_visual_mode_summary_page(data))
                     
        # 'Top Artists' page
        if 'top_artists' in data:
            pages.append(
                self._create_visual_mode_list_page('artist', data['top_artists']))
                        
        # 'Top Albums' page
        if 'top_albums' in data:
            pages.append(
                self._create_visual_mode_list_page('album', data['top_albums']))
                        
        # 'Top Songs' page
        if 'top_songs' in data:
            pages.append(
                self._create_visual_mode_list_page('song', data['top_songs']))
                        
        # 'Top Genres' page
        if 'top_genres' in data:
            pages.append(
                self._create_visual_mode_list_page('genre', data['top_genres']))
        
        return pages
    
    def _visual_mode_stats_view(self, results: dict) -> Adw.Carousel:
        """Creates multiple Spotify Wrapped-esque views of the given results.
        Multiple pages displaying the different results"""
        # setup carousel
        car = Adw.Carousel()
        car.set_allow_scroll_wheel(True)
        car.set_allow_mouse_drag(True)
        car.set_allow_long_swipes(True)
        car.set_spacing(10)
        car.set_can_focus(True)
        car.set_interactive(True)

        # add pages
        pages = self._create_visual_mode_pages(results)
        [car.append(page) for page in pages]

        return car
    
    def _show_stats(self, stats_pane: Gtk.Box, db_info: dict) -> None:
        """Calculates stats based on self.filters and displays them
        in the given pane."""
        # setup
        results = {'metadata': {}, 'data': {}}
        for k, v in self.filters.items():
            if k == 'start_date' or k == 'end_date':
                # convert dates to str
                if v:
                    results['metadata'][k] = f"{v.get_year()}-{v.get_month():02d}-{v.get_day_of_month():02d}"
                else:
                    results['metadata'][k] = None
            else:
                results['metadata'][k] = v
                
        categories = {
            'artists': find_top_artists,
            'albums': find_top_albums,
            'songs': find_top_songs,
            'genres': find_top_genres
        }
        db_type, db_path = db_info.values()

        # convert datetime
        start_date = None
        end_date = None
        if self.filters['start_date']:
            glib_date = self.filters['start_date']
            start_date = datetime(glib_date.get_year(), glib_date.get_month(), glib_date.get_day_of_month(), 0, 0, 0)
        if self.filters['end_date']:
            glib_date = self.filters['end_date']
            end_date = datetime(glib_date.get_year(), glib_date.get_month(), glib_date.get_day_of_month(), 23, 59, 59)

        # load data for making stats
        db_stats = load_stats_from_db(
            db_type=db_type,
            db_path=db_path,
            start_date=start_date,
            end_date=end_date
        )
        
        # breakdown by category
        for category, cat_func in categories.items():
            top = cat_func(
                db_type=db_type, db_path=db_path,
                n=self.filters[f'max_{category}'],
                stats_data=db_stats
            )
            results['data'][f'top_{category}'] = top

        # total listening time
        results['data']['total_listened_mins'] = get_total_listening_time(
            db_type=db_type,
            db_path=db_path,
            stats_data=db_stats,
            start_date=start_date,
            end_date=end_date
        )
        
        # clear
        mode = self.filters['mode']
        self._clear_pane(stats_pane)
        
        if mode == 'nerd':
            # nerd mode -- json
            source_view = self._nerd_mode_stats_view(results)
            stats_pane.append(source_view)
        else:
            # visual mode -- carousel
            carousel = self._visual_mode_stats_view(results)
            indicator_dots = Adw.CarouselIndicatorDots()
            indicator_dots.set_carousel(carousel)

            stats_pane.append(carousel)
            stats_pane.append(indicator_dots)
            
    def create_wrapped_box(self, stats_pane: Gtk.Box, db_info: dict) -> Gtk.Box:
        """Creates a box with all the Wrapped page filters
        and displays the search results in the given stats pane"""
        # setup
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class('stats-pg-filters')

        # add sub-boxes
        metadata_box = self._create_metadata_filter_box()
        self.stat_filter_box = self._create_stat_filter_box()
        box.append(metadata_box)
        box.append(self.stat_filter_box)
        
        # button
        generate_btn = Gtk.Button()
        generate_btn.set_label("Generate")
        generate_btn.set_size_request(60, 30)
        generate_btn.add_css_class('stats-pg-generate-btn')
        generate_btn.connect("clicked", lambda btn: self._show_stats(stats_pane, db_info))
        
        box.append(generate_btn)
        
        return box