#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shift the time axis of a time-series table by subtracting an offset, so that
a chosen moment becomes t = 0.

This does NOT remove any rows. Rows earlier than the offset simply acquire
negative times and are kept, which is usually what you want when re-zeroing a
run to the moment a gas step or a reaction starts.

Intended for the tables produced by extract_rga_ms.py (first column is
"Time Relative (sec)") and for any other tab-separated table whose first column
holds time in seconds. Only the first column is rewritten; every other field is
copied through byte-for-byte. The input file is never modified.

    # make 2200 s the new zero
    python shift_time.py --offset 2200 table.txt

    # one offset per file, matched to the order the files are given
    python shift_time.py --offset 2200,3088,2147 file1.txt file2.txt file3.txt

    # explicit, order-independent
    python shift_time.py --shift "a.txt=2200" --shift "b.txt=3088"

Output defaults to "<name>_t0.txt" beside each source; override with --suffix or
--outdir.
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


def decimals_of(text):
    """Number of digits after the decimal point, used to keep the original
    resolution when re-printing the shifted value."""
    if "." in text:
        return len(text.split(".")[1].split("e")[0].split("E")[0])
    return 0


def shift(path, offset, out_path, delimiter="\t"):
    lines = [l for l in read_lines(path) if l.strip()]
    if not lines:
        raise SystemExit("ERROR: empty file: %s" % path)
    header = lines[0].split(delimiter)
    body = [l.split(delimiter) for l in lines[1:]]

    ndec = 0
    for f in body:
        try:
            ndec = max(ndec, decimals_of(f[0]))
        except (IndexError, ValueError):
            pass
    fmt = "%." + str(ndec) + "f"

    out_rows = []
    skipped = 0
    for f in body:
        if len(f) != len(header):
            skipped += 1
            continue
        try:
            t = float(f[0])
        except ValueError:
            skipped += 1
            continue
        out_rows.append([fmt % (t - offset)] + f[1:])

    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(delimiter.join(header) + "\n")
        for r in out_rows:
            fh.write(delimiter.join(r) + "\n")

    ts = [float(r[0]) for r in out_rows]
    return dict(source=path, output=out_path, offset=offset, decimals=ndec,
                rows=len(out_rows), skipped=skipped,
                t_first=ts[0] if ts else None, t_last=ts[-1] if ts else None,
                crossed_zero=bool(ts and ts[0] < 0 <= ts[-1]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="tab-separated time-series file(s)")
    ap.add_argument("--offset", help="seconds to subtract: one value, or a comma list matched to the inputs in order")
    ap.add_argument("--shift", action="append", default=[],
                    help="explicit pair FILE=SECONDS; may be repeated")
    ap.add_argument("--suffix", default="_t0", help="appended to the stem (default: %(default)s)")
    ap.add_argument("--outdir", help="write outputs here instead of beside each source")
    ap.add_argument("--delimiter", default="\t", help="field delimiter (default: tab)")
    a = ap.parse_args(argv)

    explicit = {}
    for item in a.shift:
        if "=" not in item:
            raise SystemExit("ERROR: --shift expects FILE=SECONDS, got %r" % item)
        f, v = item.rsplit("=", 1)
        explicit[os.path.basename(f)] = float(v)

    seq = []
    if a.offset:
        seq = [float(x) for x in a.offset.split(",") if x.strip() != ""]

    if not explicit and not seq:
        raise SystemExit("ERROR: give --offset or --shift")

    rc = 0
    for i, path in enumerate(a.inputs):
        if not os.path.isfile(path):
            print("MISSING: %s" % path); rc = 1; continue
        base = os.path.basename(path)
        if base in explicit:
            off = explicit[base]
        elif len(seq) == 1:
            off = seq[0]
        elif len(seq) == len(a.inputs):
            off = seq[i]
        else:
            print("NO OFFSET for %s (got %d values for %d files)" % (base, len(seq), len(a.inputs)))
            rc = 1
            continue

        stem = os.path.splitext(base)[0]
        if a.outdir:
            os.makedirs(a.outdir, exist_ok=True)
            out = os.path.join(a.outdir, stem + a.suffix + ".txt")
        else:
            out = os.path.join(os.path.dirname(path) or ".", stem + a.suffix + ".txt")

        info = shift(path, off, out, a.delimiter)
        print("=" * 78)
        print("source      : %s" % info["source"])
        print("subtract    : %.1f s   (old 0 -> %.1f s, old %.1f s -> new 0)"
              % (info["offset"], -info["offset"], info["offset"]))
        print("rows        : %d   (all kept; skipped %d)" % (info["rows"], info["skipped"]))
        print("new time    : %.*f -> %.*f s   (decimals kept: %d)"
              % (info["decimals"], info["t_first"], info["decimals"], info["t_last"], info["decimals"]))
        print("crosses 0   : %s" % info["crossed_zero"])
        print("written     : %s" % info["output"])
    return rc


if __name__ == "__main__":
    sys.exit(main())
