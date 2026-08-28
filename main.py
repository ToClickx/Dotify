import sys
import os
import json
import subprocess

import pygame
from PIL import Image
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from music_manager import MusicManager
from music_player import MusicPlayer
import soundcloud_downloader as sc_dl

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NO_IMG = os.path.join(BASE_DIR, "noimage.png")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_audio_duration(path: str) -> float:
    ffprobe = os.path.join(BASE_DIR, "ffprobe.exe")
    if not os.path.exists(ffprobe):
        return 0.0
    try:
        r = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True, timeout=5,
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def make_pixmap(path: str, size: tuple) -> QPixmap:
    try:
        img = Image.open(path).convert("RGB")
        img = img.resize(size, Image.LANCZOS)
        data = img.tobytes("raw", "RGB")
        qi = QImage(data, size[0], size[1], size[0] * 3, QImage.Format.Format_RGB888).copy()
        return QPixmap.fromImage(qi)
    except Exception:
        pm = QPixmap(*size)
        pm.fill(QColor("#252525"))
        return pm


def rounded_pix(pm: QPixmap, r: int = 8) -> QPixmap:
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(pm.rect()), r, r)
    p.setClipPath(path)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


def fmt_time(secs: float) -> str:
    s = max(0, int(secs))
    return f"{s // 60}:{s % 60:02d}"


# ─── Stylesheet ───────────────────────────────────────────────────────────────

