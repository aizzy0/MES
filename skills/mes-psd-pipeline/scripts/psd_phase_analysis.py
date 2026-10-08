#!/usr/bin/env python3
"""Extract phase metrics at user-selected wavenumbers from a PSD v4 file.

This script uses only the Python standard library. It follows the phase
convention of psd_gui_fixed_v4.py:
  phi_max = phase of the maximum signed PSD response
  phase_lag = (-phi_max) mod 360
  phase_equivalent_delay = phase_lag/360 * period / harmonic
  signed_delay = wrapped phase_equivalent_delay in [-T/(2k), +T/(2k)]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path


def parse_values(text: str) -> list[float]:
    return [float(x) for x in re.split(r"[,\s]+", text.strip()) if x]


def load_psd(path: Path):
    lines = [line.rstrip("\r\n") for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    if len(lines) < 3:
        raise ValueError("PSD file must contain a header, a phase row, and data rows.")
    header = lines[0].split("\t")
    phases = []
    for cell in header[1:]:
        token = re.sub(r"[°\s]", "", cell)
        phases.append(float(token))
    axis = []
    rows = []
    for line in lines[2:]:
        parts = line.split("\t")
        values = [float(x) for x in parts]
        if len(values) != len(phases) + 1:
            raise ValueError("Inconsistent PSD column count.")
        axis.append(values[0])
        rows.append(values[1:])
    order = sorted(range(len(axis)), key=lambda i: axis[i])
    axis = [axis[i] for i in order]
    rows = [rows[i] for i in order]
    if len(set(axis)) != len(axis):
        raise ValueError("Duplicate values on the PSD spectral axis.")
    return axis, phases, rows


def nearest_index(axis: list[float], target: float) -> int:
    return min(range(len(axis)), key=lambda i: abs(axis[i] - target))


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract PSD phase metrics at selected wavenumbers.")
    parser.add_argument("--psd", required=True, help="Path to a *_PSD_spectra_*_dphi.txt file")
    parser.add_argument("--wavenumbers", help="Comma/space-separated wavenumbers, e.g. '1300,1450,1600'")
    parser.add_argument("--wavenumber", type=float, action="append", default=[], help="Repeatable single wavenumber")
    parser.add_argument("--metadata", help="Metadata JSON path; defaults to <PSD>.meta.json")
    parser.add_argument("--output", help="Optional output TSV path")
    args = parser.parse_args()

    targets = []
    if args.wavenumbers:
        targets.extend(parse_values(args.wavenumbers))
    targets.extend(args.wavenumber)
    if not targets:
        raise SystemExit("Provide --wavenumbers or at least one --wavenumber.")

    psd_path = Path(args.psd).expanduser().resolve()
    meta_path = Path(args.metadata).expanduser().resolve() if args.metadata else Path(str(psd_path) + ".meta.json")
    if not psd_path.exists():
        raise SystemExit(f"PSD file not found: {psd_path}")
    if not meta_path.exists():
        raise SystemExit(f"Metadata file not found: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    period = float(meta["period_s"])
    harmonic = int(meta.get("harmonic", 1))
    if period <= 0:
        raise SystemExit("Metadata period_s must be positive.")

    axis, phases, rows = load_psd(psd_path)
    results = []
    for target in targets:
        idx = nearest_index(axis, target)
        matched = axis[idx]
        curve = rows[idx]
        amp = max(curve) - min(curve)
        scale = max(1.0, max(abs(v) for v in curve))
        defined = amp > sys.float_info.epsilon * scale * 32
        if defined:
            phi_max = phases[max(range(len(curve)), key=lambda j: curve[j])]
            lag = (-phi_max) % 360.0
            delay = lag / 360.0 * period / harmonic if harmonic > 0 else float("nan")
            signed = ((lag + 180.0) % 360.0 - 180.0) / 360.0 * period / harmonic if harmonic > 0 else float("nan")
        else:
            phi_max = float("nan")
            lag = float("nan")
            delay = float("nan")
            signed = float("nan")
        results.append({
            "requested_wavenumber": target,
            "matched_wavenumber": matched,
            "phi_max_deg": phi_max,
            "phase_lag_deg": lag,
            "phase_equivalent_delay_s": delay,
            "signed_phase_equivalent_delay_s": signed,
            "phase_defined": defined,
        })

    columns = [
        "requested_wavenumber", "matched_wavenumber", "phi_max_deg",
        "phase_lag_deg", "phase_equivalent_delay_s",
        "signed_phase_equivalent_delay_s", "phase_defined",
    ]
    output_lines = ["\t".join(columns)]
    for row in results:
        output_lines.append("\t".join(str(row[c]) for c in columns))
    text = "\n".join(output_lines) + "\n"
    if args.output:
        Path(args.output).expanduser().resolve().write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
