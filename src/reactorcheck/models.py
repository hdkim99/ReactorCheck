"""Serializable domain models shared by API, CLI, GUI, and exporters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

import pandas as pd

from reactorcheck.species import molecular_weight, parse_formula

Role = Literal["reactant", "product", "inert"]
Severity = Literal["info", "warning", "error"]
CompositionTreatment = Literal["raw_measured", "normalized"]
WaterBasis = Literal["wet", "dry"]


@dataclass(frozen=True)
class Species:
    """A chemical species with explicit, validated elemental composition."""

    name: str
    formula: str
    composition: dict[str, int] = field(init=False)
    molecular_weight_g_mol: float = field(init=False)
    carbon_number: int = field(init=False)

    def __post_init__(self) -> None:
        composition = parse_formula(self.formula)
        object.__setattr__(self, "composition", composition)
        object.__setattr__(self, "molecular_weight_g_mol", molecular_weight(composition))
        object.__setattr__(self, "carbon_number", composition.get("C", 0))


@dataclass(frozen=True)
class ChannelMapping:
    """Map an outlet flow/composition column and an optional inlet flow."""

    column: str
    species: Species
    role: Role
    unit: str
    inlet: str | None = None
    inlet_column: str | None = None
    inlet_unit: str | None = None

    def __post_init__(self) -> None:
        if self.role not in {"reactant", "product", "inert"}:
            raise ValueError(f"Invalid channel role: {self.role!r}")
        if self.inlet is not None and self.inlet_column is not None:
            raise ValueError("Set only one of inlet or inlet_column")
        if self.inlet_column is not None and self.inlet_unit is None:
            raise ValueError("inlet_unit is required with inlet_column")


@dataclass(frozen=True)
class SteadyStateSettings:
    """Multi-variable rolling steady-state criteria."""

    variables: tuple[str, ...] = ()
    minimum_window: int = 5
    slope_tolerance: float = 0.02
    variation_tolerance: float = 0.02
    manual_start: float | None = None
    manual_end: float | None = None


@dataclass(frozen=True)
class CompositionSettings:
    """Explicit internal-standard reconstruction configuration.

    ``confirmed_nonreactive`` and ``assumption`` deliberately force the user to
    own the scientific assumption F_std,out = F_std,in. ReactorCheck never
    selects or declares a standard inert on the user's behalf.
    """

    normalization: CompositionTreatment
    water_basis: WaterBasis
    internal_standard: str
    internal_standard_feed: str
    confirmed_nonreactive: bool
    assumption: str
    sum_tolerance_fraction: float = 0.02

    def __post_init__(self) -> None:
        if self.normalization not in {"raw_measured", "normalized"}:
            raise ValueError(f"Invalid composition normalization: {self.normalization!r}")
        if self.water_basis not in {"wet", "dry"}:
            raise ValueError(f"Invalid water basis: {self.water_basis!r}")
        if not self.confirmed_nonreactive:
            raise ValueError(
                "Internal-standard reconstruction requires explicit nonreactive confirmation"
            )
        if not self.assumption.strip():
            raise ValueError("A written internal-standard assumption is required")
        if self.sum_tolerance_fraction < 0 or self.sum_tolerance_fraction >= 1:
            raise ValueError("Composition sum tolerance must lie in [0, 1)")


@dataclass(frozen=True)
class AnalysisConfig:
    """Complete reproducible analysis configuration."""

    time_column: str
    time_unit: str
    channels: tuple[ChannelMapping, ...]
    reference_reactant: str
    catalyst_mass: str
    standard_temperature: str = "273.15 K"
    standard_pressure: str = "1 atm"
    reactor_volume: str | None = None
    volumetric_feed: str | None = None
    mass_feed: str | None = None
    sty_product: str | None = None
    composition: CompositionSettings | None = None
    steady_state: SteadyStateSettings = field(default_factory=SteadyStateSettings)
    balance_tolerance_percent: float = 5.0
    physical_tolerance: float = 1e-9

    def __post_init__(self) -> None:
        names = [mapping.species.name for mapping in self.channels]
        if len(names) != len(set(names)):
            raise ValueError("Each species may be mapped only once")
        if self.reference_reactant not in names:
            raise ValueError("reference_reactant is not mapped")
        if not any(
            item.species.name == self.reference_reactant and item.role == "reactant"
            for item in self.channels
        ):
            raise ValueError("reference_reactant must have role 'reactant'")
        if self.composition is not None:
            standard = next(
                (
                    item
                    for item in self.channels
                    if item.species.name == self.composition.internal_standard
                ),
                None,
            )
            if standard is None:
                raise ValueError("Configured internal standard is not mapped")
            if standard.role != "inert":
                raise ValueError("Internal standard must have role 'inert'")
            if standard.inlet is not None or standard.inlet_column is not None:
                raise ValueError(
                    "Internal-standard inlet is defined only by internal_standard_feed"
                )
            water_mapped = any(item.species.formula == "H2O" for item in self.channels)
            if self.composition.water_basis == "wet" and not water_mapped:
                raise ValueError("Wet-basis composition requires an explicitly mapped H2O channel")
            if self.composition.water_basis == "dry" and water_mapped:
                raise ValueError(
                    "Dry-basis composition excludes H2O; remove the H2O composition mapping"
                )


@dataclass(frozen=True)
class QCIssue:
    """A machine-readable quality-control observation."""

    code: str
    severity: Severity
    message: str
    rows: tuple[int, ...] = ()
    value: float | None = None


@dataclass
class AnalysisResult:
    """Outputs of one analysis, with settings and source provenance."""

    processed: pd.DataFrame
    summary: pd.DataFrame
    qc_issues: list[QCIssue]
    settings: dict[str, Any]
    provenance: pd.DataFrame

    def qc_frame(self) -> pd.DataFrame:
        """Return QC issues as an exportable table."""
        return pd.DataFrame([asdict(issue) for issue in self.qc_issues])
