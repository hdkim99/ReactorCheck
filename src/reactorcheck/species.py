"""Chemical formula parsing, molecular weights, and conservative name inference."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping

# IUPAC standard atomic weights (representative conventional values), sufficient
# for common catalytic gas-phase species. Explicit composition remains inspectable.
ATOMIC_WEIGHTS: Mapping[str, float] = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "F": 18.998403,
    "Na": 22.989769,
    "Mg": 24.305,
    "Al": 26.981538,
    "Si": 28.085,
    "P": 30.973762,
    "S": 32.06,
    "Cl": 35.45,
    "Ar": 39.948,
    "K": 39.0983,
    "Ca": 40.078,
    "Fe": 55.845,
    "Co": 58.933194,
    "Ni": 58.6934,
    "Cu": 63.546,
    "Zn": 65.38,
}

COMMON_SPECIES: Mapping[str, str] = {
    "H2": "H2",
    "O2": "O2",
    "N2": "N2",
    "CO": "CO",
    "CO2": "CO2",
    "CH4": "CH4",
    "C2H4": "C2H4",
    "C2H6": "C2H6",
    "CH3OH": "CH3OH",
    "H2O": "H2O",
    "NH3": "NH3",
    "NO": "NO",
    "NO2": "NO2",
    "N2O": "N2O",
    "AR": "Ar",
}


class FormulaError(ValueError):
    """Raised for an invalid or unsupported molecular formula."""


def parse_formula(formula: str) -> dict[str, int]:
    """Parse a neutral formula with nested parentheses into element counts.

    Hydrates, charges, isotopes, and fractional compositions are intentionally
    rejected rather than silently guessed.
    """
    if not formula or not re.fullmatch(r"[A-Za-z0-9()]+", formula):
        raise FormulaError(f"Invalid formula syntax: {formula!r}")
    tokens = re.findall(r"[A-Z][a-z]?|\d+|[()]", formula)
    if "".join(tokens) != formula:
        raise FormulaError(f"Could not fully parse formula: {formula!r}")
    stack: list[defaultdict[str, int]] = [defaultdict(int)]
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token == "(":
            stack.append(defaultdict(int))
        elif token == ")":
            if len(stack) == 1:
                raise FormulaError(f"Unmatched ')' in {formula!r}")
            group = stack.pop()
            multiplier = 1
            if index + 1 < len(tokens) and tokens[index + 1].isdigit():
                index += 1
                multiplier = int(tokens[index])
            for element, count in group.items():
                stack[-1][element] += count * multiplier
        elif token.isdigit():
            raise FormulaError(f"Unexpected coefficient in {formula!r}")
        else:
            if token not in ATOMIC_WEIGHTS:
                raise FormulaError(f"Unknown element {token!r} in {formula!r}")
            multiplier = 1
            if index + 1 < len(tokens) and tokens[index + 1].isdigit():
                index += 1
                multiplier = int(tokens[index])
            stack[-1][token] += multiplier
        index += 1
    if len(stack) != 1:
        raise FormulaError(f"Unmatched '(' in {formula!r}")
    return dict(stack[0])


def molecular_weight(composition: Mapping[str, int]) -> float:
    """Calculate molecular weight in g/mol from elemental composition."""
    return sum(ATOMIC_WEIGHTS[element] * count for element, count in composition.items())


def infer_species(column_name: str) -> tuple[str, str] | None:
    """Infer a common gas species only from complete column-name tokens."""
    tokens = {token.upper() for token in re.findall(r"[A-Za-z0-9]+", column_name)}
    matches = [(name, formula) for name, formula in COMMON_SPECIES.items() if name in tokens]
    if len(matches) == 1:
        return matches[0]
    return None
