# Dependency and license review

ReactorCheck uses MIT, BSD, or similarly permissive dependencies compatible with
the project's MIT license. Runtime metadata should be rechecked before every
release.

| Dependency | Purpose | Upstream license family |
|---|---|---|
| NumPy | array calculations | BSD-3-Clause |
| pandas | tabular IO/model | BSD-3-Clause |
| Pint | unit registry/conversion | BSD-3-Clause |
| Matplotlib | figures | PSF-based permissive license |
| openpyxl | XLSX read/write | MIT |
| Hatchling | package build backend | MIT |
| pytest | tests | MIT |
| Ruff | lint | MIT |
| mypy | static typing | MIT |

Tkinter is Python's standard binding to Tcl/Tk and is not bundled by this wheel.
No GPL-only runtime dependency is required. This file is an engineering review,
not legal advice.

