# Contributing

Thank you for helping make catalytic-reactor calculations more transparent and
reproducible.

## Before opening an issue

- Search existing issues and choose the dataset-compatibility or scientific-result
  form when applicable.
- Never upload unpublished, confidential, proprietary, licensed, or identifying
  research data to a public issue. Share a minimal synthetic reproducer or sanitized
  headers/schema instead.
- Do not include credentials, internal paths, instrument serial numbers, or private
  sample names.

## Development checks

Install `.[dev]`, create a focused branch, and run:

```bash
ruff format --check .
ruff check .
mypy src
pytest
python -m build
```

## Scientific changes

Keep equations in the core, never in GUI callbacks. A change to conversion,
selectivity, yield, rate, STY, GHSV/WHSV, unit conversion, flow reconstruction, or
mass/element balance must state:

- the scientific definition and equation;
- input/output units, basis, assumptions, and physical bounds;
- a primary reference or DOI when relevant;
- whether existing numerical results change and why; and
- a hand-calculated, synthetic, or legally usable regression case covering invalid
  as well as normal inputs.

`pytest` passing alone does not establish scientific correctness. Do not weaken an
assertion to conceal a disagreement; classify the cause as implementation, test,
definition, unit, data model, or environment.

Use small Conventional Commit-style changes such as `feat:`, `fix:`, `test:`, and
`docs:`. Synthetic data must be redistributable, and public-data-derived fixtures must
identify their source, license, and reduction method.

After changing the public composition example, run
`python scripts/generate_example_assets.py` and inspect both PNG files before
committing the regenerated XLSX/visual assets.

## Self-hosted CI safety

The required CI job runs on the persistent `dgx-spark` self-hosted runner.
Pushes and manual dispatches may use that runner. Pull requests run there only when
the current repository owner opens them from a same-repository branch. Fork and
bot-authored pull-request jobs are deliberately skipped so unreviewed code or dependency
updates cannot execute on research hardware. Maintainers must review those changes before
reproducing them in an owner-authored same-repository branch.
