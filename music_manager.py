import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

AUDIO_EXTS = (".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a")
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
