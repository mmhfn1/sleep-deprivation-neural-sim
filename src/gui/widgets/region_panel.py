"""
RegionPanel — per-region firing rate bars with trend arrows.

One RegionBar per brain region; each shows:
  • Colour-coded horizontal progress bar (0–60 Hz scale)
  • Current rate in Hz (monospace, right-aligned)
  • Trend arrow (↑ red / ↓ blue / → green)
"""

from __future__ import annotations

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QProgressBar,
)
from PyQt6.QtCore import Qt

from ...models.brain_regions import REGION_PARAMS, REGION_ORDER
from ...simulation.engine import HourSnapshot


class RegionBar(QWidget):
    """Single row: region name | progress bar | Hz value | trend arrow."""

    _MAX_HZ = 60.0   # progress bar upper bound

    def __init__(self, region_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._name = region_name
        p             = REGION_PARAMS[region_name]
        r, g, b       = p.color_rgb
        self._color   = f"#{r:02x}{g:02x}{b:02x}"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 6, 2)
        layout.setSpacing(8)

        # Region name
        self._lbl_name = QLabel(p.display_name)
        self._lbl_name.setFixedWidth(136)
        self._lbl_name.setStyleSheet("color: #c9d1d9; font-size: 11px;")

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 1000)   # use 1000 steps for smooth animation
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(13)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {self._color};
                border-radius: 3px;
            }}
        """)

        # Hz label
        self._lbl_hz = QLabel("  0.0 Hz")
        self._lbl_hz.setFixedWidth(64)
        self._lbl_hz.setAlignment(Qt.AlignmentFlag.AlignRight
                                   | Qt.AlignmentFlag.AlignVCenter)
        self._lbl_hz.setStyleSheet(
            "color: #e6edf3; font-size: 11px; font-family: 'Courier New', monospace;"
        )

        # Trend arrow
        self._lbl_trend = QLabel("→")
        self._lbl_trend.setFixedWidth(18)
        self._lbl_trend.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._lbl_trend.setStyleSheet("font-size: 14px; color: #3fb950;")

        layout.addWidget(self._lbl_name)
        layout.addWidget(self._bar, stretch=1)
        layout.addWidget(self._lbl_hz)
        layout.addWidget(self._lbl_trend)

    def update_value(self, hz: float, trend: str) -> None:
        pct = int(min(1000, (hz / self._MAX_HZ) * 1000))
        self._bar.setValue(pct)
        self._lbl_hz.setText(f"{hz:5.1f} Hz")
        self._lbl_trend.setText(trend)
        color = {"↑": "#f85149", "↓": "#58a6ff", "→": "#3fb950"}.get(trend, "#8b949e")
        self._lbl_trend.setStyleSheet(f"font-size: 14px; color: {color};")


class RegionPanel(QFrame):
    """Vertical stack of RegionBar widgets inside a styled frame."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(5)

        hdr = QLabel("  CURRENT FIRING RATES")
        hdr.setStyleSheet(
            "color: #8b949e; font-size: 9px; font-weight: bold; letter-spacing: 1px;"
        )
        layout.addWidget(hdr)

        self._bars: dict[str, RegionBar] = {}
        for name in REGION_ORDER:
            bar = RegionBar(name)
            self._bars[name] = bar
            layout.addWidget(bar)

        layout.addStretch()

    def update_state(self, snap: HourSnapshot) -> None:
        for name, rs in snap.region_states.items():
            if name in self._bars:
                self._bars[name].update_value(rs.firing_rate_hz, rs.trend)
