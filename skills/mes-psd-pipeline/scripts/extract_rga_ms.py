#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract the time-relative column plus every m/z (amu) channel from a
Pfeiffer Vacuum PV MassSpec RGA export (*.dat) into a clean tab-separated file.

These exports carry a long metadata preamble whose length differs between runs,
so the data-table header is located by content rather than by line number, and
the m/z channels are recognised from the header names rather than by position.
Accepted column spellings include "17_amu", "amu17", "m/z 17" and "mass 17".

Stdlib only -- no numpy/pandas required.

Typical use:

    python extract_rga_ms.py "D:\\...\\20261001-MS\\*\\*.dat"

Output is written beside each source as "<name>_extracted.txt": one column of
relative time plus one column per m/z channel, tab-separated so Origin and
Excel read it directly.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TIME_RE = re.compile(r"^\s*time\b.*relative", re.I)
AMU_RES = [
    re.compile(r"^\s*(\d+(?:\.\d+)?)\s*_?amu\s*$", re.I),           # 17_amu / 17amu / 17 amu
    re.compile(r"^\s*amu\s*[_ ]?\s*(\d+(?:\.\d+)?)\s*$", re.I),     # amu17
    re.compile(r"^\s*(?:m\s*/\s*z|mass)\s*[=: ]\s*(\d+(?:\.\d+)?)\s*$", re.I),
]

# Conventional electron-impact assignment for the usual NH3-SCO channels.
# Informational only: several masses are ambiguous and must be checked against
# the blanks and against each other before being used quantitatively.
CONVENTIONAL = {
    "17": "NH3 (also OH fragment)",
    "18": "H2O",
    "28": "N2 / CO  (AMBIGUOUS)",
    "30": "NO (N2O fragment contributes)",
    "32": "O2",
    "44": "N2O / CO2  (AMBIGUOUS)",
    "46": "NO2",
}


def read_text(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def find_header(lines):
    """Return (index, columns) of the data table header, or (None, None)."""
    for i, line in enumerate(lines):
        if "\t" not in line:
            continue
        cols = line.rstrip("\n").split("\t")
        if any(TIME_RE.match(c) for c in cols):
            return i, cols
    return None, None


def amu_of(name):
    for rx in AMU_RES:
        m = rx.match(name)
        if m:
            v = m.group(1)
            return v.rstrip("0").rstrip(".") if "." in v else v
    return None


def convert(path, out_path=None, delimiter="\t"):
    lines = read_text(path).splitlines()
    hi, cols = find_header(lines)
    if hi is None:
        raise SystemExit("ERROR: no 'Time Relative' column found in %s" % path)

    time_idx = next(i for i, c in enumerate(cols) if TIME_RE.match(c))
    amu_cols = [(i, c, amu_of(c)) for i, c in enumerate(cols) if amu_of(c)]
    if not amu_cols:
        raise SystemExit("ERROR: no m/z (amu) columns recognised in %s" % path)

    rows = []
    for line in lines[hi + 1:]:
        if not line.strip():
            continue
        f = line.split("\t")
        if len(f) < len(cols):
            continue
        rows.append(f)

    if out_path is None:
        out_path = os.path.splitext(path)[0] + "_extracted.txt"

    header = [cols[time_idx]] + [c for _, c, _ in amu_cols]
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(delimiter.join(header) + "\n")
        for r in rows:
            fh.write(delimiter.join([r[time_idx]] + [r[i] for i, _, _ in amu_cols]) + "\n")

    return dict(source=path, output=out_path, header_line=hi + 1,
                total_columns=len(cols), exported_rows=len(rows),
                time_column=cols[time_idx],
                amu_columns=[(c, a) for _, c, a in amu_cols])


def expand(patterns):
    out = []
    for p in patterns:
        if any(ch in p for ch in "*?["):
            out.extend(sorted(glob.glob(p, recursive=True)))
        else:
            out.append(p)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="PV MassSpec .dat file(s); globs are expanded")
    ap.add_argument("--outdir", help="write outputs here instead of beside each source")
    ap.add_argument("--delimiter", default="\t", help="output delimiter (default: tab)")
    a = ap.parse_args(argv)

    files = expand(a.inputs)
    if not files:
        print("no input matched"); return 1

    rc = 0
    for p in files:
        if not os.path.isfile(p):
            print("MISSING: %s" % p); rc = 1; continue
        out = None
        if a.outdir:
            os.makedirs(a.outdir, exist_ok=True)
            out = os.path.join(a.outdir,
                               os.path.splitext(os.path.basename(p))[0] + "_extracted.txt")
        info = convert(p, out, a.delimiter)
        print("=" * 78)
        print("source       : %s" % info["source"])
        print("header line  : %d   (table had %d columns)" % (info["header_line"], info["total_columns"]))
        print("time column  : %s" % info["time_column"])
        print("m/z channels : %d" % len(info["amu_columns"]))
        for col, amu in info["amu_columns"]:
            print("    m/z %-5s  %-18s %s" % (amu, col, CONVENTIONAL.get(amu, "(no conventional label)")))
        print("data rows    : %d" % info["exported_rows"])
        print("written      : %s" % info["output"])
    print("=" * 78)
    print("Ambiguous channels (28 = N2/CO, 44 = N2O/CO2) must be resolved against")
    print("blanks or a second channel before any quantitative use.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
