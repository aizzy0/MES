---
name: mes-psd-pipeline
description: Process modulation-excitation spectroscopy (MES) data from two sources. Bruker OPUS exports (a Data Point Table *.dpt plus trace data *Trace*.DPT) are converted to generic ASCII DAT files, given a one-column time companion, and run through corrected PSD v4 analysis with phi_max, phase lag and phase-equivalent delay extracted at user-selected wavenumbers. Pfeiffer Vacuum PV MassSpec RGA exports (*.dat) have their relative-time column and every m/z (amu) channel extracted into a clean tab-separated table for plotting. Use for samples such as CHA NH3-O2, CHA O2-NH3, Pt NH3-O2 or PtCu O2-NH3.
---

# MES Data Pipeline

Use this skill for modulation-excitation spectroscopy (MES). The experiment yields two independent data sources, both handled here:

- **IR MES spectra** from Bruker OPUS exports: converted to portable ASCII, given a time axis, then corrected PSD v4 analysis (the first part of this document).
- **Mass-spec (RGA) traces** from a Pfeiffer Vacuum PrismaPro exported by PV MassSpec: the relative-time column and every m/z channel pulled into a clean table (see *Mass-spec (RGA) channel extraction* at the end).

## Required OPUS inputs

- **Data Point Table**: an OPUS `*.dpt` export containing the spectral matrix used for trace and PSD processing.
- **Trace data**: an OPUS `*Trace*.DPT` export containing the trace/time information; its first column supplies the time values.
- A separate one-column time export (`<sample>时间导出.dat`) may be used directly when available.

The generic sample name is stripped of version dots, for example `CHA NH3-O2`, `CHA O2-NH3`, or `Pt NH3-O2`.

## Mandatory parameter checkpoint

Before converting files or starting PSD, ask the user to choose or confirm the user-selectable PSD parameters. Harmonic is fixed to `1` and modulation origin is fixed to `0`.

Ask for:

- Number of spectra per complete period (suggested value for the standard workflow: `120`)
- Total periods including discarded periods (suggested: `15`)
- Number of first periods to discard (suggested: `10`)
- Phase step in degrees (suggested: `10`)
- Period in seconds, or blank to infer as `N × median(dt)` (suggested: blank)

Wait for the user's answer. Only then run the pipeline.

## Portable execution

`scripts/mes_pipeline.py` uses only the Python standard library. It does not require `numpy`, `pandas`, `scipy`, or any local custom `.py` program.

Use any Python 3.8+ interpreter, for example:

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\mes_pipeline.py' `
  --trace-source 'D:\path\CHA O2-NH3.0.dpt' `
  --time-source 'D:\path\CHA O2-NH3时间导出.dat' `
  --sample 'CHA O2-NH3' `
  --outdir 'D:\path' `
  --n-spectra 120 `
  --periods 15 `
  --discard 10 `
  --phase-step 10
```

The four user-selectable PSD parameters are required by the CLI. Harmonic and origin are fixed internally and are not prompted.

## Selected-wavenumber phase analysis

After PSD files exist, ask the user which wavenumbers to analyze. Run:

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\psd_phase_analysis.py' `
  --psd '<sample>轨迹导出_<discard>_periods_cutoff_PSD_spectra_<phase-step>_dphi.txt' `
  --wavenumbers '1300,1450,1600,2350,3600'
```

The script snaps each requested value to the nearest PSD axis point and reports:

- `phi_max_deg`: phase of the maximum signed PSD response
- `phase_lag_deg`: `(-phi_max) mod 360`
- `phase_equivalent_delay_s`: `phase_lag / 360 × period_s / harmonic`
- `signed_phase_equivalent_delay_s`: phase-equivalent delay wrapped to `[-T/(2k), +T/(2k)]`
- `phase_defined`: false when the selected curve is too flat to define a phase

The phase-equivalent delay is not a kinetic time constant. It is only a phase-to-time conversion.

## Required output names

