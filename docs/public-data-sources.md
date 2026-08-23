# Public real-data validation sources

This register distinguishes source data, publication licenses, redistribution
rights, and the level of validation actually performed. Public availability or
the ability to cite a paper does not by itself grant permission to redistribute
its dataset. Access dates below are in ISO format.

The source files are **not bundled** in ReactorCheck. The selected dataset
licenses permit redistribution with attribution, but keeping the original files
at their authoritative repositories avoids stale multi-megabyte copies and
preserves the record of record. The default test suite uses only minimal,
attributed regressions; it never downloads data.

## Dataset register

| Dataset ID | Project | Repository | Dataset DOI | Dataset license | Files used | Validation scope | Fixture included? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RC-PUB-001 | Swiss Cat+ East A1 high-throughput CO2 hydrogenation | Zenodo | [10.5281/zenodo.8314734](https://doi.org/10.5281/zenodo.8314734) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | `A1_G1_FBTesting_XDB4x_RawData.xlsx`; `A1_G1_FBData_XDB4x_mean.csv` | Raw GC/workbook IO and mapping; processed-flow mapping, API/CLI/GUI-controller/export; scientific-definition audit | Yes—inline headers and one measured row; original files no |
| RC-PUB-002 | Fixed-bed reverse water-gas shift experiment | Mendeley Data | [10.17632/sw7225g8xr.3](https://doi.org/10.17632/sw7225g8xr.3) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | `data_V2.csv` | Processed dry-composition delimiter and mapping validation; metadata/method comparison | Yes—inline header and two records; original file no |

## RC-PUB-001 — Swiss Cat+ fixed-bed reactor and online GC

**Dataset:** *Raw, processed and merged Data for Swiss Cat+ East A1 project
related to the automated and high-throughput Bayesian Optimization of CO2
hydrogenation heterogeneous catalysts*

- **Authors:** Adrian Ramirez; Erwin Lam; Daniel Pacheco; Yuhui Hou; Hermann
  Tribukait; Loïc Roch; Christophe Copéret; Paco Laveille.
- **Repository:** Zenodo record
  [8314734](https://zenodo.org/records/8314734).
- **Dataset DOI:** [10.5281/zenodo.8314734](https://doi.org/10.5281/zenodo.8314734).
- **Dataset license:** CC BY 4.0. It permits sharing and adaptation, including
  redistribution, provided attribution, a license link, and change indication
  are supplied. No third-party material was extracted into this repository.
- **Original publication:** Adrian Ramirez, Erwin Lam, Daniel Pacheco
  Gutierrez, Yuhui Hou, Hermann Tribukait, Loïc M. Roch, Christophe Copéret,
  and Paco Laveille. “Accelerated exploration of heterogeneous CO2
  hydrogenation catalysts by Bayesian-optimized high-throughput and automated
  experimentation.” *Chem Catalysis* 4(2), 100888 (2024).
  [10.1016/j.checat.2023.100888](https://doi.org/10.1016/j.checat.2023.100888).
- **Accessible method version:** ChemRxiv preprint
  [10.26434/chemrxiv-2023-kmd91](https://doi.org/10.26434/chemrxiv-2023-kmd91),
  CC BY-NC 4.0. This is a publication license, separate from the dataset's CC BY
  4.0 license.
- **Access date:** 2026-08-23.
- **Technique:** four parallel fixed-bed reactors, automated high-throughput
  CO2 hydrogenation, and online FID/TCD gas chromatography. The publication
  explicitly identifies helium as the internal standard; ReactorCheck still
  requires the user to confirm the nonreactive-standard assumption.

### Files inspected

`A1_G1_FBTesting_XDB4x_RawData.xlsx`

- **Size:** 150,533 bytes.
- **SHA-256:**
  `85726cbefbbaf808b2a2936b418f28bcb646d0c7e00cd4690a679f81c2f65d83`.
- **Zenodo MD5:** `1357edc21b44c337603f3bf79fcf1abe`.
- **Sheet:** `Run Data`.
- **Shape:** 125 rows × 175 columns.
- **Columns audited:** identifiers and time (`SampleTimeId`, `LocalTime`,
  `UtcTime`, `RunName`, `Reactor`, `Block`, `ElapsedRunTime`); reactor state
  (`Reactor_Gas_Flow_Nml_min`, inlet/outlet pressure, temperature PV/SP);
  GC provenance (`FID_F_FileName`, `FID_F_MethodName`,
  `FID_F_SampleDateTime`, `FID_F_SampleId`); detector-specific measurements
  including `FID_B_CO2_Conc`, `TCD_Aux_CO2_Conc`, `TCD_Aux_H2_Conc`,
  `TCD_Aux_He_Conc`, `TCD_Aux_N2_Conc`, `TCD_Aux_CO_Conc`,
  `FID_F_CH4_Conc`, and `FID_B_MeOH_Conc`; catalyst metadata including
  `R_MassLoaded`, `C_CatalystID`, `C_Support`, and `C_Metal`.
- **Observed variation:** the same species can occur on more than one detector
  (`FID_B_CO2_Conc` and `TCD_Aux_CO2_Conc`). ReactorCheck deliberately returns
  both as suggestions and does not select a detector. One row contains zero
  helium and therefore cannot support internal-standard reconstruction.
- **Processing performed:** read-only workbook inspection, sheet/shape/header
  validation, conservative mapping suggestions, and a one-row minimal
  regression retaining only cited measured values from `SampleTimeId=715`,
  `Reactor=1`, and `ElapsedRunTime=4.423007`. The original workbook was
  not changed or copied into the repository.
- **Validation level:** raw workbook IO and mapping are validated. Complete
  scientific reproduction of every catalyst result is not claimed because the
  detector choice and publication processing must be supplied explicitly.

`A1_G1_FBData_XDB4x_mean.csv`

- **Size:** 8,032 bytes.
- **SHA-256:**
  `92a93f9174b66a22faae53f92c6f996d595567cf056a0c2a7c8872e3a4d0a217`.
- **Zenodo MD5:** `7a6bdc57c72a8e11d93b0e1fe2e3f20b`.
- **Shape:** 16 rows × 39 columns.
- **Columns:** `Unit`, `Reactor`, `Temperature Set (°C)`, `Pressure Set
  (barg)`, `Block`, `Temperature (°C)`, `Pressure (barg)`, `Time on Stream
  (h)`, the `CO2`, `N2`, `He`, and `H2` inlet-flow columns, reconstructed
  `*_fr (ml/min)` columns for H2, He, N2, CO2, CO, CH4, MeOH, C2–C4
  hydrocarbons/alcohols, `Sumcarbon (%)`, `CO2 Conversion (%)`, and four
  published selectivity columns.
- **Processing performed:** read-only parsing and mapping audit; API, CLI, GUI
  controller, QC, and XLSX export exercise with the selected original flow
  columns. No source rows were normalized, smoothed, removed, or interpolated.
- **Validation level:** processed tabular data and runtime call paths. The
  resulting direct-disappearance conversion is **not** a reproduction of the
  published conversion definition; see “Scientific-definition boundary”.

### Scientific-definition boundary

The publication defines `Sumcarbon` from detected carbon-containing species and
defines CO2 conversion from the CO2 share of that carbon-normalized sum. It also
defines product selectivity on a carbon-number basis and calculates formation
rates using the measured helium standard. ReactorCheck's current conversion is
the explicit inlet/outlet disappearance definition
`(F_CO2,in - F_CO2,out) / F_CO2,in`. Applying that definition directly to the
published `*_fr` table produces materially different values and physical-range
QC warnings. This is a **scientific-definition difference**, not a value to
silently coerce or an excuse to replace the existing definition. The published
carbon-normalized workflow remains unsupported.

The processed rows are block/catalyst summaries. `Time on Stream (h)` is
retained, but those rows are not treated as one continuous time trace for
automatic steady-state detection. Detector selection, block grouping, and
publication-specific carbon normalization remain explicit external processing.

## RC-PUB-002 — processed fixed-bed rWGS table

**Dataset:** *Experimental Reverse Water-Gas Shift (rWGS) Reaction Dataset from
a Fixed-Bed Reactor*

- **Authors:** Enzo Komatz; Marion Andritz; Christoph Markowitsch.
- **Repository:** Mendeley Data
  [sw7225g8xr/3](https://data.mendeley.com/datasets/sw7225g8xr/3).
- **Dataset DOI:** [10.17632/sw7225g8xr.3](https://doi.org/10.17632/sw7225g8xr.3).
- **Dataset license:** CC BY 4.0. The repository states that sharing and
  modification are permitted with attribution, a license link, and an
  indication of changes. The original file is nevertheless not redistributed
  by ReactorCheck.
- **Original publication:** Enzo Komatz, Marion Andritz, and Christoph
  Markowitsch. “Experimental dataset of the reverse water-gas shift reaction in
  a fixed-bed reactor setup under varying reactor conditions.” *Data in Brief*
  65, 112485 (2026).
  [10.1016/j.dib.2026.112485](https://doi.org/10.1016/j.dib.2026.112485),
  CC BY-NC 4.0. The publication license is separate from the dataset license.
- **Method reference:** Enzo Komatz, *Development of automated software for
  analysis and simulation of the reverse water gas shift reaction* (Master's
  thesis, 2025).
  [10.34901/mul.pub.2025.108](https://doi.org/10.34901/mul.pub.2025.108).
- **Access date:** 2026-08-23.
- **Technique:** fixed-bed rWGS reactor with calibrated mass-flow controllers
  and an NDIR gas analyzer. This is real laboratory data but **not a GC export**;
  it was selected to test a real fixed-bed, dry-mol% tabular layout and CSV
  compatibility.

### File inspected

`data_V2.csv`

- **Size:** 31,698 bytes.
- **SHA-256:**
  `9700726a1146c812b8dbb63ab5d7e8cf4fcf55e480668a52fbe0287bac3077b2`.
- **Format:** semicolon-delimited CSV with CRLF records.
- **Shape after correct parsing:** 313 rows × 15 columns.
- **Columns:** `H2toCO2`, `GHSV`, `pset`, `Tout`, `Tset`,
  `GA_H2_corrected`, `GA_CH4_corrected`, `GA_CO_corrected`,
  `GA_CO2_corrected`, `u_GA_H2`, `u_GA_CH4`, `u_GA_CO`, `u_GA_CO2`,
  `XCO2`, and `SCO`.
- **Units from source metadata:** ratio dimensionless; GHSV in h^-1; pressure
  in bara; temperatures in °C; analyzer and uncertainty columns in dry mol%;
  conversion/selectivity in percent.
- **Processing performed:** read-only parsing, delimiter/header/shape audit,
  mapping audit, and a two-row regression retaining the public header and
  zero-based source data rows 0 and 1. No censored values, normalization, or recalculation
  was introduced.
- **Validation level:** processed/normalized supplementary table. Raw analyzer
  signals and the time series used to establish steady state are not present in
  this file.

This table contains independent steady-state operating points and no time
column. ReactorCheck does not synthesize timestamps or run time-series
steady-state detection on it. The source's `XCO2` and `SCO` remain published
metrics; uncertainty columns (`u_GA_*`) and derived conversion/selectivity
columns are not suggested as species measurements.

## Failure register

| Dataset ID | Real-data issue | Classification | Resolution | Regression |
| --- | --- | --- | --- | --- |
| RC-PUB-002 | Semicolon CSV was parsed as 313 × 1 under a comma-only parser | IO/parser bug | Conservative comma/semicolon/tab detection; multiple structurally valid delimiters fail explicitly | `test_public_semicolon_csv_is_read_as_fifteen_columns`; `test_ambiguous_csv_delimiter_fails_explicitly` |
| RC-PUB-001 / 002 | Published conversion/selectivity and `u_GA_*` uncertainty headers were suggested as measured species | Schema/mapping bug | Exclude only explicit derived/error tokens and the source's `u_` prefix; corrected flow/concentration columns remain candidates | `test_public_metric_and_uncertainty_columns_are_not_species_measurements` |
| RC-PUB-001 | `TCD_Aux_He_Conc` was not recognized, preventing an explicitly configured He-standard workflow | Schema/mapping bug | Add He formula/atomic weight and conservative complete-token recognition; user confirmation remains mandatory | `test_public_raw_gc_header_recognizes_helium_without_selecting_a_detector`; `test_public_raw_gc_row_supports_explicit_helium_reconstruction` |
| RC-PUB-001 | FID and TCD both expose CO2 measurements | User ambiguity, not a parser bug | Preserve both suggestions; require user detector mapping | Header regression verifies two CO2 candidates |
| RC-PUB-001 | Published carbon-normalized conversion differs from direct inlet/outlet disappearance | Scientific-definition difference / unsupported workflow | Document and expose QC; do not rewrite the core definition | Opt-in external validation records the numerical difference |
| RC-PUB-002 | Table has no timestamp or raw stabilization trace | Unsupported workflow | Do not fabricate time or claim steady-state detection | Documented boundary; no implementation added |

## Reproduce the external validation

Download the three exact source files from the repository records above. Then,
from an editable or installed ReactorCheck environment, run:

```bash
python scripts/validate_public_reactor_data.py \
  --swisscat-raw /path/to/A1_G1_FBTesting_XDB4x_RawData.xlsx \
  --swisscat-mean /path/to/A1_G1_FBData_XDB4x_mean.csv \
  --rwgs /path/to/data_V2.csv \
  --output-dir /path/to/new-empty-validation-output
```

The script verifies filename, size, and SHA-256 before reading anything. It
exercises raw/processed IO, conservative suggestions, API analysis, CLI
suggest/analyze, GUI-controller load/analyze, QC, and complete XLSX export. Its
`validation-report.json` records source identities, source shapes, no implicit
transformations/exclusions, QC codes, and the unresolved conversion-definition
difference. It does not download data and is not part of default `pytest`.

With a functional Tk display (or `xvfb-run`), the actual widget path can be
checked against the processed public file and generated configuration:

```bash
python tests/gui_widget_smoke.py \
  /path/to/A1_G1_FBData_XDB4x_mean.csv \
  /path/to/new-empty-validation-output/swisscat-mean-config.json \
  /path/to/new-empty-validation-output/swisscat-mean-tk-widget.xlsx \
  --conversion-column conversion_CO2_fraction \
  --expected-conversion -0.09004780446173652
```

## Assessed but not selected for this validation round

- **Zenodo 10.5281/zenodo.21884075**, *Dataset for: Dopant-Controlled Oxygen
  Vacancy Dynamics Define CO2-to-Methanol Catalysis on In2O3* (Becker et al.;
  CC BY 4.0; publication
  [10.1038/s41467-026-72876-w](https://doi.org/10.1038/s41467-026-72876-w)).
  `04_Figure_4_a_catalysis_operando.zip` is 6,132,151 bytes (SHA-256
  `bcadc5efc35229e1920c04500ca3325164137ff2c677b2487c2b392ba439810f`)
  and contains genuine Chromeleon hierarchical text reports, GC calibration
  RTF, and MS/QMS exports. These are not flat CSV/XLSX tables and therefore are
  a real but currently unsupported vendor-report workflow. No vendor adapter
  was added from a single dataset.
- Mendeley Data [10.17632/z5bypjm62y.1](https://doi.org/10.17632/z5bypjm62y.1)
  contains real raw GC data for liquid-batch reductive amination, outside the
  catalytic flow-reactor scope selected here.
- Mendeley Data [10.17632/3rd2hm4zrw.1](https://doi.org/10.17632/3rd2hm4zrw.1)
  concerns trickle-bed styrene experiments but exposes primarily PDF GC
  reports rather than a reproducible flat feed/outlet table.
- Dryad [10.25349/D9ZG6B](https://doi.org/10.25349/D9ZG6B) includes genuine
  GC-FID/TCD data with an argon standard, but the underlying experiment is
  batch polyethylene upcycling rather than the declared flow-reactor workflow.
- Figshare/ACS supplementary candidates dominated figure images, PDF-only
  summaries, HPLC/electrochemical data, or simulation output; NIST candidates
  were compiled kinetics rather than source laboratory exports. Harvard
  Dataverse and OSF searches did not yield a better licensed raw
  reactor-plus-GC table for this round. These were excluded rather than being
  mislabeled as raw-file validation.