QSS = """
* { font-family: 'Segoe UI', Arial, sans-serif; }

QMainWindow, QWidget { background: #0d0d0d; color: #fff; }

/* ── sidebar ── */
QWidget#sidebar {
    background: #111111;
    border-right: 1px solid #1e1e1e;
}
QLabel#logo {
    color: #1db954;
    font-size: 20px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 4px 0;
}
QPushButton.nav {
    background: transparent;
    color: #a0a0a0;
    text-align: left;
    border: none;
    border-radius: 8px;
    padding: 11px 16px;
    font-size: 14px;
}
QPushButton.nav:hover  { background: #1a1a1a; color: #ffffff; }
QPushButton.nav:checked { background: #1a1a1a; color: #1db954; font-weight: bold; }

/* ── now-playing bar ── */
QWidget#npbar {
    background: #111111;
    border-top: 1px solid #1e1e1e;
}
QLabel#np-title  { color: #ffffff; font-size: 13px; font-weight: bold; }
QLabel#np-artist { color: #a0a0a0; font-size: 11px; }
QLabel#np-time   { color: #a0a0a0; font-size: 11px; min-width: 36px; }

/* ── transport controls ── */
QPushButton#ctrl {
    background: transparent; color: #a0a0a0;
    border: none; border-radius: 4px;
    font-size: 18px; padding: 4px 8px; min-width: 32px;
}
QPushButton#ctrl:hover { color: #ffffff; }
QPushButton#ctrl-main {
    background: transparent; color: #a0a0a0;
    border: none; border-radius: 18px;
    font-size: 18px; min-width: 36px; min-height: 36px; padding: 4px 10px;
}
QPushButton#ctrl-main:hover { color: #ffffff; background: #1a1a1a; }

/* ── sliders ── */
QSlider#prog, QSlider#vol { background: transparent; }
QSlider#prog::groove:horizontal { background:#333; height:4px; border-radius:2px; }
QSlider#prog::add-page:horizontal { background:#333; height:4px; border-radius:2px; }
QSlider#prog::sub-page:horizontal { background:#1db954; height:4px; border-radius:2px; }
QSlider#prog::handle:horizontal {
    background:#ffffff; width:10px; height:10px;
    border-radius:5px; margin:-5px 0;
}
QSlider#prog:hover::handle:horizontal { background:#ffffff; }

QSlider#vol::groove:horizontal { background:#333; height:3px; border-radius:2px; }
QSlider#vol::add-page:horizontal { background:#333; height:3px; border-radius:2px; }
QSlider#vol::sub-page:horizontal { background:#a0a0a0; height:3px; border-radius:2px; }
QSlider#vol::sub-page:horizontal:hover { background:#1db954; }
QSlider#vol::handle:horizontal {
    background:#ffffff; width:10px; height:10px;
    border-radius:5px; margin:-4px 0;
}

/* ── scrollbar ── */
QScrollBar:vertical { background:transparent; width:6px; margin:0; }
QScrollBar::handle:vertical { background:#2a2a2a; border-radius:3px; min-height:20px; }
QScrollBar::handle:vertical:hover { background:#555; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }

/* ── search bar ── */
QLineEdit#search {
    background:#1a1a1a; color:#fff;
    border:1px solid #2a2a2a; border-radius:20px;
    padding:8px 18px; font-size:13px;
}
QLineEdit#search:focus { border-color: #ffffff; }

/* ── page ── */
QLabel#page-title { color:#fff; font-size:26px; font-weight:bold; }
QLabel#section-label { color:#a0a0a0; font-size:11px; font-weight:bold; letter-spacing:1px; }

/* ── song row ── */
QWidget#song-row { background: transparent; border-radius: 8px; }

/* ── playlist card ── */
QWidget#pl-card { background:#1a1a1a; border-radius:12px; }
QWidget#pl-card:hover { background:#222222; }
QLabel#pl-name  { color:#fff; font-size:13px; font-weight:bold; }
QLabel#pl-count { color:#a0a0a0; font-size:11px; }

/* ── buttons ── */
QPushButton#green-btn {
    background:#1db954; color:#000;
    border:none; border-radius:20px;
    padding:10px 24px; font-size:13px; font-weight:bold;
}
QPushButton#green-btn:hover { background:#1ed760; }
QPushButton#green-btn:disabled { background:#1a4d30; color:#555; }

QPushButton#ghost-btn {
    background:transparent; color:#a0a0a0;
    border:1px solid #333; border-radius:20px;
    padding:10px 24px; font-size:13px;
}
QPushButton#ghost-btn:hover { background:#1a1a1a; color:#fff; border-color:#fff; }

QPushButton#back-btn {
    background:#1a1a1a; color:#a0a0a0;
    border:none; border-radius:8px;
    padding:7px 14px; font-size:13px;
}
QPushButton#back-btn:hover { background:#252525; color:#fff; }

QPushButton#row-play {
    background:#1db954; color:#000;
    border:none; border-radius:4px;
    padding:5px 14px; font-size:12px; font-weight:bold;
}
QPushButton#row-play:hover { background:#1ed760; }

QPushButton#row-del {
    background:transparent; color:#a0a0a0;
    border:1px solid #333; border-radius:13px;
    font-size:13px; font-weight:bold;
}
QPushButton#row-del:hover { background:#3a1a1a; color:#ff6b6b; border-color:#ff6b6b; }

/* ── downloader ── */
QTabWidget::pane { background:transparent; border:none; }
QTabBar::tab { background:transparent; color:#a0a0a0; padding:10px 24px; border:none; font-size:13px; }
QTabBar::tab:selected { color:#fff; border-bottom:2px solid #1db954; }
QTabBar::tab:hover { color:#fff; }

QLineEdit {
    background:#1a1a1a; color:#fff;
    border:1px solid #2a2a2a; border-radius:8px;
    padding:10px 14px; font-size:13px;
}
QLineEdit:focus { border-color:#1db954; }

QListWidget {
    background:#1a1a1a; color:#fff;
    border:none; border-radius:8px;
}
QListWidget::item { padding:8px 12px; border-radius:4px; }
QListWidget::item:selected { background:#252525; color:#1db954; }
QListWidget::item:hover { background:#1f1f1f; }

QLabel#status { color:#a0a0a0; font-size:12px; padding:2px 0; }

QScrollArea, QScrollArea > QWidget > QWidget { background:transparent; border:none; }
"""


# ─── Worker threads ───────────────────────────────────────────────────────────

