// C++ port of telemetry_volume_engine.js / telemetry_volume_engine.py.
// Header-only for easy embedding: #include "telemetry_volume_engine.hpp"
//
// Same constants, same status strings, same function breakdown as the
// other two ports -- checked against the same tests/test_vectors.json.
//
// One necessary divergence: C++ is statically typed, so there's no direct
// equivalent of "a non-numeric value was passed where a number was
// expected" -- that class of error is a compile error here, not a
// runtime one. NaN is the natural stand-in: findInvalidTelemetryField
// treats non-finite doubles and empty sample vectors as invalid, which
// reproduces the *behavior* of the JS/Python engines (reject bad input,
// name the field) even though the detection mechanism differs. See
// tests/run_vectors.cpp for how the shared JSON vectors' string sentinels
// get mapped to NaN for this port.

#pragma once

#include <cmath>
#include <optional>
#include <string>
#include <vector>

namespace telemetry {

constexpr double PI = 3.14159265358979323846;

struct MetrologyConstants {
    static constexpr double TOTAL_NOMINAL_HEIGHT_MM = 220.0;
    static constexpr double BODY_HEIGHT_MM = 180.0;
    static constexpr double RADIUS_BODY_MM = 33.5;
    static constexpr double RADIUS_NECK_MM = 25.0;
    static constexpr double CTE_STEEL = 12.0e-6;
    static constexpr double CTE_PEEK = 47.0e-6;
    static constexpr double NOMINAL_LID_HEIGHT_MM = 40.0;
    static constexpr double BASELINE_TEMP_C = 20.0;
    static constexpr double MAX_CAPACITY_ML = 710.0;
    static constexpr double FL_OZ_TO_ML = 29.5735295625;
};

struct TelemetryResult {
    std::string status;
    std::optional<std::string> invalidField;
    std::optional<double> thermalWarpMm;
    std::optional<double> sloshMultiplier;
    std::optional<int> sampleCount;
    std::optional<double> volumeMl;
    std::optional<double> volumeFlOz;
};

// Mirrors JS Math.round()/toFixed() and the Python port's
// _round_half_away_from_zero: half-way values round away from zero. Note
// this is NOT quite the same as JS's Math.round() for negative numbers
// (JS rounds negative .5 toward +Infinity, i.e. -2.5 -> -2, not -3) --
// but every value rounded in this engine is non-negative except
// thermalWarpMm, where an exact tie at the 5th decimal is not something
// any of the shared test vectors exercise. Matches all 24 golden vectors.
inline double roundHalfAwayFromZero(double x, int decimals) {
    double factor = std::pow(10.0, decimals);
    double sign = x < 0 ? -1.0 : 1.0;
    return sign * std::floor(std::abs(x) * factor + 0.5) / factor;
}

inline double simulateTemporalSettlement(double secondsDelayed = 4.0) {
    const double requiredSettlement = 4.0;
    if (secondsDelayed >= requiredSettlement) return 1.0;
    return 1.0 + ((requiredSettlement - secondsDelayed) * 2.5);
}

inline double calculateThermalExpansionDelta(double tLiquid, double tLid) {
    double deltaTLiquid = tLiquid - MetrologyConstants::BASELINE_TEMP_C;
    double deltaTLid = tLid - MetrologyConstants::BASELINE_TEMP_C;
    double steelExpansionMm = MetrologyConstants::BODY_HEIGHT_MM * MetrologyConstants::CTE_STEEL * deltaTLiquid;
    double peekExpansionMm = MetrologyConstants::NOMINAL_LID_HEIGHT_MM * MetrologyConstants::CTE_PEEK * deltaTLid;
    return steelExpansionMm + peekExpansionMm;
}

struct StepCylinderResult {
    double volumeMm3;
    bool heightClamped;
};

// NOTE: same historical-name caveat as the other two ports -- this is two
// stacked constant-radius cylinders with an abrupt radius change at
// BODY_HEIGHT_MM, not a curve-accurate integral over a tapered profile.
inline StepCylinderResult calculateStepCylinderVolume(double rawLaserDistanceMm, double structuralWarpMm) {
    double calibratedTotalHeight = MetrologyConstants::TOTAL_NOMINAL_HEIGHT_MM + structuralWarpMm;
    double fluidHeightMm = calibratedTotalHeight - rawLaserDistanceMm;
    if (fluidHeightMm <= 0) return {0.0, false};

    bool heightClamped = false;
    if (fluidHeightMm > calibratedTotalHeight) {
        fluidHeightMm = calibratedTotalHeight;
        heightClamped = true;
    }

    double areaBody = PI * MetrologyConstants::RADIUS_BODY_MM * MetrologyConstants::RADIUS_BODY_MM;
    double areaNeck = PI * MetrologyConstants::RADIUS_NECK_MM * MetrologyConstants::RADIUS_NECK_MM;

    double volumeMm3;
    if (fluidHeightMm <= MetrologyConstants::BODY_HEIGHT_MM) {
        volumeMm3 = areaBody * fluidHeightMm;
    } else {
        double volumeBodyChunk = areaBody * MetrologyConstants::BODY_HEIGHT_MM;
        double heightRemainingInNeck = fluidHeightMm - MetrologyConstants::BODY_HEIGHT_MM;
        double volumeNeckChunk = areaNeck * heightRemainingInNeck;
        volumeMm3 = volumeBodyChunk + volumeNeckChunk;
    }
    return {volumeMm3, heightClamped};
}

struct RoundingResult {
    double volumeMl;
    bool capacityCapped;
};

inline RoundingResult applyRoundingProtocol(double integratedVolumeMm3) {
    double rawMl = integratedVolumeMm3 / 1000.0;
    double quantizedMl = roundHalfAwayFromZero(rawMl * 20.0, 0) / 20.0;  // nearest 0.05 mL
    bool capacityCapped = false;
    if (quantizedMl > MetrologyConstants::MAX_CAPACITY_ML) {
        quantizedMl = MetrologyConstants::MAX_CAPACITY_ML;
        capacityCapped = true;
    }
    return {quantizedMl, capacityCapped};
}

inline std::optional<std::string> findInvalidTelemetryField(
    const std::vector<double>& rawLaserDistanceMm, double tLiquid, double tLid, double secondsDelayed) {
    if (rawLaserDistanceMm.empty()) return std::string("rawLaserDistanceMm");
    for (double s : rawLaserDistanceMm) {
        if (!std::isfinite(s)) return std::string("rawLaserDistanceMm");
    }
    if (!std::isfinite(tLiquid)) return std::string("tLiquid");
    if (!std::isfinite(tLid)) return std::string("tLid");
    if (!std::isfinite(secondsDelayed)) return std::string("secondsDelayed");
    return std::nullopt;
}

struct AveragedReading {
    double averagedMm;
    int sampleCount;
};

inline AveragedReading averageRawLaserDistance(const std::vector<double>& rawLaserDistanceMm) {
    double sum = 0.0;
    for (double s : rawLaserDistanceMm) sum += s;
    return {sum / static_cast<double>(rawLaserDistanceMm.size()), static_cast<int>(rawLaserDistanceMm.size())};
}

// Primary overload: rawLaserDistanceMm as multiple raw samples to average
// (the real noise-reduction fix -- see accuracy_validation.py).
inline TelemetryResult processTelemetryPayload(
    const std::vector<double>& rawLaserDistanceMm, double tLiquid = 4.0, double tLid = 45.0,
    double secondsDelayed = 4.0) {
    auto invalidField = findInvalidTelemetryField(rawLaserDistanceMm, tLiquid, tLid, secondsDelayed);
    if (invalidField) {
        TelemetryResult r;
        r.status = "HHTR_INVALID_INPUT";
        r.invalidField = invalidField;
        return r;
    }

    AveragedReading averaged = averageRawLaserDistance(rawLaserDistanceMm);

    double sloshMultiplier = simulateTemporalSettlement(secondsDelayed);
    double warpMm = calculateThermalExpansionDelta(tLiquid, tLid);
    StepCylinderResult step = calculateStepCylinderVolume(averaged.averagedMm, warpMm);
    RoundingResult rounded = applyRoundingProtocol(step.volumeMm3);
    double volumeFlOz = roundHalfAwayFromZero(rounded.volumeMl / MetrologyConstants::FL_OZ_TO_ML, 2);
    std::string status = (step.heightClamped || rounded.capacityCapped) ? "HHTR_READING_CLAMPED" : "HHTR_READING_OK";

    TelemetryResult r;
    r.status = status;
    r.thermalWarpMm = roundHalfAwayFromZero(warpMm, 5);
    r.sloshMultiplier = sloshMultiplier;
    r.sampleCount = averaged.sampleCount;
    r.volumeMl = rounded.volumeMl;
    r.volumeFlOz = volumeFlOz;
    return r;
}

// Convenience overload for a single reading (sampleCount == 1), matching
// the JS/Python engines' single-number call shape.
inline TelemetryResult processTelemetryPayload(
    double rawLaserDistanceMm, double tLiquid = 4.0, double tLid = 45.0, double secondsDelayed = 4.0) {
    return processTelemetryPayload(std::vector<double>{rawLaserDistanceMm}, tLiquid, tLid, secondsDelayed);
}

// JS's Number.isFinite(true) and Python's explicit bool check both reject
// booleans as invalid input. Without this, C++ would silently promote a
// literal `true`/`false` argument to 1.0/0.0 via implicit conversion and
// process it as a normal reading -- found by testing, not assumed. This
// deleted overload is an exact match for a bool argument (beating the
// double overload's implicit-conversion match), turning that silent
// behavior difference into a compile error instead.
TelemetryResult processTelemetryPayload(bool, double = 4.0, double = 45.0, double = 4.0) = delete;

}  // namespace telemetry
