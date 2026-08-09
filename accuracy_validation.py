"""
Real fix for the accuracy problem the honest loop in
simulation_reference.py exposes.

ROOT CAUSE (measured, not guessed -- see the diagnostic below):
A single ToF laser reading has ~0.15mm of Gaussian noise. In the wide body
of the vessel (cross-sectional area ~3526 mm^2), that noise is amplified by
the cross-section into ~0.53 mL of volume noise per reading -- enough to
exceed a 1.0 mL / 99%-reliability target about 5-7% of the time, purely
from sensor physics. That is what simulation_reference.py's first (honest)
loop reports correctly when it trips its failure threshold.

The "Kalman filter" in simulation_reference.py's later iterations does NOT
fix this: it multiplies the *reported* error by a fixed factor (~0.11-0.12)
before comparing it to the 1.0 mL threshold, without changing the actual
computed volume at all. That makes the report say "100% accurate" while
the real measurement is exactly as noisy as before -- a textbook case of a
QA metric being gamed instead of the underlying quantity being improved.

THE ACTUAL FIX: average multiple raw laser samples per reading event
before computing volume. This is a standard, legitimate noise-reduction
technique for real ToF sensors ("burst sampling"): averaging N independent
samples reduces noise by 1/sqrt(N).

MULTI-SEED VALIDATION (see run_multi_seed_validation): a single seeded
1,000-sip run is one draw from a distribution, not the true failure rate --
an earlier version of this file reported "N=4: 0/1000 failures (0.00%)"
from exactly one such draw, which overstated the case. Aggregating 200
independent trials (200,000 total readings per N) gives a real answer:

    N | mean failure rate | worst single trial | 95% upper bound
    1 |            5.268% |              7.90%  |           5.37%
    2 |            0.663% |              1.30%  |           0.70%
    3 |            0.094% |              0.60%  |           0.11%
    4 |            0.016% |              0.20%  |           0.023%
    5 |            0.004% |              0.10%  |           0.007%

Two corrections to the earlier single-seed claim: N=4's true rate is
~0.016%, not a literal 0% -- comfortably under the 1% target, but not
exactly zero. And N=2's worst observed trial (1.30%) actually breaches the
1% target, so N=2 does not reliably meet the reliability goal the way a
single lucky 0.90% draw suggested. N=4 is used below because it holds a
consistent margin under 1% across all 200 trials tested, not because of
one favorable run.
"""

import math
import random
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- Geometry / thermal model (matches simulation_reference.py) ---
TOTAL_NOMINAL_HEIGHT_MM = 220.0
SHOULDER_HEIGHT_MM = 180.0
RADIUS_BODY_MM = 33.5
RADIUS_NECK_MM = 25.0
CTE_STEEL = 12.0e-6
CTE_PEEK = 47.0e-6
BASELINE_TEMP_C = 20.0
MAX_CAPACITY_ML = 710.0

# Unit conversion (exact NIST factor)
ISO_FL_OZ_TO_ML = 29.5735295625
ISO_ML_TO_FL_OZ = 1.0 / ISO_FL_OZ_TO_ML
TARGET_RELIABILITY = 0.990  # 99%

AREA_BODY = np.pi * (RADIUS_BODY_MM ** 2)
AREA_NECK = np.pi * (RADIUS_NECK_MM ** 2)

# Sensor noise spec (single-shot laser reading standard deviation)
LASER_NOISE_STD_MM = 0.15
# Number of raw laser samples averaged per reported reading
SAMPLES_PER_READING = 4


def simulate_temporal_settlement(seconds_delayed=4.0):
    """Matches simulation_reference.py. By design, this only ever scales
    simulated sensor noise below -- never the computed volume."""
    required_settlement = 4.0
    if seconds_delayed >= required_settlement:
        return 1.0
    return 1.0 + ((required_settlement - seconds_delayed) * 2.5)


def calculate_thermal_expansion_delta(t_liquid, t_lid):
    delta_t_liquid = t_liquid - BASELINE_TEMP_C
    delta_t_lid = t_lid - BASELINE_TEMP_C
    steel_expansion_mm = SHOULDER_HEIGHT_MM * CTE_STEEL * delta_t_liquid
    peek_expansion_mm = 40.0 * CTE_PEEK * delta_t_lid
    return steel_expansion_mm + peek_expansion_mm


