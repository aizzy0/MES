#!/usr/bin/env python3
"""Portable MES ASCII -> time companion -> corrected PSD v4 pipeline.

This script uses only the Python standard library. It does not import or call
the local time_convert2D_fixed_v4.py or psd_gui_fixed_v4.py programs.

Required PSD parameters are intentionally explicit:
  --n-spectra, --periods, --discard, --phase-step
The harmonic is fixed to 1 and the time origin is fixed to 0.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import statistics
from pathlib import Path


def normalize_number(value: str) -> str:
    """Normalize a numeric token to the OPUS-style ASCII representation."""
    s = value.strip()
    if not s:
        return s
    sign = ""
    if s[0] in "+-":
        sign, s = s[0], s[1:]
    if s.replace(".", "").strip("0") == "":
        return "0"

    if "e" in s.lower():
        mantissa, exponent = re.split("[eE]", s, maxsplit=1)
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{sign}{mantissa}E{int(exponent)}"

    if s.startswith("0."):
        frac = s[2:]
        first = next((i for i, c in enumerate(frac) if c != "0"), None)
        if first is not None and first >= 3:
            digits = frac[first:].rstrip("0") or "0"
            mant = digits[0] + (("." + digits[1:]) if len(digits) > 1 else "")
            return f"{sign}{mant}E{-(first + 1)}"

    return sign + s.rstrip("0").rstrip(".")


def infer_sample(source: Path) -> str:
    name = source.name
    for suffix in (".DPT", ".dpt", ".dat", ".DAT"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    name = re.sub(r"(_?-?\d*_?periods_cutoff.*)$", "", name, flags=re.I)
    name = re.sub(r"(_?PSD.*)$", "", name, flags=re.I)
    name = re.sub(r"_t$", "", name, flags=re.I)
    name = re.sub(r"轨迹导出\d*$", "", name)
    name = re.sub(r"时间导出\d*$", "", name)
    name = re.sub(r"\.0$", "", name)
    name = name.strip()
    if not name:
        raise ValueError(f"Cannot infer sample name from {source.name!r}; pass --sample.")
    return name


def read_numeric_tokens(path: Path) -> list[list[str]]:
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for line in handle:
            line = line.rstrip("\r\n")
            if not line:
                continue
            if "\t" in line:
                rows.append(line.split("\t"))
            elif "," in line:
                rows.append(line.split(","))
            else:
                rows.append([line])
    return rows


def write_trace_ascii(source: Path, sample: str, outdir: Path) -> Path:
    out = outdir / f"{sample}轨迹导出.dat"
    rows = read_numeric_tokens(source)
    if not rows:
        raise ValueError(f"No numeric rows found in {source}")
    with out.open("w", encoding="ascii", newline="") as handle:
        for row in rows:
            if len(row) < 2:
                raise ValueError("Trace export must contain at least two columns.")
            handle.write("\t".join(normalize_number(v) for v in row) + "\r\n")
    return out


def copy_time_ascii(source: Path, sample: str, outdir: Path) -> Path:
    out = outdir / f"{sample}时间导出.dat"
    if source.resolve() != out.resolve():
        shutil.copyfile(source, out)
    return out


def read_time_column(path: Path) -> list[float]:
    values: list[float] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            parts = [p for p in re.split(r"[\t, ]+", line) if p]
            if len(parts) != 1:
                raise ValueError("Time export must contain exactly one numeric column.")
            values.append(float(parts[0]))
    return values


def write_time_companion(trace: Path, time_file: Path) -> Path:
    values = read_time_column(time_file)
    if len(values) < 3:
        raise ValueError("Time file must contain at least three values.")
    out = trace.with_name(trace.stem + "_t" + trace.suffix)
    with out.open("w", encoding="ascii", newline="") as handle:
        for value in values:
            handle.write(f"{value:.5f}\r\n")
    return out


def read_trace_header(path: Path) -> tuple[int, int]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for line in handle:
            if line.strip():
                return len(line.rstrip("\r\n").split("\t")), 1
    raise ValueError("Trace file is empty.")


def parse_period(times: list[float], n: int, period_arg: float | None) -> float:
    intervals = [times[i + 1] - times[i] for i in range(len(times) - 1)]
    dt = statistics.median(intervals)
    if dt <= 0:
        raise ValueError("Time values must be strictly increasing.")
    for value in intervals:
        if not math.isclose(value, dt, rel_tol=1e-3, abs_tol=1e-8):
            raise ValueError("Nonuniform acquisition times; complete evenly sampled cycles are required.")
    inferred = n * dt
    if period_arg is not None:
        if period_arg <= 0 or not math.isclose(period_arg, inferred, rel_tol=1e-3, abs_tol=1e-8):
            raise ValueError(f"Specified period {period_arg} s does not match inferred {inferred:g} s.")
        return float(period_arg)
    return inferred


def format_float(value: float) -> str:
    if value == 0:
        return "0.0"
    return repr(float(value))


def run_pipeline(trace: Path, time_file: Path, outdir: Path, sample: str,
                 n: int, periods: int, discard: int, dphi: float,
                 period_arg: float | None) -> dict:
    harmonic = 1
    origin = 0.0
    if n < 3 or periods < 1 or not 0 <= discard < periods:
        raise ValueError("Require n >= 3, periods >= 1, and 0 <= discard < periods.")
    if not 0 < dphi <= 180:
        raise ValueError("Phase step must be in (0, 180] degrees.")
    if harmonic < 0:
        raise ValueError("Harmonic must be >= 0.")

    times = read_time_column(time_file)
    required = periods * n
    if len(times) < required:
        raise ValueError(f"Need {required} time points, but time file contains only {len(times)}.")
    period = parse_period(times[:required], n, period_arg)

    retained = periods - discard
    times_used = times[discard * n:required]
    avg_times = [t - discard * period for t in times_used[:n]]
    phases = [i * dphi for i in range(int(math.ceil(360.0 / dphi)))]

    avg_path = outdir / f"{sample}轨迹导出_{discard}_periods_cutoff_averaged.txt"
    psd_path = outdir / f"{sample}轨迹导出_{discard}_periods_cutoff_PSD_spectra_{dphi:g}_dphi.txt"
    avg_meta_path = Path(str(avg_path) + ".meta.json")
    psd_meta_path = Path(str(psd_path) + ".meta.json")

    meta = {
        "format_version": 4,
        "period_s": period,
        "origin_s": origin,
        "harmonic": harmonic,
        "phase_step_deg": dphi,
        "reference": "square" if harmonic == 0 else "sin(k*omega*(t-origin)+phi)",
        "spectra_per_period": n,
        "periods_requested": periods,
        "discarded_periods": discard,
        "source": trace.name,
        "time_mean_removed": True,
        "time_units": "s",
        "quadrature": "periodic equal-weight sum",
    }

    axis_offsets = []
    expected_columns = None
    with trace.open("r", encoding="utf-8-sig", newline="") as handle:
        while True:
            offset = handle.tell()
            line = handle.readline()
            if not line:
                break
            line = line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split("\t")
            if expected_columns is None:
                expected_columns = len(parts)
                if expected_columns != len(times) + 1:
                    raise ValueError("Spectral matrix columns must equal time count + 1.")
            elif len(parts) != expected_columns:
                raise ValueError("Inconsistent column count in trace file.")
            axis_offsets.append((float(parts[0]), offset))

    if not axis_offsets:
        raise ValueError("Trace file contains no data rows.")
    if len({axis for axis, _ in axis_offsets}) != len(axis_offsets):
        raise ValueError("Duplicate values on the spectral axis.")
    axis_offsets.sort(key=lambda item: item[0])

    avg_handle = avg_path.open("w", encoding="utf-8", newline="")
    psd_handle = psd_path.open("w", encoding="utf-8", newline="")
    avg_handle.write("Wavenumber / 1/cm\t" + "\t".join(
        f"#{i + 1} ({t:.9g} s)" for i, t in enumerate(avg_times)
    ) + "\n")
    psd_handle.write("Wavenumber / 1/cm\t" + "\t".join(f"{p:g}°" for p in phases) + "\n")
    avg_handle.write("0.0\t" + "\t".join(format_float(t) for t in avg_times) + "\n")
    psd_handle.write("0.0\t" + "\t".join(format_float(p) for p in phases) + "\n")

    omega = 2.0 * math.pi / period
    phase_rads = [math.radians(p) for p in phases]
    with trace.open("r", encoding="utf-8-sig", newline="") as handle:
        for axis, offset in axis_offsets:
            handle.seek(offset)
            line = handle.readline().rstrip("\r\n")
            values = [float(x) for x in line.split("\t")]
            spectra = values[1:]
            if len(spectra) < required:
                raise ValueError(f"Need {required} spectra, but input contains only {len(spectra)}.")
            selected = spectra[discard * n:required]
            averages = []
            for j in range(n):
                averages.append(sum(selected[p * n + j] for p in range(retained)) / retained)
            mean_avg = sum(averages) / len(averages)
            centered = [value - mean_avg for value in averages]
            psd_values = []
            for phase_rad in phase_rads:
                total = 0.0
                for j, value in enumerate(centered):
                    angle = harmonic * omega * (avg_times[j] - origin) + phase_rad
                    if harmonic > 0:
                        reference = math.sin(angle)
                    else:
                        reference = 1.0 if math.sin(angle) >= 0 else -1.0
                    total += value * reference
                psd_values.append(2.0 / len(centered) * total)
            avg_handle.write(format_float(axis) + "\t" + "\t".join(format_float(v) for v in averages) + "\n")
            psd_handle.write(format_float(axis) + "\t" + "\t".join(format_float(v) for v in psd_values) + "\n")

    if avg_handle is None or psd_handle is None:
        raise ValueError("Trace file contains no data rows.")
    avg_handle.close()
    psd_handle.close()
    avg_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    psd_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "sample": sample,
        "trace_ascii": str(trace),
        "time_ascii": str(time_file),
        "time_companion": str(trace.with_name(trace.stem + "_t" + trace.suffix)),
        "averaged": str(avg_path),
        "psd": str(psd_path),
        "period_s": period,
        "spectra_per_period": n,
        "periods_requested": periods,
        "discarded_periods": discard,
        "phase_step_deg": dphi,
    }


def find_time_file(outdir: Path, sample: str) -> Path:
    candidates = [
        outdir / f"{sample}时间导出.dat",
        outdir / f"{sample}时间导出1.dat",
        outdir / f"{sample}.0时间导出1.dat",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No time export found. Pass --time-source explicitly.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Portable MES ASCII/time/PSD pipeline")
    parser.add_argument("--trace-source", required=True)
    parser.add_argument("--time-source")
    parser.add_argument("--sample")
    parser.add_argument("--outdir")
    parser.add_argument("--n-spectra", type=int, required=True)
    parser.add_argument("--periods", type=int, required=True)
    parser.add_argument("--discard", type=int, required=True)
    parser.add_argument("--phase-step", type=float, required=True)
    parser.add_argument("--period", type=float, default=None)
    args = parser.parse_args()

    trace_source = Path(args.trace_source).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve() if args.outdir else trace_source.parent
    outdir.mkdir(parents=True, exist_ok=True)
    sample = args.sample or infer_sample(trace_source)

    trace_ascii = write_trace_ascii(trace_source, sample, outdir)
    time_source = Path(args.time_source).expanduser().resolve() if args.time_source else find_time_file(outdir, sample)
    time_ascii = copy_time_ascii(time_source, sample, outdir)
    write_time_companion(trace_ascii, time_ascii)
    summary = run_pipeline(
        trace_ascii, time_ascii, outdir, sample,
        args.n_spectra, args.periods, args.discard,
        args.phase_step, args.period
    )
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
