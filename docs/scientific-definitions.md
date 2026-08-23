# Scientific definitions and assumptions

ReactorCheck never infers reaction stoichiometry or oxidation state. A user maps
measured outlet flows and explicit inlet flows; all species formulas are parsed
into elemental compositions. Internal molar-flow units are mol/h.

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
