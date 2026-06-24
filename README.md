# Sleep Deprivation Neural Firing Simulation

A real-time animated computational neuroscience simulation modelling how
**72 hours of continuous sleep deprivation** alters neural firing rates
across five major brain regions, with an optional Phase 2 pharmacology
layer for **caffeine** and **nicotine**.

---

## Quick start

```bash
pip install -r requirements.txt
python run.py
```

Minimum Python: **3.10**.  Tested on Windows 11, macOS 13, Ubuntu 22.04.

---

## Features

| Feature | Detail |
|---|---|
| **Animated neural canvas** | 200 nodes (5 regions × 40), Poisson spike-driven 60 FPS |
| **Borbély two-process model** | ODE-based, S never reaches 1.0 — no flatline |
| **5 brain regions** | PFC, Hippocampus, Thalamus, Amygdala, Brainstem RAS |
| **PyQtGraph time-series** | Pre-loaded 73-hour firing-rate chart, cursor scrub |
| **Impairment arc gauge** | NORMAL → MILD → MODERATE → SEVERE → CRITICAL |
| **Microsleep injection** | Thalamus, onset at 28 h, probability rises to 72 h |
| **Caffeine model** | Bateman PK, Hill PD, adenosine rebound, amygdala anxiety |
| **Nicotine model** | Bateman PK, nAChR occupancy, tolerance, synergy |
| **CSV export** | All 73-hour firing-rate time-series |
| **Speed control** | 1×, 2×, 5×, 10× playback |

---

## Scientific model

### Process S — homeostatic sleep pressure

```
dS/dt = (1 − S) / τ_w       τ_w = 18.2 h,   S(0) = 0.20
```

Analytic solution: `S(t) = 1 − 0.80 · exp(−t / 18.2)`  
At 72 h: **S ≈ 0.982** — asymptotic approach, never reaches 1.0.

### Process C — circadian alerting signal

```
C(t) = 0.5 · [1 + cos(2π(t − 14) / 24)]
```

Peaks at 14:00 (2 pm), troughs at 02:00.

### Sleep propensity

```
W(t) = clip(0.85·S − 0.40·C,  0,  1)
```

### Per-region firing rate

```
rate(t) = f_floor + (f_base − f_floor) · (1 − 0.92 · tanh(|α| · W))
```

| Region | Baseline | α | Behaviour |
|---|---|---|---|
| Prefrontal Cortex | 35 Hz | +0.90 | Steepest decline |
| Hippocampus | 28 Hz | +0.75 | Memory encoding collapses ~24 h |
| Thalamus | 40 Hz | +0.65 | Microsleep bursts after 28 h |
| **Amygdala** | 22 Hz | **−0.50** | **Increases** — emotional dysregulation |
| Brainstem RAS | 30 Hz | +0.45 | Most resilient |

Biological floor = 8–12% of baseline; neurons never go silent.

### Microsleep

Thalamus-only, onset at 28 h.  Probability rises linearly to 4% per frame
at 72 h.  Each event suppresses thalamic firing by 95% for 4–12 frames
(67–200 ms), matching empirically observed sleep intrusions.

### Caffeine pharmacokinetics

One-compartment Bateman model: `t½ = 5.5 h`, `t_peak = 1 h`.  
PD: Hill equation reduces effective S by up to 60% at peak.  
Rebound: adenosine surge (+0.12 S) when plasma < 10% of peak.  
High dose (>400 mg cumulative): amygdala anxiety +15%.

### Nicotine pharmacokinetics

`t½ = 2.0 h`, `t_peak = 0.25 h` (inhalation).  
Per-region nAChR boost: PFC +18%, Hippo +12%, Brainstem +10%,  
Amygdala +8%, Thalamus +5%.  Tolerance: `E_eff = E_max · exp(−0.15 · n_prev)`.  
Caffeine+nicotine synergy: extra 5% amygdala anxiety.

---

## Project structure

```
sleep-deprivation-neural-sim/
├── run.py                         ← entry point
├── requirements.txt
├── src/
│   ├── models/
│   │   ├── two_process_model.py   ← Borbély ODE solver
│   │   ├── brain_regions.py       ← per-region firing rates
│   │   ├── spike_generator.py     ← Poisson + microsleep
│   │   └── pharmacology.py        ← caffeine & nicotine PK/PD
│   ├── simulation/
│   │   ├── engine.py              ← orchestrator, pre-computes 73 snapshots
│   │   └── recorder.py            ← time-series store + CSV export
│   └── gui/
│       ├── app.py                 ← QApplication + dark stylesheet
│       ├── main_window.py         ← master layout + signal routing
│       └── widgets/
│           ├── neural_canvas.py   ← 60 FPS animated centerpiece
│           ├── timeseries_plot.py ← PyQtGraph rolling chart
│           ├── region_panel.py    ← animated firing-rate bars
│           ├── impairment_gauge.py← arc gauge (QPainter)
│           ├── playback_controls.py
│           └── substance_panel.py ← Phase 2 caffeine / nicotine UI
└── tests/
    ├── test_two_process.py
    ├── test_spike_generator.py
    └── test_pharmacology.py
```

---

## Running the tests

```bash
python tests/test_two_process.py
python tests/test_spike_generator.py
python tests/test_pharmacology.py
```

Or run all at once:

```bash
python -m pytest tests/ -v    # if pytest is installed
```

---

## Controls

| Control | Action |
|---|---|
| **▶ Play / ⏸ Pause** | Start / stop playback |
| **◀ ▶▶** | Step backward / forward one hour |
| **Speed: 1× 2× 5× 10×** | Playback speed |
| **Hour slider** | Scrub to any hour |
| **↺ Reset** | Rewind to hour 0, clear pharmacology |
| **⬇ Export CSV** | Save 73-hour data to CSV |
| **☕ Caffeine / 🚬 Nicotine** | Enable Phase-2 dose inputs |
| **Apply** | Recompute simulation with doses |

---

## References

- Borbély, A.A. (1982). *A two process model of sleep regulation.*  
  Human Neurobiology, 1(3), 195–204.
- Åkerstedt, T. & Folkard, S. (1995). *Validation of the S and C components of the three-process model of alertness regulation.*  
  Sleep, 18(1), 1–6.
- Harrison & Horne (2000). *The impact of sleep deprivation on decision making.*  
  Journal of Experimental Psychology: Applied, 6(3), 236–249.
