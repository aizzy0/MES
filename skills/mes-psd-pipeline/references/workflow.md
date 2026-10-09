# MES workflow

This skill covers two independent data sources from the same experiment:

- **Part 1** IR MES spectra: Bruker OPUS exports to corrected PSD.
- **Part 2** mass-spec (RGA) traces: Pfeiffer PV MassSpec exports to plottable channel tables.

## Part 1 - IR MES spectra (OPUS to corrected PSD)

### Inputs

- Source trace table from OPUS, normally a `.dpt` with comma-separated fixed decimals.
- One-column time export in seconds. If only a trace DPT is available, its first column can be used as the time source.
- Generic sample name without version dots, for example `CHA O2-NH3`, `CHA NH3-O2`, or `Pt NH3-O2`.

### Step 1: collect PSD parameters

Before executing the pipeline, ask the user to select or confirm the user-selectable parameters. Harmonic is fixed to 1 and time origin is fixed to 0.

| Parameter | CLI option | Suggested value |
|---|---|---:|
| Spectra per complete period | `--n-spectra` | 120 |
| Total periods including discarded | `--periods` | 15 |
| Discarded first periods | `--discard` | 10 |
| Phase step / degrees | `--phase-step` | 10 |
| Period / s | `--period` | blank = infer |

Do not run the pipeline until the user has answered.

### Step 2: run the portable pipeline

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\mes_pipeline.py' `
  --trace-source '<source trace .dpt>' `
  --time-source '<one-column time export>' `
  --sample '<sample>' `
  --outdir '<output directory>' `
  --n-spectra <N> `
  --periods <P> `
  --discard <D> `
  --phase-step <PHI>
```

The script performs the conversion and corrected PSD calculation using only the Python standard library.

### Phase analysis at selected wavenumbers

After generating a PSD file, ask the user for wavenumbers they want to inspect. Run:

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\psd_phase_analysis.py' `
  --psd '<PSD file>' `
  --wavenumbers '1300,1450,1600,2350,3600'
```

The analysis reads the PSD file and its `.meta.json` sidecar. For each requested wavenumber it snaps to the nearest axis point and reports:

- `phi_max_deg`: phase where the signed PSD response is maximum
- `phase_lag_deg`: `(-phi_max) mod 360`
- `phase_equivalent_delay_s`: `phase_lag/360 × period_s / harmonic`
- `signed_phase_equivalent_delay_s`: wrapped to `[-T/(2k), +T/(2k)]`
- `phase_defined`: false for a flat/noisy curve with no reliable phase

Use distances in time only as phase-equivalent comparisons, not as kinetic time constants. The result depends on the phase origin and the `.meta.json` harmonic/period values.

### Output names

For the standard `120 / 15 / 10 / 10` choices with fixed harmonic 1 and origin 0:

```text
<sample>轨迹导出.dat
<sample>时间导出.dat
<sample>轨迹导出_t.dat
<sample>轨迹导出_10_periods_cutoff_averaged.txt
<sample>轨迹导出_10_periods_cutoff_averaged.txt.meta.json
<sample>轨迹导出_10_periods_cutoff_PSD_spectra_10_dphi.txt
<sample>轨迹导出_10_periods_cutoff_PSD_spectra_10_dphi.txt.meta.json
```

The discard count and phase step appear in the PSD output names. Keep the metadata sidecars with the corresponding TXT files.

### Calculation invariants

- Time companion is written as one numeric column.
- Period is inferred from `N × median(dt)` unless explicitly supplied.
- Only complete periods are used.
- Retained periods equal `periods - discard`.
- The time mean is removed from each spectral row before PSD.
- Phase count is `ceil(360 / phase_step)`.

### Troubleshooting

- If the time file has multiple columns, convert it to a single column first.
- If `--period` disagrees with the time grid, the script rejects the input.
- If the trace table has fewer columns than `periods × spectra_per_period + 1`, the script rejects it.
- Do not use the older GUI scripts for final results; the portable pipeline contains the corrected v4 calculation.

## Part 2 - Mass-spec (RGA) traces

The mass-spectrometry side is a Pfeiffer Vacuum PrismaPro RGA exported by PV MassSpec.
See `references/rga-dat-format.md` for the file layout, the column-name variants and
the interference table.

### Step 1: extract the time column and the m/z channels

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\extract_rga_ms.py' "D:\...\20261001-MS\*\*.dat"
```

Each `*.dat` becomes `<name>_extracted.txt` beside it: relative time plus every
recognised m/z channel, tab separated, peripheral and analog columns dropped. The
header row is found by content and the channels by name, so runs with a different
preamble length or channel set still work. Report back the channel list with each
mass before continuing.

### Step 2: put the runs on a common time base

Two operations, easily confused. Establish which one is wanted.

**Re-zero** keeps every row and subtracts a constant, so a chosen moment becomes
t = 0 and earlier points go negative:

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\shift_time.py' --offset 2200 table.txt
```

**Trim** drops the rows below a cutoff; the axis is not re-zeroed:

```powershell
python 'C:\path\to\mes-psd-pipeline\scripts\trim_by_time.py' --min-time 1800 table.txt
```

Both take one value for every file, a comma list matched to the input order, or
repeated `--shift` / `--cut` `FILE=SECONDS` pairs. **Ask the user for the values
and for which operation they want; do not infer either.** Cutting the first 2200
seconds and setting 2200 s to zero differ by one word and by 353 rows.

A common request is `-2200` on one run and a different value on another, because
each run started its gas sequence at a different wall-clock offset. Confirm the
per-file list before applying it.

Channel assignments and the interferences to watch are tabulated in
`references/rga-dat-format.md`. Resolve the N2 (m/z 28, CO overlaps) and N2O
(m/z 44, CO2 overlaps) ambiguities before using those channels
quantitatively, and treat a channel that sits at its detection floor as
below detection rather than as data.

### Verification

- Data rows equal the `<N> TimePoints` value in the `*.dat` preamble.
- Every row has the same column count as the header.
- After a shift the row count is unchanged and the new first/last timestamps equal
  the old ones minus the offset; after a trim every kept row is at or after the cutoff.
- Spot-check two or three rows against the source, comparing verbatim strings
  rather than parsed floats.