```text
<sample>轨迹导出.dat
<sample>时间导出.dat
<sample>轨迹导出_t.dat
<sample>轨迹导出_<discard>_periods_cutoff_averaged.txt
<sample>轨迹导出_<discard>_periods_cutoff_PSD_spectra_<phase_step>_dphi.txt
```

plus the two `.meta.json` sidecars.

`<sample>` is the generic sample name, for example `CHA O2-NH3` or `Pt NH3-O2`. Do not place `.0`, `_Trace_`, or other version/trace suffixes in output filenames.

## Verification

Require all of the following before reporting success:

- Trace table is TAB-separated ASCII and has no non-ASCII bytes.
- Time companion has exactly one numeric column.
- Averaged output has `1 + N` columns.
- PSD output has `1 + ceil(360 / phase_step)` columns.
- `period_s` is inferred or agrees with `N × median(dt)`.
- Metadata records requested periods, discarded periods, spectra per period, harmonic, origin, and phase step.

Read `references/workflow.md` for the detailed sequence and troubleshooting notes.

## Mass-spec (RGA) channel extraction

The mass-spectrometry side of the same experiment is a Pfeiffer Vacuum PrismaPro
RGA exported by PV MassSpec. Each `*.dat` opens with a metadata preamble of a few
hundred lines -- whose length differs between runs -- followed by a tab-separated
table whose header begins `Time Relative (sec)` and continues with the recorded
channels (`17_amu`, `18_amu`, ...) and a block of peripheral digital I/O.

`scripts/extract_rga_ms.py` reduces those exports to the columns that matter and
writes them beside each source as `<name>_extracted.txt`:

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\extract_rga_ms.py' "D:\...\20261001-MS\*\*.dat"
```

Stdlib only. The header row is found by content and the m/z columns by name, so
varying preamble lengths and spellings (`17_amu`, `amu17`, `m/z 17`, `mass 17`)
all resolve. Output is tab-separated with the peripheral and analog columns
dropped, so it loads straight into Origin or Excel.

The script extracts **every** recognised m/z channel and nothing else. If the
user also wants pressure, ionizer state, or digital I/O, add those deliberately
rather than widening the match -- and confirm the channel list with the user
before writing outputs, the same way the PSD parameters are confirmed.

### Aligning the time axis

Two operations look alike and produce opposite results. **Establish which one the
user wants before running either** -- see the warning below.

**Re-zero (shift) the axis** keeps every row and subtracts a constant from the
time column, so a chosen moment becomes t = 0. Rows before that moment simply
become negative. This is what "make 2200 s the zero point" or "subtract 2200 s
from the times" means.

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\shift_time.py' --offset 2200 table.txt

python 'C:\path\to\mes-psd-pipeline\scripts\shift_time.py' `
  --offset 2200,3088,2147,2203,2253,2284,2098,2500 f1.txt ... f8.txt
```

Output is `<name>_t0.txt`. The decimal count of the original time column is
preserved, and every other column is copied through byte-for-byte.

**Remove the lead-in (trim)** drops the rows below a cutoff and keeps the rest.
The axis is not re-zeroed. Use it only when the user explicitly wants rows gone.

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\trim_by_time.py' --min-time 1800 table.txt
```

Output is `<name>_cut.txt`.

Both scripts take one value for every file, a comma list matched to the input
order, or repeated `--shift` / `--cut` `FILE=SECONDS` pairs.

**Confirm the operation and the values; pick neither yourself.** "Cut the first
2200 seconds" and "set 2200 s to zero" are one word apart and mean opposite
things -- one deletes 353 rows, the other deletes nothing. List the files with
their numbering and time ranges, say in the reply which operation you are about
to run, then apply exactly the values given. Do not infer the operation from the
word "time" alone.

Verify after either operation: for a shift the row count is unchanged, every
non-time column is byte-identical, and the new first/last timestamps equal the
old ones minus the offset; for a trim every kept row is at or after the cutoff
and the kept range still ends where the original did.

Read `references/rga-dat-format.md` for the full preamble layout, the
column-name variants, and the verification checklist.

