# Interchange and provenance

ReactorCheck is independent software; it does not currently import Ordifile or
OperandoMerge internal APIs. Its stable v0.1 interchange is transparent tabular
data plus JSON settings:

- `experiment_time_s`: canonical elapsed time while the original time remains.
- `flow_in_<species>_mol_h`, `flow_out_<species>_mol_h`: normalized flows.
- calculated columns include metric, species/basis, and unit in their names.
- `provenance` records source file, source column/unit, formula, inlet source, and
  standard-state settings.
- `settings.json` or the Excel `settings` sheet records the complete calculation
  configuration and selected steady-state intervals.

Future interoperability should version a public schema rather than introduce a
shared private Python package.

