"""
CAD-realistic worked example: sizing the inner wall of a vacuum-insulated
bottle using the real product geometry (33.5 mm body radius, from
telemetry_volume_engine.js's RADIUS_BODY_MM), unit_conversion.py, and the
same Barlow/Timoshenko formulas used in substrate_optimization_simulation.py.

Load case: a double-wall vacuum-insulated bottle has the gap between its
walls evacuated. The inner wall must withstand up to 1 standard atmosphere
of external differential pressure without tearing (hoop stress, Barlow) or
buckling (Timoshenko) -- this is a real, physically grounded scenario for
this exact product, not an arbitrary pressure pick.

This script computes the required wall thickness. See
SOLIDWORKS_VERIFICATION.md for the independent verification steps -- this
script's output is a prediction to check a CAD/FEA tool against, not a
substitute for actually checking it.
"""
import math
from unit_conversion import convert

# Real bottle geometry (telemetry_volume_engine.js: RADIUS_BODY_MM = 33.5)
R_MM = 33.5
R_M = R_MM / 1000.0

# 1 standard atmosphere, converted psi<->Pa via the tested unit_conversion module
P_PA = 101325.0
P_PSI = convert(P_PA, "pascal", "psi")

SAFETY_FACTOR = 1.5

# 304 Stainless Steel -- same material already used for CTE_STEEL in the
# real telemetry engine, and already listed in substrate_optimization_simulation.py
MATERIAL = {
    "name": "304 Stainless Steel",
    "yield_strength_pa": 2.15e8,
    "youngs_modulus_pa": 1.93e11,
    "poisson_ratio": 0.29,
    "density_kg_m3": 8000.0,
}


def compute_required_wall_thickness(R_m, P_pa, SF, sigma_y, E, nu):
    """Barlow's Formula (hoop stress) and Timoshenko's elastic buckling
    formula -- same two formulas as substrate_optimization_simulation.py."""
    t_hoop = (P_pa * R_m * SF) / sigma_y
    t_buckle = R_m * ((4.0 * P_pa * SF * (1 - nu**2)) / E) ** (1.0 / 3.0)
    t_required = max(t_hoop, t_buckle)
    governs = "buckling" if t_buckle > t_hoop else "hoop stress"
    return t_hoop, t_buckle, t_required, governs


if __name__ == "__main__":
    t_hoop, t_buckle, t_required, governs = compute_required_wall_thickness(
        R_M, P_PA, SAFETY_FACTOR,
        MATERIAL["yield_strength_pa"], MATERIAL["youngs_modulus_pa"], MATERIAL["poisson_ratio"],
    )
    mass_per_m = math.pi * ((R_M + t_required) ** 2 - R_M ** 2) * MATERIAL["density_kg_m3"]

    print(f"Load case: 1 standard atmosphere external differential pressure")
    print(f"  {P_PA:.1f} Pa = {P_PSI:.4f} psi (converted via unit_conversion.py)")
    print(f"Geometry: R = {R_MM} mm (real bottle body radius)")
    print(f"Material: {MATERIAL['name']}")
    print()
    print(f"t_hoop     = {t_hoop * 1000:.4f} mm  (Barlow's Formula)")
    print(f"t_buckle   = {t_buckle * 1000:.4f} mm  (Timoshenko buckling)")
    print(f"t_required = {t_required * 1000:.4f} mm  ({t_required * 1000 / 25.4:.5f} in) -- governed by {governs}")
    print(f"mass per unit length = {mass_per_m:.4f} kg/m")
    print()
    print("This is a prediction. See SOLIDWORKS_VERIFICATION.md to check it")
    print("independently in CAD/FEA -- this script cannot verify itself.")
