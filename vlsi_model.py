"""Technology-parameterized first-order CMOS inverter-chain model.

The model combines a simple transistor-width area proxy with an RC delay
estimate. It is intended for educational optimization and later LTspice
validation; it is not a foundry sign-off model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TechnologyParameters:
    """Illustrative CMOS technology parameters (replace with PDK values later).

    The defaults describe an educational, nominal 180 nm-like example. The
    resistance values are reference effective on-resistances for minimum-width
    devices at the reference supply and temperature. ``r_p_min_ohm`` is the
    PMOS resistance at a PMOS width equal to the minimum NMOS width; the
    configured PMOS/NMOS width ratio is applied separately.
    """

    technology_name: str = "Illustrative 180 nm CMOS (not a foundry PDK)"
    channel_length_um: float = 0.18
    min_nmos_width_um: float = 0.22
    pmos_to_nmos_width_ratio: float = 2.0

    # Capacitance parameters.
    oxide_capacitance_fF_per_um2: float = 6.9
    overlap_capacitance_fF_per_um: float = 0.15
    diffusion_capacitance_fF_per_um_width: float = 0.35
    diffusion_capacitance_fF_per_um2: float = 0.50
    diffusion_length_um: float = 0.18

    # Effective on-resistance at the reference supply/temperature.
    r_n_min_ohm: float = 12_000.0
    r_p_min_ohm: float = 24_000.0
    reference_supply_voltage_v: float = 1.8
    supply_voltage_v: float = 1.8
    threshold_voltage_n_v: float = 0.40
    threshold_voltage_p_abs_v: float = 0.40

    # First-order temperature dependence of on-resistance.
    reference_temperature_c: float = 27.0
    temperature_c: float = 27.0
    resistance_tempco_per_c: float = 0.002

    def __post_init__(self) -> None:
        positive_fields = (
            "channel_length_um",
            "min_nmos_width_um",
            "pmos_to_nmos_width_ratio",
            "oxide_capacitance_fF_per_um2",
            "overlap_capacitance_fF_per_um",
            "diffusion_capacitance_fF_per_um_width",
            "diffusion_capacitance_fF_per_um2",
            "diffusion_length_um",
            "r_n_min_ohm",
            "r_p_min_ohm",
            "reference_supply_voltage_v",
            "supply_voltage_v",
        )
        for field_name in positive_fields:
            if getattr(self, field_name) <= 0:
                raise ValueError(f"{field_name} must be positive")
        if self.supply_voltage_v <= self.threshold_voltage_n_v:
            raise ValueError("Supply voltage must exceed NMOS threshold voltage")
        if self.supply_voltage_v <= self.threshold_voltage_p_abs_v:
            raise ValueError("Supply voltage must exceed |PMOS threshold voltage|")
        if self.resistance_tempco_per_c < 0:
            raise ValueError("resistance_tempco_per_c cannot be negative")


@dataclass(frozen=True)
class CircuitConfig:
    """Topology and optimization constraints for the inverter chain."""

    n_stages: int = 4
    fixed_first_stage_size: float = 1.0
    min_size: float = 1.0
    max_size: float = 64.0
    external_load_multiplier: float = 64.0
    interconnect_capacitance_fF_per_stage: float = 0.20

    def __post_init__(self) -> None:
        if self.n_stages < 2:
            raise ValueError("The inverter chain must contain at least two stages")
        if self.fixed_first_stage_size <= 0:
            raise ValueError("fixed_first_stage_size must be positive")
        if self.min_size <= 0 or self.max_size <= self.min_size:
            raise ValueError("Sizing bounds must satisfy 0 < min_size < max_size")
        if self.external_load_multiplier <= 0:
            raise ValueError("external_load_multiplier must be positive")
        if self.interconnect_capacitance_fF_per_stage < 0:
            raise ValueError("Interconnect capacitance cannot be negative")


DEFAULT_TECH = TechnologyParameters()
DEFAULT_CONFIG = CircuitConfig()


def _device_dimensions(size: float, tech: TechnologyParameters) -> tuple[float, float]:
    """Return (Wn, Wp) in micrometres for a normalized sizing factor."""
    wn = tech.min_nmos_width_um * size
    wp = wn * tech.pmos_to_nmos_width_ratio
    return wn, wp


def _gate_input_capacitance_fF(size: float, tech: TechnologyParameters) -> float:
    """Estimate inverter input capacitance from gate-oxide and overlap terms."""
    wn, wp = _device_dimensions(size, tech)
    total_gate_width = wn + wp
    gate_area = total_gate_width * tech.channel_length_um
    oxide_cap = tech.oxide_capacitance_fF_per_um2 * gate_area
    overlap_cap = tech.overlap_capacitance_fF_per_um * total_gate_width
    return oxide_cap + overlap_cap


def _output_diffusion_capacitance_fF(size: float, tech: TechnologyParameters) -> float:
    """Estimate output-node drain diffusion capacitance for one inverter."""
    wn, wp = _device_dimensions(size, tech)
    total_drain_width = wn + wp
    diffusion_area = total_drain_width * tech.diffusion_length_um
    return (
        tech.diffusion_capacitance_fF_per_um_width * total_drain_width
        + tech.diffusion_capacitance_fF_per_um2 * diffusion_area
    )


def _effective_resistances_ohm(
    size: float, tech: TechnologyParameters
) -> tuple[float, float]:
    """Return (pull-down resistance, pull-up resistance) for one inverter.

    Resistance scales inversely with device width. Supply and temperature
    corrections are deliberately first-order approximations.
    """
    n_headroom_ref = tech.reference_supply_voltage_v - tech.threshold_voltage_n_v
    n_headroom = tech.supply_voltage_v - tech.threshold_voltage_n_v
    p_headroom_ref = tech.reference_supply_voltage_v - tech.threshold_voltage_p_abs_v
    p_headroom = tech.supply_voltage_v - tech.threshold_voltage_p_abs_v
    n_voltage_scale = n_headroom_ref / n_headroom
    p_voltage_scale = p_headroom_ref / p_headroom

    temperature_scale = 1.0 + tech.resistance_tempco_per_c * (
        tech.temperature_c - tech.reference_temperature_c
    )
    if temperature_scale <= 0:
        raise ValueError("Temperature correction produced non-positive resistance")

    r_n = tech.r_n_min_ohm * n_voltage_scale * temperature_scale / size
    p_width_scale = tech.pmos_to_nmos_width_ratio * size
    r_p = tech.r_p_min_ohm * p_voltage_scale * temperature_scale / p_width_scale
    return r_n, r_p


def evaluate_design_details(
    variable_sizes: Iterable[float],
    config: CircuitConfig = DEFAULT_CONFIG,
    tech: TechnologyParameters = DEFAULT_TECH,
) -> dict:
    """Return area, delay and per-stage RC details for [x2, ..., xN].

    Stage 1 is fixed. Each inverter's input capacitance is based on its NMOS
    and PMOS widths. Each stage drives the next inverter's input capacitance,
    its own output diffusion capacitance, and an interconnect capacitance. The
    final stage instead drives an external load expressed as a multiple of the
    minimum inverter input capacitance.

    Stage transition delays use t = 0.69 * R * C. The reported path delay is
    the sum of the slower (rise/fall) transition at each stage.

    Area is the sum of transistor channel areas (Wn + Wp) * L. It excludes
    standard-cell placement whitespace, contacts, routing and layout overhead.
    """
    variable = tuple(float(v) for v in variable_sizes)
    expected = config.n_stages - 1
    if len(variable) != expected:
        raise ValueError(f"Expected {expected} sizing variables, received {len(variable)}")
    if any(not (config.min_size <= v <= config.max_size) for v in variable):
        raise ValueError(
            f"All sizing factors must be within [{config.min_size}, {config.max_size}]"
        )

    sizes = (config.fixed_first_stage_size, *variable)
    min_input_cap = _gate_input_capacitance_fF(1.0, tech)
    external_load_fF = config.external_load_multiplier * min_input_cap

    total_area_um2 = 0.0
    total_delay_ns = 0.0
    stage_rows: list[dict[str, float | int]] = []

    for index, size in enumerate(sizes):
        wn, wp = _device_dimensions(size, tech)
        active_area = (wn + wp) * tech.channel_length_um
        input_cap = _gate_input_capacitance_fF(size, tech)
        diffusion_cap = _output_diffusion_capacitance_fF(size, tech)
        r_n, r_p = _effective_resistances_ohm(size, tech)

        if index < config.n_stages - 1:
            driven_cap = _gate_input_capacitance_fF(sizes[index + 1], tech)
        else:
            driven_cap = external_load_fF

        total_load_cap = (
            driven_cap
            + diffusion_cap
            + config.interconnect_capacitance_fF_per_stage
        )
        # Ohm * fF = 1e-15 seconds; multiply by 1e-6 for nanoseconds.
        fall_delay_ns = 0.69 * r_n * total_load_cap * 1e-6
        rise_delay_ns = 0.69 * r_p * total_load_cap * 1e-6
        worst_transition_delay_ns = max(rise_delay_ns, fall_delay_ns)

        total_area_um2 += active_area
        total_delay_ns += worst_transition_delay_ns
        stage_rows.append({
            "stage": index + 1,
            "size_factor": size,
            "nmos_width_um": wn,
            "pmos_width_um": wp,
            "transistor_channel_area_um2": active_area,
            "input_capacitance_fF": input_cap,
            "output_diffusion_capacitance_fF": diffusion_cap,
            "driven_load_capacitance_fF": driven_cap,
            "interconnect_capacitance_fF": config.interconnect_capacitance_fF_per_stage,
            "total_output_load_fF": total_load_cap,
            "pull_down_resistance_ohm": r_n,
            "pull_up_resistance_ohm": r_p,
            "fall_delay_ns": fall_delay_ns,
            "rise_delay_ns": rise_delay_ns,
            "worst_transition_delay_ns": worst_transition_delay_ns,
        })

    return {
        "area_um2": float(total_area_um2),
        "delay_ns": float(total_delay_ns),
        "external_load_fF": float(external_load_fF),
        "minimum_inverter_input_capacitance_fF": float(min_input_cap),
        "technology_name": tech.technology_name,
        "stage_metrics": stage_rows,
    }


def evaluate_design(
    variable_sizes: Iterable[float],
    config: CircuitConfig = DEFAULT_CONFIG,
    tech: TechnologyParameters = DEFAULT_TECH,
) -> tuple[float, float]:
    """Return (transistor channel area in um^2, estimated path delay in ns)."""
    details = evaluate_design_details(variable_sizes, config, tech)
    return details["area_um2"], details["delay_ns"]


def equal_stage_effort_design(
    config: CircuitConfig = DEFAULT_CONFIG,
) -> tuple[float, ...]:
    """Return the ideal logical-effort sizing reference for this chain.

    This is an analytical reference only. It does not exactly minimize the
    upgraded RC model because the latter includes diffusion and wire caps.
    """
    total_path_effort = (
        config.external_load_multiplier / config.fixed_first_stage_size
    )
    per_stage_effort = total_path_effort ** (1.0 / config.n_stages)
    return tuple(
        config.fixed_first_stage_size * per_stage_effort**i
        for i in range(1, config.n_stages)
    )
