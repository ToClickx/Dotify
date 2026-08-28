"""
SoundCloud downloader — core function + legacy standalone GUI.
"""
import os
import re
import shutil
import threading
import requests
from sclib import SoundcloudAPI, Track, Playlist

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONG_LIBRARY = os.path.join(BASE_DIR, "music", "song_library")
PLAYLISTS_DIR = os.path.join(BASE_DIR, "music", "playlists")

_api = None


def _get_api():
    global _api
    if _api is None:
        _api = SoundcloudAPI()
    return _api


def _sanitize(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip(" .")


def _download_track(track: "Track", save_dir: str, on_status=None) -> str | None:
    """Download a single Track to save_dir. Returns folder name or None on failure."""
    def emit(msg):
        print(msg)
        if on_status:
            on_status(msg)

    artist = _sanitize(track.artist or "Unknown Artist")
    title = _sanitize(track.title or "Unknown Title")
    name = f"{artist} - {title}"
    folder = os.path.join(save_dir, name)

    if os.path.exists(folder):
        emit(f"Skipping '{name}' (already exists)")
        return name

    try:
        os.makedirs(folder, exist_ok=True)
        emit(f"Downloading '{name}'…")
        with open(os.path.join(folder, f"{name}.mp3"), "wb") as fh:
            track.write_mp3_to(fh)

        if track.artwork_url:
            emit("Fetching artwork…")
            resp = requests.get(track.artwork_url, timeout=10)
            resp.raise_for_status()
            with open(os.path.join(folder, f"{name}.jpg"), "wb") as fh:
                fh.write(resp.content)

        emit(f"Done: '{name}'")
        return name
    except Exception as e:
        emit(f"Failed '{name}': {e}")
        if os.path.exists(folder):
            shutil.rmtree(folder, ignore_errors=True)
        return None


def download(url: str, on_status=None):
    """
    Download a SoundCloud track or playlist from *url*.
    on_status: optional callable(str) for progress messages.
    """
    def emit(msg):
        print(msg)
        if on_status:
            on_status(msg)

    os.makedirs(SONG_LIBRARY, exist_ok=True)
    os.makedirs(PLAYLISTS_DIR, exist_ok=True)

    if not url.startswith("https://"):
        url = "https://" + url

    emit("Resolving URL…")
    try:
        item = _get_api().resolve(url)
    except Exception as e:
        emit(f"Could not resolve URL: {e}")
        return

    if isinstance(item, Track):
        _download_track(item, SONG_LIBRARY, on_status)

    elif isinstance(item, Playlist):
        pl_name = _sanitize(item.title)
        emit(f"Downloading playlist '{item.title}' ({len(item.tracks)} tracks)…")
        downloaded = []
        for track in item.tracks:
            name = _download_track(track, SONG_LIBRARY, on_status)
            if name:
                downloaded.append(name)

        pl_file = os.path.join(PLAYLISTS_DIR, f"{pl_name}.txt")
        with open(pl_file, "w", encoding="utf-8") as fh:
            fh.write("\n".join(downloaded) + "\n")
        emit(f"Playlist saved: {pl_file}")
    else:
        emit("URL did not resolve to a track or playlist.")


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
