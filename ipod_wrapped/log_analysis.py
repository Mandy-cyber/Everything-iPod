from hashlib import md5
import os
import re
import json
import polars as pl
import webbrowser
from dotenv import load_dotenv
import requests

from constants import *

load_dotenv()

# this is an incredibly rough draft--just me coding
# empty thoughts, just vibes

class LogAnalyser:

    def __init__(self, log_location='../sample_files/playback.log'):
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
        log_lines = []
        with open(file_loc, 'r') as file:
            for line in file:
                log_lines.append(line)
        return log_lines
    
    def parse_path(self, path: str) -> tuple:
        path_sections = path.split('/')[1:]
        artist = path_sections[2].strip()
        album = path_sections[3].strip()
        song = path_sections[4].split('-')[1]
        song = self.clean_song(song)
        return album, artist, song
    
    def clean_song(self, song: str) -> str:
        song_with_ext = '.'.join(song.split('.')[1:])
        for ext in song_extensions:
            if song_with_ext.endswith(ext):
                song_wout_ext = song_with_ext.split(ext)[0]
                break
        
        return song_wout_ext.strip()

    def logs_to_df(self) -> pl.DataFrame:
        entries = []
        failed = []

        for log_entry in self.log_data:
            match = re.match(ipod_log_pattern, log_entry.strip())
            if match:
                try:
                    album, artist, song = self.parse_path(str(match.group(4)))
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
                except:
                    failed.append(log_entry)

        df = pl.DataFrame(entries)
        if len(failed) > 0:
            print(f"Failed to parse {len(failed)} entries.\n{print(entry for entry in failed)}")

        return df
    

    def find_song_genres(self, entry: tuple) -> str:
        artist, track = entry
        song_genres = []
        req_str = '{}/2.0/?method=track.getInfo&api_key={}&artist={}&track={}&format=json'.format(
            lastfm_root, self.api_key, artist, track
        )
        resp = requests.get(req_str)
        
        toptags = json.loads(resp.text)['track'].get('toptags', {})
        for tag in toptags['tag']:
            tag_name = tag['name'].lower().strip()
            if tag_name in all_genres:
                song_genres.append(tag_name)

        return ','.join(song_genres)

    

    # def last_fm_auth(self) -> None:
    #     raw_token_sig = f'api_key{self.api_key}methodauth.getTokentoken{self.shared_secret}'.encode()
    #     token_api_sig = md5(raw_token_sig).hexdigest()

    #     token_req = '{}/2.0/?method=auth.gettoken&api_key={}&api_sig={}&format=json'.format(
    #         auth_root, self.api_key, token_api_sig
    #     )
    #     token_resp = requests.get(token_req)
    #     token = json.loads(token_resp.text)["token"]

    #     user_auth_req = '{}/?api_key={}&token={}&format=json'.format(
    #         user_auth_root, self.api_key, token
    #     )
    #     webbrowser.open(user_auth_req)

    #     raw_session_sig = f'api_key{self.api_key}methodauth.getSessiontoken{token}'.encode()
    #     session_api_sig = md5(raw_session_sig).hexdigest()

    #     session_req = '{}/2.0/?method=auth.getSession&api_key={}&token={}&api_sig={}&format=json'.format(
    #         auth_root, self.api_key, token, session_api_sig
    #     )
    #     session_resp = requests.get(session_req)
    #     session_token = json.loads(session_resp.text)
    #     print(session_token)

        



if __name__ == "__main__":
    LogAnalyser()