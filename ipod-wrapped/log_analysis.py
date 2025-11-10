from hashlib import md5
import os
import re
import json
import polars as pl
from dotenv import load_dotenv
import requests
from time import sleep

from constants import *

load_dotenv()

class LogAnalyser:

    def __init__(self, log_location='../sample-files/playback.log'):
        self.genre_data = dict()
        self.failed_songs = dict()

        try:
            self.api_key = os.getenv('API_KEY')
            self.shared_secret = os.getenv('SHARED_SECRET')
            self.log_data = self.load_logs(log_location)
            self.log_df = self.logs_to_df()
            print(f"Loaded {len(self.log_df)} log entries")
            print(self.log_df.head())
        except Exception as e:
            print(f"Could not analyze logs: {e}")
            return
        
    @staticmethod
    def load_logs(file_loc: str) -> list:
        """Loads the logs from the given file location

        Args:
            file_loc (str): the location of the log file

        Returns:
            list: a list of each line in the log file
        """
        log_lines = []
        with open(file_loc, 'r') as file:
            for line in file:
                if not line.startswith('#'):
                    log_lines.append(line)
        return log_lines
    

    def parse_track_info(self, path: str) -> tuple:
        """Parses track info from the given path.

        Args:
            path (str): a path in the iPod log

        Returns:
            tuple: (album, artist, song) found from the path
        """
        path_sections = path.split('/')[1:]
        artist = path_sections[2].strip()
        album = self.fix_explicit_label(path_sections[3].strip())
        song = self.clean_song(path_sections[4].split('-')[1])
        return album, artist, song
    

    def fix_explicit_label(self, file: str) -> str:
        """Removes the 'Explicit; tag and re-adds it neatly to the
        given string. This is because sometimes (often) the rockbox
        log cuts it off...

        Args:
            file (str): the file name to be fixed

        Returns:
            str: the fixed string
        """
        if '(Exp' in file:
            new_name = file.split(' (Exp')[0]
            file = f"{new_name} (Explicit)"
        return file


    def clean_song(self, song: str) -> str:
        """Attempts to properly format the song title, removing
        unnecessary info

        Args:
            song (str): the song name to clean

        Returns:
            str: the 'cleaned' song name
        """
        song_with_ext = '.'.join(song.split('.')[1:])
        song_wout_ext = song_with_ext

        # remove extension
        for ext in song_extensions:
            if song_with_ext.endswith(ext):
                song_wout_ext = song_with_ext.split(ext)[0]
                break

        return self.fix_explicit_label(song_wout_ext.strip())


    def logs_to_df(self) -> pl.DataFrame:
        """Creates a dataframe of all info found in the iPod
        log file

        Returns:
            pl.DataFrame: A dataframe of the iPod log data
        """
        entries = []
        failed = []

        for log_entry in self.log_data:
            match = re.match(ipod_log_pattern, log_entry.strip())
            if match:
                try:
                    album, artist, song = self.parse_track_info(str(match.group(4)))
                    entries.append({
                        'timestamp': int(match.group(1)),
                        'elapsed_ms': int(match.group(2)),
                        'length_ms': int(match.group(3)),
                        'file_path': str(match.group(4)),
                        'album': album,
                        'genres': self.find_song_genres((artist, song)),
                        'artist': artist,
                        "song": song
                    })
                except Exception as e:
                    failed.append(log_entry)
                    print(f'failed: {log_entry}')

        df = pl.DataFrame(entries)
        if len(failed) > 0:
            print(f"Failed to parse {len(failed)} entries")

        return df
    

    def find_song_genres(self, entry: tuple) -> str:
        """Finds the genres associated with the given entry

        Args:
            entry (tuple): (artist, track) to find the genres for

        Returns:
            str: the genres associated with the given entry
        """
        artist, track = entry
        # check if we've looked it up before -- TODO: eventually store data e.g. in mongo
        if track in self.failed_songs:
            return ""
        if track in self.genre_data:
            return self.genre_data[track]
        
        # make request to last.fm
        song_genres = []
        req_str = '{}/2.0/?method=track.getInfo&api_key={}&artist={}&track={}&autocorrect=1&format=json'.format(
            lastfm_root, self.api_key, artist, track.replace(" (Explicit)", "")
        )
        resp = requests.get(req_str)
        
        try:
            # grab valid genre tags
            toptags = json.loads(resp.text)['track'].get('toptags', {})
            for tag in toptags['tag']:
                tag_name = tag['name'].lower().strip()
                if tag_name in all_genres:
                    song_genres.append(tag_name)

            genre_str = ','.join(song_genres)
            self.genre_data[track] = genre_str
        except Exception as e:
            # probably poorly formmated track name
            print(f"Failed to find genres for track '{track}' by {artist}")
            self.failed_songs[track] = artist
        
        if len(genre_str) == 0:
            genre_str = ""

        sleep(0.5) # last.fm rate limiting
        return genre_str
    

    def calc_total_plays(self) -> pl.DataFrame:
        """Calculates the total number of plays of each song in the
        log dataframe.

        Returns:
            pl.DataFrame: the dataframe with total plays calculated
        """
        summary = self.log_df.group_by(['artist', 'song', 'album', 'genres']).agg([
            pl.len().alias('total_plays'),
            pl.col('length_ms').first().alias('song_length_ms'),
            pl.col('elapsed_ms').sum().alias('total_elapsed_ms'),
        ]).sort('total_plays', descending=True)
        return summary


    def df_to_file(self, df: pl.DataFrame = None, 
                   output_file: str = '../sample-files/ipod_log.csv') -> None:
        """Writes the given dataframe, or the log dataframe, to the given
        output file.

        Args:
            df (pl.DataFrame, optional): The dataframe to write. Defaults to None.
            output_file (str, optional): Where to write the df to. 
                                        Defaults to '../sample-files/ipod_log.csv'.
        """
        if df is None:
            df = self.log_df
        df.write_csv(output_file)

        
if __name__ == "__main__":
    analyser = LogAnalyser()
    df = analyser.calc_total_plays()
    analyser.df_to_file(df, '../sample-files/total_plays.csv')