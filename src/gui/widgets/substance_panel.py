"""
SubstancePanel — Phase 2 pharmacology with interval dosing.

Dose amount spinboxes are now QDoubleSpinBox (1 decimal place):
  Caffeine:  0.5 – 1000.0 mg, step 0.5
  Nicotine:  0.1 – 20.0 mg,   step 0.1

Every / From / To remain integer hour selectors.

doses_changed emits the full flat list of individual dose dicts.
"""
from __future__ import annotations
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QFrame, QHBoxLayout, QVBoxLayout,
    QLabel, QCheckBox, QSpinBox, QDoubleSpinBox, QPushButton,
)
from PyQt6.QtCore import pyqtSignal


class SubstancePanel(QWidget):
    doses_changed = pyqtSignal(list)   # [{substance, dose_mg, hour}, ...]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    # ── Build ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 2, 6, 2)
        root.setSpacing(3)

        # Header row
        hdr = QHBoxLayout()
        phase = QLabel("PHASE 2 — Pharmacology")
        phase.setStyleSheet(
            "color:#8b949e; font-size:9px; font-weight:bold; letter-spacing:1px;"
        )
        hdr.addWidget(phase)
        hdr.addStretch()

        self._btn_apply = QPushButton("Apply Doses")
        self._btn_apply.setFixedHeight(24)
        self._btn_apply.setFixedWidth(100)
        self._btn_apply.setEnabled(False)
        self._btn_apply.setToolTip("Recompute simulation with the current dose schedule")
        hdr.addWidget(self._btn_apply)
        root.addLayout(hdr)

        # Controls row
        row = QHBoxLayout(); row.setSpacing(10)

        # ── Caffeine ─────────────────────────────────────────────────────
        self._caff_en = QCheckBox("Caffeine")
        self._caff_en.setStyleSheet("color:#e6edf3; font-size:11px; font-weight:bold;")
        row.addWidget(self._caff_en)

        row.addWidget(self._lbl("Amount:"))
        self._caff_dose = self._dspin(
            lo=0.5, hi=1000.0, default=200.0, step=0.5,
            suffix=" mg", width=90,
            tip="Dose per administration (mg)",
        )
        row.addWidget(self._caff_dose)

        row.addWidget(self._lbl("Every:"))
        self._caff_interval = self._ispin(
            lo=1, hi=24, default=4, suffix=" h", width=58,
            tip="Repeat dose every N hours",
        )
        row.addWidget(self._caff_interval)

        row.addWidget(self._lbl("From:"))
        self._caff_from = self._ispin(lo=0, hi=71, default=8,  suffix=" h", width=54)
        row.addWidget(self._caff_from)

        row.addWidget(self._lbl("To:"))
        self._caff_to   = self._ispin(lo=1, hi=72, default=48, suffix=" h", width=54)
        row.addWidget(self._caff_to)

        row.addWidget(self._vline())

        # ── Nicotine ─────────────────────────────────────────────────────
        self._nic_en = QCheckBox("Nicotine")
        self._nic_en.setStyleSheet("color:#e6edf3; font-size:11px; font-weight:bold;")
        row.addWidget(self._nic_en)

        row.addWidget(self._lbl("Amount:"))
        self._nic_dose = self._dspin(
            lo=0.1, hi=20.0, default=2.0, step=0.1,
            suffix=" mg", width=80,
            tip="Dose per administration (mg)",
        )
        row.addWidget(self._nic_dose)

        row.addWidget(self._lbl("Every:"))
        self._nic_interval = self._ispin(
            lo=1, hi=24, default=6, suffix=" h", width=58,
            tip="Repeat dose every N hours",
        )
        row.addWidget(self._nic_interval)

        row.addWidget(self._lbl("From:"))
        self._nic_from = self._ispin(lo=0, hi=71, default=20, suffix=" h", width=54)
        row.addWidget(self._nic_from)

        row.addWidget(self._lbl("To:"))
        self._nic_to   = self._ispin(lo=1, hi=72, default=56, suffix=" h", width=54)
        row.addWidget(self._nic_to)

        row.addStretch()
        root.addLayout(row)

        # ── Wire ─────────────────────────────────────────────────────────
        self._caff_en.toggled.connect(self._sync)
        self._nic_en.toggled.connect(self._sync)
        self._btn_apply.clicked.connect(self._on_apply)
        self._sync()

    # ── Widget factories ──────────────────────────────────────────────────
    @staticmethod
    def _lbl(text: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet("color:#8b949e; font-size:10px;")
        return l

    @staticmethod
    def _dspin(lo: float, hi: float, default: float, step: float,
               suffix: str, width: int, tip: str = "") -> QDoubleSpinBox:
        """Decimal spinbox — dose amounts (mg, one decimal place)."""
        sb = QDoubleSpinBox()
        sb.setRange(lo, hi)
        sb.setValue(default)
        sb.setSingleStep(step)
        sb.setDecimals(1)
        sb.setSuffix(suffix)
        sb.setFixedWidth(width)
        sb.setEnabled(False)
        if tip:
            sb.setToolTip(tip)
        return sb

    @staticmethod
    def _ispin(lo: int, hi: int, default: int, suffix: str,
               width: int, tip: str = "") -> QSpinBox:
        """Integer spinbox — hours."""
        sb = QSpinBox()
        sb.setRange(lo, hi)
        sb.setValue(default)
        sb.setSuffix(suffix)
        sb.setFixedWidth(width)
        sb.setEnabled(False)
        if tip:
            sb.setToolTip(tip)
        return sb

    @staticmethod
    def _vline() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setStyleSheet("color:#30363d;")
        f.setFixedWidth(1)
        return f

    # ── Slots ─────────────────────────────────────────────────────────────
    def _sync(self):
        c = self._caff_en.isChecked()
        n = self._nic_en.isChecked()
        for w in (self._caff_dose, self._caff_interval,
                  self._caff_from, self._caff_to):
            w.setEnabled(c)
        for w in (self._nic_dose, self._nic_interval,
                  self._nic_from, self._nic_to):
            w.setEnabled(n)
        self._btn_apply.setEnabled(c or n)

    def _on_apply(self):
        doses = []
        if self._caff_en.isChecked():
            doses.extend(self._build_schedule(
                "caffeine",
                self._caff_dose.value(),          # float, 1 d.p.
                self._caff_interval.value(),
                self._caff_from.value(),
                self._caff_to.value(),
            ))
        if self._nic_en.isChecked():
            doses.extend(self._build_schedule(
                "nicotine",
                self._nic_dose.value(),            # float, 1 d.p.
                self._nic_interval.value(),
                self._nic_from.value(),
                self._nic_to.value(),
            ))
        if doses:
            self.doses_changed.emit(doses)

    @staticmethod
    def _build_schedule(substance: str, dose_mg: float,
                        interval_h: int, from_h: int, to_h: int) -> list[dict]:
        """Generate one dose dict for every interval from from_h to to_h inclusive."""
        doses = []
        h = from_h
        while h <= to_h:
            doses.append({
                "substance": substance,
                "dose_mg":   dose_mg,    # already float
                "hour":      float(h),
            })
            h += interval_h
        return doses

    # ── External API ──────────────────────────────────────────────────────
    def reset(self):
        """Restore defaults and disable all controls."""
        self._caff_en.setChecked(False)
        self._nic_en.setChecked(False)
        self._caff_dose.setValue(200.0)
        self._caff_interval.setValue(4)
        self._caff_from.setValue(8)
        self._caff_to.setValue(48)
        self._nic_dose.setValue(2.0)
        self._nic_interval.setValue(6)
        self._nic_from.setValue(20)
        self._nic_to.setValue(56)
        self._sync()
