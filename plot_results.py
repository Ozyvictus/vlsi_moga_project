"""Create plots for the technology-parameterized CMOS MOGA results."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def create_plots(
    X: np.ndarray,
    F: np.ndarray,
    history_rows: list[tuple[int, float, float]],
    baseline_cases: dict,
    selected: dict[str, int],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1) Pareto front.
    fig, ax = plt.subplots(figsize=(8.5, 6.0))
    ax.scatter(F[:, 0], F[:, 1], s=26, alpha=0.8, label="NSGA-II Pareto solutions")
    marker_styles = {
        "minimum_area": ("s", "Minimum-area solution"),
        "minimum_delay": ("^", "Minimum-delay solution"),
        "balanced_compromise": ("*", "Balanced compromise"),
    }
    for key, (marker, label) in marker_styles.items():
        idx = selected[key]
        ax.scatter(
            F[idx, 0], F[idx, 1], marker=marker, s=150,
            edgecolors="black", linewidths=0.8, label=label, zorder=5
        )
    ax.set_title("Pareto Front: CMOS Transistor Area vs RC Delay")
    ax.set_xlabel("Transistor channel area proxy (µm²)")
    ax.set_ylabel("Estimated path delay (ns)")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "pareto_front.png", dpi=220)
    plt.close(fig)

    # 2) Convergence of the best objective values in each generation.
    if history_rows:
        data = np.asarray(history_rows, dtype=float)
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        axes[0].plot(data[:, 0], data[:, 1])
        axes[0].set_title("Best Area by Generation")
        axes[0].set_xlabel("Generation")
        axes[0].set_ylabel("Transistor channel area proxy (µm²)")
        axes[0].grid(True, alpha=0.3)

        axes[1].plot(data[:, 0], data[:, 2])
        axes[1].set_title("Best Delay by Generation")
        axes[1].set_xlabel("Generation")
        axes[1].set_ylabel("Estimated path delay (ns)")
        axes[1].grid(True, alpha=0.3)
        fig.suptitle("NSGA-II Convergence")
        fig.tight_layout()
        fig.savefig(output_dir / "convergence.png", dpi=220)
        plt.close(fig)

    # 3) Compare representative designs against the ideal equal-effort reference.
    labels = ["Minimum area", "Balanced", "Minimum delay", "Equal-effort reference"]
    pareto_indices = [
        selected["minimum_area"],
        selected["balanced_compromise"],
        selected["minimum_delay"],
    ]
    areas = [F[i, 0] for i in pareto_indices]
    delays = [F[i, 1] for i in pareto_indices]
    eq_area, eq_delay = baseline_cases["equal_stage_effort_reference"][1]
    areas.append(eq_area)
    delays.append(eq_delay)

    x_positions = np.arange(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    axes[0].bar(x_positions, areas)
    axes[0].set_title("Area Comparison")
    axes[0].set_ylabel("Transistor channel area proxy (µm²)")
    axes[0].set_xticks(x_positions, labels, rotation=20, ha="right")
    axes[0].grid(axis="y", alpha=0.3)

    axes[1].bar(x_positions, delays)
    axes[1].set_title("Delay Comparison")
    axes[1].set_ylabel("Estimated path delay (ns)")
    axes[1].set_xticks(x_positions, labels, rotation=20, ha="right")
    axes[1].grid(axis="y", alpha=0.3)
    fig.suptitle("Representative CMOS Area–Delay Trade-offs")
    fig.tight_layout()
    fig.savefig(output_dir / "design_comparison.png", dpi=220)
    plt.close(fig)
