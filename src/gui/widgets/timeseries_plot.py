"""
TimeSeriesPlot — PyQtGraph rolling line chart.

Pre-loads all 73 hours of data via load_history(); thereafter only
the cursor line moves as the user scrubs through hours.  This means
the chart never recomputes or reallocates during playback — only a
single InfiniteLine.setPos() call per tick.

PyQtGraph's setData() is O(n) in the data length but runs in C++,
easily handling 73 points at 60 FPS with zero perceptible lag.
"""

from __future__ import annotations

from typing import Optional
import numpy as np

import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ...models.brain_regions import REGION_PARAMS, REGION_ORDER


# Configure PyQtGraph global defaults (must run before creating any widgets)
pg.setConfigOptions(antialias=True, background="#0d1117", foreground="#8b949e")


def _region_pen(name: str, width: float = 2.0) -> pg.mkPen:
    r, g, b = REGION_PARAMS[name].color_rgb
    return pg.mkPen(color=(r, g, b), width=width)


class TimeSeriesPlot(QWidget):
    """
    Live time-series chart showing firing rates for all 5 brain regions
    over the full 0–72 h simulation timeline.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._hours: np.ndarray = np.array([], dtype=float)
        self._rates: dict[str, np.ndarray] = {
            name: np.array([], dtype=float) for name in REGION_ORDER
        }

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        self.pw = pg.PlotWidget()
        pi = self.pw.getPlotItem()

        # ── Axes ──────────────────────────────────────────────────
        pi.setLabel("left",   "Firing Rate", units="Hz",
                    **{"color": "#8b949e", "font-size": "10px"})
        pi.setLabel("bottom", "Hours Awake",
                    **{"color": "#8b949e", "font-size": "10px"})

        pi.getAxis("left").setStyle(
            tickFont=QFont("Arial", 8),
            tickLength=-5,
        )
        pi.getAxis("bottom").setStyle(
            tickFont=QFont("Arial", 8),
            tickLength=-5,
        )

        # ── Ranges ────────────────────────────────────────────────
        self.pw.setXRange(0, 72, padding=0.01)
        self.pw.setYRange(0, 52, padding=0.02)
        self.pw.setMouseEnabled(x=False, y=False)
        self.pw.showGrid(x=True, y=True, alpha=0.12)

        # ── Legend ────────────────────────────────────────────────
        legend = pi.addLegend(offset=(10, 10), labelTextColor="#8b949e")
        legend.setLabelTextSize("9pt")

        # ── One curve per region ───────────────────────────────────
        self._curves: dict[str, pg.PlotDataItem] = {}
        for name in REGION_ORDER:
            pen  = _region_pen(name)
            name_display = REGION_PARAMS[name].display_name
            curve = self.pw.plot([], [], pen=pen, name=name_display)
            self._curves[name] = curve

        # ── Playback cursor ───────────────────────────────────────
        self._cursor = pg.InfiniteLine(
            pos=0.0,
            angle=90,
            pen=pg.mkPen(color="#ffffff", width=1,
                         style=Qt.PenStyle.DashLine),
            movable=False,
        )
        self.pw.addItem(self._cursor)

        layout.addWidget(self.pw)

    # ── Data management ───────────────────────────────────────────────────

    def load_history(self, snapshots: list) -> None:
        """
        Pre-load all hour snapshots.  Call this after engine.precompute().
        """
        self._hours = np.array([s.hour for s in snapshots], dtype=float)
        for name in REGION_ORDER:
            self._rates[name] = np.array(
                [s.region_states[name].firing_rate_hz for s in snapshots],
                dtype=float,
            )
        self._refresh_curves()

    def update_cursor(self, hour: int) -> None:
        """Move the playback cursor.  O(1) — does not touch curve data."""
        self._cursor.setPos(float(hour))

    def reset(self) -> None:
        """Clear all data (called before a fresh precompute)."""
        self._hours = np.array([], dtype=float)
        for name in REGION_ORDER:
            self._rates[name] = np.array([], dtype=float)
        for curve in self._curves.values():
            curve.setData([], [])
        self._cursor.setPos(0.0)

    # ── Private ───────────────────────────────────────────────────────────

    def _refresh_curves(self) -> None:
        """Push current data arrays to all PyQtGraph curves."""
        if len(self._hours) == 0:
            return
        for name in REGION_ORDER:
            if len(self._rates[name]) == len(self._hours):
                self._curves[name].setData(self._hours, self._rates[name])
