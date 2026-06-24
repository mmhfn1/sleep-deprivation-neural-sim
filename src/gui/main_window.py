"""
MainWindow — master layout, header, and signal routing.

Changes from v1:
- Gauge now receives snap.W (sleep pressure) instead of impairment_index
  so the arc position and the header label are always in agreement.
- Adenosine S display uses .4f to avoid showing "1.000" when S≈0.9999.
- step_forward/step_backward slots accept an `amount` int parameter.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QLabel, QFrame, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QFont

from ..simulation.engine import SimulationEngine
from .widgets.neural_canvas    import NeuralCanvas
from .widgets.timeseries_plot  import TimeSeriesPlot
from .widgets.region_panel     import RegionPanel
from .widgets.impairment_gauge import ImpairmentGauge
from .widgets.playback_controls import PlaybackControls
from .widgets.substance_panel   import SubstancePanel


_STATUS_COLORS = {
    "NORMAL":   "#3fb950",
    "MILD":     "#d29922",
    "MODERATE": "#f0883e",
    "SEVERE":   "#f85149",
    "CRITICAL": "#ff2222",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._hour    = 0
        self._playing = False
        self._speed   = 1

        self.engine = SimulationEngine(parent=self)

        self._play_timer = QTimer(self)
        self._play_timer.timeout.connect(self._tick)

        self._build_ui()
        self._connect_signals()

        self.engine.precompute()
        self.timeseries.load_history(self.engine.get_all_snapshots())
        self._push_hour(0)

    # ── UI construction ───────────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("Sleep Deprivation Neural Firing Simulation")
        self.setMinimumSize(1400, 860)
        self.resize(1640, 980)

        root_w = QWidget(); self.setCentralWidget(root_w)
        root = QVBoxLayout(root_w)
        root.setContentsMargins(8,8,8,8); root.setSpacing(6)

        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(3)
        splitter.setStyleSheet("QSplitter::handle { background: #21262d; }")

        self.neural_canvas = NeuralCanvas()
        self.neural_canvas.setMinimumWidth(520)
        splitter.addWidget(self.neural_canvas)
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([620, 780])
        root.addWidget(splitter, stretch=1)

        root.addWidget(self._build_bottom())

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(54)
        frame.setStyleSheet("QFrame{background:#161b22;border:1px solid #30363d;border-radius:6px;}")
        lay = QHBoxLayout(frame); lay.setContentsMargins(16,0,16,0); lay.setSpacing(0)

        title = QLabel("Sleep Deprivation Neural Firing Simulation")
        f = QFont("Segoe UI", 13, QFont.Weight.Bold); title.setFont(f)
        title.setStyleSheet("color:#e6edf3;")

        self._lbl_hours  = QLabel("Hours Awake:  0 h")
        self._lbl_hours.setStyleSheet("color:#58a6ff; font-size:13px; font-weight:bold;")

        self._lbl_status = QLabel("Status:  NORMAL")
        self._lbl_status.setStyleSheet("color:#3fb950; font-size:13px; font-weight:bold;")

        self._lbl_S = QLabel("Adenosine S:  0.2000")
        self._lbl_S.setStyleSheet("color:#8b949e; font-size:12px;")

        self._lbl_W = QLabel("W:  0.000")
        self._lbl_W.setStyleSheet("color:#8b949e; font-size:12px;")

        sep = lambda: self._vline()
        lay.addWidget(title); lay.addStretch()
        lay.addWidget(self._lbl_hours); lay.addWidget(sep())
        lay.addWidget(self._lbl_status); lay.addWidget(sep())
        lay.addWidget(self._lbl_S); lay.addWidget(sep())
        lay.addWidget(self._lbl_W)
        return frame

    def _build_right_panel(self) -> QWidget:
        w = QWidget(); lay = QVBoxLayout(w)
        lay.setContentsMargins(0,0,0,0); lay.setSpacing(6)
        self.timeseries = TimeSeriesPlot()
        lay.addWidget(self.timeseries, stretch=3)
        br = QHBoxLayout(); br.setSpacing(6)
        self.gauge = ImpairmentGauge(); self.gauge.setFixedWidth(162)
        br.addWidget(self.gauge)
        self.region_panel = RegionPanel()
        br.addWidget(self.region_panel, stretch=1)
        lay.addLayout(br, stretch=2)
        return w

    def _build_bottom(self) -> QFrame:
        frame = QFrame(); frame.setFixedHeight(130)
        frame.setStyleSheet("QFrame{background:#161b22;border:1px solid #30363d;border-radius:6px;}")
        lay = QVBoxLayout(frame); lay.setContentsMargins(8,6,8,6); lay.setSpacing(4)
        self.playback = PlaybackControls()
        lay.addWidget(self.playback)
        lay.addWidget(self._hline())
        self.substance = SubstancePanel()
        lay.addWidget(self.substance)
        return frame

    def _vline(self) -> QFrame:
        f = QFrame(); f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet("color:#30363d;"); f.setFixedWidth(1)
        f.setContentsMargins(10,0,10,0); return f

    def _hline(self) -> QFrame:
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("color:#30363d;"); return f

    # ── Signal wiring ─────────────────────────────────────────────────────
    def _connect_signals(self):
        pb = self.playback
        pb.play_requested .connect(self._on_play)
        pb.pause_requested.connect(self._on_pause)
        pb.step_forward   .connect(self._on_step_fwd)
        pb.step_backward  .connect(self._on_step_back)
        pb.hour_changed   .connect(self._on_hour_changed)
        pb.speed_changed  .connect(self._on_speed_changed)
        pb.reset_requested.connect(self._on_reset)
        pb.export_requested.connect(self._on_export)
        self.substance.doses_changed.connect(self._on_doses_changed)

    # ── Playback slots ────────────────────────────────────────────────────
    @pyqtSlot()
    def _on_play(self):
        if self._hour >= 72: self._hour = 0
        self._playing = True
        self._play_timer.start(max(50, int(1000/self._speed)))

    @pyqtSlot()
    def _on_pause(self):
        self._playing = False; self._play_timer.stop()

    @pyqtSlot(int)
    def _on_step_fwd(self, amount: int):
        self._hour = min(72, self._hour + amount)
        self._push_hour(self._hour); self.playback.set_hour(self._hour)

    @pyqtSlot(int)
    def _on_step_back(self, amount: int):
        self._hour = max(0, self._hour - amount)
        self._push_hour(self._hour); self.playback.set_hour(self._hour)

    @pyqtSlot(int)
    def _on_hour_changed(self, hour: int):
        self._hour = hour; self._push_hour(hour)

    @pyqtSlot(int)
    def _on_speed_changed(self, speed: int):
        self._speed = speed
        if self._playing:
            self._play_timer.setInterval(max(50, int(1000/speed)))

    @pyqtSlot()
    def _on_reset(self):
        self._on_pause(); self._hour = 0
        self.engine.reset()
        self.timeseries.reset()
        self.timeseries.load_history(self.engine.get_all_snapshots())
        self.neural_canvas.reset()
        self.substance.reset()
        self._push_hour(0); self.playback.set_hour(0)

    @pyqtSlot()
    def _on_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Simulation Data", "firing_data.csv", "CSV Files (*.csv)"
        )
        if path:
            if not self.engine.export_csv(path):
                QMessageBox.warning(self, "Export Failed",
                                    "No data to export — run the simulation first.")

    @pyqtSlot(list)
    def _on_doses_changed(self, doses: list):
        was_playing = self._playing; self._on_pause()
        self.engine.clear_pharma()
        for d in doses:
            if d["substance"] == "caffeine":
                self.engine.set_caffeine_dose(d["dose_mg"], d["hour"])
            else:
                self.engine.set_nicotine_dose(d["dose_mg"], d["hour"])
        self.engine.precompute()
        self.timeseries.reset()
        self.timeseries.load_history(self.engine.get_all_snapshots())
        self._push_hour(self._hour)
        if was_playing: self._on_play()

    # ── Timer tick ────────────────────────────────────────────────────────
    def _tick(self):
        if self._hour >= 72:
            self._on_pause(); self.playback.set_playing(False); return
        self._hour += 1
        self._push_hour(self._hour); self.playback.set_hour(self._hour)

    # ── Display update ────────────────────────────────────────────────────
    def _push_hour(self, hour: int):
        snap = self.engine.get_snapshot(hour)

        self._lbl_hours.setText(f"Hours Awake:  {hour} h")
        # snap.S is now TRUE biological S (adenosine concentration, never pharma-modified)
        self._lbl_S.setText(f"Adenosine S:  {min(snap.S, 0.9999):.4f}")
        # Show effective W plus the masking delta when pharma is active
        delta = snap.W - snap.W_unmasked
        if abs(delta) > 0.01:
            sign = "+" if delta > 0 else ""
            self._lbl_W.setText(f"W:  {snap.W:.3f}  ({sign}{delta:.3f} pharma)")
        else:
            self._lbl_W.setText(f"W:  {snap.W:.3f}")

        color = _STATUS_COLORS.get(snap.impairment_label, "#3fb950")
        self._lbl_status.setText(f"Status:  {snap.impairment_label}")
        self._lbl_status.setStyleSheet(
            f"color:{color}; font-size:13px; font-weight:bold;"
        )

        self.neural_canvas.update_state(snap)
        self.region_panel.update_state(snap)
        # Pass W to gauge so the arc position matches the header status label
        self.gauge.update_value(snap.W, snap.impairment_label)
        self.timeseries.update_cursor(hour)
