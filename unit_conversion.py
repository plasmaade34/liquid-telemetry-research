"""
Engineering unit conversion via canonical SI-base normalization.

Architecture: every unit is defined by (dimensions, scale, offset) relative
to its SI base unit. Converting A -> B goes through the SI base as an
intermediate step (A -> SI -> B) instead of needing a direct A -> B formula,
which avoids an O(N^2) matrix of pairwise conversions for N units.

dimensions is a 7-vector of exponents on the SI base units, in order:
[mass(kg), length(m), time(s), current(A), temperature(K), amount(mol), luminosity(cd)]

For a unit u: value_in_si_base = raw_value * u.scale + u.offset
(the offset is only nonzero for affine conversions, e.g. Fahrenheit)
"""

REGISTRY = {
    "pascal": {"name": "Pascal", "dimensions": (1, -1, -2, 0, 0, 0, 0), "scale": 1.0, "offset": 0.0},
    "psi": {"name": "Pounds per Square Inch", "dimensions": (1, -1, -2, 0, 0, 0, 0), "scale": 6894.75729, "offset": 0.0},
    "bar": {"name": "Bar", "dimensions": (1, -1, -2, 0, 0, 0, 0), "scale": 100000.0, "offset": 0.0},
    "kelvin": {"name": "Kelvin", "dimensions": (0, 0, 0, 0, 1, 0, 0), "scale": 1.0, "offset": 0.0},
    "fahrenheit": {"name": "Fahrenheit", "dimensions": (0, 0, 0, 0, 1, 0, 0), "scale": 5.0 / 9.0, "offset": 273.15 - 32 * 5.0 / 9.0},
    "celsius": {"name": "Celsius", "dimensions": (0, 0, 0, 0, 1, 0, 0), "scale": 1.0, "offset": 273.15},
}

DIMENSION_LABELS = {
    (1, -1, -2, 0, 0, 0, 0): "Pressure [M1 L-1 T-2]",
    (0, 0, 0, 0, 1, 0, 0): "Temperature [Theta1]",
}


def convert(value: float, from_unit: str, to_unit: str, registry: dict = REGISTRY) -> float:
    u1 = registry[from_unit]
    u2 = registry[to_unit]

    if u1["dimensions"] != u2["dimensions"]:
        raise ValueError(f"Cannot convert incompatible dimensions: {from_unit} -> {to_unit}")

    canonical_value = (value * u1["scale"]) + u1["offset"]
    target_value = (canonical_value - u2["offset"]) / u2["scale"]
    return target_value


def convert_response(value: float, from_unit: str, to_unit: str, precision: int = 2, registry: dict = REGISTRY) -> dict:
    """Same as convert(), but returns the full response shape (with
    precision actually applied, and the canonical SI value included) --
    convert() itself doesn't round, so this is what a caller should use
    if it wants the response schema shown in the API examples."""
    u1 = registry[from_unit]
    u2 = registry[to_unit]
    canonical_value = (value * u1["scale"]) + u1["offset"]
    output_value = convert(value, from_unit, to_unit, registry)

    return {
        "status": "success",
        "input": {"value": value, "unit": from_unit},
        "output": {"value": round(output_value, precision), "unit": to_unit},
        "canonicalSI": {"value": round(canonical_value, precision), "unit": registry_base_unit_name(u1["dimensions"], registry)},
        "dimension": DIMENSION_LABELS.get(u1["dimensions"], str(u1["dimensions"])),
    }


def registry_base_unit_name(dimensions: tuple, registry: dict = REGISTRY) -> str:
    for unit_id, u in registry.items():
        if u["dimensions"] == dimensions and u["scale"] == 1.0 and u["offset"] == 0.0:
            return unit_id
    raise ValueError(f"No canonical base unit registered for dimensions {dimensions}")
