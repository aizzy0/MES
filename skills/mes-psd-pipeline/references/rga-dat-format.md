# Pfeiffer PV MassSpec RGA export format

Notes on the `*.dat` files produced by PV MassSpec for a Pfeiffer Vacuum PrismaPro
RGA, and on turning them into a plottable table.

## File layout

The file is text, tab-delimited in the data section, and consists of three parts.

**1. Title lines** - a handful of fixed lines:

```
PV MassSpec-20.08.01
EXPORTED BIN DATA
```

**2. Metadata preamble** - a few hundred lines of `Key<TAB>Value` pairs under
headings such as `Run Path and Name`, `Sensor`, `Hardware Parameters`,
`Ionizer and Detector`, `External I/O`, and acquisition settings. Useful entries:

| Key | Meaning |
|---|---|
| `Run Path and Name` | original `.isi` path, and the acquisition timestamp |
| `Sensor` | instrument model and serial, e.g. `RGA PrismaPro 100 44528567` |
| `Emission (uA)`, `Electron energy (eV)` | ion source settings |
| `Multiplier (V)` | detector setting |
| `Start Time (at the acquisition location)` | wall-clock start |
| `Stop Mode` | e.g. `Time (s)` |
| `<N> TimePoints` | number of rows in the data table |
| `<N> Bins` | number of scanned channels |

**The preamble length is not fixed.** It depends on which subsystems were
configured for that acquisition, so never address the data table by line number.
Scan for the header line instead.

**3. Data table** - one header row, then one row per time point.

## The data-table header

The first column is the relative time; the rest are the recorded channels and a
block of peripheral digital I/O. A representative field list:

```
Time Relative (sec)
Time Absolute (UTC)
Time Absolute (Date_Time)
Step
Ionizer_State
Pressure_(mBar)
External_Pressure_(mBar)
17_amu  18_amu  28_amu  30_amu  32_amu  44_amu  46_amu
Periph:_Digital_In_0  ...  Periph:_Digital_Out_11
```

Column-name variants to accept when locating the m/z channels:

| spelling | example |
|---|---|
| `<mass>_amu` | `17_amu` |
| `<mass>amu` | `17amu` |
| `amu<mass>` | `amu17` |
| `m/z <mass>` | `m/z 17` |
| `mass <mass>` | `mass 17` |

Locate the header by searching for a tab-containing line that has a column
matching `time ... relative` (case-insensitive). Locate the m/z columns by name,
never by index, so that a run with a different channel set still works.

## Extraction rules

- Emit the relative-time column first, then every recognised m/z channel.
- Preserve the numeric strings verbatim. The channels are in scientific
  notation and rewriting them through a float round-trip loses digits.
- Drop the peripheral / analog columns; they are status flags, not data.
- Skip blank lines and any row whose field count is below the header width.
- Check the row count against the `<N> TimePoints` value in the preamble.

## m/z assignments and interferences

Electron-impact ionisation at 70 eV fragments molecules, so a channel is rarely
one species. For NH3-SCO the usual channels are:

| m/z | usual assignment | interference to watch |
|---|---|---|
| 15 | NH3 fragment (NH) | CH3 from hydrocarbons |
| 16 | NH3 fragment (NH2) | O, CH4 |
| 17 | NH3 molecular ion | OH from water - the two are not separable here |
| 18 | H2O | |
| 28 | N2 | CO - **the two are indistinguishable on this RGA** |
| 30 | NO | N2O fragments to NO, so 30 also tracks N2O |
| 32 | O2 | |
| 44 | N2O | CO2 - **check against m/z 12 or 22 before assigning** |
| 46 | NO2 | |

Consequences for reporting:

- **N2 selectivity cannot be taken from m/z 28 alone.** CO from incomplete
  combustion sits on the same channel. Either trace m/z 12 as a CO proxy or
  state the assumption explicitly.
- **N2O cannot be taken from m/z 44 alone.** CO2 sits there too. A carbon-free
  feed makes CO2 unlikely but not impossible; a blank or a carbon balance
  settles it. m/z 30 corroborates N2O but is shared with NO.
- **Water is usually in large excess** relative to the N-containing products, so
  m/z 18 saturates or carries a large background quickly. Check whether the
  channel clipped before using its shape.

## Verification checklist

Before reporting success:

- The header line was located by content, not by a hard-coded line number.
- Every m/z channel found is listed back to the user with its mass.
- Data rows exported equals the `<N> TimePoints` value in the preamble.
- Every row has the same column count as the header.
- Spot-check two or three rows against the source, comparing the selected
  columns verbatim (not as parsed floats).
- The relative-time column increases monotonically.

## Worked example

The CHA NH3-O2 / O2-NH3 export set used during development had a 371-line
preamble, so the header sat on line 372, and carried 7 m/z channels
(17, 18, 28, 30, 32, 44, 46) among 31 columns. Data rows ranged from 1083 to
1286 across the eight runs. Extracting all eight and comparing every cell back
to the source gave 9286 rows with zero mismatches.
