"""
PlaybackControls — redesigned with:
- ASCII-safe button labels (no broken Unicode glyphs)
- Step-size selector (1h / 6h / 12h / 24h) that controls how far
  each "|<" / ">|" click jumps
- Speed buttons show "1x" "2x" "5x" "10x" (lowercase x, always works)
- Speed tooltip explains hours-per-second rate

Signals
-------
  play_requested   ()
  pause_requested  ()
  step_forward     (int amount)   ← carries chosen step size
  step_backward    (int amount)
  hour_changed     (int)          ← slider scrub
  speed_changed    (int)          ← multiplier 1/2/5/10
  reset_requested  ()
  export_requested ()
"""
from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QSlider, QLabel, QButtonGroup, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal


class PlaybackControls(QWidget):

    play_requested   = pyqtSignal()
    pause_requested  = pyqtSignal()
    step_forward     = pyqtSignal(int)
    step_backward    = pyqtSignal(int)
    hour_changed     = pyqtSignal(int)
    speed_changed    = pyqtSignal(int)
    reset_requested  = pyqtSignal()
    export_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._block_slider = False
        self._step_size    = 1    # hours per step-click
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 4, 6, 2)
        root.setSpacing(5)

        # ── Row 1: transport + step size + speed + utilities ──────
        row1 = QHBoxLayout(); row1.setSpacing(6)

        # Transport
        self._btn_back  = self._btn("|<", 34, 28, tip="Step backward (by selected step size)")
        self._btn_play  = self._btn("Play  >>", 90, 28, checkable=True)
        self._btn_fwd   = self._btn(">|", 34, 28, tip="Step forward (by selected step size)")

        row1.addWidget(self._btn_back)
        row1.addWidget(self._btn_play)
        row1.addWidget(self._btn_fwd)
        row1.addWidget(self._vline())

        # Step-size selector
        lbl_step = QLabel("Step:")
        lbl_step.setStyleSheet("color:#8b949e; font-size:10px;")
        row1.addWidget(lbl_step)

        self._step_group = QButtonGroup(self)
        self._step_btns: dict[int, QPushButton] = {}
        for hours in (1, 6, 12, 24):
            b = self._btn(f"{hours}h", 36, 26, checkable=True, tip=f"Step {hours} hour(s) at a time")
            b.setProperty("step_h", hours)
            self._step_group.addButton(b)
            self._step_btns[hours] = b
            row1.addWidget(b)
        self._step_btns[1].setChecked(True)

        row1.addWidget(self._vline())

        # Speed selector
        lbl_spd = QLabel("Speed:")
        lbl_spd.setStyleSheet("color:#8b949e; font-size:10px;")
        row1.addWidget(lbl_spd)

        self._speed_group = QButtonGroup(self)
        self._speed_btns: dict[int, QPushButton] = {}
        for spd, tip in ((1,"1 hour / second"), (2,"2 hours / second"),
                         (5,"5 hours / second"), (10,"10 hours / second")):
            b = self._btn(f"{spd}x", 38, 26, checkable=True, tip=tip)
            b.setProperty("spd", spd)
            self._speed_group.addButton(b)
            self._speed_btns[spd] = b
            row1.addWidget(b)
        self._speed_btns[1].setChecked(True)

        row1.addWidget(self._vline())
        row1.addStretch()

        self._btn_reset  = self._btn("Reset",      72, 26, tip="Rewind to hour 0")
        self._btn_export = self._btn("Export CSV", 96, 26, tip="Save 73-hour data as CSV")
        row1.addWidget(self._btn_reset)
        row1.addWidget(self._btn_export)

        # ── Row 2: hour scrubber ──────────────────────────────────
        row2 = QHBoxLayout(); row2.setSpacing(8)

        lbl_h  = QLabel("Hour:")
        lbl_h.setStyleSheet("color:#8b949e; font-size:10px;")
        lbl_0  = QLabel("0 h")
        lbl_0.setStyleSheet("color:#484f58; font-size:10px;")
        lbl_72 = QLabel("72 h")
        lbl_72.setStyleSheet("color:#484f58; font-size:10px;")

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 72)
        self._slider.setValue(0)
        self._slider.setTickInterval(6)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)

        self._lbl_cur = QLabel("0 h")
        self._lbl_cur.setFixedWidth(38)
        self._lbl_cur.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_cur.setStyleSheet("color:#58a6ff; font-size:11px; font-weight:bold;")

        for w in (lbl_h, lbl_0): row2.addWidget(w)
        row2.addWidget(self._slider, stretch=1)
        row2.addWidget(lbl_72)
        row2.addWidget(self._lbl_cur)

        root.addLayout(row1)
        root.addLayout(row2)

        # ── Wire ─────────────────────────────────────────────────
        self._btn_back.clicked.connect(self._on_back)
        self._btn_fwd.clicked.connect(self._on_fwd)
        self._btn_play.clicked.connect(self._on_play)
        self._btn_reset.clicked.connect(self._on_reset)
        self._btn_export.clicked.connect(self.export_requested)
        self._slider.valueChanged.connect(self._on_slider)
        self._step_group.buttonClicked.connect(self._on_step_size)
        self._speed_group.buttonClicked.connect(self._on_speed)

    # ── Helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _btn(text: str, w: int = 0, h: int = 28,
             checkable: bool = False, tip: str = "") -> QPushButton:
        b = QPushButton(text)
        if w: b.setFixedWidth(w)
        b.setFixedHeight(h)
        b.setCheckable(checkable)
        if tip: b.setToolTip(tip)
        return b

    @staticmethod
    def _vline() -> QFrame:
        f = QFrame(); f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet("color:#30363d;"); f.setFixedWidth(1); return f

    # ── Slots ─────────────────────────────────────────────────────────────
    def _on_play(self, checked: bool):
        if checked:
            self._btn_play.setText("|| Pause")
            self.play_requested.emit()
        else:
            self._btn_play.setText("Play  >>")
            self.pause_requested.emit()

    def _on_back(self):
        self.step_backward.emit(self._step_size)

    def _on_fwd(self):
        self.step_forward.emit(self._step_size)

    def _on_slider(self, value: int):
        if not self._block_slider:
            self._lbl_cur.setText(f"{value} h")
            self.hour_changed.emit(value)

    def _on_step_size(self, btn: QPushButton):
        h = btn.property("step_h")
        if h: self._step_size = int(h)

    def _on_speed(self, btn: QPushButton):
        s = btn.property("spd")
        if s: self.speed_changed.emit(int(s))

    def _on_reset(self):
        self._btn_play.setChecked(False)
        self._btn_play.setText("Play  >>")
        self.reset_requested.emit()

    # ── External control ──────────────────────────────────────────────────
    def set_hour(self, hour: int):
        self._block_slider = True
        self._slider.setValue(hour)
        self._lbl_cur.setText(f"{hour} h")
        self._block_slider = False

    def set_playing(self, playing: bool):
        self._btn_play.setChecked(playing)
        self._btn_play.setText("|| Pause" if playing else "Play  >>")
