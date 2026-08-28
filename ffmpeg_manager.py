"""
ffmpeg_manager.py
-----------------
Ensures ffmpeg.exe and ffprobe.exe are available next to the app.

On first run (or a fresh clone) they are missing because they are git-ignored.
This module auto-downloads a static Windows build (no admin rights, no install
wizard) and extracts the two executables into the project folder so yt-dlp can
convert audio to MP3.
"""
import os
import sys
import io
import time
import zipfile
import urllib.request
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
DOWNLOAD_MARKER = ".ffmpeg.downloading"


def ffmpeg_ready() -> bool:
    """True when ffmpeg.exe + ffprobe.exe are present in the project folder."""
    return (
        os.path.exists(os.path.join(BASE_DIR, "ffmpeg.exe"))
        and os.path.exists(os.path.join(BASE_DIR, "ffprobe.exe"))
    )


def _emit(on_status, msg):
    print(msg)
    if on_status:
        try:
            on_status(msg)
        except Exception:
            pass


def ensure_ffmpeg(on_status=None, force: bool = False) -> tuple[bool, str]:
    """Make sure ffmpeg.exe + ffprobe.exe exist. Auto-downloads them if missing.

    Returns (ok, message). Works on Windows; on other OSes only checks presence.
    """
    if not (sys.platform.startswith("win") or sys.platform == "cygwin"):
        if ffmpeg_ready():
            return True, "ffmpeg present."
        return False, "Auto-install is only supported on Windows (see README)."

    if ffmpeg_ready() and not force:
        return True, "ffmpeg present."

    if os.path.exists(DOWNLOAD_MARKER):
        # Another Dotify instance is already downloading — wait for it briefly.
        _emit(on_status, "Another instance is downloading ffmpeg — waiting…")
        waited_for = 0.0
        while os.path.exists(DOWNLOAD_MARKER) and waited_for < 180:
            time.sleep(1.0)
            waited_for += 1.0
        if ffmpeg_ready():
            return True, "ffmpeg ready (installed by another instance)."
        return False, "Timed out waiting for the other instance."

    # Everything below only cleans up its own temp folder on failure.
    tmp_root = tempfile.mkdtemp(prefix="dotify_ffmpeg_")
    try:
        with open(DOWNLOAD_MARKER, "w") as _f:
            _f.write(str(os.getpid()))

        zip_path = os.path.join(tmp_root, "ffmpeg.zip")
        _emit(on_status, "ffmpeg not found — downloading a static build "
                         "(~80–100 MB, one-time)…")
        _download_ffmpeg(FFMPEG_URL, zip_path, on_status)
        _extract_binaries(zip_path, BASE_DIR)
    except Exception as e:
        return False, (f"Auto-install failed: {e}. Place ffmpeg.exe and ffprobe.exe "
                       f"in '{BASE_DIR}' manually (see README).")
    finally:
        try:
            os.remove(DOWNLOAD_MARKER)
        except OSError:
            pass
        try:
            import shutil
            shutil.rmtree(tmp_root, ignore_errors=True)
        except Exception:
            pass

    if ffmpeg_ready():
        _emit(on_status, "ffmpeg installed successfully.")
        return True, "ffmpeg installed successfully."
    return False, f"ffmpeg still missing in '{BASE_DIR}'. Check the project README."


def _download_ffmpeg(url: str, dest: str, on_status=None):
    """Download *url* to *dest*, reporting progress via on_status."""
    req = urllib.request.Request(url, headers={"User-Agent": "Dotify/1.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        written = 0
        _emit(on_status, "Downloading ffmpeg… 0%")
        with open(dest, "wb") as fh:
            while True:
                chunk = resp.read(1 << 20)  # 1 MB chunks
                if not chunk:
                    break
                fh.write(chunk)
                written += len(chunk)
                if total:
                    pct = written * 100 // total
                    _emit(on_status, f"Downloading ffmpeg… {pct}%")
    _emit(on_status, "ffmpeg downloaded — extracting…")


def _extract_binaries(zip_path: str, base_dir: str):
    """Extract ffmpeg.exe and ffprobe.exe from the release zip into base_dir."""
    found = {"ffmpeg.exe": None, "ffprobe.exe": None}
    # The build lives under a folder ending in /bin/ffmpeg.exe etc.
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            base = os.path.basename(name)
            if base in found and found[base] is None and "/bin/" in name:
                found[base] = name
        for exe, entry in found.items():
            if entry is None:
                raise RuntimeError(f"Could not find {exe} in the ffmpeg archive.")
            with zf.open(entry) as src, open(os.path.join(base_dir, exe), "wb") as dst:
                dst.write(src.read())