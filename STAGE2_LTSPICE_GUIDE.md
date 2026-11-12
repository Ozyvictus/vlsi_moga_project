# Stage 2 — LTspice transistor-level validation

## Purpose

Stage 1 optimized a four-stage CMOS inverter chain using an analytical RC model.
Stage 2 exports the three representative sizing solutions to LTspice so that
transient propagation delay can be measured from transistor-level waveforms.

The three cases are:

- `minimum_area.cir`
- `balanced_compromise.cir`
- `minimum_delay.cir`

## Before running LTspice

1. Run `python optimize.py` to refresh `outputs/design_summary.csv`.
2. Run `python export_ltspice.py` to regenerate the LTspice netlists.
3. Open the `ltspice_netlists` folder.
4. Open each `.cir` file in LTspice and click **Run**.

No new Python packages are needed for netlist generation. The external LTspice
application is required to run the transistor-level simulations.

## Circuit setup

Each netlist contains:

- Four cascaded CMOS inverters.
- Stage 1 fixed at the minimum normalized size.
- Stages 2–4 set to one of the NSGA-II representative sizing solutions.
- Supply voltage: the same value as the Stage-1 model (default 1.8 V).
- Input pulse: 0 to VDD, 20 ps rise/fall, 10 ns period.
- Output load: 64 times the Stage-1 minimum-inverter input capacitance.
- Explicit output-node capacitances for the Stage-1 diffusion and wire estimates.
- Transient simulation: 25 ns maximum duration, 2 ps maximum timestep.

The transistor widths are calculated from the same normalized sizing factors
used in Python:

- `Wn = Wn_min * size_factor`
- `Wp = Wn * PMOS_to_NMOS_width_ratio`

## What model is used?

The generated netlists use generic long-channel SPICE LEVEL=1 NMOS and PMOS
models. `KP` is estimated using the LEVEL=1 triode equation around the output
mid-supply point so the initial on-resistance is approximately consistent
with the Stage-1 effective-resistance assumptions.

This is an educational consistency bridge, **not a foundry PDK**. It does not
represent a verified 180 nm process. A real PDK model or documented device
model should replace it for technology-specific or sign-off claims.

## Automatic measurements

Each deck includes:

```spice
.meas TRAN tplh TRIG V(in) VAL={VDD/2} RISE=1 TARG V(out) VAL={VDD/2} RISE=1
.meas TRAN tphl TRIG V(in) VAL={VDD/2} FALL=1 TARG V(out) VAL={VDD/2} FALL=1
.meas TRAN tpd_avg PARAM (tplh+tphl)/2
```

- `tplh`: input rising 50% crossing to output rising 50% crossing.
- `tphl`: input falling 50% crossing to output falling 50% crossing.
- `tpd_avg`: arithmetic average of the two propagation-delay measurements.

After running a deck, open **View → SPICE Error Log** (usually `Ctrl+L`) and
record `tplh`, `tphl`, and `tpd_avg`. LTspice `.MEAS` uses trigger and target
crossings to calculate the time difference; see the LTspice measurement
reference: https://ltspicehelpmanual.azurewebsites.net/measure--evaluateuser-definedele.htm

## Results template

Fill in `ltspice_measurements_template.csv` using the numbers from each LTspice
SPICE Error Log. Do not put the Python delay estimate in an LTspice-measured
column.

When you have completed all three simulations, share the CSV or the three log
files. The comparison should then calculate:

`percentage_error = abs(LTspice_tpd - Python_delay) / Python_delay * 100`

The comparison should be interpreted carefully: the first-order RC model uses
a fixed effective resistance and lumped capacitances, while LEVEL=1 SPICE uses
nonlinear transistor current equations. The purpose of the experiment is to
quantify that model difference, not to force the two delays to match.

## Troubleshooting

- **No measurements shown:** ensure the transient simulation completed and
  inspect the SPICE Error Log for convergence errors.
- **Measurement failed:** inspect the input and output waveforms and verify
  both cross `VDD/2`. The output might not have settled if the transient stop
  time or pulse period was changed.
- **Very slow simulation:** retain the 2 ps maximum timestep initially; reduce
  output waveform saving only if the machine has memory constraints.
- **Unknown model or syntax errors:** confirm that the `.cir` file was opened
  in LTspice and not pasted into a schematic directive with missing lines.

## Important reporting rule

Report the Stage-1 delay as **analytical RC estimated delay** and the Stage-2
number as **LTspice transistor-level simulated delay**. Do not label either as
measured silicon delay.
