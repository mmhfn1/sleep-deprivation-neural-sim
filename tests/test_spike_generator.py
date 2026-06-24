"""
tests/test_spike_generator.py

Validates the brain region model and spike generator:
  • No region ever has zero firing rate across all 73 hours
  • Biological floor is respected at every hour
  • Amygdala INCREASES under sleep deprivation (inverse response)
  • PFC DECREASES substantially by hour 48
  • Brainstem is the most resilient (least suppressed at 48 h)
  • Spike generator produces events at baseline rates
  • No flatline at hour 72 (worst case)
  • Microsleep probability is 0 before 28 h and >0 after
  • Impairment index stays in [0, 1]
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from src.models.two_process_model import TwoProcessModel
from src.models.brain_regions import BrainRegionModel, REGION_PARAMS, REGION_ORDER
from src.models.spike_generator import SpikeGenerator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _brain():
    return BrainRegionModel()

def _states():
    m = TwoProcessModel(); m.solve()
    return m.get_hourly_states()

def _region_states_at(hour: int):
    sts = _states()
    return _brain().compute_all_regions(sts[hour])


def _run(label: str, fn):
    try:
        fn()
        print(f"  ✓  {label}")
        return True
    except AssertionError as e:
        print(f"  ✗  {label}: {e}")
        return False


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_no_zero_rates_anywhere():
    """No region should ever flatline across 73 hours."""
    brain = _brain()
    for h, state in enumerate(_states()):
        rs = brain.compute_all_regions(state)
        for name, r in rs.items():
            assert r.firing_rate_hz > 0.1, \
                f"Zero/near-zero rate at h={h}, region={name}: {r.firing_rate_hz:.4f} Hz"


def test_biological_floor_respected_at_72h():
    """Floor = 8–12% of baseline; must hold at the worst-case hour."""
    rs = _region_states_at(72)
    for name, r in rs.items():
        p     = REGION_PARAMS[name]
        floor = p.baseline_hz * p.floor_fraction
        assert r.firing_rate_hz >= floor * 0.98, (
            f"{name} at h=72: {r.firing_rate_hz:.3f} Hz < floor {floor:.3f} Hz"
        )


def test_amygdala_increases_with_deprivation():
    """Amygdala (α<0) must have a higher firing rate at h=48 than h=0."""
    r0  = _region_states_at(0)["amygdala"]
    r48 = _region_states_at(48)["amygdala"]
    assert r48.firing_rate_hz > r0.firing_rate_hz, (
        f"Amygdala should increase: h=0 {r0.firing_rate_hz:.2f} Hz "
        f"→ h=48 {r48.firing_rate_hz:.2f} Hz"
    )


def test_amygdala_above_baseline_by_48h():
    """Amygdala should be clearly above its resting baseline at 48 h."""
    r48 = _region_states_at(48)["amygdala"]
    assert r48.firing_rate_hz > r48.baseline_hz * 1.10, (
        f"Amygdala h=48: {r48.firing_rate_hz:.2f} Hz "
        f"not >10% above baseline {r48.baseline_hz:.2f} Hz"
    )


def test_pfc_decreases_substantially():
    """PFC should be well below baseline by hour 48."""
    r0  = _region_states_at(0)["pfc"]
    r48 = _region_states_at(48)["pfc"]
    assert r48.firing_rate_hz < r0.firing_rate_hz * 0.82, (
        f"PFC should drop >18%: h=0 {r0.firing_rate_hz:.2f} → h=48 {r48.firing_rate_hz:.2f} Hz"
    )


def test_brainstem_most_resilient_at_48h():
    """Brainstem (α=0.45) should retain more of its baseline than PFC (α=0.90)."""
    brain = _brain()
    sts   = _states()
    rs48  = brain.compute_all_regions(sts[48])

    pfc_drop      = 1.0 - rs48["pfc"].firing_rate_hz      / rs48["pfc"].baseline_hz
    brainstem_drop= 1.0 - rs48["brainstem"].firing_rate_hz / rs48["brainstem"].baseline_hz
    assert brainstem_drop < pfc_drop, (
        f"Brainstem should be more resilient than PFC at h=48; "
        f"pfc_drop={pfc_drop:.3f}, brainstem_drop={brainstem_drop:.3f}"
    )


def test_no_flatline_at_72h():
    """The spike generator must produce events at h=72 firing rates."""
    rs  = _region_states_at(72)
    gen = SpikeGenerator({r: 40 for r in REGION_ORDER})
    assert gen.validate_no_flatline(rs), (
        "Flatline detected at h=72: " +
        ", ".join(f"{n}={r.firing_rate_hz:.2f}" for n, r in rs.items())
    )


def test_spike_events_produced_at_baseline():
    """Over 1 simulated second (60 frames) at h=0, events should be plentiful."""
    rs  = _region_states_at(0)
    gen = SpikeGenerator({r: 40 for r in REGION_ORDER}, rng_seed=1)
    total = sum(
        len(gen.generate_frame_spikes(rs, dt=1/60.0)) for _ in range(60)
    )
    assert total > 100, f"Only {total} spike events in 1 s at baseline — too few"


def test_microsleep_zero_before_28h():
    """Microsleep probability must be 0 before hour 28."""
    brain = _brain()
    for h in range(28):
        p = brain.compute_microsleep_probability(float(h))
        assert p == 0.0, f"Microsleep prob nonzero at h={h}: {p}"


def test_microsleep_positive_after_28h():
    brain = _brain()
    p_40 = brain.compute_microsleep_probability(40.0)
    assert p_40 > 0.0, "Microsleep probability should be >0 at h=40"


def test_impairment_index_in_range():
    """Impairment index must stay in [0, 1] across all hours."""
    brain = _brain()
    for h, state in enumerate(_states()):
        rs  = brain.compute_all_regions(state)
        idx = brain.compute_impairment_index(rs)
        assert 0.0 <= idx <= 1.0, \
            f"Impairment index out of [0,1] at h={h}: {idx:.5f}"


def test_spike_events_sparser_at_72h():
    """
    Spike count at h=72 should be lower than at h=0
    (PFC/hippo/thalamus/brainstem all suppressed).
    Amygdala going up partially offsets this but overall count is lower.
    """
    rs0  = _region_states_at(0)
    rs72 = _region_states_at(72)
    gen  = SpikeGenerator({r: 40 for r in REGION_ORDER}, rng_seed=7)

    n0 = sum(
        len(gen.generate_frame_spikes(rs0, dt=1/60.0)) for _ in range(60)
    )
    gen.reset()
    n72 = sum(
        len(gen.generate_frame_spikes(rs72, dt=1/60.0)) for _ in range(60)
    )
    assert n72 < n0, (
        f"Expected fewer events at h=72 ({n72}) than h=0 ({n0})"
    )


# ── Runner ────────────────────────────────────────────────────────────────────

TESTS = [
    ("No zero rates across 73 hours",           test_no_zero_rates_anywhere),
    ("Biological floor respected at h=72",      test_biological_floor_respected_at_72h),
    ("Amygdala increases with deprivation",     test_amygdala_increases_with_deprivation),
    ("Amygdala >10% above baseline at h=48",    test_amygdala_above_baseline_by_48h),
    ("PFC decreases >18% by h=48",              test_pfc_decreases_substantially),
    ("Brainstem more resilient than PFC",       test_brainstem_most_resilient_at_48h),
    ("No flatline at h=72",                     test_no_flatline_at_72h),
    ("Spike events produced at baseline",       test_spike_events_produced_at_baseline),
    ("Microsleep = 0 before h=28",              test_microsleep_zero_before_28h),
    ("Microsleep > 0 after h=28",               test_microsleep_positive_after_28h),
    ("Impairment index in [0,1]",               test_impairment_index_in_range),
    ("Fewer spikes at h=72 than h=0",           test_spike_events_sparser_at_72h),
]


def run_all() -> int:
    print("\n── Spike Generator & Brain Region Tests ────────────")
    passed = sum(_run(label, fn) for label, fn in TESTS)
    failed = len(TESTS) - passed
    print(f"\n  {passed}/{len(TESTS)} passed", "✓" if failed == 0 else "✗")
    return failed


if __name__ == "__main__":
    sys.exit(run_all())