class ClickableSlider(QSlider):
    """Slider that jumps to the clicked spot on the track.

    Fusion + custom QSS keeps the handle draggable but drops the native
    'click on the track to set the value' behavior, so we restore it here.
    """

    def mousePressEvent(self, e):
        if (e.button() == Qt.MouseButton.LeftButton
                and self.orientation() == Qt.Orientation.Horizontal):
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)
            groove = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove)
            handle = self.style().subControlRect(
                QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle)
            if handle.isValid() and handle.contains(e.position().toPoint()):
                super().mousePressEvent(e)
                return
            if groove.isValid() and groove.width() > 0:
                x = int(e.position().x())
                x = max(groove.left(), min(groove.right(), x))
                value = QStyle.sliderValueFromPosition(
                    self.minimum(), self.maximum(), x - groove.left(), groove.width())
                self.setValue(value)
                self.sliderReleased.emit()
                return
        super().mousePressEvent(e)


class SeekSlider(QWidget):
    """Custom-painted progress slider. No Fusion halo, precise click + drag."""

    seekRequested = pyqtSignal(int)   # value (0..1000) committed on release
    dragStarted = pyqtSignal()
    dragEnded = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._dragging = False
        self.setFixedHeight(24)
        self.setMinimumWidth(120)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # -- value API ----------------------------------------------
    def setValue(self, v):
        v = max(0, min(1000, int(v)))
        if not self._dragging:
            self._value = v
        self.update()

    def value(self):
        return self._value

    # -- input ------------------------------------------------
    def _frac_from(self, x) -> float:
        pad = 10
        w = self.width() - 2 * pad
        if w <= 0:
            return 0.0
        return max(0.0, min(1.0, (x - pad) / w))

    def _value_from(self, x) -> int:
        return int(round(self._frac_from(x) * 1000))

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._value = self._value_from(e.position().x())
            self.dragStarted.emit()
            self.update()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._dragging:
            self._value = self._value_from(e.position().x())
            self.update()

    def mouseReleaseEvent(self, e):
        if self._dragging:
            self._dragging = False
            self._value = self._value_from(e.position().x())
            self.dragEnded.emit()
            self.seekRequested.emit(self._value)
            self.update()
            return
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    # -- paint ------------------------------------------------
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pad = 10
        track_h = 5
        y = (self.height() - track_h) // 2
        w = self.width() - 2 * pad
        frac = self._value / 1000.0
        r = track_h / 2

        track = QRectF(pad, y, w, track_h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#333333"))
        p.drawRoundedRect(track, r, r)

        fill_w = max(1.0, w * frac)
        fill = QRectF(pad, y, fill_w, track_h)
        p.setBrush(QColor("#1db954"))
        p.drawRoundedRect(fill, r, r)

        cx = pad + w * frac
        cy = self.height() / 2
        hr = 5.5
        # subtle dark ring so the handle reads on any fill color
        p.setBrush(QColor("#878787"))
        p.drawEllipse(QPointF(cx, cy), hr + 1.5, hr + 1.5)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(cx, cy), hr, hr)
        p.end()


class _DurThread(QThread):
    result = pyqtSignal(float)

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self):
        self.result.emit(get_audio_duration(self._path))


class DownloadThread(QThread):
    status_signal = pyqtSignal(str)
    done_signal   = pyqtSignal(bool)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn   = fn
        self._args = args
        self._kw   = kwargs

    def run(self):
        try:
            self._fn(*self._args, on_status=self.status_signal.emit, **self._kw)
            self.done_signal.emit(True)
        except Exception as e:
            self.status_signal.emit(f"Error: {e}")
            self.done_signal.emit(False)


class _FfmpegWorker(QThread):
    done = pyqtSignal(str)

    def run(self):
        from ffmpeg_manager import ensure_ffmpeg
        _ok, msg = ensure_ffmpeg()
        self.done.emit(msg)


# ─── Now Playing Bar ─────────────────────────────────────────────────────────