def calculate_step_cylinder_volume(raw_laser_distance_mm, structural_warp_mm):
    calibrated_total_height = TOTAL_NOMINAL_HEIGHT_MM + structural_warp_mm
    fluid_height_mm = calibrated_total_height - raw_laser_distance_mm
    if fluid_height_mm <= 0:
        return 0.0
    if fluid_height_mm > calibrated_total_height:
        fluid_height_mm = calibrated_total_height
    if fluid_height_mm <= SHOULDER_HEIGHT_MM:
        return AREA_BODY * fluid_height_mm
    return AREA_BODY * SHOULDER_HEIGHT_MM + AREA_NECK * (fluid_height_mm - SHOULDER_HEIGHT_MM)


def apply_thousandth_protocol(integrated_volume_mm3):
    quantized_ml = np.round(integrated_volume_mm3 / 1000.0, 1)
    return min(quantized_ml, MAX_CAPACITY_ML)


def true_height_from_volume_ml(volume_ml):
    """Inverse of calculate_step_cylinder_volume, used only to build the
    simulated ground truth for testing."""
    vol_body_max_ml = (AREA_BODY * SHOULDER_HEIGHT_MM) / 1000.0
    if volume_ml <= vol_body_max_ml:
        return (volume_ml * 1000.0) / AREA_BODY
    return SHOULDER_HEIGHT_MM + ((volume_ml * 1000.0 - AREA_BODY * SHOULDER_HEIGHT_MM) / AREA_NECK)


def read_averaged_laser_distance(true_height_mm, warp_mm, n_samples,
                                  noise_std_mm=LASER_NOISE_STD_MM, slosh_multiplier=1.0):
    """Take n_samples independent raw laser readings and average them.
    This is the real fix: averaging N independent Gaussian samples reduces
    noise standard deviation by 1/sqrt(N), unlike simulation_reference.py's
    "Kalman filter," which only rescales the error metric after the fact.

    slosh_multiplier scales the per-sample noise (matching
    simulation_reference.py's use of it -- unsettled fluid means noisier
    raw samples, not a bigger real volume). It never touches the returned
    volume."""
    samples = [
        (TOTAL_NOMINAL_HEIGHT_MM + warp_mm) - true_height_mm + random.gauss(0, noise_std_mm) * slosh_multiplier
        for _ in range(n_samples)
    ]
    return sum(samples) / n_samples


def run_honest_stress_test(sip_volume_list, n_samples, t_liq=4.0, t_ld=45.0):
    """1,000-sip stress test using REAL error for pass/fail -- no rescaling."""
    warp_mm = calculate_thermal_expansion_delta(t_liq, t_ld)
    current_true_volume_ml = MAX_CAPACITY_ML
    failures = 0
    errors = []
    for sip_ml in sip_volume_list:
        expected_volume_ml = max(0.0, current_true_volume_ml - sip_ml)
        true_height_mm = true_height_from_volume_ml(expected_volume_ml)
        avg_reading_mm = read_averaged_laser_distance(true_height_mm, warp_mm, n_samples)
        integrated_mm3 = calculate_step_cylinder_volume(avg_reading_mm, warp_mm)
        calculated_volume_ml = apply_thousandth_protocol(integrated_mm3)
        error_ml = abs(calculated_volume_ml - expected_volume_ml)
        errors.append(error_ml)
        if error_ml > 1.0:
            failures += 1
        current_true_volume_ml = expected_volume_ml if expected_volume_ml > 0 else MAX_CAPACITY_ML
    errors = np.array(errors)
    return {
        "failures": failures,
        "total": len(sip_volume_list),
        "accuracy_pct": (len(sip_volume_list) - failures) / len(sip_volume_list) * 100,
        "mean_abs_error_ml": errors.mean(),
        "std_abs_error_ml": errors.std(),
    }


def wilson_upper_bound(failures, n, z=1.96):
    """One-sided Wilson score upper bound on a binomial failure
    probability, at the given z (1.96 => ~97.5% one-sided => commonly
    quoted as a 95% upper bound). Used because failure counts here can be
    small (single digits out of 200,000), where a normal approximation
    alone is unreliable."""
    if n == 0:
        return float("nan")
    phat = failures / n
    denom = 1 + z**2 / n
    center = phat + z**2 / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2))
    return (center + margin) / denom


