import os
import re
import shutil
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_EXTS = (".mp3", ".wav", ".wave", ".ogg", ".flac", ".aac", ".m4a")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".ico")


class MusicManager:
    def __init__(self):
        self.song_library_path = os.path.join(BASE_DIR, "music", "song_library")
        self.playlists_path = os.path.join(BASE_DIR, "music", "playlists")
        os.makedirs(self.song_library_path, exist_ok=True)
        os.makedirs(self.playlists_path, exist_ok=True)

    def get_songs(self) -> dict:
        """Return {song_folder_name: {song_path, image_path}} for all songs in the library."""
        songs = {}
        for root, dirs, files in os.walk(self.song_library_path):
            if root == self.song_library_path:
                continue  # skip root level; songs live in sub-folders
            data = {}
            for file in files:
                lower = file.lower()
                if lower.endswith(AUDIO_EXTS):
                    data["song_path"] = os.path.join(root, file)
                elif lower.endswith(IMAGE_EXTS) and "image_path" not in data:
                    data["image_path"] = os.path.join(root, file)
            if "song_path" in data:
                folder_name = os.path.basename(root)
                if "image_path" not in data:
                    data["image_path"] = os.path.join(BASE_DIR, "noimage.png")
                songs[folder_name] = data
        return songs

    def get_playlists(self) -> dict:
        """Return {playlist_name: file_path} for every .txt playlist file."""
        playlists = {}
        for file in os.listdir(self.playlists_path):
            if file.endswith(".txt"):
                name = os.path.splitext(file)[0]
                playlists[name] = os.path.join(self.playlists_path, file)
        return playlists

    def get_playlist_songs(self, playlist_name: str) -> list:
        """Return [(song_name, song_data), ...] for the given playlist."""
        playlist_path = os.path.join(self.playlists_path, f"{playlist_name}.txt")
        songs_all = self.get_songs()
        result = []
        if not os.path.exists(playlist_path):
            return result
        with open(playlist_path, "r", encoding="utf-8") as fh:
            for line in fh:
                name = line.strip()
                if name and name in songs_all:
                    result.append((name, songs_all[name]))
        return result

    def create_playlist(self, name: str) -> bool:
        """Create an empty playlist file. Returns False if it already exists."""
        path = os.path.join(self.playlists_path, f"{name}.txt")
        if os.path.exists(path):
            return False
        open(path, "w").close()
        return True

    def add_to_playlist(self, playlist_name: str, song_name: str):
        path = os.path.join(self.playlists_path, f"{playlist_name}.txt")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{song_name}\n")

    def delete_song(self, song_name: str) -> bool:
        """Delete a song folder from the library. Returns True on success."""
        folder = os.path.join(self.song_library_path, song_name)
        if not os.path.isdir(folder):
            return False
        shutil.rmtree(folder, ignore_errors=True)
        return not os.path.exists(folder)

    def delete_playlist(self, playlist_name: str) -> bool:
        """Delete a playlist file. Returns True on success."""
        path = os.path.join(self.playlists_path, f"{playlist_name}.txt")
        if not os.path.exists(path):
            return False
        os.remove(path)
        return not os.path.exists(path)

    def remove_from_playlist(self, playlist_name: str, song_name: str) -> bool:
        """Remove a song from a playlist. Returns True if it was present."""
        path = os.path.join(self.playlists_path, f"{playlist_name}.txt")
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip()]
        if song_name not in lines:
            return False
        lines = [ln for ln in lines if ln != song_name]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + ("\n" if lines else ""))
        return True

    # ------------------------------------------------------------------ #
    #  Importing local audio files
    # ------------------------------------------------------------------ #

    def import_audio_files(self, paths: list[str]) -> tuple[list[str], list[str]]:
        """Copy local audio files into the library as individual songs.

        Returns (added_names, skipped_messages).
        """
        added, skipped = [], []
        for path in paths:
            if not os.path.isfile(path):
                skipped.append(f"{os.path.basename(path)} — file not found")
                continue
            ext = os.path.splitext(path)[1].lower()
            if ext not in AUDIO_EXTS:
                skipped.append(f"{os.path.basename(path)} — unsupported type")
                continue

            base = os.path.basename(path)
            stem = os.path.splitext(base)[0]
            title = self._unique_folder_name(stem)
            folder = os.path.join(self.song_library_path, title)
            try:
                os.makedirs(folder, exist_ok=True)
                shutil.copy2(path, os.path.join(folder, base))
            except Exception as e:
                skipped.append(f"{base} — {e}")
                continue
            self._import_artwork(path, folder, stem, base)
            added.append(title)
        return added, skipped

    @staticmethod
    def _sanitize_folder(name: str) -> str:
        cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip(" .")
        return cleaned or "untitled"

    def _unique_folder_name(self, name: str) -> str:
        name = self._sanitize_folder(name)
        candidate = name
        i = 2
        while os.path.isdir(os.path.join(self.song_library_path, candidate)):
            candidate = f"{name} ({i})"
            i += 1
        return candidate

    def _import_artwork(self, src: str, folder: str, stem: str, base: str):
        """Best-effort artwork: a sibling image next to the file, else embedded
        cover art extracted with ffmpeg."""
        sibling_dir = os.path.dirname(src)
        for e in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            cand = os.path.join(sibling_dir, stem + e)
            if os.path.isfile(cand):
                try:
                    shutil.copy2(cand, os.path.join(folder, stem + e))
                    return
                except Exception:
                    break

        exe = os.path.join(BASE_DIR, "ffmpeg.exe")
        if not os.path.exists(exe):
            return
        out = os.path.join(folder, "artwork.jpg")
        try:
            r = subprocess.run(
                [exe, "-y", "-loglevel", "error", "-i", src,
                 "-frames:v", "1", "-c:v", "mjpeg", out],
                capture_output=True, timeout=30)
            if r.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 0:
                return
        except Exception:
            pass
        try:
            os.remove(out)
        except OSError:
            pass