class NowPlayingBar(QWidget):
    def __init__(self, player: MusicPlayer, parent=None):
        super().__init__(parent)
        self.player = player
        self.setObjectName("npbar")
        self.setFixedHeight(88)
        self._duration = 0.0
        self._dragging = False
        self._setup_ui()

        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(20, 8, 20, 8)
        root.setSpacing(0)

        # ── left: art + info ──────────────────────────
        left = QHBoxLayout()
        left.setSpacing(12)

        self.art_lbl = QLabel()
        self.art_lbl.setFixedSize(52, 52)
        self.art_lbl.setStyleSheet("border-radius: 6px; background: #1a1a1a;")
        left.addWidget(self.art_lbl)

        info = QVBoxLayout()
        info.setSpacing(2)
        self.title_lbl  = QLabel("Not playing")
        self.title_lbl.setObjectName("np-title")
        self.title_lbl.setMaximumWidth(200)
        self.title_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.artist_lbl = QLabel("")
        self.artist_lbl.setObjectName("np-artist")
        info.addWidget(self.title_lbl)
        info.addWidget(self.artist_lbl)
        left.addLayout(info)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setMinimumWidth(220)

        # ── centre: controls + progress ───────────────
        centre = QVBoxLayout()
        centre.setSpacing(6)
        centre.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.shuffle_btn = self._make_ctrl("⇄")
        self.prev_btn    = self._make_ctrl("⏮")
        self.play_btn    = QPushButton("▶")
        self.play_btn.setObjectName("ctrl-main")
        self.play_btn.setFixedSize(36, 36)
        self.next_btn    = self._make_ctrl("⏭")
        self.repeat_btn  = self._make_ctrl("↻")

        self.shuffle_btn.setCheckable(True)
        self.repeat_btn.setCheckable(True)

        for b in (self.shuffle_btn, self.prev_btn, self.play_btn, self.next_btn, self.repeat_btn):
            btns.addWidget(b)

        self.play_btn.clicked.connect(self._on_play_pause)
        self.prev_btn.clicked.connect(self._on_prev)
        self.next_btn.clicked.connect(self._on_next)

        # progress row
        prog_row = QHBoxLayout()
        prog_row.setSpacing(8)
        self.elapsed_lbl = QLabel("0:00")
        self.elapsed_lbl.setObjectName("np-time")
        self.total_lbl = QLabel("0:00")
        self.total_lbl.setObjectName("np-time")

        self.prog_slider = SeekSlider()
        self.prog_slider.dragStarted.connect(lambda: setattr(self, "_dragging", True))
        self.prog_slider.dragEnded.connect(lambda: setattr(self, "_dragging", False))
        self.prog_slider.seekRequested.connect(self._on_seek)

        prog_row.addWidget(self.elapsed_lbl)
        prog_row.addWidget(self.prog_slider, 1)
        prog_row.addWidget(self.total_lbl)

        centre.addLayout(btns)
        centre.addLayout(prog_row)

        # ── right: volume ──────────────────────────────
        right = QHBoxLayout()
        right.setSpacing(8)
        right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        vol_icon = QLabel("🔊")
        vol_icon.setStyleSheet("color: #a0a0a0; font-size: 14px;")
        self.vol_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setObjectName("vol")
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.valueChanged.connect(lambda v: self.player.change_volume(v / 100))
        self.player.change_volume(0.8)
        right.addWidget(vol_icon)
        right.addWidget(self.vol_slider)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setMinimumWidth(180)

        root.addWidget(left_w)
        root.addStretch(1)
        root.addLayout(centre, 0)
        root.addStretch(1)
        root.addWidget(right_w)

    def _make_ctrl(self, text: str) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName("ctrl")
        b.setFixedSize(32, 32)
        return b

    # ── public API ────────────────────────────────────

    def load_song(self, name: str, image_path: str, duration: float):
        self._duration = duration
        self.title_lbl.setText(name)
        self.artist_lbl.setText("")
        self.prog_slider.setValue(0)
        self.elapsed_lbl.setText("0:00")
        self.total_lbl.setText(fmt_time(duration))
        pm = rounded_pix(make_pixmap(image_path, (52, 52)), r=6)
        self.art_lbl.setPixmap(pm)
        self.play_btn.setText("⏸")

    def update_duration(self, duration: float):
        self._duration = duration
        self.total_lbl.setText(fmt_time(duration))

    # ── internal ──────────────────────────────────────

    def _tick(self):
        if self.player.is_active() and not self._dragging:
            pos = self.player.get_position()
            self.elapsed_lbl.setText(fmt_time(pos))
            if self._duration > 0:
                self.prog_slider.setValue(int(pos / self._duration * 1000))
        if self.player.is_playing():
            self.play_btn.setText("⏸")
        elif self.player.is_paused():
            self.play_btn.setText("▶")

        # Auto-advance
        win = self.window()
        if isinstance(win, MainWindow) and self.player.song_ended():
            win.next_song(from_end=True)

    def _on_play_pause(self):
        if not self.player.is_active():
            return
        self.player.toggle_pause()

    def _on_prev(self):
        win = self.window()
        if isinstance(win, MainWindow):
            win.prev_song()

    def _on_next(self):
        win = self.window()
        if isinstance(win, MainWindow):
            win.next_song()

    def _on_seek(self):
        self._dragging = False
        if self._duration > 0:
            target = self.prog_slider.value() / 1000 * self._duration
            self.player.seek(target)


