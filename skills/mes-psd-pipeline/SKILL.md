---
name: mes-psd-pipeline
description: Process modulation-excitation spectroscopy from Bruker OPUS exports. Requires an OPUS Data Point Table (*.dpt) and trace data (*Trace*.DPT); converts them to generic ASCII DAT files, builds a one-column time companion, runs corrected PSD v4 analysis, and extracts phi_max, phase lag, and phase-equivalent delay at user-selected wavenumbers. Use for samples such as CHA NH3-O2, CHA O2-NH3, or Pt NH3-O2.
---

# MES PSD Pipeline

Use this skill for modulation-excitation spectroscopy processing after OPUS has exported the required data. The skill converts the OPUS exports to portable ASCII files, prepares the time axis, and performs corrected PSD v4 analysis.

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
