# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
versions follow semantic versioning.

## [0.2.1] - 2026-08-23

### Fixed

- Corrected the primary installation and publication-status documentation for
  the public PyPI package. There are no scientific API or calculation changes.

## [0.2.0] - 2026-08-23

### Added

- Explicit internal-standard reconstruction from mole fraction, percent, or ppm
  composition channels with hand-calculated scientific regressions.
- Independent raw/normalized treatment and wet/dry water-basis settings.
- GUI controls, CLI/config support, composition QC, and full reconstruction
  provenance for the mole-fraction workflow.
- PyPI Trusted Publishing release workflow with clean-wheel and GUI validation.

## [0.1.0] - 2026-08-23

### Added

- CSV/XLSX mapping, explicit species formulas, and Pint-backed unit validation.
- Conversion, two selectivity bases, yield consistency, element/mass recovery,
  product rate, STY, GHSV, and WHSV.
- Multi-variable steady-state candidates, manual override, structured QC,
  provenance-aware Excel/CSV export, figures, CLI, and connected Tk GUI.
- Hand-calculated scientific regressions and independent CI/package smoke checks.
