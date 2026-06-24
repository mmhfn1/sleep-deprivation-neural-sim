"""
QApplication bootstrap and global dark stylesheet.

Import and call create_app() before constructing any Qt widgets.
"""

from __future__ import annotations

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


def create_app(argv: list | None = None) -> QApplication:
    """Create and configure the QApplication with the dark theme."""
    if argv is None:
        argv = sys.argv

    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(argv)
    app.setApplicationName("Sleep Deprivation Neural Firing Simulation")
    app.setApplicationVersion("1.0.0")

    # Global font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    app.setStyleSheet(_stylesheet())
    return app


def _stylesheet() -> str:
    return """
    /* ── Base ─────────────────────────────────────────────────── */
    QMainWindow, QWidget {
        background-color: #0d1117;
        color: #e6edf3;
    }

    /* ── Group boxes ──────────────────────────────────────────── */
    QGroupBox {
        border: 1px solid #30363d;
        border-radius: 6px;
        margin-top: 10px;
        padding-top: 10px;
        color: #8b949e;
        font-size: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }

    /* ── Buttons ──────────────────────────────────────────────── */
    QPushButton {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 5px;
        padding: 5px 14px;
        color: #e6edf3;
        font-size: 11px;
    }
    QPushButton:hover {
        background-color: #30363d;
        border-color: #58a6ff;
    }
    QPushButton:pressed {
        background-color: #161b22;
    }
    QPushButton:checked {
        background-color: #1f6feb;
        border-color: #388bfd;
        color: #ffffff;
    }
    QPushButton:disabled {
        color: #484f58;
        border-color: #21262d;
    }

    /* ── Sliders ──────────────────────────────────────────────── */
    QSlider::groove:horizontal {
        height: 4px;
        background: #30363d;
        border-radius: 2px;
    }
    QSlider::handle:horizontal {
        width: 14px;
        height: 14px;
        margin: -5px 0;
        background: #1f6feb;
        border-radius: 7px;
        border: none;
    }
    QSlider::handle:horizontal:hover {
        background: #388bfd;
    }
    QSlider::sub-page:horizontal {
        background: #1f6feb;
        border-radius: 2px;
    }

    /* ── Spin boxes ───────────────────────────────────────────── */
    QSpinBox {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 4px;
        padding: 3px 6px;
        color: #e6edf3;
        font-size: 11px;
    }
    QSpinBox:focus {
        border-color: #1f6feb;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        background: #30363d;
        border: none;
        width: 16px;
    }
    QSpinBox::up-button:hover, QSpinBox::down-button:hover {
        background: #484f58;
    }

    /* ── Check boxes ──────────────────────────────────────────── */
    QCheckBox {
        color: #e6edf3;
        spacing: 6px;
    }
    QCheckBox::indicator {
        width: 14px;
        height: 14px;
        border: 1px solid #30363d;
        border-radius: 3px;
        background: #21262d;
    }
    QCheckBox::indicator:checked {
        background: #1f6feb;
        border-color: #388bfd;
    }

    /* ── Labels ───────────────────────────────────────────────── */
    QLabel {
        color: #e6edf3;
        background: transparent;
    }

    /* ── Progress bars ────────────────────────────────────────── */
    QProgressBar {
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 3px;
        text-align: center;
    }
    QProgressBar::chunk {
        border-radius: 3px;
    }

    /* ── Scroll bars ──────────────────────────────────────────── */
    QScrollBar:vertical {
        background: #0d1117;
        width: 7px;
        margin: 0;
    }
    QScrollBar::handle:vertical {
        background: #30363d;
        border-radius: 3px;
        min-height: 20px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0;
    }

    /* ── Frame / panel borders ────────────────────────────────── */
    QFrame[frameShape="4"],   /* HLine */
    QFrame[frameShape="5"] {  /* VLine */
        color: #30363d;
    }

    /* ── Splitter handle ──────────────────────────────────────── */
    QSplitter::handle {
        background: #30363d;
    }

    /* ── Graphics view (neural canvas host) ───────────────────── */
    QGraphicsView {
        border: none;
        background: transparent;
    }
    """
