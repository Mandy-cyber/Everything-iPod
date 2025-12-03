# Everything-iPod
> I'm just a sleepy girl, there's a lot of rough edges and things to adjust/fix/add/remove in the repo. Tek time with me, soon come!

<!-- START OF MDTOC -->
### Table of Contents
- [iPod Wrapped](#ipod-wrapped)
    - [Requirements](#requirements)
    - [Getting Started](#getting-started)
- [Utility Scripts](#utility-scripts)
    - [`album_art_fixer.py`](#album_art_fixerpy)
    - [`sync_ipod.sh`](#sync_ipodsh)
    - [`reload_theme.sh`](#reload_themesh)
    - [`update_album_genres.py`](#update_album_genrespy)
- [FAQs](#faqs)

<!-- END OF MDTOC -->

<br>

# iPod Wrapped

This is my silly little attempt to recreate Spotify Wrapped for iPod music listening. It's a GTK4 app to sync your listening history and generate Spotify Wrapped-esque stats for whatever time range you please.

## Requirements

1. An iPod running [rockbox](https://www.ifixit.com/Guide/How+to+install+Rockbox+on+an+iPod+Classic/114824)

2. **Logging** needs to be enabled on your iPod. Go to `Settings > Playback Settings > Logging > On`

3. Create a `.env` file in the `ipod_wrapped` directory, and add the necessary values.
```bash
# last.fm api 
# (will eventually not require individual users to have their own)
LASTFM_API_KEY=
LASTFM_SHARED_SECRET=

# (optional) mongo
# things only stored in mongo if you adjust the code, will add UI enabling later
MONGODB_URI=
```

## Getting Started

Now, you're ready to run the iPod Wrapped app! Listen to some music first with logging enabled so you actually get some results in the app though haha!

1. In `ipod_wrapped/` run `python main.py`

2. Make sure your iPod is plugged in to your laptop and accessible in the filesystem

3. Open the *sync* pop-up. Click the menu icon and then the sync icon.

4. "Start Wrapped" and have fun!!

<br>

# Utility Scripts
A collection of scripts that do random helpful things

## `album_art_fixer.py`
This is **not** my code! Full credit goes to [Xpl0itU](https://github.com/Xpl0itU/rockbox_scripts/blob/master/album_art_fix.py). I just use the script in the *sync_ipod.sh* logic.

## `sync_ipod.sh`
Syncs your local music directory with your iPod's. First extracts art covers from each album, before syncing the music and covers.

**Usage**
```bash
./sync_ipod.sh /path/to/local/Music/dir/ /path/to/iPod/Music/dir/
```

## `reload_theme.sh`
Reloads your rockbox UI simulator with the theme being developed in *./rockbox-theme*.

**Usage**
```bash
# adjust your env variables or dirs set in reload_theme.sh first
# TODO: accept args
./reload_theme.sh
```

## `update_album_genres.py`
Manually update albums missing genre information in your iPod Wrapped db. Eventually this functionality will be added to the UI. Till then:

**Usage**
```bash
# edit the ALBUMS_WITH_GENRES list at the top of the file, then
python update_album_genres.py
```

<br>

# FAQs
Ask me stuff so I have stuff to put here <3