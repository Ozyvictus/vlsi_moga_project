"""Run NSGA-II for technology-parameterized CMOS area-delay optimization."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from nsga2 import run_nsga2
from vlsi_model import (
    DEFAULT_CONFIG,
    DEFAULT_TECH,
    evaluate_design,
    evaluate_design_details,
    equal_stage_effort_design,
)

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"


def select_compromise(F: np.ndarray) -> int:
    """Select a balanced point by distance to the normalized ideal point."""
    f_min = F.min(axis=0)
    f_max = F.max(axis=0)
    span = np.where((f_max - f_min) == 0.0, 1.0, f_max - f_min)
    normalized = (F - f_min) / span
    return int(np.argmin(np.linalg.norm(normalized, axis=1)))


def save_pareto_csv(X: np.ndarray, F: np.ndarray, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "x2_size_factor", "x3_size_factor", "x4_size_factor",
            "transistor_channel_area_um2", "estimated_delay_ns"
        ])
        for x, f in zip(X, F):
            writer.writerow([*map(float, x), *map(float, f)])


def save_stage_metrics(sizes: np.ndarray, path: Path) -> None:
    details = evaluate_design_details(sizes)
    rows = details["stage_metrics"]
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_model_parameters(path: Path) -> None:
    values = {
        **{f"technology.{key}": value for key, value in vars(DEFAULT_TECH).items()},
        **{f"circuit.{key}": value for key, value in vars(DEFAULT_CONFIG).items()},
        "model.area_definition": "Sum of transistor channel areas (Wn + Wp) * L; excludes layout overhead",
        "model.delay_definition": "Sum of per-stage worst-transition delays using 0.69 * R * C",
    }
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["parameter", "value"])
        writer.writerows(values.items())


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = DEFAULT_CONFIG
    lower = np.full(cfg.n_stages - 1, cfg.min_size, dtype=float)
    upper = np.full(cfg.n_stages - 1, cfg.max_size, dtype=float)

    pareto_X, pareto_F, history_rows = run_nsga2(
        objective_function=evaluate_design,
        lower_bounds=lower,
        upper_bounds=upper,
        population_size=120,
        generations=180,
        seed=42,
    )

    if len(pareto_X) == 0:
        raise RuntimeError("NSGA-II returned an empty Pareto front.")

    save_pareto_csv(pareto_X, pareto_F, OUTPUT_DIR / "pareto_front.csv")

    selected = {
        "minimum_area": int(np.argmin(pareto_F[:, 0])),
        "minimum_delay": int(np.argmin(pareto_F[:, 1])),
        "balanced_compromise": select_compromise(pareto_F),
    }

    minimum_size_x = np.full(cfg.n_stages - 1, cfg.min_size, dtype=float)
    equal_effort_x = np.asarray(equal_stage_effort_design(), dtype=float)
    equal_effort_x = np.clip(equal_effort_x, cfg.min_size, cfg.max_size)
    baseline_cases = {
        "minimum_size": (minimum_size_x, evaluate_design(minimum_size_x)),
        "equal_stage_effort_reference": (
            equal_effort_x, evaluate_design(equal_effort_x)
        ),
    }

    with (OUTPUT_DIR / "design_summary.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow([
            "design", "x2_size_factor", "x3_size_factor", "x4_size_factor",
            "transistor_channel_area_um2", "estimated_delay_ns"
        ])
        for name, idx in selected.items():
            writer.writerow([name, *pareto_X[idx].tolist(), *pareto_F[idx].tolist()])
        for name, (x, objectives) in baseline_cases.items():
            writer.writerow([name, *x.tolist(), *objectives])

    with (OUTPUT_DIR / "convergence.csv").open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["generation", "best_area_um2", "best_delay_ns"])
        writer.writerows(history_rows)

    balanced_sizes = pareto_X[selected["balanced_compromise"]]
    save_stage_metrics(balanced_sizes, OUTPUT_DIR / "balanced_design_stage_metrics.csv")
    save_model_parameters(OUTPUT_DIR / "model_parameters.csv")

    from plot_results import create_plots
    create_plots(pareto_X, pareto_F, history_rows, baseline_cases, selected, OUTPUT_DIR)

    print("\n=== TECHNOLOGY-PARAMETERIZED CMOS MODEL ===")
    print(f"Technology parameter set: {DEFAULT_TECH.technology_name}")
    print(f"Supply: {DEFAULT_TECH.supply_voltage_v:.2f} V | Temperature: {DEFAULT_TECH.temperature_c:.1f} °C")
    print(f"Minimum inverter input capacitance: {evaluate_design_details(minimum_size_x)['minimum_inverter_input_capacitance_fF']:.4f} fF")
    print(f"External load: {evaluate_design_details(minimum_size_x)['external_load_fF']:.4f} fF")
    print("\n=== KEY RESULTS ===")
    print(f"Pareto solutions returned: {len(pareto_F)}")
    for name, idx in selected.items():
        x = pareto_X[idx]
        f = pareto_F[idx]
        print(
            f"{name:>20}: x2={x[0]:7.3f}, x3={x[1]:7.3f}, "
            f"x4={x[2]:7.3f}, area={f[0]:.6f} um^2, delay={f[1]:.6f} ns"
        )

    print("\nOutputs written to:", OUTPUT_DIR)
    print("- pareto_front.csv, design_summary.csv, convergence.csv")
    print("- balanced_design_stage_metrics.csv, model_parameters.csv")
    print("- pareto_front.png, convergence.png, design_comparison.png")
    print("\nNote: area is a transistor-channel-area proxy; delay is a first-order RC estimate.")


if __name__ == "__main__":
    main()
