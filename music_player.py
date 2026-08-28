import pygame


class MusicPlayer:
    def __init__(self):
        pygame.mixer.init()
        self._playing = False
        self._paused = False
        self._current_path = None

    def play(self, track_path):
        pygame.mixer.music.load(track_path)
        pygame.mixer.music.play()
        self._playing = True
        self._paused = False
        self._current_path = track_path

    def pause(self):
        if self._playing and not self._paused:
            pygame.mixer.music.pause()
            self._paused = True

    def unpause(self):
        if self._paused:
            pygame.mixer.music.unpause()
            self._paused = False

    def toggle_pause(self):
        if self._paused:
            self.unpause()
        else:
            self.pause()

    def stop(self):
        pygame.mixer.music.stop()
        self._playing = False
        self._paused = False
        self._current_path = None

    def change_volume(self, volume: float):
        """volume: 0.0 – 1.0"""
        pygame.mixer.music.set_volume(volume)

    def get_position(self) -> float:
        """Current playback position in seconds."""
        if not self._playing:
            return 0.0
        return max(0.0, pygame.mixer.music.get_pos() / 1000.0)

    def seek(self, seconds: float):
        """Seek to position (seconds). Works for MP3 with pygame 2+."""
        try:
            pygame.mixer.music.set_pos(seconds)
        except Exception:
            pass

    def is_playing(self) -> bool:
        return self._playing and not self._paused

    def is_paused(self) -> bool:
        return self._paused

    def is_active(self) -> bool:
        """True when a song is loaded (playing or paused)."""
        return self._playing

    def song_ended(self) -> bool:
        """True if a song was playing but has now naturally finished."""
        if self._playing and not self._paused:
            return not pygame.mixer.music.get_busy()
        return False
