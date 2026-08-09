"""
Python port of telemetry_volume_engine.js.

Kept as a line-for-line mirror of the JS engine (same constants, same
function names translated to snake_case, same status strings) rather than
a more "Pythonic" rewrite, specifically so the two can be checked against
shared golden test vectors (see tests/) without the comparison being
muddied by incidental implementation differences.

One deliberate deviation: Python's built-in round() uses round-half-to-even
("banker's rounding"), while JS's Math.round()/toFixed() round half away
from zero. All values here are non-negative except thermalWarpMm, so
_round_half_away_from_zero() is used everywhere a JS engine .toFixed()-
or Math.round()-style rounding needs to be reproduced exactly.
"""

import math

METROLOGY_CONSTANTS = {
    "TOTAL_NOMINAL_HEIGHT_MM": 220.0,
    "BODY_HEIGHT_MM": 180.0,
    "RADIUS_BODY_MM": 33.5,
    "RADIUS_NECK_MM": 25.0,
    "CTE_STEEL": 12.0e-6,
    "CTE_PEEK": 47.0e-6,
    "NOMINAL_LID_HEIGHT_MM": 40.0,
    "BASELINE_TEMP_C": 20.0,
    "MAX_CAPACITY_ML": 710.0,
    "FL_OZ_TO_ML": 29.5735295625,
}


def _round_half_away_from_zero(x, decimals):
    """Mirrors JS Math.round()/Number.toFixed() rounding (half away from
    zero), unlike Python's round() (half to even)."""
    factor = 10 ** decimals
    sign = -1.0 if x < 0 else 1.0
    return sign * math.floor(abs(x) * factor + 0.5) / factor


def _is_finite_number(x):
    """Mirrors JS Number.isFinite(): true numbers only, no bool, no NaN/inf."""
    if isinstance(x, bool):
        return False
    if not isinstance(x, (int, float)):
        return False
    return math.isfinite(x)


def simulate_temporal_settlement(seconds_delayed=4.0):
    required_settlement = 4.0
    if seconds_delayed >= required_settlement:
        return 1.0
    return 1.0 + ((required_settlement - seconds_delayed) * 2.5)


def calculate_thermal_expansion_delta(t_liquid, t_lid):
    delta_t_liquid = t_liquid - METROLOGY_CONSTANTS["BASELINE_TEMP_C"]
    delta_t_lid = t_lid - METROLOGY_CONSTANTS["BASELINE_TEMP_C"]
    steel_expansion_mm = METROLOGY_CONSTANTS["BODY_HEIGHT_MM"] * METROLOGY_CONSTANTS["CTE_STEEL"] * delta_t_liquid
    peek_expansion_mm = METROLOGY_CONSTANTS["NOMINAL_LID_HEIGHT_MM"] * METROLOGY_CONSTANTS["CTE_PEEK"] * delta_t_lid
    return steel_expansion_mm + peek_expansion_mm


def calculate_step_cylinder_volume(raw_laser_distance_mm, structural_warp_mm):
    calibrated_total_height = METROLOGY_CONSTANTS["TOTAL_NOMINAL_HEIGHT_MM"] + structural_warp_mm
    fluid_height_mm = calibrated_total_height - raw_laser_distance_mm
    if fluid_height_mm <= 0:
        return 0.0, False

    height_clamped = False
    if fluid_height_mm > calibrated_total_height:
        fluid_height_mm = calibrated_total_height
        height_clamped = True

    area_body = math.pi * METROLOGY_CONSTANTS["RADIUS_BODY_MM"] ** 2
    area_neck = math.pi * METROLOGY_CONSTANTS["RADIUS_NECK_MM"] ** 2

    if fluid_height_mm <= METROLOGY_CONSTANTS["BODY_HEIGHT_MM"]:
        volume_mm3 = area_body * fluid_height_mm
    else:
        volume_body_chunk = area_body * METROLOGY_CONSTANTS["BODY_HEIGHT_MM"]
        height_remaining_in_neck = fluid_height_mm - METROLOGY_CONSTANTS["BODY_HEIGHT_MM"]
        volume_neck_chunk = area_neck * height_remaining_in_neck
        volume_mm3 = volume_body_chunk + volume_neck_chunk

    return volume_mm3, height_clamped


def apply_rounding_protocol(integrated_volume_mm3):
    raw_ml = integrated_volume_mm3 / 1000.0
    quantized_ml = _round_half_away_from_zero(raw_ml * 20, 0) / 20  # nearest 0.05 mL
    capacity_capped = False
    if quantized_ml > METROLOGY_CONSTANTS["MAX_CAPACITY_ML"]:
        quantized_ml = METROLOGY_CONSTANTS["MAX_CAPACITY_ML"]
        capacity_capped = True
    return quantized_ml, capacity_capped


def find_invalid_telemetry_field(raw_laser_distance_mm, t_liquid, t_lid, seconds_delayed):
    if isinstance(raw_laser_distance_mm, list):
        if len(raw_laser_distance_mm) == 0 or not all(_is_finite_number(s) for s in raw_laser_distance_mm):
            return "rawLaserDistanceMm"
    elif not _is_finite_number(raw_laser_distance_mm):
        return "rawLaserDistanceMm"
    if not _is_finite_number(t_liquid):
        return "tLiquid"
    if not _is_finite_number(t_lid):
        return "tLid"
    if not _is_finite_number(seconds_delayed):
        return "secondsDelayed"
    return None


def average_raw_laser_distance(raw_laser_distance_mm):
    if isinstance(raw_laser_distance_mm, list):
        return sum(raw_laser_distance_mm) / len(raw_laser_distance_mm), len(raw_laser_distance_mm)
    return raw_laser_distance_mm, 1


def process_telemetry_payload(raw_laser_distance_mm, t_liquid=4.0, t_lid=45.0, seconds_delayed=4.0):
    invalid_field = find_invalid_telemetry_field(raw_laser_distance_mm, t_liquid, t_lid, seconds_delayed)
    if invalid_field:
        return {
            "status": "HHTR_INVALID_INPUT",
            "invalidField": invalid_field,
            "thermalWarpMm": None,
            "sloshMultiplier": None,
            "sampleCount": None,
            "volumeMl": None,
            "volumeFlOz": None,
        }

    averaged_mm, sample_count = average_raw_laser_distance(raw_laser_distance_mm)

    slosh_multiplier = simulate_temporal_settlement(seconds_delayed)
    warp_mm = calculate_thermal_expansion_delta(t_liquid, t_lid)
    integrated_mm3, height_clamped = calculate_step_cylinder_volume(averaged_mm, warp_mm)
    volume_ml, capacity_capped = apply_rounding_protocol(integrated_mm3)
    volume_fl_oz = _round_half_away_from_zero(volume_ml / METROLOGY_CONSTANTS["FL_OZ_TO_ML"], 2)
    status = "HHTR_READING_CLAMPED" if (height_clamped or capacity_capped) else "HHTR_READING_OK"

    return {
        "status": status,
        "thermalWarpMm": _round_half_away_from_zero(warp_mm, 5),
        "sloshMultiplier": slosh_multiplier,
        "sampleCount": sample_count,
        "volumeMl": volume_ml,
        "volumeFlOz": volume_fl_oz,
    }


def process_batch_telemetry(payloads):
    return [
        process_telemetry_payload(
            p.get("rawLaserDistanceMm"), p.get("tLiquid", 4.0), p.get("tLid", 45.0), p.get("secondsDelayed", 4.0)
        )
        for p in payloads
    ]
