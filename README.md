# MES

## English

### MES PSD Pipeline

Process modulation-excitation spectroscopy from Bruker OPUS exports. This skill requires:

- an OPUS **Data Point Table** (`*.dpt`) containing the spectral matrix;
- an OPUS **trace data** export (`*Trace*.DPT`) containing the trace/time information. The first column supplies the time axis.

The skill converts these inputs to generic ASCII DAT files, builds a one-column time companion, and runs corrected PSD v4 analysis. It is suitable for samples such as `CHA NH3-O2`, `CHA O2-NH3`, and `Pt NH3-O2`.

### Required inputs

1. OPUS Data Point Table (`*.dpt`)
2. OPUS trace export (`*Trace*.DPT`)
3. Optional separate one-column time export (`<sample>时间导出.dat`)

Generic output names must not contain version dots. For example, use `CHA NH3-O2`, not `CHA NH3-O2.0`.

### Processing workflow

1. Convert the Data Point Table to TAB-separated ASCII `<sample>轨迹导出.dat`.
2. Copy or create the one-column time file `<sample>时间导出.dat`.
3. Create the time companion `<sample>轨迹导出_t.dat` as an `N x 1` numeric column.
4. Run corrected PSD v4 with the selected parameters.
5. Write averaged and PSD TXT files plus metadata sidecars.

### Portable execution

The pipeline uses only the Python standard library. It does not require `numpy`, `pandas`, `scipy`, or any local custom Python program.

```powershell
python 'skills/mes-psd-pipeline/scripts/mes_pipeline.py' `
  --trace-source '<Data Point Table .dpt>' `
  --time-source '<one-column time export>' `
  --sample '<sample>' `
  --outdir '<output directory>' `
  --n-spectra <N> `
  --periods <P> `
  --discard <D> `
  --phase-step <PHI>
```

The user must select or confirm these parameters before execution:

- `--n-spectra`: number of spectra per complete period
- `--periods`: total periods including discarded periods
- `--discard`: number of first periods to discard
- `--phase-step`: phase step in degrees
- `--period`: optional period in seconds; blank means infer as `N x median(dt)`

Fixed parameters:

- `harmonic = 1`
- `origin = 0`

### Outputs

```text
<sample>轨迹导出.dat
<sample>时间导出.dat
<sample>轨迹导出_t.dat
<sample>轨迹导出_<discard>_periods_cutoff_averaged.txt
<sample>轨迹导出_<discard>_periods_cutoff_averaged.txt.meta.json
<sample>轨迹导出_<discard>_periods_cutoff_PSD_spectra_<phase-step>_dphi.txt
<sample>轨迹导出_<discard>_periods_cutoff_PSD_spectra_<phase-step>_dphi.txt.meta.json
```

### Verification

- Trace output is TAB-separated ASCII and contains no non-ASCII bytes.
- Time companion contains exactly one numeric column.
- Averaged output has `1 + N` columns.
- PSD output has `1 + ceil(360 / phase_step)` columns.
- Metadata records periods, discarded periods, spectra per period, phase step, harmonic, and origin.
- `period_s` is inferred or agrees with `N x median(dt)`.

## Selected-wavenumber phase analysis

After generating a PSD file, provide the wavenumbers to inspect. The phase-analysis script snaps each value to the nearest PSD axis point and reports:

- `phi_max_deg`
- `phase_lag_deg`
- `phase_equivalent_delay_s`
- `signed_phase_equivalent_delay_s`
- `phase_defined`

```powershell
python 'skills/mes-psd-pipeline/scripts/psd_phase_analysis.py' `
  --psd '<PSD spectra TXT>' `
  --wavenumbers '1300,1450,1600,2350,3600'
```

`phase_equivalent_delay_s` is a phase-to-time conversion, not a kinetic time constant.

## Mass-spec (RGA) channel extraction

The same experiment also produces a Pfeiffer Vacuum PrismaPro RGA exported by
PV MassSpec. Each `*.dat` opens with a metadata preamble of a few hundred lines,
then a tab-separated table whose header begins `Time Relative (sec)` and
continues with the recorded channels (`17_amu`, `18_amu`, ...).

`extract_rga_ms.py` reduces each export to the columns that matter and writes
`<name>_extracted.txt` beside it: relative time plus every recognised m/z channel.

```powershell
python 'skills/mes-psd-pipeline/scripts/extract_rga_ms.py' "D:\...\20261001-MS\*\*.dat"
```

The header row is found by content and the m/z columns by name, so different
preamble lengths and column spellings (`17_amu`, `amu17`, `m/z 17`) all work.
Standard library only.

### Aligning the time axis

Two operations that are easy to confuse, and they do opposite things:

| Script | Effect | Output |
|---|---|---|
| `shift_time.py --offset <sec>` | re-zeroes the axis: keeps every row and subtracts a constant, so a chosen moment becomes t = 0 (earlier points go negative) | `<name>_t0.txt` |
| `trim_by_time.py --min-time <sec>` | drops the rows below a cutoff; the axis is **not** re-zeroed | `<name>_cut.txt` |

Both accept one value for every file, a comma list matched to the input order, or
repeated `--shift` / `--cut` `FILE=SECONDS` pairs.

Confirm which operation is wanted before running either: "cut the first 2200
seconds" deletes rows, while "set 2200 s to zero" deletes none.

Channel assignments and the interferences to watch are tabulated in
`skills/mes-psd-pipeline/references/rga-dat-format.md`.


---

## 中文

### MES 调制激发光谱 PSD 处理

用于处理 Bruker OPUS 导出的调制激发光谱数据。该 skill 需要：

