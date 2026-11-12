"""Sanity checks for the technology-parameterized CMOS model and NSGA-II."""

from dataclasses import replace

import numpy as np

from nsga2 import dominates, run_nsga2
from vlsi_model import (
    DEFAULT_CONFIG,
    DEFAULT_TECH,
    TechnologyParameters,
    evaluate_design,
    evaluate_design_details,
    equal_stage_effort_design,
)


def main() -> None:
    minimum_sizes = np.ones(DEFAULT_CONFIG.n_stages - 1, dtype=float)
    area_min, delay_min = evaluate_design(minimum_sizes)
    details = evaluate_design_details(minimum_sizes)

    # Units and dimensions: all reported quantities must be finite and positive.
    assert np.isfinite(area_min) and area_min > 0
    assert np.isfinite(delay_min) and delay_min > 0
    assert len(details["stage_metrics"]) == DEFAULT_CONFIG.n_stages
    assert details["external_load_fF"] > details["minimum_inverter_input_capacitance_fF"]

    # Larger transistor widths increase the channel-area proxy.
    larger_sizes = np.array([2.0, 2.0, 2.0])
    area_larger, _ = evaluate_design(larger_sizes)
    assert area_larger > area_min

    # A larger external load must increase path delay for the same design.
    heavier_load_cfg = replace(DEFAULT_CONFIG, external_load_multiplier=128.0)
    _, heavier_load_delay = evaluate_design(minimum_sizes, heavier_load_cfg)
    assert heavier_load_delay > delay_min

    # Lower supply and higher temperature must increase the first-order delay.
    low_voltage_tech = replace(DEFAULT_TECH, supply_voltage_v=1.2)
    _, low_voltage_delay = evaluate_design(minimum_sizes, tech=low_voltage_tech)
    assert low_voltage_delay > delay_min

    hot_tech = replace(DEFAULT_TECH, temperature_c=75.0)
    _, hot_delay = evaluate_design(minimum_sizes, tech=hot_tech)
    assert hot_delay > delay_min

    # The ideal equal-effort point is now a reference design, not an exact
    # optimum for the added diffusion/wire-capacitance RC model.
    reference_x = np.asarray(equal_stage_effort_design())
    reference_area, reference_delay = evaluate_design(reference_x)
    assert reference_area > area_min
    assert reference_delay > 0

    # Deterministic execution on a small test run.
    lower = np.full(DEFAULT_CONFIG.n_stages - 1, DEFAULT_CONFIG.min_size)
    upper = np.full(DEFAULT_CONFIG.n_stages - 1, DEFAULT_CONFIG.max_size)
    X, F, history = run_nsga2(
        evaluate_design,
        lower,
        upper,
        population_size=36,
        generations=25,
        seed=7,
    )
    assert len(X) > 0 and len(X) == len(F)
    assert np.all(X >= lower - 1e-10) and np.all(X <= upper + 1e-10)
    assert len(history) == 26
    assert np.all(np.isfinite(F))
    assert np.all(F > 0)

    # No solution in the returned first front should dominate another.
    for i in range(len(F)):
        for j in range(len(F)):
            if i != j:
                assert not dominates(F[i], F[j])

    print("All sanity checks passed.")
    print(f"Minimum-size design: area={area_min:.6f} um^2, delay={delay_min:.6f} ns")
    print(f"Ideal equal-effort reference: area={reference_area:.6f} um^2, delay={reference_delay:.6f} ns")
    print(f"Test run Pareto solutions: {len(F)}")


if __name__ == "__main__":
    main()
