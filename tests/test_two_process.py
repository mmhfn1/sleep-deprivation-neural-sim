"""
tests/test_two_process.py

Validates the Borbély two-process model:
  • S never reaches 1.0 (no flatline possible)
  • C stays in [0, 1] throughout
  • W stays in [0, 1] throughout
  • S is monotonically non-decreasing during continuous wake
  • Correct number of hourly states produced
  • Impairment increases from hour 8 → hour 48
  • Impairment label transitions occur in expected order
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.models.two_process_model import TwoProcessModel, TwoProcessParams, impairment_label


def _run(label: str, fn):
    try:
        fn()
        print(f"  ✓  {label}")
        return True
    except AssertionError as e:
        print(f"  ✗  {label}: {e}")
        return False


def test_S_never_one():
    m = TwoProcessModel(); m.solve()
    v = m.validate()
    assert v["S_never_reaches_1"], \
        f"S reached 1.0! max = {v['S_max_value']:.8f}"


def test_S_max_reasonable():
    m = TwoProcessModel(); m.solve()
    v = m.validate()
    max_S = v["S_max_value"]
    assert 0.95 < max_S < 1.0, \
        f"S max {max_S:.5f} outside expected range (0.95, 1.0)"


def test_C_in_range():
    m = TwoProcessModel(); m.solve()
    v = m.validate()
    assert v["C_in_range"], f"C out of [0,1]: {v['C_range']}"


def test_W_in_range():
    m = TwoProcessModel(); m.solve()
    v = m.validate()
    assert v["W_in_range"], f"W out of [0,1]: {v['W_range']}"


def test_S_monotonic():
    m = TwoProcessModel(); m.solve()
    v = m.validate()
    assert v["S_monotonic"], "S is not monotonically non-decreasing during wake"


def test_hourly_state_count():
    m = TwoProcessModel()
    states = m.get_hourly_states()
    assert len(states) == 73, f"Expected 73 states (h=0..72), got {len(states)}"


def test_impairment_increases():
    m = TwoProcessModel()
    states = m.get_hourly_states()
    W_8  = states[8].W
    W_48 = states[48].W
    assert W_48 > W_8, \
        f"W should increase from h=8 ({W_8:.4f}) to h=48 ({W_48:.4f})"


def test_impairment_labels_progress():
    """Labels should transition NORMAL → higher states as hours grow."""
    m = TwoProcessModel()
    states = m.get_hourly_states()
    labels = [s.impairment_level for s in states]

    # Hour 0 must be NORMAL
    assert labels[0] == "NORMAL", f"Hour 0 label: {labels[0]}"

    # Hour 72 must be at least SEVERE
    order = ["NORMAL", "MILD", "MODERATE", "SEVERE", "CRITICAL"]
    idx_72 = order.index(labels[72]) if labels[72] in order else -1
    assert idx_72 >= 3, f"Hour 72 label: {labels[72]} (expected SEVERE or CRITICAL)"


def test_circadian_has_two_peaks():
    """C should have at least 2 peaks in 72 h (period = 24 h)."""
    m = TwoProcessModel(); m.solve()
    C_vals = [s.C for s in m._states]
    peaks = sum(
        1 for i in range(1, len(C_vals) - 1)
        if C_vals[i] > C_vals[i-1] and C_vals[i] > C_vals[i+1]
    )
    assert peaks >= 2, f"Expected ≥2 circadian peaks, found {peaks}"


def test_custom_params():
    """Model must work with non-default parameters."""
    p = TwoProcessParams(tau_w=20.0, S0=0.30)
    m = TwoProcessModel(params=p)
    m.solve()
    v = m.validate()
    assert v["S_never_reaches_1"]
    assert v["S_monotonic"]


# ── Runner ────────────────────────────────────────────────────────────────────

TESTS = [
    ("S never reaches 1.0",           test_S_never_one),
    ("S max value in (0.95, 1.0)",     test_S_max_reasonable),
    ("C stays in [0, 1]",              test_C_in_range),
    ("W stays in [0, 1]",              test_W_in_range),
    ("S is monotonically increasing",  test_S_monotonic),
    ("73 hourly states produced",      test_hourly_state_count),
    ("W increases from h=8 to h=48",   test_impairment_increases),
    ("Impairment labels progress",     test_impairment_labels_progress),
    ("Circadian has ≥2 peaks in 72 h", test_circadian_has_two_peaks),
    ("Custom TwoProcessParams works",  test_custom_params),
]


def run_all() -> int:
    print("\n── Two-Process Model Tests ──────────────────────────")
    passed = sum(_run(label, fn) for label, fn in TESTS)
    failed = len(TESTS) - passed
    print(f"\n  {passed}/{len(TESTS)} passed", "✓" if failed == 0 else "✗")
    return failed


if __name__ == "__main__":
    sys.exit(run_all())
