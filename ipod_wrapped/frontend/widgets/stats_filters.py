import json
from datetime import datetime
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk

from backend import find_top_genres, find_top_artists, find_top_albums, find_top_songs, load_stats_from_db 


class StatsFilters:
    """Represents a set of stats filters/entries to
    apply when running iPod Wrapped"""
    
    DEFAULT_MAX = 5
    
    def __init__(self) -> None:
        """Initialize default filters"""
        self.filters = {
            'mode': '',
            'start_date': None,
            'end_date': None,
            'wrapped_title': 'My iPod Wrapped Stats',
            'max_artists': self.DEFAULT_MAX,
            'max_albums': self.DEFAULT_MAX,
            'max_songs': self.DEFAULT_MAX,
            'max_genres': self.DEFAULT_MAX,
        }
        

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
            stat_label = Gtk.Label(label=f"Top {int(self.DEFAULT_MAX)} {stat}")

            stat_entry.connect('value-changed', self._on_stat_entry_changed, stat_label, stat)

            stat_box.append(bullet)
            stat_box.append(stat_entry)
            stat_box.append(stat_label)
            box.append(stat_box)

        return box
        
         
    def _on_mode_dropdown_changed(self, dropdown: Gtk.DropDown, _pspec) -> None:
        selected = dropdown.get_selected()
        if selected == 0:
            self.filters["mode"] = "nerd"
        elif selected == 1:
            self.filters["mode"] = "visual"

    def _on_title_entry_activated(self, entry: Gtk.Entry) -> None:
        self.filters["wrapped_title"] = entry.get_text()
    
    def _on_stat_entry_changed(self, spin_button: Gtk.SpinButton, label: Gtk.Label, stat: str) -> None:
        # update label
        value = int(spin_button.get_value())
        label.set_label(f"Top {value} {stat}")
        # update stat
        self.filters[f"max_{stat}"] = value

    def _on_from_date_selected(self, calendar: Gtk.Calendar, button: Gtk.MenuButton, popover: Gtk.Popover) -> None:
        # update label
        date = calendar.get_date()
        button.set_label(f"{date.get_year()}-{date.get_month()+1:02d}-{date.get_day_of_month():02d}")
        # update stat
        self.filters['start_date'] = date
        popover.popdown()

    def _on_to_date_selected(self, calendar: Gtk.Calendar, button: Gtk.MenuButton, popover: Gtk.Popover) -> None:
        # update label
        date = calendar.get_date()
        button.set_label(f"{date.get_year()}-{date.get_month()+1:02d}-{date.get_day_of_month():02d}")
        # update stat
        self.filters['end_date'] = date
        popover.popdown()
    
    
    def _show_stats(self, stats_pane: Gtk.Box, db_info: dict) -> None:
        # setup
        results = dict()
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
            start_date = datetime(glib_date.get_year(), glib_date.get_month() + 1, glib_date.get_day_of_month())
        if self.filters['end_date']:
            glib_date = self.filters['end_date']
            end_date = datetime(glib_date.get_year(), glib_date.get_month() + 1, glib_date.get_day_of_month())

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
            results[f'top_{category}'] = top
        
        # show stats
        print(json.dumps(results, indent=4))
        # stats_pane.append()


    def create_wrapped_box(self, stats_pane: Gtk.Box, db_info: dict) -> Gtk.Box:
        """Creates a box with all the Wrapped page filters
        and displays the search results in the given stats pane"""
        # setup
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class('stats-pg-filters')
        
        # add sub-boxes
        metadata_box = self._create_metadata_filter_box()
        stat_filter_box = self._create_stat_filter_box()
        box.append(metadata_box)
        box.append(stat_filter_box)
        
        # add button
        generate_btn = Gtk.Button()
        generate_btn.set_label("Generate")
        generate_btn.set_size_request(60, 30)
        generate_btn.connect("clicked", lambda btn: self._show_stats(stats_pane, db_info))
        
        box.append(generate_btn)
        
        return box