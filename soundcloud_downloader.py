"""
SoundCloud downloader — core function + legacy standalone GUI.
Uses yt-dlp (SoundCloud is supported natively) so no extra dependency is needed.
"""
import os
import re
import shutil
import threading
import yt_dlp
from ffmpeg_manager import ensure_ffmpeg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONG_LIBRARY = os.path.join(BASE_DIR, "music", "song_library")
PLAYLISTS_DIR = os.path.join(BASE_DIR, "music", "playlists")


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip(" .")


def _base_opts(quiet=True):
    return {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": quiet,
        "no_warnings": True,
        "ffmpeg_location": BASE_DIR,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "keepvideo": False,
        "writethumbnail": True,
    }


def _emit(msg, on_status):
    print(msg)
    if on_status:
        on_status(msg)


def _download_track(entry: dict, on_status=None) -> str | None:
    """Download a single resolved track to music/song_library/{Artist - Title}/.
    Returns the folder name, or None on failure."""
    def emit(msg):
        _emit(msg, on_status)

    uploader = _sanitize(entry.get("uploader") or entry.get("artist") or "Unknown Artist")
    title = _sanitize(entry.get("title") or "Unknown Title")
    name = f"{uploader} - {title}"
    folder = os.path.join(SONG_LIBRARY, name)

    if os.path.exists(folder):
        emit(f"Skipping '{name}' (already exists)")
        return name

    url = entry.get("webpage_url") or entry.get("url")
    if not url:
        emit(f"Cannot download '{name}': no url.")
        return None

    os.makedirs(folder, exist_ok=True)
    opts = _base_opts()
    opts["outtmpl"] = os.path.join(folder, "audio.%(ext)s")
    try:
        emit(f"Downloading '{name}'…")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        emit(f"Done: '{name}'")
        return name
    except Exception as e:
        emit(f"Failed '{name}': {e}")
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
        return None


def download(url: str, on_status=None):
    """Download a SoundCloud track or playlist from *url*."""
    def emit(msg):
        _emit(msg, on_status)

    os.makedirs(SONG_LIBRARY, exist_ok=True)
    os.makedirs(PLAYLISTS_DIR, exist_ok=True)

    if not url.startswith("http"):
        url = "https://" + url

    ok, msg = ensure_ffmpeg(on_status=on_status)
    if not ok:
        emit(f"Download cancelled — {msg}")
        return

    emit("Resolving URL…")
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "noplaylist": False}) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        emit(f"Could not resolve URL: {e}")
        return

    if info.get("_type") == "playlist" or "entries" in info:
        entries = [e for e in info.get("entries", []) if e]
        pl_name = _sanitize(info.get("title") or "Playlist")
        emit(f"Downloading playlist '{pl_name}' ({len(entries)} tracks)…")
        downloaded = []
        for entry in entries:
            name = _download_track(entry, on_status)
            if name:
                downloaded.append(name)

        pl_file = os.path.join(PLAYLISTS_DIR, f"{pl_name}.txt")
        with open(pl_file, "w", encoding="utf-8") as fh:
            fh.write("\n".join(downloaded) + "\n")
        emit(f"Playlist saved: {pl_file}")
    else:
        _download_track(info, on_status)


# ─── Legacy standalone window ─────────────────────────────────────────────────

def main():
    import tkinter as tk
    from tkinter import messagebox

    def _on_click():
        url = entry.get().strip()
        if not url:
            messagebox.showwarning("Input Error", "Please enter a SoundCloud URL.")
            return
        if "soundcloud.com" not in url:
            messagebox.showwarning("Input Error", "Not a SoundCloud URL.")
            return

        def _run():
            download(url, on_status=lambda m: status.config(text=m))
        threading.Thread(target=_run, daemon=True).start()

    root = tk.Tk()
    root.title("SoundCloud Downloader")
    root.geometry("560x200")
    tk.Label(root, text="SoundCloud URL:").pack(pady=8)
    entry = tk.Entry(root, width=60)
    entry.pack()
    tk.Button(root, text="Download", command=_on_click).pack(pady=12)
    status = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
    status.pack(side=tk.BOTTOM, fill=tk.X, padx=4, pady=4)
    root.mainloop()


if __name__ == "__main__":
    main()