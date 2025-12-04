# Everything-iPod
> I'm just a sleepy girl, there's a lot of rough edges and things to adjust/fix/add/remove in the repo. Tek time with me, soon come!

<!-- START OF MDTOC -->
### Table of Contents
- [iPod Wrapped](#ipod-wrapped)
    - [Requirements](#requirements)
    - [Getting Started](#getting-started)
- ["The Letter"](#the-letter)
- [Utility Scripts](#utility-scripts)
    - [`album_art_fixer.py`](#album_art_fixerpy)
    - [`sync_ipod.sh`](#sync_ipodsh)
    - [`reload_theme.sh`](#reload_themesh)
    - [`update_album_genres.py`](#update_album_genrespy)
- [FAQs](#faqs)
- [TODO](#todo)
    - [ipod_wrapped](#ipod_wrapped)
    - [rockbox_theme](#rockbox_theme)

<!-- END OF MDTOC -->

<br>

# iPod Wrapped

This is my silly little attempt to recreate Spotify Wrapped for iPod music listening. It's a GTK4 app to sync your listening history and generate Spotify Wrapped-esque stats for whatever time range you please.
<img width="670" height="526" alt="image" src="https://github.com/user-attachments/assets/1eba74db-6477-45e1-92b5-ea5273f07c45" />

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

# "The Letter"
> N.B. Like most other rockbox themes, you'll need the default Rockbox font pack downloaded.

A custom rockbox theme I drew and coded to act as a 'love letter' to physical media. It adjusts the main, while-playing, and USB, screens to look as follows:

<img width="320" height="240" alt="2" src="https://github.com/user-attachments/assets/a65e44be-ee63-485f-84b4-b21921b64a0c" />
<img width="320" height="240" alt="1" src="https://github.com/user-attachments/assets/a2afede1-63bd-483e-91a4-c38d25e18e2f" />
<img width="320" height="240" alt="3" src="https://github.com/user-attachments/assets/cd9f0248-4880-4d27-9b35-5b43956a5fb5" />
<br>

**Usage**
```bash
# copy the theme over to your iPod
cp -r rockbox-theme/.rockbox/. /path/to/iPod/.rockbox/dir
```

When I have figured out the lock screen, I will submit it to Rockbox's theme gallery for easier downloading & feedback <3. Also if you or someone you love are good with making custom themes PLEASE i have questions. Single-handedly hardest coding project I've attempted purely in terms of "where the hell is helpful documentation"... Yes I *have read the __outdated__ manual and wiki*.

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

<br>

# TODO

## ipod_wrapped
- [ ] Accept args for reload_theme.sh script
- [ ] Add functionality to update album genres in the UI (currently only via utility script)
- [ ] Come back to rockbox theme .sbs file (line 84)
- [ ] Add proper rate limiting logic for log analysis
- [ ] Implement light mode logic for GTK styling
- [ ] Add music player functionality
- [ ] On bottom bar click, show expanded view
- [ ] Add currently playing UI elements to bottom bar
- [ ] Implement bottom bar stub methods
- [ ] Fix 'sorter' not bringing user back to top of table in songs page
- [ ] Fix wonky resizing in songs page
- [ ] Add right click menu with 'add to queue' and 'play next' options for genre songs

### rockbox_theme
- [ ] Fix and uncomment "the letter" lockscreen
- [ ] Create a vinyl theme