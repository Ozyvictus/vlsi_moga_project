LTspice Stage 2 netlists
========================

Open each .cir file in LTspice and click Run.
Open View > SPICE Error Log (Ctrl+L) after simulation to read tplh, tphl,
and tpd_avg measurements.

These are illustrative LEVEL=1 MOS models, not a foundry PDK. The KP
values are estimated to roughly match the Stage-1 effective resistance
around mid-supply. Differences between Python and LTspice are expected
because the transistor-level model has nonlinear I-V behaviour and
additional model assumptions.
