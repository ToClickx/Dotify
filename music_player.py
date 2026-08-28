import os
import wave
import time
import hashlib
import subprocess

import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SLICE_DIR = os.path.join(BASE_DIR, "music", ".slices")
os.makedirs(SLICE_DIR, exist_ok=True)
MAX_CACHED_SLICES = 40


def _ffmpeg_exe() -> str:
    exe = os.path.join(BASE_DIR, "ffmpeg.exe")
    return exe if os.path.exists(exe) else "ffmpeg"


class MusicPlayer:
    """pygame music player with reliable seeking.

    pygame/SDL_mixer cannot seek MP3s (or even WAVs) via start=, so we decode
    each track to a cached full-length WAV (ffmpeg) once, and seek by writing a
    small WAV slice starting at the target second and playing that from 0.
    """

    def __init__(self):
        pygame.mixer.init()
        self._playing = False
        self._paused = False
        self._current_path = None
        self._duration = 0.0
        self._cache_wav = None
        self._slice_start = 0.0

    # ---------------------------------------------------------------- #
    #  Conversion helpers
    # ---------------------------------------------------------------- #

    def _to_wav(self, path: str) -> str:
        """Return a stable cache path (or a real wav path) for *path*."""
        if path.lower().endswith((".wav", ".wave")):
            return path
        key = hashlib.md5(
            f"{path}|{os.path.getsize(path)}|{os.path.getmtime(path)}".encode()
        ).hexdigest()
        cache = os.path.join(SLICE_DIR, f"{key}.wav")
        if os.path.exists(cache):
            return cache
        try:
            r = subprocess.run(
                [_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", path,
                 "-ac", "2", "-ar", "44100", cache],
                capture_output=True, timeout=300,
            )
            if r.returncode == 0 and os.path.exists(cache):
                return cache
        except Exception:
            pass
        # Fall back to the original file (seek will be unavailable).
        return path

    def _slice(self, wav_path: str, start_sec: float) -> str:
        """Write a WAV slice starting at start_sec and return its path."""
        with wave.open(wav_path, "rb") as wav:
            ch = wav.getnchannels()
            sw = wav.getsampwidth()
            fr = wav.getframerate()
            nf = wav.getnframes()
        self._duration = nf / fr if fr else 0.0

        if start_sec <= 0:
            return wav_path

        bytes_per_sec = fr * ch * sw
        end_frame = max(0, int(nf - 0.35 * fr))  # keep a little tail
        frame = min(int(start_sec * fr), end_frame)
        byte_offset = frame * ch * sw

        with wave.open(wav_path, "rb") as wav:
            wav.setpos(frame)
            data = wav.readframes(end_frame - frame)

        key = hashlib.md5(f"{wav_path}|{frame}".encode()).hexdigest()[:12]
        slice_path = os.path.join(SLICE_DIR, f"s_{key}.wav")
        with wave.open(slice_path, "wb") as out:
            out.setnchannels(ch)
            out.setsampwidth(sw)
            out.setframerate(fr)
            out.writeframes(data)
        self._trim_cache()
        return slice_path

    def _trim_cache(self):
        try:
            files = sorted(
                (os.path.join(SLICE_DIR, f) for f in os.listdir(SLICE_DIR)),
                key=os.path.getmtime, reverse=True,
            )
            for f in files[MAX_CACHE_SLICES:]:
                os.remove(f)
        except Exception:
            pass

    # ---------------------------------------------------------------- #
    #  Public API
    # ---------------------------------------------------------------- #

    def play(self, track_path):
        self._current_path = track_path
        if track_path.lower().endswith((".wav", ".wave")):
            self._cache_wav = track_path
        else:
            self._cache_wav = self._to_wav(track_path)
        self._start_from(0.0, paused=False)

    def _start_from(self, seconds: float, paused: bool):
        try:
            seg = self._slice(self._cache_wav, max(0.0, seconds))
        except Exception as e:
            print("slice error:", e)
            seg = self._cache_wav
            self._slice_start = 0.0
        else:
            self._slice_start = max(0.0, seconds) if seg != self._cache_wav else 0.0
        pygame.mixer.music.load(seg)
        pygame.mixer.music.play()
        if paused:
            pygame.mixer.music.pause()
        self._paused = paused
        self._playing = True

    def seek(self, seconds: float):
        if not self._playing or self._cache_wav is None:
            return
        self._start_from(max(0.0, seconds), paused=self._paused)

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
        self._slice_start = 0.0

    def change_volume(self, volume: float):
        pygame.mixer.music.set_volume(volume)

    def get_position(self) -> float:
        if not self._playing:
            return 0.0
        rel = pygame.mixer.music.get_pos() / 1000.0
        return max(0.0, self._slice_start + rel)

    def is_playing(self):
        return self._playing and not self._paused

    def is_paused(self):
        return self._paused

    def is_active(self):
        return self._playing

    def song_ended(self):
        if self._playing and not self._paused:
            return not pygame.mixer.music.get_busy()
        return False