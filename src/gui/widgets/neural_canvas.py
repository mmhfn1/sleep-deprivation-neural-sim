"""
NeuralCanvas — 60 FPS animated neural network visualization.

Fixes in this version:
- MicrosleepOverlay: smooth fade-in/out (6 frames), dark indigo tint
  instead of jarring pure black, "MICROSLEEP" label, reduced opacity.
- PulsePool: unchanged, still pre-allocated.
- VignetteOverlay: unchanged.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QBrush, QColor, QPen, QPainter,
    QFont, QRadialGradient,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QGraphicsScene, QGraphicsView,
    QGraphicsEllipseItem, QGraphicsLineItem,
    QGraphicsTextItem, QGraphicsItem,
)

from ...models.brain_regions import REGION_PARAMS, REGION_ORDER
from ...models.spike_generator import SpikeGenerator
from ...simulation.engine import HourSnapshot

# ── Constants ──────────────────────────────────────────────────────────────
FPS             = 60
FRAME_DT        = 1.0 / FPS
NODE_RADIUS     = 5.0
NODE_COUNT      = 40
FLASH_FRAMES    = 9
PULSE_FRAMES    = 14
PULSE_MAX_R     = 32.0
MAX_PULSES_POOL = 120
MAX_NEW_PULSES_PER_REGION = 2
CANVAS_W        = 820
CANVAS_H        = 720

REGION_LAYOUT: dict[str, tuple[float, float, float, float]] = {
    "pfc":         (410,  90,  165,  58),
    "hippocampus": (155, 325,  105, 142),
    "thalamus":    (410, 370,   90,  80),
    "amygdala":    (665, 325,  105, 142),
    "brainstem":   (410, 600,   85,  70),
}

CONNECTIONS = [
    ("pfc","hippocampus"),("pfc","thalamus"),("pfc","amygdala"),
    ("hippocampus","thalamus"),("hippocampus","amygdala"),
    ("thalamus","amygdala"),("thalamus","brainstem"),("brainstem","thalamus"),
]

LABEL_OFFSETS: dict[str, tuple[float, float]] = {
    "pfc":         (410,  14),
    "hippocampus": (155, 168),
    "thalamus":    (410, 278),
    "amygdala":    (665, 168),
    "brainstem":   (410, 522),
}


# ── NodeItem ───────────────────────────────────────────────────────────────
class NodeItem(QGraphicsEllipseItem):
    def __init__(self, x: float, y: float, base_color: QColor):
        super().__init__(-NODE_RADIUS, -NODE_RADIUS, 2*NODE_RADIUS, 2*NODE_RADIUS)
        self.setPos(x, y); self.setZValue(2)
        self.base_color = base_color
        self.flash_frames = 0; self.flash_amp = 1.0
        self._set_resting(1.0)

    def trigger_flash(self, amplitude: float = 1.0):
        self.flash_frames = FLASH_FRAMES
        self.flash_amp = float(np.clip(amplitude, 0.2, 2.0))

    def animate(self) -> bool:
        if self.flash_frames > 0:
            glow = self.flash_frames / FLASH_FRAMES
            self._set_flash(glow)
            self.flash_frames -= 1
            return True
        return False

    def set_dim(self, dim: float):
        self._set_resting(dim)

    def _set_flash(self, glow: float):
        c = self.base_color; amp = self.flash_amp
        r = min(255, int(c.red()   + (255-c.red())   * glow * amp * 0.80))
        g = min(255, int(c.green() + (255-c.green()) * glow * amp * 0.80))
        b = min(255, int(c.blue()  + (255-c.blue())  * glow * amp * 0.80))
        col = QColor(r,g,b)
        self.setBrush(QBrush(col))
        self.setPen(QPen(QColor(min(255,r+30), min(255,g+30), min(255,b+30)), 1.2))

    def _set_resting(self, dim: float):
        c = self.base_color; d = float(np.clip(dim, 0.0, 1.0))
        s = 0.28 + 0.06*d
        col  = QColor(int(c.red()*s), int(c.green()*s), int(c.blue()*s))
        pcol = QColor(int(c.red()*(s+0.12)), int(c.green()*(s+0.12)), int(c.blue()*(s+0.12)))
        self.setBrush(QBrush(col)); self.setPen(QPen(pcol, 1.0))


# ── PulseItem & PulsePool ─────────────────────────────────────────────────
class PulseItem(QGraphicsEllipseItem):
    def __init__(self):
        super().__init__(0,0,1,1); self.setZValue(1)
        self._color = QColor(255,255,255); self._frame = 0
        self.setVisible(False)

    def reset(self, x: float, y: float, color: QColor):
        self.setPos(x,y); self._color = color; self._frame = 0
        self.setVisible(True); self._update()

    def animate(self) -> bool:
        self._frame += 1
        if self._frame >= PULSE_FRAMES:
            self.setVisible(False); return False
        self._update(); return True

    def _update(self):
        t = self._frame / PULSE_FRAMES
        r = NODE_RADIUS + (PULSE_MAX_R - NODE_RADIUS) * t
        a = int(220 * (1.0-t)**1.4)
        c = self._color
        self.setRect(-r,-r,2*r,2*r)
        self.setPen(QPen(QColor(c.red(),c.green(),c.blue(),a), 1.5))
        self.setBrush(QBrush(Qt.GlobalColor.transparent))


class PulsePool:
    def __init__(self, scene: QGraphicsScene, size: int = MAX_PULSES_POOL):
        self._free:   list[PulseItem] = []
        self._active: list[PulseItem] = []
        for _ in range(size):
            p = PulseItem(); scene.addItem(p); self._free.append(p)

    def spawn(self, x: float, y: float, color: QColor) -> bool:
        if not self._free: return False
        p = self._free.pop(); p.reset(x,y,color); self._active.append(p); return True

    def tick(self):
        alive = []
        for p in self._active:
            if p.animate(): alive.append(p)
            else: self._free.append(p)
        self._active = alive


# ── VignetteOverlay ───────────────────────────────────────────────────────
class VignetteOverlay(QGraphicsItem):
    def __init__(self, w: float, h: float):
        super().__init__(); self._w=w; self._h=h; self._intensity=0.0
        self.setZValue(10); self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def set_intensity(self, intensity: float):
        new = float(np.clip(intensity, 0.0, 1.0))
        if abs(new - self._intensity) > 0.005:
            self._intensity = new; self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(0,0,self._w,self._h)

    def paint(self, painter: QPainter, option, widget=None):
        if self._intensity < 0.01: return
        grad = QRadialGradient(self._w/2, self._h/2, self._w*0.72)
        a = int(190 * self._intensity)
        grad.setColorAt(0.00, QColor(0,0,0,0))
        grad.setColorAt(0.50, QColor(60,0,0,0))
        grad.setColorAt(0.78, QColor(130,0,0,int(a*0.5)))
        grad.setColorAt(1.00, QColor(200,0,0,a))
        painter.fillRect(self.boundingRect(), grad)


# ── MicrosleepOverlay (FIXED) ─────────────────────────────────────────────
class MicrosleepOverlay(QGraphicsItem):
    """
    Smooth fade-in/fade-out dark indigo tint over the thalamus.
    No longer a jarring pure-black pop — fades over FADE_FRAMES.
    Includes a small 'MICROSLEEP' text label.
    """
    FADE_FRAMES   = 5      # frames to fade in OR out (~83 ms)
    MAX_ALPHA     = 130    # max opacity (was 195) — less aggressive
    TINT_COLOR    = (28, 18, 60)  # dark indigo, not pure black

    def __init__(self, cx: float, cy: float, rx: float, ry: float):
        super().__init__()
        self._cx, self._cy = cx, cy
        self._rx, self._ry = rx + 8, ry + 8
        self._alpha       = 0
        self._target      = 0       # 0 or MAX_ALPHA
        self.setZValue(8)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def set_active(self, active: bool):
        self._target = self.MAX_ALPHA if active else 0
        # schedule incremental update in tick()

    def tick(self):
        """Call once per animation frame to step the fade."""
        step = self.MAX_ALPHA // self.FADE_FRAMES
        if self._alpha < self._target:
            self._alpha = min(self._alpha + step, self._target)
            self.update()
        elif self._alpha > self._target:
            self._alpha = max(self._alpha - step, self._target)
            self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(
            self._cx - self._rx - 24,
            self._cy - self._ry - 20,
            (self._rx + 24) * 2,
            (self._ry + 20) * 2,
        )

    def paint(self, painter: QPainter, option, widget=None):
        if self._alpha < 1: return
        r, g, b = self.TINT_COLOR
        painter.setBrush(QBrush(QColor(r, g, b, self._alpha)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(self._cx, self._cy), float(self._rx), float(self._ry))

        # "MICROSLEEP" label — only visible when fairly opaque
        if self._alpha > 60:
            label_alpha = min(255, int((self._alpha - 60) / (self.MAX_ALPHA - 60) * 200))
            painter.setPen(QPen(QColor(160, 120, 255, label_alpha)))
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(
                QRectF(self._cx - 45, self._cy - 10, 90, 20),
                Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                "💤 MICROSLEEP"
            )


# ── NeuralCanvas ──────────────────────────────────────────────────────────
class NeuralCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_snap: Optional[HourSnapshot] = None
        self.spike_gen = SpikeGenerator({r: NODE_COUNT for r in REGION_ORDER}, rng_seed=42)

        self.scene = QGraphicsScene(0, 0, CANVAS_W, CANVAS_H)
        self.scene.setBackgroundBrush(QBrush(QColor(8, 10, 16)))

        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,2)
        layout.setSpacing(2)
        layout.addWidget(self.view, stretch=1)

        cap = QLabel("Neural Activity Canvas  ·  40 neurons/region  ·  60 FPS")
        cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cap.setStyleSheet("color: #484f58; font-size: 9px;")
        layout.addWidget(cap)

        self._nodes:          dict[str, list[NodeItem]]             = {}
        self._node_positions: dict[str, list[tuple[float,float]]]   = {}
        self._rng_layout = np.random.default_rng(0)

        self._build_graph()

        self._vignette = VignetteOverlay(CANVAS_W, CANVAS_H)
        self.scene.addItem(self._vignette)

        tl = REGION_LAYOUT["thalamus"]
        self._micro_overlay = MicrosleepOverlay(tl[0], tl[1], tl[2], tl[3])
        self.scene.addItem(self._micro_overlay)

        self._pulse_pool = PulsePool(self.scene, MAX_PULSES_POOL)
        self._build_labels()

        self._timer = QTimer(self)
        self._timer.setInterval(int(1000/FPS))
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # ── External API ──────────────────────────────────────────────────────
    def update_state(self, snap: HourSnapshot):
        self._current_snap = snap

    def reset(self):
        self._current_snap = None
        self.spike_gen.reset()
        for nodes in self._nodes.values():
            for n in nodes:
                n.flash_frames = 0; n._set_resting(1.0)
        self._vignette.set_intensity(0.0)
        self._micro_overlay.set_active(False)

    # ── Graph construction ─────────────────────────────────────────────────
    def _place_nodes_in_ellipse(self, cx,cy,rx,ry,n):
        positions = []
        attempts  = 0
        while len(positions) < n and attempts < n*200:
            attempts += 1
            x = self._rng_layout.uniform(cx-rx, cx+rx)
            y = self._rng_layout.uniform(cy-ry, cy+ry)
            if ((x-cx)/rx)**2 + ((y-cy)/ry)**2 <= 0.92:
                positions.append((float(x), float(y)))
        return positions

    def _region_qcolor(self, name: str) -> QColor:
        r,g,b = REGION_PARAMS[name].color_rgb; return QColor(r,g,b)

    def _build_graph(self):
        for name in REGION_ORDER:
            cx,cy,rx,ry = REGION_LAYOUT[name]
            color        = self._region_qcolor(name)
            positions    = self._place_nodes_in_ellipse(cx,cy,rx,ry,NODE_COUNT)
            self._node_positions[name] = positions
            nodes = []
            for x,y in positions:
                node = NodeItem(x,y,color); self.scene.addItem(node); nodes.append(node)
            self._nodes[name] = nodes
        self._build_edges()

    def _build_edges(self):
        ec = QColor(50,62,82,70)
        for src,dst in CONNECTIONS:
            sp = self._node_positions[src]; dp = self._node_positions[dst]
            for _ in range(int(self._rng_layout.integers(3,7))):
                sx,sy = sp[self._rng_layout.integers(len(sp))]
                dx,dy = dp[self._rng_layout.integers(len(dp))]
                line  = QGraphicsLineItem(sx,sy,dx,dy)
                line.setPen(QPen(ec, 0.8)); line.setZValue(0)
                self.scene.addItem(line)

    def _build_labels(self):
        display = {
            "pfc":"Prefrontal Cortex","hippocampus":"Hippocampus",
            "thalamus":"Thalamus","amygdala":"Amygdala","brainstem":"Brainstem RAS",
        }
        font = QFont("Arial", 9, QFont.Weight.Bold)
        for name,(lx,ly) in LABEL_OFFSETS.items():
            color = self._region_qcolor(name).lighter(130)
            item  = QGraphicsTextItem(display[name])
            item.setDefaultTextColor(color); item.setFont(font); item.setZValue(5)
            bw = item.boundingRect().width()
            item.setPos(lx - bw/2, ly); self.scene.addItem(item)

    # ── 60 FPS tick ───────────────────────────────────────────────────────
    def _tick(self):
        snap = self._current_snap
        if snap is None: return

        region_states = snap.region_states
        W             = snap.W
        micro_prob    = snap.microsleep_prob

        events = self.spike_gen.generate_frame_spikes(
            region_states, dt=FRAME_DT, W=W, microsleep_prob=micro_prob
        )

        pulses_spawned: dict[str,int] = {r:0 for r in REGION_ORDER}
        for ev in events:
            rname    = ev.region_name
            n_nodes  = len(self._nodes[rname])
            node_idx = ev.node_index % n_nodes
            self._nodes[rname][node_idx].trigger_flash(ev.amplitude)
            if pulses_spawned[rname] < MAX_NEW_PULSES_PER_REGION:
                px,py = self._node_positions[rname][node_idx]
                self._pulse_pool.spawn(px, py, self._region_qcolor(rname))
                pulses_spawned[rname] += 1

        self._pulse_pool.tick()

        for rname, nodes in self._nodes.items():
            rs = region_states.get(rname)
            p  = REGION_PARAMS[rname]
            if p.alpha >= 0.0 and rs is not None:
                floor = p.baseline_hz * p.floor_fraction
                denom = max(p.baseline_hz - floor, 1e-9)
                dim   = float(np.clip((rs.firing_rate_hz - floor) / denom, 0.08, 1.0))
            else:
                dim = 1.0
            for node in nodes:
                if not node.animate(): node.set_dim(dim)

        # Microsleep overlay — smooth fade via tick()
        in_micro = self.spike_gen.is_in_microsleep("thalamus")
        self._micro_overlay.set_active(in_micro)
        self._micro_overlay.tick()

        self._vignette.set_intensity(snap.W * 0.92)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