def run_multi_seed_validation(n_samples, num_trials=200, sips_per_trial=1000,
                               t_liq=4.0, t_ld=45.0, base_seed=1000):
    """
    Run num_trials independent 1,000-sip stress tests, each with its own
    fresh seed, and aggregate REAL failure statistics across all of them.

    A single seeded run (run_honest_stress_test called once) reports one
    draw from a distribution -- it can look better or worse than the true
    rate purely by chance. This reports the mean rate, the worst single
    trial observed, and a 95% one-sided upper confidence bound over the
    full pooled sample, which is the standard the earlier single-seed
    "N=4: 0.00% failures" claim in this file's docstring did not meet.
    """
    trial_failure_counts = []
    for t in range(num_trials):
        seed = base_seed + t
        np.random.seed(seed)
        sips = np.random.uniform(15.0, 60.0, sips_per_trial)
        random.seed(seed)
        result = run_honest_stress_test(sips, n_samples=n_samples, t_liq=t_liq, t_ld=t_ld)
        trial_failure_counts.append(result["failures"])

    trial_failure_counts = np.array(trial_failure_counts)
    total_failures = int(trial_failure_counts.sum())
    total_draws = num_trials * sips_per_trial
    trial_rates_pct = (trial_failure_counts / sips_per_trial) * 100

    return {
        "n_samples": n_samples,
        "num_trials": num_trials,
        "total_draws": total_draws,
        "total_failures": total_failures,
        "mean_failure_rate_pct": total_failures / total_draws * 100,
        "worst_trial_failure_rate_pct": trial_rates_pct.max(),
        "best_trial_failure_rate_pct": trial_rates_pct.min(),
        "std_across_trials_pct": trial_rates_pct.std(),
        "upper_95_bound_pct": wilson_upper_bound(total_failures, total_draws) * 100,
    }


def run_iso_unit_reporting_loop(sip_list, n_samples=SAMPLES_PER_READING, settlement_time=4.0,
                                 t_liq=4.0, t_ld=45.0, make_plot=True, plot_path=None):
    """
    Real-fix replacement for run_flight_certification_loop() in
    simulation_reference.py (renamed here -- this is a handheld-bottle QA
    loop, not an aviation certification procedure, despite the name it
    inherited from that source material). Same mL + fl oz reporting shape,
    and the same pass/fail target (TARGET_RELIABILITY), but:
      - uses N-sample laser averaging (the actual noise fix) instead of a
        single noisy reading
      - never rescales the reported error -- pass/fail is judged on the
        real computed volume, exactly as processTelemetryPayload would
        return it in telemetry_volume_engine.js
    """
    warp_mm = calculate_thermal_expansion_delta(t_liq, t_ld)
    slosh_multiplier = simulate_temporal_settlement(settlement_time)
    current_true_volume_ml = MAX_CAPACITY_ML

    total_cycles = 0
    failures = 0
    cycles_x, errors_ml_y, errors_floz_y = [], [], []
    last_volume_ml = last_volume_floz = 0.0

    for idx, sip_ml in enumerate(sip_list, start=1):
        total_cycles += 1
        expected_volume_ml = max(0.0, current_true_volume_ml - sip_ml)
        true_height_mm = true_height_from_volume_ml(expected_volume_ml)

        avg_reading_mm = read_averaged_laser_distance(
            true_height_mm, warp_mm, n_samples, slosh_multiplier=slosh_multiplier
        )
        integrated_mm3 = calculate_step_cylinder_volume(avg_reading_mm, warp_mm)
        calculated_volume_ml = apply_thousandth_protocol(integrated_mm3)
        calculated_volume_floz = calculated_volume_ml * ISO_ML_TO_FL_OZ

        # REAL error -- no rescaling before the threshold check
        error_ml = abs(calculated_volume_ml - expected_volume_ml)
        error_floz = error_ml * ISO_ML_TO_FL_OZ

        cycles_x.append(idx)
        errors_ml_y.append(error_ml)
        errors_floz_y.append(error_floz)

        if error_ml > 1.0:
            failures += 1
            if failures > 10:
                print(f"[CRITICAL HALT] System telemetry breached 99% baseline at step {idx}.")
                break

        last_volume_ml, last_volume_floz = calculated_volume_ml, calculated_volume_floz
        current_true_volume_ml = expected_volume_ml if expected_volume_ml > 0 else MAX_CAPACITY_ML

    accuracy_pct = (total_cycles - failures) / total_cycles * 100
    passed = (failures / total_cycles) <= (1.0 - TARGET_RELIABILITY)

    print("=====================================================================")
    print("STARTING 1,000-SIP STRESS-TEST RUN (REAL FIX, mL / fl oz REPORT)")
    print("=====================================================================")
    print(f"Samples averaged per reading: {n_samples}")
    print("=====================================================================")
    print("FINAL UNIT-CONVERSION REPORT")
    print("=====================================================================")
    print(f"Total Telemetry Cycles Processed: {total_cycles} / {len(sip_list)}")
    print(f"Total Volumetric Failures Logged: {failures}")
    print(f"Calculated Operational Accuracy: {accuracy_pct:.2f}%")
    print(f"Last Tracked Volume (Metric):    {last_volume_ml:.2f} mL")
    print(f"Last Tracked Volume (US/Custom):  {last_volume_floz:.2f} fl oz")
    status_str = "PASSED (real measurement, no rescaling)" if passed else "FAILED (threshold exceeded)"
    print(f"Report Status:                   {status_str}")
    print("=====================================================================")

    if make_plot:
        fig, ax1 = plt.subplots(figsize=(12, 5))
        color = "#2ca02c"
        ax1.set_xlabel("Simulation Cycle (Sip #)", fontsize=12)
        ax1.set_ylabel("Absolute Error (mL)", color=color, fontsize=12)
        ax1.plot(cycles_x, errors_ml_y, color=color, alpha=0.7, label="Real Error (mL)")
        ax1.tick_params(axis="y", labelcolor=color)
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax2 = ax1.twinx()
        color = "#1f77b4"
        ax2.set_ylabel("Absolute Error (fl oz)", color=color, fontsize=12)
        ax2.plot(cycles_x, errors_floz_y, color=color, alpha=0.5, linestyle="--", label="Real Error (fl oz)")
        ax2.tick_params(axis="y", labelcolor=color)
        plt.axhline(y=1.0, color="red", linestyle=":", label="1.0 mL Threshold", linewidth=1.5)
        plt.title(
            f"1,000-Sip Stress Test, Real Fix (N={n_samples} samples/reading, no rescaling)",
            fontsize=14, fontweight="bold",
        )
        fig.tight_layout()
        if plot_path:
            fig.savefig(plot_path, dpi=150, bbox_inches="tight")
            print(f"Plot saved to {plot_path}")
        plt.close(fig)

    return {
        "total_cycles": total_cycles,
        "failures": failures,
        "accuracy_pct": accuracy_pct,
        "passed": passed,
        "last_volume_ml": last_volume_ml,
        "last_volume_floz": last_volume_floz,
    }


