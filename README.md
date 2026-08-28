<img width="960" height="691" alt="image" src="https://github.com/user-attachments/assets/76d0ef4b-1bf0-4705-905c-16ce7cb24f49" />

# Dotify

A dark, Spotify-style desktop music player with a built-in downloader, built
with Python, PyQt6, and pygame. Browse your local library, build playlists, and
pull audio from SoundCloud right from the app.

> **Built with AI assistance.** This project was developed with the help of an
> AI coding assistant. The code is deterministic and has been reviewed by a
> human.

## Features

- **Local library** — point it at a folder of MP3/WAV/OGG/FLAC/AAC/M4A files
  (one sub-folder per track with optional artwork) and it builds your library
  automatically
- **Search** — filter the library by title, artist, or playlist
- **Playlists** — create playlists and add songs from the library; playlists are
  plain `.txt` files under `music/playlists/`
- **Now Playing bar** — play / pause, previous / next, seek slider, and volume
  slider with elapsed & total time
- **Download from SoundCloud** — paste a track or playlist URL to pull audio plus
  artwork (via `yt-dlp`)
- **Dark UI** — custom Qt stylesheet (Fusion) with a dark slider groove, green
  accents, and edge-to-edge layout
- **Background downloads** — downloading and duration lookup run in QThreads so
  the UI stays responsive

## Requirements

- Python 3.10+
- Dependencies:

```bash
pip install -r requirements.txt
```

- **ffmpeg (and ffprobe)** are required for SoundCloud downloads to convert to
  MP3. **Dotify auto-installs them on first download** — it fetches a static
  Windows build (~100 MB) into the project folder automatically, no admin
  rights needed. To skip that and provide your own instead, drop `ffmpeg.exe`
  and `ffprobe.exe` next to `main.py` (git-ignored either way).

## Usage

```bash
python main.py
```

Drop audio folders into `music/song_library/`, or paste a SoundCloud track /
playlist URL into the **Download Music** page to fill the library.

## Project Layout

```
Dotify/
├── main.py                     # App entry point + main window
├── music_manager.py            # Library + playlist management
├── music_player.py             # pygame playback wrapper (play/pause/seek)
├── ffmpeg_manager.py           # Auto-downloads ffmpeg/ffprobe when missing
├── soundcloud_downloader.py    # SoundCloud track/playlist download (yt-dlp)
├── music/                      # Local song library + playlists (gitignored)
├── noimage.png                 # Fallback cover art
└── icon.ico                    # App icon
```

## Notes & disclaimer

- Only download content you have the rights to keep. This tool is intended for
  personal, lawful use (e.g. your own uploads or Creative-Commons material).
- The downloader is unaffiliated with SoundCloud — use it at your own
  responsibility and in compliance with the platform's terms and local law.

## License

MIT
