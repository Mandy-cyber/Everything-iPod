import os
import json
from collections import deque
from typing import Optional, List, Dict, Callable
from datetime import datetime

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

from .constants import Repeat


class MusicPlayer:
    """Handles audio playback, queue management, and play tracking"""

    def __init__(self, state_file: str = None):
        """Initialize the music player

        Args:
            state_file (str): Path to save/load player state
        """
        # setup
        self.state_file = state_file
        self.current_song: dict = None
        self.queue = deque()# upcoming songs
        self.history = deque(maxlen=50)  # previous songs (limited to last 50)
        self.position = 0
        self.volume = 0.5
        self.is_playing = False
        self.is_paused = False
        self.shuffle = False
        self.repeat = Repeat.NONE

        # callbacks for UI updates
        self.on_song_changed = None
        self.on_state_changed = None
        self.on_position_changed = None
        self.on_queue_changed = None
        
        # UI position updating
        self.update_timer_id = None

        # setup gst player & bus
        Gst.init(None)
        player = Gst.ElementFactory.make("playbin", "player")
        self.player = player
        
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        # don't show video window (audio-only)
        fakesink = Gst.ElementFactory.make("fakesink", "fakesink")
        self.player.set_property("video-sink", fakesink)
        

    def play(self, song_path: str, metadata: dict) -> bool:
        """Play a song immediately, clearing the queue

        Args:
            song_path (str): Full path to the audio file
            metadata (dict): Song metadata (song, artist, album, art_path, duration_ms)

        Returns:
            bool: True if playback started successfully
        """
        if not song_path or not os.path.exists(song_path):
            print(f"Song file not found: {song_path}")
            return False

        # stop current playback
        self.player.set_state(Gst.State.NULL)

        # clear queue and update current song
        self.queue.clear()
        self.current_song = {
            "song_path": song_path,
            "metadata": metadata
        }

        # set new file URI
        file_uri = f"file://{song_path}"
        self.player.set_property("uri", file_uri)

        # start playback
        ret = self.player.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to change pipeline to PLAYING state")
            return False

        # start position update timer
        self._start_position_timer()

        # notify UI
        if self.on_song_changed:
            self.on_song_changed(metadata)

        return True

    def add_to_queue(self, song_path: str, metadata: dict) -> None:
        """Add song to end of queue

        Args:
            song_path (str): Full path to the audio file
            metadata (dict): Song metadata
        """
        self.queue.append({
            "song_path": song_path,
            "metadata": metadata
        })

        # notify UI
        if self.on_queue_changed:
            self.on_queue_changed(list(self.queue))

    def play_next(self, song_path: str, metadata: dict) -> None:
        """Insert song to play after current song

        Args:
            song_path (str): Full path to the audio file
            metadata (dict): Song metadata
        """
        self.queue.appendleft({
            "song_path": song_path,
            "metadata": metadata
        })

        # notify UI
        if self.on_queue_changed:
            self.on_queue_changed(list(self.queue))
    
    def pause(self) -> None:
        """Pause playback"""
        # change state
        ret = self.player.set_state(Gst.State.PAUSED)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to change pipeline to PAUSED state")
            return

        # stop position updates
        self._stop_position_timer()

    def resume(self) -> None:
        """Resume playback"""
        # change state
        ret = self.player.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to change pipeline to PLAYING state")
            return

        # restart position updates
        self._start_position_timer()

    def stop(self) -> None:
        """Stop playback"""
        # change state
        ret = self.player.set_state(Gst.State.NULL)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to change pipeline to NULL (stop) state")
            return
        
        self.current_song = None
        # stop position updates
        self._stop_position_timer()

    def skip(self) -> None:
        """Skip to next song in queue"""
        if self.current_song:
            self.history.append(self.current_song)

        if not self.queue:
            # handle repeat modes
            if self.repeat == Repeat.ONE and self.current_song:
                # replay current song
                self.history.pop()
                song_path = self.current_song["song_path"]
                metadata = self.current_song["metadata"]
                self._play_song(song_path, metadata)
                return
            else:
                # no more songs, stop playback
                self.stop()
                return

        # get next song
        next_song = self.queue.popleft()
        song_path = next_song["song_path"]
        metadata = next_song["metadata"]

        # validate song exists
        if not song_path or not os.path.exists(song_path):
            print(f"Song file not found: {song_path}. Skipping...")
            self.skip()
            return

        # play next
        self.current_song = next_song
        self._play_song(song_path, metadata)

        # notify UI
        if self.on_queue_changed:
            self.on_queue_changed(list(self.queue))

    def previous(self) -> None:
        """Go back to previous song"""
        if not self.history:
            print("No previous songs in history")
            return

        # curr song now next
        if self.current_song:
            self.queue.appendleft(self.current_song)

        # get prev. song
        prev_song = self.history.pop()
        song_path = prev_song["song_path"]
        metadata = prev_song["metadata"]

        # validate song exists
        if not song_path or not os.path.exists(song_path):
            print(f"Song file not found: {song_path}. Going back...")
            self.previous()
            return

        # play prev. song
        self.current_song = prev_song
        self._play_song(song_path, metadata)

        # notify UI
        if self.on_queue_changed:
            self.on_queue_changed(list(self.queue))

    def _play_song(self, song_path: str, metadata: dict) -> None:
        """Play a song without modifying queue/history"""
        # stop curr. playback
        self.player.set_state(Gst.State.NULL)

        # set new file URI
        file_uri = f"file://{song_path}"
        self.player.set_property("uri", file_uri)

        # start playback
        ret = self.player.set_state(Gst.State.PLAYING)
        if ret == Gst.StateChangeReturn.FAILURE:
            print("Unable to change pipeline to PLAYING state")
            return

        # start position updater
        self._start_position_timer()

        # notify UI
        if self.on_song_changed:
            self.on_song_changed(metadata)

    def seek(self, position_ms: int) -> None:
        """Seek to position in current song

        Args:
            position_ms (int): Position in milliseconds
        """
        if not self.current_song:
            print("No song currently loaded")
            return

        if position_ms < 0:
            print("Invalid seek position")
            return

        # convert ms to nanoseconds
        position_ns = position_ms * Gst.MSECOND

        # perform seek
        seek_result = self.player.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
            position_ns
        )

        if not seek_result:
            print(f"Seek to {position_ms}ms failed")
            return

        # update position tracker
        self.position = position_ms / 1000.0  # convert to seconds

        # notify UI of position change
        if self.on_position_changed:
            self.on_position_changed(self.position)
        

    def set_volume(self, volume: float) -> None:
        """Set playback volume

        Args:
            volume (float): Volume level 0.0-1.0
        """
        pass

    def toggle_shuffle(self) -> bool:
        """Toggle shuffle mode

        Returns:
            bool: New shuffle state
        """
        pass

    def cycle_repeat(self) -> str:
        """Cycle through repeat modes: none -> one -> all -> none

        Returns:
            str: New repeat mode
        """
        pass

    def get_queue(self) -> List[dict]:
        """Get current queue

        Returns:
            List[dict]: List of queued songs with metadata
        """
        pass

    def remove_from_queue(self, index: int) -> None:
        """Remove song from queue by index

        Args:
            index (int): Queue index to remove
        """
        pass

    def clear_queue(self) -> None:
        """Clear all songs from queue"""
        pass

    def get_current_song(self) -> Optional[dict]:
        """Get currently playing song metadata

        Returns:
            Optional[dict]: Current song metadata or None
        """
        pass

    def get_position(self) -> int:
        """Get current playback position

        Returns:
            int: Position in milliseconds
        """
        pass

    def get_duration(self) -> int:
        """Get duration of current song

        Returns:
            int: Duration in milliseconds
        """
        pass

    def save_state(self) -> None:
        """Save player state to file"""
        pass

    def load_state(self) -> None:
        """Load player state from file"""
        pass

    def _on_song_complete(self) -> None:
        """Called when a song finishes playing"""
        # log play to database
        # advance to next song
        pass

    def _log_play(self, song_path: str, metadata: dict, elapsed_ms: int) -> None:
        """Log completed play to ui_plays table

        Args:
            song_path (str): Path to song file
            metadata (dict): Song metadata
            elapsed_ms (int): Time listened in milliseconds
        """
        pass

    def _start_position_timer(self):
        """Start timer to update playback position"""
        if self.update_timer_id is None:
            self.update_timer_id = GLib.timeout_add(100, self._update_position)
            
    def _stop_position_timer(self):
        """Stop position update timer"""
        if self.update_timer_id:
            GLib.source_remove(self.update_timer_id)
            self.update_timer_id = None
            
    def _update_position(self) -> bool:
        """Query and update current position"""
        if not self.is_playing:
            return False
            
        # get position in nanoseconds
        success, position = self.player.query_position(Gst.Format.TIME)
        if success:
            # convert to seconds + notify UI
            self.position = position / Gst.SECOND
            if self.on_position_changed:
                self.on_position_changed(self.position)
        
        return True
        
    def _on_bus_message(self, bus, message) -> None:
        """Handle messages from GStreamer bus"""
        t = message.type
        
        if t == Gst.MessageType.EOS:
            # song finished
            self.skip()
            
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"Error: {err}, {debug}")
            self.stop()
            if self.on_state_changed:
                self.on_state_changed()
                
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.player:
                # parse state change
                old_state, new_state, _ = message.parse_state_changed()
                print(f"State changed from {old_state.value_nick} to {new_state.value_nick}")
                
                # update state trackers
                if new_state == Gst.State.PLAYING:
                    self.is_playing = True
                    self.is_paused = False
                elif new_state == Gst.State.PAUSED:
                    self.is_playing = False
                    self.is_paused = True
                elif new_state == Gst.State.NULL or new_state == Gst.State.READY:
                    self.is_playing = False
                    self.is_paused = False
                
                # notify UI
                if self.on_state_changed:
                    self.on_state_changed()