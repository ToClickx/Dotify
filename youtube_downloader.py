"""
YouTube downloader — core functions + legacy standalone GUI.
Core functions are importable without any GUI running.
"""
import os
import threading
import requests
import yt_dlp
from ffmpeg_manager import ensure_ffmpeg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SONG_LIBRARY = os.path.join(BASE_DIR, "music", "song_library")


def search(query: str, limit: int = 10) -> list:
    """Return list of {title, url, thumbnail_url} dicts."""
    results = []
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        for entry in info.get("entries", []):
            vid = entry.get("id")
            if not vid:
                continue
            results.append({
                "title": entry.get("title", "Untitled"),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "thumbnail_url": entry.get("thumbnail") or "",
            })
    except Exception as e:
        print(f"YouTube search error: {e}")
    return results


def download(url: str, title: str, on_status=None):
    """
    Download audio for *url* into SONG_LIBRARY/{title}/.
    Also downloads the thumbnail.
    on_status: optional callable(str) for progress messages.
    """
    def emit(msg):
        print(msg)
        if on_status:
            on_status(msg)

    folder = os.path.join(SONG_LIBRARY, title)
    os.makedirs(folder, exist_ok=True)

    ok, msg = ensure_ffmpeg(on_status=on_status)
    if not ok:
        emit(f"Download cancelled — {msg}")
        return

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(folder, "%(title)s.%(ext)s"),
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "ffmpeg_location": BASE_DIR,
        "quiet": True,
        "no_warnings": True,
        "keepvideo": False,
        "progress_hooks": [lambda d: emit(f"Downloading… {d.get('_percent_str', '')}".strip())],
    }
    try:
        emit(f"Downloading '{title}'…")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
        emit("Download complete.")

        # Try to grab thumbnail
        thumb_url = info.get("thumbnail") if info else None
        if thumb_url:
            emit("Fetching thumbnail…")
            resp = requests.get(thumb_url, timeout=10)
            resp.raise_for_status()
            with open(os.path.join(folder, "image.jpg"), "wb") as f:
                f.write(resp.content)
            emit("Thumbnail saved.")
    except Exception as e:
        emit(f"Error: {e}")


# ─── Legacy standalone window ─────────────────────────────────────────────────

def main():
    import tkinter as tk
    from tkinter import Listbox, Scrollbar

    _results = []

    def _search():
        nonlocal _results
        _results = search(search_entry.get())
        lb.delete(0, tk.END)
        for r in _results:
            lb.insert(tk.END, r["title"])

    def _download():
        idx = lb.curselection()
        if not idx:
            return
        r = _results[idx[0]]
        threading.Thread(
            target=download, args=(r["url"], r["title"]), daemon=True
        ).start()

    root = tk.Tk()
    root.title("YouTube Downloader")
    tk.Label(root, text="Search:").pack(pady=8)
    search_entry = tk.Entry(root, width=50)
    search_entry.pack()
    tk.Button(root, text="Search", command=_search).pack(pady=6)
    lb = Listbox(root, width=70, height=10)
    lb.pack(pady=4)
    sb = Scrollbar(root)
    sb.pack(side=tk.RIGHT, fill=tk.Y)
    lb.config(yscrollcommand=sb.set)
    sb.config(command=lb.yview)
    tk.Button(root, text="Download", command=_download).pack(pady=12)
    root.mainloop()


if __name__ == "__main__":
    main()