- OPUS 导出的 **Data Point Table**（`*.dpt`），提供完整光谱矩阵；
- OPUS 导出的 **trace 数据**（`*Trace*.DPT`），提供 trace 信息，其第一列用于时间轴。

该 skill 会将输入转换为通用 ASCII DAT 文件，生成一列时间伴生文件，并执行修正后的 PSD v4 计算。适用于 `CHA NH3-O2`、`CHA O2-NH3`、`Pt NH3-O2` 等样品。

### 需要的输入

1. OPUS Data Point Table（`*.dpt`）
2. OPUS trace 导出文件（`*Trace*.DPT`）
3. 可选：独立的一列时间导出文件（`<样品名>时间导出.dat`）

输出的通用样品名中不能带版本点号。例如应使用 `CHA NH3-O2`，不能使用 `CHA NH3-O2.0`。

### 处理流程

1. 将 Data Point Table 转换为 TAB 分隔的 ASCII 文件 `<样品名>轨迹导出.dat`。
2. 生成或复制一列时间文件 `<样品名>时间导出.dat`。
3. 生成 `N x 1` 的时间伴生文件 `<样品名>轨迹导出_t.dat`。
4. 按用户选择的参数执行修正后的 PSD v4 计算。
5. 保存 averaged、PSD 结果及对应的 metadata 文件。

### 可移植运行

该流程只依赖 Python 标准库，不需要 `numpy`、`pandas`、`scipy`，也不依赖本地自定义 Python 程序。

```powershell
python 'skills/mes-psd-pipeline/scripts/mes_pipeline.py' `
  --trace-source '<Data Point Table .dpt>' `
  --time-source '<一列时间导出文件>' `
  --sample '<通用样品名>' `
  --outdir '<输出目录>' `
  --n-spectra <每周期谱图数> `
  --periods <总周期数> `
  --discard <需删除的前若干个周期> `
  --phase-step <相分辨率>
```

执行前必须先让用户选择或确认：

- `--n-spectra`：每个完整周期的谱图数
- `--periods`：总周期数，包含需要删除的周期
- `--discard`：需要删除的前若干周期数
- `--phase-step`：相分辨率（度）
- `--period`：可选周期长度（秒），留空则按 `N x median(dt)` 推断

固定参数：

- `harmonic = 1`
- `origin = 0`

### 输出文件

```text
<样品名>轨迹导出.dat
<样品名>时间导出.dat
<样品名>轨迹导出_t.dat
<样品名>轨迹导出_<discard>_periods_cutoff_averaged.txt
<样品名>轨迹导出_<discard>_periods_cutoff_averaged.txt.meta.json
<样品名>轨迹导出_<discard>_periods_cutoff_PSD_spectra_<phase-step>_dphi.txt
<样品名>轨迹导出_<discard>_periods_cutoff_PSD_spectra_<phase-step>_dphi.txt.meta.json
```

### 校验要求

- 轨迹导出文件为 TAB 分隔的纯 ASCII 文件。
- 时间伴生文件只有一列数值。
- averaged 输出列数为 `1 + N`。
- PSD 输出列数为 `1 + ceil(360 / phase_step)`。
- metadata 中记录总周期数、删除周期数、每周期谱图数、相分辨率、谐波和时间原点。
- `period_s` 通过数据推断，或与 `N x median(dt)` 一致。

### 选定波数的相位分析

生成 PSD 文件后，可以直接输入需要分析的波数。脚本会自动匹配最近的波数点，并输出：

- `phi_max_deg`：最大相位
- `phase_lag_deg`：相位滞后
- `phase_equivalent_delay_s`：相位等效延迟
- `signed_phase_equivalent_delay_s`：带符号的等效延迟
- `phase_defined`：该波数是否可以可靠定义相位

```powershell
python 'skills/mes-psd-pipeline/scripts/psd_phase_analysis.py' `
  --psd '<PSD光谱TXT>' `
  --wavenumbers '1300,1450,1600,2350,3600'
```

`phase_equivalent_delay_s` 只是相位到时间的换算，不是动力学时间常数。

### 质谱（RGA）通道提取

同一次实验还有质谱数据，来自 Pfeiffer Vacuum PrismaPro，由 PV MassSpec 导出。每个 `*.dat`
开头是几百行元数据，随后是 TAB 分隔的数据表，表头以 `Time Relative (sec)` 开始，
后面是记录的通道（`17_amu`、`18_amu`……）。

`extract_rga_ms.py` 把这些导出精简成需要的列，在源文件旁生成
`<名称>_extracted.txt`：相对时间 + 全部识别到的 m/z 通道。

```powershell
python 'skills/mes-psd-pipeline/scripts/extract_rga_ms.py' "D:\...\20261001-MS\*\*.dat"
```

表头按内容定位、m/z 列按列名识别，所以元数据长度不同、列名写法不同
（`17_amu`、`amu17`、`m/z 17`）都能处理。只用 Python 标准库。

### 时间轴对齐

两个容易混淆、效果相反的操作：

| 脚本 | 效果 | 输出 |
|---|---|---|
| `shift_time.py --offset <秒>` | **时间归零**：保留全部行，减去常数，使某个时刻成为 t = 0（更早的点变为负值） | `<名称>_t0.txt` |
| `trim_by_time.py --min-time <秒>` | **裁掉起始段**：删除切点之前的行，时间轴**不**归零 | `<名称>_cut.txt` |

两者都支持：所有文件用同一数值、按输入顺序逗号分隔逐文件给值，或重复使用
`--shift` / `--cut` 的 `文件=秒数` 形式。

执行前请确认到底要哪一种：**"剪掉前 2200 秒"会删掉数据行，而"把 2200 秒设为 0"一行都不删。**

通道归属与需要注意的干扰列在
`skills/mes-psd-pipeline/references/rga-dat-format.md`。
