"""Smoke tests for the Stage-2 LTspice netlist exporter."""

from pathlib import Path

from export_ltspice import OUTPUT_DIR, _read_designs, render_netlist


def main() -> None:
    designs = _read_designs()
    assert set(designs) == {"minimum_area", "balanced_compromise", "minimum_delay"}

    for name, sizes in designs.items():
        text = render_netlist(name, sizes)
        assert text.count("NMOD W=") == 4
        assert text.count("PMOD W=") == 4
        assert ".tran 0 25n 0 2p" in text
        assert ".meas TRAN tplh" in text
        assert ".meas TRAN tphl" in text
        assert ".meas TRAN tpd_avg" in text
        assert "\n.end\n" in text

    print("All LTspice exporter smoke tests passed.")
    print(f"Generated netlist directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