# ─── Sidebar ──────────────────────────────────────────────────────────────────

class Sidebar(QWidget):
    page_changed = pyqtSignal(str)

    PAGES = [("🎵  Library", "library"), ("📋  Playlists", "playlists"), ("⬇  Download", "download")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 24, 12, 24)
        layout.setSpacing(4)

        logo = QLabel("DOTIFY")
        logo.setObjectName("logo")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)
        layout.addSpacing(24)

        self._btns: list[QPushButton] = []
        for label, page_id in self.PAGES:
            btn = QPushButton(label)
            btn.setProperty("class", "nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, pid=page_id: self._select(pid))
            layout.addWidget(btn)
            self._btns.append(btn)

        layout.addStretch()
        self._select("library")

    def _select(self, page_id: str):
        for btn, (_, pid) in zip(self._btns, self.PAGES):
            btn.setChecked(pid == page_id)
        self.page_changed.emit(page_id)


# ─── Song Row ─────────────────────────────────────────────────────────────────

class SongRow(QWidget):
    play_clicked = pyqtSignal(int)  # emits queue index
    delete_requested = pyqtSignal(str)  # emits song (folder) name

    def __init__(self, index: int, name: str, image_path: str, is_playing: bool = False):
        super().__init__()
        self.setObjectName("song-row")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.index = index
        self._name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(12)

        art = QLabel()
        art.setFixedSize(44, 44)
        art.setPixmap(rounded_pix(make_pixmap(image_path, (44, 44)), r=5))
        layout.addWidget(art)

        title = QLabel(name)
        title.setStyleSheet(
            "color: #1db954; font-size: 13px; font-weight: bold;"
            if is_playing else "color: #ffffff; font-size: 13px;"
        )
        title.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title.setMinimumWidth(200)
        layout.addWidget(title, 1)

        btn = QPushButton("▶  Play")
        btn.setObjectName("row-play")
        btn.setFixedWidth(72)
        btn.clicked.connect(lambda: self.play_clicked.emit(self.index))
        layout.addWidget(btn)

        del_btn = QPushButton("⌫")
        del_btn.setObjectName("row-del")
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("Delete")
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self._name))
        layout.addWidget(del_btn)

    def mousePressEvent(self, event):
        self.play_clicked.emit(self.index)


# ─── Library Page ─────────────────────────────────────────────────────────────

