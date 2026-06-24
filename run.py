#!/usr/bin/env python3
"""
Sleep Deprivation Neural Firing Simulation
==========================================

Entry point:
    python run.py

Requires:
    PyQt6 >= 6.6   pyqtgraph >= 0.13   numpy >= 1.26   scipy >= 1.12
"""

from __future__ import annotations

import sys
import os

# Guarantee the repo root is on sys.path regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gui.app import create_app
from src.gui.main_window import MainWindow


def main() -> None:
    app    = create_app(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
