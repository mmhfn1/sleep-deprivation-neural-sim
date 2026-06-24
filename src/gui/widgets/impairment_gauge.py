"""
ImpairmentGauge — arc gauge showing SLEEP PRESSURE (W value).

Uses W directly (0→1) so the gauge position and impairment label
are always consistent: CRITICAL W → needle near 100%.

Colour interpolation: green (NORMAL) → amber → orange → red (CRITICAL).
"""
from __future__ import annotations
import math
from typing import Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont


_STOPS = [
    (0.00, QColor("#3fb950")),
    (0.25, QColor("#8bc34a")),
    (0.45, QColor("#d29922")),
    (0.60, QColor("#f0883e")),
    (0.75, QColor("#f85149")),
    (1.00, QColor("#ff2222")),
]


def _lerp(c1: QColor, c2: QColor, t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    return QColor(
        int(c1.red()   + (c2.red()   - c1.red())   * t),
        int(c1.green() + (c2.green() - c1.green()) * t),
        int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
    )


def _value_color(v: float) -> QColor:
    for i in range(len(_STOPS)-1):
        lo_t, lo_c = _STOPS[i]; hi_t, hi_c = _STOPS[i+1]
        if v <= hi_t:
            span = hi_t - lo_t
            return _lerp(lo_c, hi_c, (v-lo_t)/span if span > 1e-9 else 0.0)
    return _STOPS[-1][1]


class ImpairmentGauge(QWidget):
    """
    Arc gauge displaying sleep propensity W ∈ [0,1].
    Label and colour are derived from W, so they always agree with the header status.
    """
    _START = 210
    _SPAN  = 240

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._value = 0.0
        self._label = "NORMAL"
        self.setMinimumSize(140, 180)
        self.setStyleSheet("background:#161b22; border:1px solid #30363d; border-radius:6px;")

    def update_value(self, value: float, label: str) -> None:
        self._value = max(0.0, min(1.0, value))
        self._label = label
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H   = self.width(), self.height()
        margin = 18
        diam   = min(W - margin*2, H - margin*2 - 30)
        cx     = W / 2; cy = margin + diam/2 + 4; r = diam/2

        arc_rect = QRectF(cx-r, cy-r, 2*r, 2*r)

        # Track
        painter.setPen(QPen(QColor("#21262d"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(arc_rect, int(self._START*16), int(-self._SPAN*16))

        # Value arc
        if self._value > 0.002:
            painter.setPen(QPen(_value_color(self._value), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(arc_rect, int(self._START*16), int(-self._SPAN*self._value*16))

        # Needle
        ang = math.radians(self._START - self._SPAN * self._value)
        nl  = r * 0.66
        painter.setPen(QPen(QColor("#c9d1d9"), 2))
        painter.drawLine(QPointF(cx, cy), QPointF(cx + nl*math.cos(ang), cy - nl*math.sin(ang)))
        painter.setBrush(QBrush(QColor("#c9d1d9"))); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 5.0, 5.0)

        # Header title
        painter.setPen(QPen(QColor("#484f58")))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(QRectF(0, 6, W, 16), Qt.AlignmentFlag.AlignHCenter, "SLEEP PRESSURE")

        # Label
        color = _value_color(self._value)
        painter.setPen(QPen(color))
        painter.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        painter.drawText(QRectF(0, cy+r*0.18, W, 26), Qt.AlignmentFlag.AlignHCenter, self._label)

        # Percentage (W × 100)
        painter.setPen(QPen(QColor("#8b949e")))
        painter.setFont(QFont("Arial", 10))
        painter.drawText(QRectF(0, cy+r*0.18+24, W, 22),
                         Qt.AlignmentFlag.AlignHCenter, f"W = {self._value:.3f}")
        painter.end()
