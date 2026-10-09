#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Drop the leading part of a time-series table: keep only rows whose first
column is >= a cutoff, and write the result to a new file.

Intended for the tables produced by extract_rga_ms.py (first column is
"Time Relative (sec)") and for any other tab-separated table whose first column
holds the time in seconds. The input file is never modified.

The cutoff can be one value for every input, or one per input:

    # same cutoff for all files
    python trim_by_time.py --min-time 1800 *.txt

    # one cutoff per file, matched in the order the files are given
    python trim_by_time.py --min-time 1800,2400,3000 a.txt b.txt c.txt

    # explicit, order-independent
    python trim_by_time.py --cut "a.txt=1800" --cut "b.txt=2400"

Output defaults to "<name>_cut.txt" beside each source; override with --suffix
or --outdir.
"""

from __future__ import annotations

import argparse
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def read_lines(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc).splitlines()
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace").splitlines()


def as_float(s):
    try:
        return float(s)
    except ValueError:
        return None


def trim(path, min_time, out_path, delimiter="\t"):
    lines = [l for l in read_lines(path) if l.strip()]
    if not lines:
        raise SystemExit("ERROR: empty file: %s" % path)
    header = lines[0].split(delimiter)
    kept, dropped, skipped = [], 0, 0
    for line in lines[1:]:
        f = line.split(delimiter)
        if len(f) != len(header):
            skipped += 1
            continue
        t = as_float(f[0])
        if t is None:
            skipped += 1
            continue
        if t >= min_time:
            kept.append(line)
        else:
            dropped += 1
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(delimiter.join(header) + "\n")
        for line in kept:
            fh.write(line + "\n")
    first = kept[0].split(delimiter)[0] if kept else None
    last = kept[-1].split(delimiter)[0] if kept else None
    return dict(source=path, output=out_path, cutoff=min_time,
                rows_in=len(lines) - 1, rows_out=len(kept),
                dropped=dropped, skipped=skipped, first_kept=first, last_kept=last)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="tab-separated time-series file(s)")
    ap.add_argument("--min-time", help="cutoff in seconds: one value, or a comma list matched to the inputs in order")
    ap.add_argument("--cut", action="append", default=[],
                    help="explicit pair FILE=SECONDS; may be repeated")
    ap.add_argument("--suffix", default="_cut", help="appended to the stem (default: %(default)s)")
    ap.add_argument("--outdir", help="write outputs here instead of beside each source")
    ap.add_argument("--delimiter", default="\t", help="field delimiter (default: tab)")
    a = ap.parse_args(argv)

    explicit = {}
    for item in a.cut:
        if "=" not in item:
            raise SystemExit("ERROR: --cut expects FILE=SECONDS, got %r" % item)
        f, v = item.rsplit("=", 1)
        explicit[os.path.basename(f)] = float(v)

    seq = []
    if a.min_time:
        seq = [float(x) for x in a.min_time.split(",") if x.strip() != ""]

    if not explicit and not seq:
        raise SystemExit("ERROR: give --min-time or --cut")

    rc = 0
    for i, path in enumerate(a.inputs):
        if not os.path.isfile(path):
            print("MISSING: %s" % path); rc = 1; continue
        base = os.path.basename(path)
        if base in explicit:
            cut = explicit[base]
        elif len(seq) == 1:
            cut = seq[0]
        elif len(seq) == len(a.inputs):
            cut = seq[i]
        else:
            print("NO CUTOFF for %s (got %d values for %d files)" % (base, len(seq), len(a.inputs)))
            rc = 1
            continue

        stem = os.path.splitext(base)[0]
        out = os.path.join(a.outdir if a.outdir else os.path.dirname(path) or ".",
                           stem + a.suffix + ".txt")
        if a.outdir:
            os.makedirs(a.outdir, exist_ok=True)

        info = trim(path, cut, out, a.delimiter)
        print("=" * 78)
        print("source     : %s" % info["source"])
        print("cutoff     : >= %.1f s" % info["cutoff"])
        print("rows       : %d -> %d   (dropped %d, skipped %d)"
              % (info["rows_in"], info["rows_out"], info["dropped"], info["skipped"]))
        if info["rows_out"]:
            print("kept range : %s -> %s s" % (info["first_kept"], info["last_kept"]))
        else:
            print("!! nothing left after the cutoff -- check the value against the file's time range")
            rc = 1
        print("written    : %s" % info["output"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
