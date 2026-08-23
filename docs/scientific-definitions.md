# Scientific definitions and assumptions

ReactorCheck never infers reaction stoichiometry or oxidation state. A user maps
measured outlet flows and explicit inlet flows; all species formulas are parsed
into elemental compositions. Internal molar-flow units are mol/h.

## Internal-standard composition reconstruction

The composition workflow requires a user-selected species `std`, its feed flow,
an explicit boolean confirmation that it is nonreactive, and a written assumption
that `F_std,out = F_std,in`. ReactorCheck never selects N2, Ar, or another species
automatically. With measured outlet mole fractions:

`F_i,out = (y_i,out / y_std,out) F_std,in`.

`fraction`, percent/`mol%`, and `ppm`/`ppmv` inputs are first converted to mole
fraction. Missing, non-finite, zero, or negative standard fraction prevents the
division and stops analysis. A nonpositive or dimensionally incompatible standard
feed also stops analysis.

Composition treatment and water basis are deliberately independent:

- `normalization = raw_measured` uses converted fractions as measured.
- `normalization = normalized` divides every mapped fraction by the row's raw
  mapped sum. Raw and used values are both retained.
- `water_basis = wet` means H2O participates in the composition denominator and
  therefore requires an explicitly mapped H2O channel.
- `water_basis = dry` means H2O was excluded from the reported denominator. H2O
  must not be mapped because a dry composition cannot reconstruct its flow.

A flat `composition.basis` value is rejected because it cannot represent valid
combinations such as wet+raw or dry+normalized. Global normalization leaves every
`y_i/y_std` ratio unchanged; synthetic regression tests verify this invariance.
The raw mapped sum is nevertheless checked against the configured tolerance and
reported as QC, because a poor sum can reveal missing channels or unit mistakes.

For reference reactant `R` and product `P`:

- Conversion: `X_R = (F_R,in - F_R,out) / F_R,in`.
- Net product formation: `ΔF_P = F_P,out - F_P,in`.
- Molar selectivity: `S_P,mol = ΔF_P / (F_R,in - F_R,out)`.
- Carbon selectivity: `S_P,C = n_C,P ΔF_P / [n_C,R (F_R,in - F_R,out)]`.
- Direct molar yield: `Y_P = ΔF_P / F_R,in`.
- Identity check: `Y_P = X_R S_P,mol` under these same definitions.
- Element recovery: `100 Σ_i(n_E,i F_i,out) / Σ_i(n_E,i F_i,in)` percent.
- Measured-species mass recovery: `100 Σ_i(MW_i F_i,out) / Σ_i(MW_i F_i,in)` percent.
- Product rate: `r_P = ΔF_P / m_cat`, reported in equivalent columns as
  mol gcat^-1 h^-1, mmol gcat^-1 h^-1, and mol kgcat^-1 s^-1.
- Mass STY: `STY_P = ΔF_P MW_P / m_cat`, reported as gproduct gcat^-1 h^-1.
- GHSV: standard volumetric feed rate / configured reactor volume, h^-1.
- WHSV: total feed mass rate / catalyst mass, h^-1.

The measured mass and element recoveries cover only mapped species. Values below
100% may identify measurement closure problems or simply omitted species; QC
cannot distinguish those cases without more experimental information.

## Standard gas volume

Molar and volume flow are different dimensions. Conversion of standard volume
flow uses `n_dot = P_std V_dot / (R T_std)` with the exact configured standard
temperature and pressure. Defaults are 273.15 K and 1 atm. This is an ideal-gas
assumption; change the flow to a molar unit upstream when a real-gas correction
is required. `sccm` is treated as cm^3/min at that explicit standard state.

## Steady-state detector

For every trailing window and every selected variable, the detector fits a
first-order least-squares slope. It requires both
`|slope| × window_time_span / scale <= slope_tolerance` and
`sample_standard_deviation / scale <= variation_tolerance`, where `scale` is the
maximum of absolute mean, peak-to-peak range, and floating-point epsilon. All
variables must pass. Windows containing missing or non-increasing time fail.

The automatic mask is a candidate, not proof of thermodynamic steady state. A
manual inclusive time range can replace it and is stored in exported settings.

## QC interpretation

QC issues are not silently used to alter calculations. Errors and warnings cover
missing/duplicate input, negative measurements, robust-MAD outliers, physical
conversion bounds, carbon-selectivity closure, element balance deviation, and
non-steady rows. A calculation with QC issues remains inspectable and exportable.

For composition data, physically invalid negative fractions and invalid standard
fractions stop reconstruction. Raw sum deviation and any converted fraction above
unity are recorded separately from reaction-metric QC. Normalization never erases
the raw sum or the original columns.

## Multi-reactant scope

Version 0.2 retains one explicit `reference_reactant`. Combined multi-reactant
conversion/selectivity denominators require user-declared stoichiometric bases
and are planned. ReactorCheck does not sum reactant consumption or infer reaction
coefficients automatically.