class LibraryPage(QWidget):
    play_requested = pyqtSignal(list, int)  # queue, index

    def __init__(self, manager: MusicManager):
        super().__init__()
        self._manager = manager
        self._all_songs: list[tuple] = []
        self._current_index = -1
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 12)
        layout.setSpacing(12)

        title = QLabel("Library")
        title.setObjectName("page-title")
        layout.addWidget(title)

        self._search = QLineEdit()
        self._search.setObjectName("search")
        self._search.setPlaceholderText("🔍  Search songs…")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._vbox = QVBoxLayout(self._content)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(4)
        self._vbox.addStretch()
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

        reload_btn = QPushButton("↺  Reload Library")
        reload_btn.setObjectName("ghost-btn")
        reload_btn.setFixedWidth(160)
        reload_btn.clicked.connect(self.load_songs)
        layout.addWidget(reload_btn)

        self.load_songs()

    def load_songs(self):
        songs = self._manager.get_songs()
        self._all_songs = list(songs.items())
        self._render(self._all_songs)

    def _filter(self, text: str):
        q = text.lower()
        filtered = [(n, d) for n, d in self._all_songs if q in n.lower()]
        self._render(filtered)

    def _render(self, songs: list):
        # Remove old rows (leave stretch at end)
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (name, data) in enumerate(songs):
            row = SongRow(i, name, data.get("image_path", NO_IMG),
                          is_playing=(i == self._current_index))
            row.play_clicked.connect(lambda idx, s=songs: self.play_requested.emit(s, idx))
            row.delete_requested.connect(self._delete_song)
            self._vbox.insertWidget(self._vbox.count() - 1, row)

    def _delete_song(self, name: str):
        resp = QMessageBox.question(
            self, "Delete Song",
            f"Delete '{name}' from the library?\nThis removes its folder on disk.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            self._manager.delete_song(name)
            self.load_songs()

    def set_playing_index(self, index: int):
        self._current_index = index


# ─── Playlist Card ────────────────────────────────────────────────────────────

class PlaylistCard(QWidget):
    clicked = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, name: str, song_count: int, art_path: str):
        super().__init__()
        self.setObjectName("pl-card")
        self.setFixedSize(156, 196)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._name = name

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        art = QLabel()
        art.setFixedSize(132, 132)
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setPixmap(rounded_pix(make_pixmap(art_path, (132, 132)), r=8))
        layout.addWidget(art)

        lbl = QLabel(name)
        lbl.setObjectName("pl-name")
        lbl.setWordWrap(True)
        lbl.setMaximumWidth(132)
        layout.addWidget(lbl)

        cnt = QLabel(f"{song_count} songs")
        cnt.setObjectName("pl-count")
        layout.addWidget(cnt)

        self._del_btn = QPushButton("⌫")
        self._del_btn.setObjectName("row-del")
        self._del_btn.setFixedSize(26, 26)
        self._del_btn.setToolTip("Delete playlist")
        self._del_btn.setParent(self)
        self._del_btn.raise_()
        self._del_btn.clicked.connect(lambda: self.delete_requested.emit(self._name))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._del_btn.move(self.width() - self._del_btn.width() - 8, 8)

    def mousePressEvent(self, event):
        self.clicked.emit(self._name)


# ─── Playlists Page ───────────────────────────────────────────────────────────