def main():
    # Seed BOTH RNGs used (simulation_reference.py only seeds np.random,
    # leaving the stdlib `random` module -- used for the Gaussian sensor
    # noise -- unseeded and therefore non-reproducible between runs).
    np.random.seed(42)
    simulated_sips_ml = np.random.uniform(15.0, 60.0, 1000)

    print("=" * 70)
    print("SINGLE-SEED SNAPSHOT (seed=42) -- one draw, not the true rate")
    print("=" * 70)
    for n in (1, 2, 3, 4, 5):
        random.seed(42)
        result = run_honest_stress_test(simulated_sips_ml, n_samples=n)
        print(
            f"N={n} sample(s)/reading: {result['failures']}/{result['total']} failures "
            f"({100 - result['accuracy_pct']:.2f}%), "
            f"mean|err|={result['mean_abs_error_ml']:.4f} mL, "
            f"std={result['std_abs_error_ml']:.4f} mL"
        )

    print()
    print("=" * 100)
    print("MULTI-SEED VALIDATION -- 200 independent trials x 1,000 sips = 200,000 draws per N")
    print("=" * 100)
    header = f"{'N':>3} | {'mean_rate':>10} | {'worst_trial':>11} | {'best_trial':>10} | {'95%_upper_bound':>16}"
    print(header)
    print("-" * len(header))
    for n in (1, 2, 3, 4, 5):
        stats = run_multi_seed_validation(n_samples=n)
        print(
            f"{n:>3} | {stats['mean_failure_rate_pct']:>9.4f}% | "
            f"{stats['worst_trial_failure_rate_pct']:>10.4f}% | "
            f"{stats['best_trial_failure_rate_pct']:>9.4f}% | "
            f"{stats['upper_95_bound_pct']:>15.4f}%"
        )

    print()
    selected_stats = run_multi_seed_validation(n_samples=SAMPLES_PER_READING)
    print(f"Selected SAMPLES_PER_READING={SAMPLES_PER_READING}")
    print(
        f"Real accuracy (mean over {selected_stats['num_trials']} trials): "
        f"{100 - selected_stats['mean_failure_rate_pct']:.4f}%, "
        f"95% upper bound on failure rate: {selected_stats['upper_95_bound_pct']:.4f}% "
        f"(target: <=1.0000%)"
    )
    print("=" * 70)

    print()
    random.seed(42)
    run_iso_unit_reporting_loop(simulated_sips_ml, n_samples=SAMPLES_PER_READING)


if __name__ == "__main__":
    main()
