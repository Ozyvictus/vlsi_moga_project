# Multi-Objective Genetic Algorithm for VLSI Area–Delay Optimization

## Stage 1: Technology-parameterized CMOS RC model

This version uses NSGA-II to minimize two objectives for a four-stage CMOS
inverter/buffer chain:

1. **Transistor channel area proxy (µm²)** — the sum of `(Wn + Wp) × L` across
   the inverter stages. It excludes contacts, diffusion spacing, routing,
   standard-cell whitespace and other layout overhead.
2. **Estimated path delay (ns)** — the sum of worst-transition stage delays
   using a first-order RC model.

The first inverter is fixed at a normalized size of 1. NSGA-II optimizes the
remaining three sizing factors (`x2`, `x3`, `x4`). The final inverter drives an
external load equal to 64 times the input capacitance of a minimum-size
inverter.

## Circuit and device model

For every stage, normalized size `x` scales the transistor widths:

- `Wn = Wn_min × x`
- `Wp = Wn × (Wp/Wn ratio)`

The area proxy is:

`A = Σ [(Wn_i + Wp_i) × L]`

The input capacitance estimate includes gate-oxide and overlap components:

`C_in = Cox × (Wn + Wp) × L + Cov × (Wn + Wp)`

The output diffusion capacitance is approximated from drain width and
junction area. Each stage drives the next stage's input capacitance (or the
external load for the final stage), its own output diffusion capacitance, and
an interconnect capacitance.

For each stage:

`t_fall = 0.69 × R_n × C_total`

`t_rise = 0.69 × R_p × C_total`

The path delay sums the slower of the rise/fall estimates at each stage.
The effective on-resistances scale inversely with device width and include
first-order supply-voltage and temperature corrections.

## Technology assumptions and limitations

`vlsi_model.py` contains a `TechnologyParameters` dataclass. The default
values are an **illustrative educational 180 nm-like parameter set**, not a
foundry PDK and not measured silicon data. In particular, the effective
on-resistances, capacitance densities, overlap capacitance and diffusion
capacitance must be replaced or calibrated using a real PDK, a documented
technology reference, or LTspice device-model simulations before making
technology-specific claims.

The RC estimator is a first-order approximation. It does not model short-
channel effects, nonlinear transistor I–V curves, input slew dependence,
Miller effects, coupling capacitance, internal waveform shape, process corners,
statistical mismatch, or detailed layout parasitics. The area objective is
transistor channel area, not placed standard-cell area or die area.

The ideal equal-stage-effort sizing is retained only as a **reference design**.
It is not claimed to be the exact optimum of the upgraded RC model because
the RC model includes diffusion and interconnect capacitances.

## Install

Python 3.10 or later is recommended. From this folder:

```bash
python -m venv .venv
```

Activate the environment:

- Windows PowerShell: `\.venv\Scripts\Activate.ps1`
- Windows PowerShell alternative if script activation is restricted:
  `\.venv\Scripts\python.exe -m pip install -r requirements.txt` and then
  `\.venv\Scripts\python.exe optimize.py`
- macOS/Linux: `source .venv/bin/activate`

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run and test

```bash
python test_project.py
python optimize.py
```

The NSGA-II implementation is included in `nsga2.py`; it does not require
`pymoo`. The script creates an `outputs/` folder containing:

- `pareto_front.csv` — non-dominated candidate designs.
- `design_summary.csv` — minimum-area, minimum-delay, balanced, and reference designs.
- `convergence.csv` — best objective values per generation.
- `balanced_design_stage_metrics.csv` — per-stage widths, capacitances, resistances and delays for the balanced design.
- `model_parameters.csv` — all technology and circuit parameters used.
- `pareto_front.png`, `convergence.png`, `design_comparison.png` — plots.

## Next stage

Stage 2 should validate selected sizing points using LTspice with a consistent
MOSFET model, supply voltage, temperature, input waveform, and output load.
The analytical model and SPICE setup must use matching assumptions before
comparing their delays.

## Stage 2: LTspice validation

The Stage-2 files are provided to validate representative optimized designs
with transistor-level transient simulation:

1. Run `python export_ltspice.py` to produce LTspice decks from the latest
   `outputs/design_summary.csv`.
2. Open the three `.cir` files in `ltspice_netlists/` using LTspice and run
   each simulation.
3. Read `tplh`, `tphl`, and `tpd_avg` in the LTspice SPICE Error Log.
4. Enter the simulator measurements into
   `ltspice_netlists/ltspice_measurements_template.csv`.

See `STAGE2_LTSPICE_GUIDE.md` for the circuit setup, measurement definitions,
model assumptions and troubleshooting instructions. The generic LEVEL=1 MOS
models are illustrative and are not a foundry PDK.