class PlaylistsPage(QWidget):
    open_playlist = pyqtSignal(str)

    def __init__(self, manager: MusicManager):
        super().__init__()
        self._manager = manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Playlists")
        title.setObjectName("page-title")
        header.addWidget(title)
        header.addStretch()
        new_btn = QPushButton("＋  New Playlist")
        new_btn.setObjectName("green-btn")
        new_btn.clicked.connect(self._create_playlist)
        header.addWidget(new_btn)
        layout.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._grid_w = QWidget()
        self._grid = QGridLayout(self._grid_w)
        self._grid.setSpacing(16)
        self._grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_w)
        layout.addWidget(self._scroll, 1)

        self.load_playlists()

    def load_playlists(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        playlists = self._manager.get_playlists()
        songs_all = self._manager.get_songs()
        col_max = 4
        for i, (name, _) in enumerate(playlists.items()):
            songs = self._manager.get_playlist_songs(name)
            art = songs[0][1].get("image_path", NO_IMG) if songs else NO_IMG
            card = PlaylistCard(name, len(songs), art)
            card.clicked.connect(self.open_playlist)
            card.delete_requested.connect(self._delete_playlist)
            self._grid.addWidget(card, i // col_max, i % col_max)

    def _delete_playlist(self, name: str):
        resp = QMessageBox.question(
            self, "Delete Playlist",
            f"Delete playlist '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            self._manager.delete_playlist(name)
            self.load_playlists()

    def _create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")
        if ok and name.strip():
            if self._manager.create_playlist(name.strip()):
                self.load_playlists()
            else:
                QMessageBox.warning(self, "Error", "A playlist with that name already exists.")


# ─── Playlist Songs Page ──────────────────────────────────────────────────────

class PlaylistSongsPage(QWidget):
    play_requested = pyqtSignal(list, int)
    back_clicked   = pyqtSignal()

    def __init__(self, manager: MusicManager):
        super().__init__()
        self._manager = manager
        self._songs: list[tuple] = []
        self._playlist_name = ""
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        back_btn = QPushButton("← Playlists")
        back_btn.setObjectName("back-btn")
        back_btn.clicked.connect(self.back_clicked)
        self._del_pl_btn = QPushButton("🗑  Delete Playlist")
        self._del_pl_btn.setObjectName("ghost-btn")
        self._del_pl_btn.clicked.connect(self._delete_playlist)
        header.addWidget(back_btn)
        header.addWidget(self._del_pl_btn)
        header.addStretch()
        self._title_lbl = QLabel("Playlist")
        self._title_lbl.setObjectName("page-title")
        header.addWidget(self._title_lbl)
        header.addStretch()
        layout.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._content = QWidget()
        self._vbox = QVBoxLayout(self._content)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(4)
        self._vbox.addStretch()
        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll, 1)

    def load(self, playlist_name: str):
        self._playlist_name = playlist_name
        self._title_lbl.setText(playlist_name)
        self._songs = self._manager.get_playlist_songs(playlist_name)

        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (name, data) in enumerate(self._songs):
            row = SongRow(i, name, data.get("image_path", NO_IMG))
            row.play_clicked.connect(lambda idx: self.play_requested.emit(self._songs, idx))
            row.delete_requested.connect(self._remove_song_from_playlist)
            self._vbox.insertWidget(self._vbox.count() - 1, row)

    def _remove_song_from_playlist(self, name: str):
        resp = QMessageBox.question(
            self, "Remove from Playlist",
            f"Remove '{name}' from '{self._playlist_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            self._manager.remove_from_playlist(self._playlist_name, name)
            self.load(self._playlist_name)

    def _delete_playlist(self):
        resp = QMessageBox.question(
            self, "Delete Playlist",
            f"Delete playlist '{self._playlist_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if resp == QMessageBox.StandardButton.Yes:
            self._manager.delete_playlist(self._playlist_name)
            self.back_clicked.emit()


# ─── Downloader Page ──────────────────────────────────────────────────────────

class SoundCloudTab(QWidget):
    def __init__(self):
        super().__init__()
        self._thread: DownloadThread | None = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(10)

        label = QLabel("Paste a SoundCloud track or playlist URL:")
        label.setStyleSheet("color: #a0a0a0; font-size: 13px;")
        layout.addWidget(label)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("https://soundcloud.com/…")
        layout.addWidget(self._entry)

        self._status = QLabel("Ready.")
        self._status.setObjectName("status")
        layout.addWidget(self._status)

        dl_btn = QPushButton("⬇  Download")
        dl_btn.setObjectName("green-btn")
        dl_btn.setFixedWidth(160)
        dl_btn.clicked.connect(self._download)
        layout.addWidget(dl_btn)
        layout.addStretch()

    def _download(self):
        url = self._entry.text().strip()
        if not url:
            self._status.setText("Enter a URL first.")
            return
        self._status.setText("Starting…")
        self._thread = DownloadThread(sc_dl.download, url)
        self._thread.status_signal.connect(self._status.setText)
        self._thread.done_signal.connect(lambda ok: self._status.setText(
            "✔ Done!" if ok else "✘ Failed."
        ))
        self._thread.start()


class DownloaderPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 12)
        layout.setSpacing(12)

        title = QLabel("Download Music")
        title.setObjectName("page-title")
        layout.addWidget(title)

        layout.addWidget(SoundCloudTab(), 1)


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        pygame.mixer.init()
        pygame.init()

        self.setWindowTitle("Dotify")
        self.resize(960, 660)
        try:
            self.setWindowIcon(QIcon(os.path.join(BASE_DIR, "icon.ico")))
        except Exception:
            pass

        self._manager = MusicManager()
        self._player  = MusicPlayer()
        self._queue: list[tuple] = []
        self._queue_index = -1

        self._build_ui()
        self._warm_ffmpeg()

    def _warm_ffmpeg(self):
        """Auto-download ffmpeg in the background so it's ready before a download."""
        import ffmpeg_manager
        if ffmpeg_manager.ffmpeg_ready():
            return
        self._ffmpeg_worker = _FfmpegWorker()
        self._ffmpeg_worker.done.connect(
            lambda msg: self.statusBar().showMessage(f"ffmpeg: {msg}", 8000))
        self._ffmpeg_worker.start()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── body (sidebar + stack) ──
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._on_page_changed)
        body.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        self._lib_page  = LibraryPage(self._manager)
        self._pl_page   = PlaylistsPage(self._manager)
        self._plsongs   = PlaylistSongsPage(self._manager)
        self._dl_page   = DownloaderPage()

        for w in (self._lib_page, self._pl_page, self._plsongs, self._dl_page):
            self._stack.addWidget(w)

        self._lib_page.play_requested.connect(self._play_from_queue)
        self._plsongs.play_requested.connect(self._play_from_queue)
        self._pl_page.open_playlist.connect(self._open_playlist)
        self._plsongs.back_clicked.connect(lambda: self._stack.setCurrentWidget(self._pl_page))

        body.addWidget(self._stack, 1)

        # ── now playing bar ──
        self._np = NowPlayingBar(self._player)

        outer.addLayout(body, 1)
        outer.addWidget(self._np)

        self._stack.setCurrentWidget(self._lib_page)

    # ── navigation ────────────────────────────────────

    def _on_page_changed(self, page_id: str):
        mapping = {"library": self._lib_page, "playlists": self._pl_page, "download": self._dl_page}
        if page_id == "playlists":
            self._pl_page.load_playlists()
        self._stack.setCurrentWidget(mapping[page_id])

    def _open_playlist(self, name: str):
        self._plsongs.load(name)
        self._stack.setCurrentWidget(self._plsongs)

    # ── playback ──────────────────────────────────────

    def _play_from_queue(self, queue: list, index: int):
        self._queue = queue
        self._queue_index = index
        self._play_index(index)

    def _play_index(self, index: int):
        if index < 0 or index >= len(self._queue):
            return
        self._queue_index = index
        name, data = self._queue[index]
        path = data["song_path"]
        image = data.get("image_path", NO_IMG)
        self._player.play(path)

        # get duration in a thread to avoid blocking
        self._np.load_song(name, image, 0.0)
        self._dur_thread = _DurThread(path)
        self._dur_thread.result.connect(self._np.update_duration)
        self._dur_thread.start()

    def next_song(self, from_end: bool = False):
        if not self._queue:
            return
        if self._np.repeat_btn.isChecked() and from_end:
            self._play_index(self._queue_index)
            return
        if self._np.shuffle_btn.isChecked():
            import random
            new_idx = random.randint(0, len(self._queue) - 1)
        else:
            new_idx = self._queue_index + 1
        if new_idx < len(self._queue):
            self._play_index(new_idx)
        else:
            self._player.stop()

    def prev_song(self):
        if not self._queue:
            return
        # If >3 seconds in, restart; otherwise go back
        if self._player.get_position() > 3:
            self._play_index(self._queue_index)
        else:
            new_idx = max(0, self._queue_index - 1)
            self._play_index(new_idx)


# ─── Entry Point ─────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    # Fusion so QSS subcontrols (::groove/::sub-page/::handle) render correctly
    # instead of the native Windows style painting a white slider.
    app.setStyle("Fusion")
    app.setStyleSheet(QSS)

    # Set Segoe UI font globally if available
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
