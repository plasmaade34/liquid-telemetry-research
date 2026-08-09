"""
Real, validated replacement for the undefined Phi(sigma_y/rho) term that
appeared in an earlier draft of STRUCTURAL_FRAMEWORK_NOTES.md. Instead of
an unspecified "specific strength adjustment coefficient," this derives
and tests the actual material index for minimum-mass design, per Ashby's
materials-selection methodology (M.F. Ashby, "Materials Selection in
Mechanical Design").

DERIVATION (not asserted -- shown):

Yield/hoop-stress-limited wall (Barlow's Formula):
    t_hoop = P * R * SF / sigma_y                    ->  t_hoop is proportional to 1/sigma_y
    mass_per_length ~ t * rho                          ->  mass ~ rho / sigma_y
    Minimizing mass means MAXIMIZING sigma_y / rho     ->  M_yield = sigma_y / rho

Elastic-buckling-limited wall (Timoshenko):
    t_buckle = R * (4 P SF (1 - nu^2) / E)^(1/3)       ->  t_buckle is proportional to E^(-1/3)
    mass_per_length ~ t * rho                          ->  mass ~ rho * E^(-1/3)
    Minimizing mass means MAXIMIZING E^(1/3) / rho     ->  M_buckle = E^(1/3) / rho

These are real, standard results, not the undefined Phi() from the earlier
draft. This script tests whether they actually predict which material
gives the lowest real mass, across the same pressure sweep as
substrate_optimization_simulation.py, using its real numbers -- honestly
reporting where the prediction holds and where it doesn't, rather than
assuming it always will.
"""

import numpy as np
import pandas as pd

R = 0.1  # m
SF = 1.5
ATM_TO_PA = 101325

MATERIALS = {
    "304 Stainless Steel": dict(density=8000.0, yield_strength=2.15e8, youngs_modulus=1.93e11, poisson_ratio=0.29),
    "6061-T6 Aluminum": dict(density=2700.0, yield_strength=2.76e8, youngs_modulus=6.89e10, poisson_ratio=0.33),
    "Titanium Grade 5": dict(density=4430.0, yield_strength=8.80e8, youngs_modulus=1.14e11, poisson_ratio=0.34),
}


def material_indices():
    rows = []
    for name, p in MATERIALS.items():
        m_yield = p["yield_strength"] / p["density"]
        m_buckle = (p["youngs_modulus"] ** (1 / 3)) / p["density"]
        rows.append({"Material": name, "M_yield (sigma_y/rho)": m_yield, "M_buckle (E^(1/3)/rho)": m_buckle})
    return pd.DataFrame(rows)


def run_sweep(pressures_atm):
    rows = []
    for p_atm in pressures_atm:
        p_pa = p_atm * ATM_TO_PA
        for name, p in MATERIALS.items():
            t_hoop = (p_pa * R * SF) / p["yield_strength"]
            t_buckle = R * ((4.0 * p_pa * SF * (1 - p["poisson_ratio"] ** 2)) / p["youngs_modulus"]) ** (1.0 / 3.0)
            t_req = max(t_hoop, t_buckle)
            mass = np.pi * ((R + t_req) ** 2 - R ** 2) * p["density"]
            rows.append(
                {
                    "Pressure_Atm": p_atm,
                    "Material": name,
                    "t_hoop_mm": t_hoop * 1000,
                    "t_buckle_mm": t_buckle * 1000,
                    "t_req_mm": t_req * 1000,
                    "governs": "buckle" if t_buckle > t_hoop else "hoop",
                    "Mass_kg_m": mass,
                }
            )
    return pd.DataFrame(rows)


def validate_index_predictions(df, indices_df):
    """
    At each pressure point, check whether ranking materials by the index
    appropriate to whichever mechanism governs for the LOWEST-mass
    candidate actually predicts the real mass ranking. Reports the
    fraction of pressure points where the prediction is fully correct,
    and flags where mechanisms are mixed across materials (the case the
    simple single-index comparison isn't really valid for).
    """
    idx = indices_df.set_index("Material")
    total = 0
    correct = 0
    mixed_regime_points = 0

    for p_atm, group in df.groupby("Pressure_Atm"):
        total += 1
        governs_set = set(group["governs"])
        actual_ranking = list(group.sort_values("Mass_kg_m")["Material"])

        if len(governs_set) > 1:
            # Materials at this pressure are governed by different
            # mechanisms -- a single index doesn't cleanly apply here.
            mixed_regime_points += 1
            continue

        mechanism = governs_set.pop()
        index_col = "M_buckle (E^(1/3)/rho)" if mechanism == "buckle" else "M_yield (sigma_y/rho)"
        predicted_ranking = list(idx[index_col].sort_values(ascending=False).index)

        if predicted_ranking == actual_ranking:
            correct += 1

    clean_regime_points = total - mixed_regime_points
    return {
        "total_pressure_points": total,
        "mixed_regime_points": mixed_regime_points,
        "clean_regime_points": clean_regime_points,
        "correct_predictions_in_clean_regime": correct,
        "accuracy_in_clean_regime_pct": (correct / clean_regime_points * 100) if clean_regime_points else float("nan"),
    }


def main():
    print("=" * 70)
    print("MATERIAL INDICES (derived, not asserted)")
    print("=" * 70)
    indices_df = material_indices()
    print(indices_df.to_string(index=False))
    print()
    print("Note: the two indices disagree on which material is 'best' --")
    print("Titanium leads on M_yield, but Aluminum leads on M_buckle.")
    print("Which one matters depends on which failure mode actually governs.")

    print()
    print("=" * 70)
    print("VALIDATION 1: original 0.1-10 atm range (matches substrate_optimization_simulation.py)")
    print("=" * 70)
    df_narrow = run_sweep(np.linspace(0.1, 10.0, 100))
    result_narrow = validate_index_predictions(df_narrow, indices_df)
    for k, v in result_narrow.items():
        print(f"{k}: {v}")
    print()
    print("IMPORTANT CAVEAT: in this range, buckling governs for all three")
    print("materials at every pressure tested (see breakdown below). That means")
    print("this range only ever exercises M_buckle -- it says nothing about")
    print("whether M_yield actually predicts anything, because the yield-limited")
    print("regime never comes up here.")
    print(df_narrow.groupby(["Material"])["governs"].value_counts().to_string())

    # Crossover pressures (hoop overtakes buckling) are far higher than 10 atm
    # for all three materials -- extend the sweep to actually exercise both
    # regimes, instead of only ever validating M_buckle.
    print()
    print("=" * 70)
    print("VALIDATION 2: extended 0.1-1200 atm range (exercises BOTH regimes)")
    print("=" * 70)
    df_wide = run_sweep(np.linspace(0.1, 1200.0, 2000))
    result_wide = validate_index_predictions(df_wide, indices_df)
    for k, v in result_wide.items():
        print(f"{k}: {v}")
    print()
    print(df_wide.groupby(["Material"])["governs"].value_counts().to_string())


if __name__ == "__main__":
    main()
