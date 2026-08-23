# Contributing

Install `.[dev]`, create a focused branch, and run `ruff check .`, `mypy src`,
`pytest`, and `python -m build` before opening a pull request. Keep scientific
equations in the core, never in GUI callbacks. New equations require a definition,
units, assumptions, a hand-calculated or synthetic regression case, and physical
edge cases. Do not weaken assertions to conceal a scientific disagreement; record
whether the cause is implementation, test, definition, unit, model, or environment.

Use small Conventional Commit-style changes such as `feat:`, `fix:`, `test:`, and
`docs:`. Synthetic data must be redistributable. Never commit private experimental
data, credentials, or personally identifying metadata.

After changing the public composition example, run
`python scripts/generate_example_assets.py` and inspect both PNG files before
committing the regenerated XLSX/visual assets.
