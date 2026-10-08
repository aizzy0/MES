# MES PSD workflow

## Inputs

- Source trace table from OPUS, normally a `.dpt` with comma-separated fixed decimals.
- One-column time export in seconds. If only a trace DPT is available, its first column can be used as the time source.
- Generic sample name without version dots, for example `CHA O2-NH3`, `CHA NH3-O2`, or `Pt NH3-O2`.

## Step 1: collect PSD parameters

Before executing the pipeline, ask the user to select or confirm the user-selectable parameters. Harmonic is fixed to 1 and time origin is fixed to 0.

| Parameter | CLI option | Suggested value |
|---|---|---:|
| Spectra per complete period | `--n-spectra` | 120 |
| Total periods including discarded | `--periods` | 15 |
| Discarded first periods | `--discard` | 10 |
| Phase step / degrees | `--phase-step` | 10 |
| Period / s | `--period` | blank = infer |

Do not run the pipeline until the user has answered.

## Step 2: run the portable pipeline

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

## Phase analysis at selected wavenumbers

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

## Output names

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

## Calculation invariants

- Time companion is written as one numeric column.
- Period is inferred from `N × median(dt)` unless explicitly supplied.
- Only complete periods are used.
- Retained periods equal `periods - discard`.
- The time mean is removed from each spectral row before PSD.
- Phase count is `ceil(360 / phase_step)`.

## Troubleshooting

- If the time file has multiple columns, convert it to a single column first.
- If `--period` disagrees with the time grid, the script rejects the input.
- If the trace table has fewer columns than `periods × spectra_per_period + 1`, the script rejects it.
- Do not use the older GUI scripts for final results; the portable pipeline contains the corrected v4 calculation.
