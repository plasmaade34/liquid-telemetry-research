// Cross-language golden vector test runner (C++ side).
// Build:  g++ -std=c++17 -O2 -o run_vectors_cpp tests/run_vectors.cpp
// Run:    ./run_vectors_cpp        (from the repo root, so the relative
//                                   path to tests/test_vectors.json resolves)
//
// String sentinels in the shared JSON vectors (used by JS/Python to
// trigger "non-numeric input" invalid-input cases) are mapped to NaN
// here, since C++ can't receive a string where a double is expected --
// see telemetry_volume_engine.hpp's header comment for why that's the
// right adaptation, not a workaround being hidden.

#include <cmath>
#include <fstream>
#include <iostream>
#include <limits>
#include <sstream>
#include <string>
#include <vector>

#include "../telemetry_volume_engine.hpp"
#include "json_mini.hpp"

using telemetry::TelemetryResult;

namespace {

double toDoubleOrNaN(const jsonmini::Value& v) {
    if (v.isNumber()) return v.asNumber();
    return std::numeric_limits<double>::quiet_NaN();  // string sentinel or unexpected type
}

std::vector<double> extractRawDistances(const jsonmini::Value& input) {
    const jsonmini::Value* raw = input.find("rawLaserDistanceMm");
    if (!raw) return {};
    if (raw->isArray()) {
        std::vector<double> out;
        for (const auto& el : raw->asArray()) out.push_back(toDoubleOrNaN(el));
        return out;
    }
    return {toDoubleOrNaN(*raw)};
}

double getOrDefault(const jsonmini::Value& input, const std::string& key, double def) {
    const jsonmini::Value* v = input.find(key);
    if (!v) return def;
    return toDoubleOrNaN(*v);
}

bool approxEqual(double a, double b, double eps = 1e-9) { return std::fabs(a - b) < eps; }

}  // namespace

int main() {
    std::ifstream f("tests/test_vectors.json");
    if (!f) {
        std::cerr << "Could not open tests/test_vectors.json -- run this from the repo root.\n";
        return 1;
    }
    std::stringstream buf;
    buf << f.rdbuf();
    jsonmini::Value vectors = jsonmini::parse(buf.str());

    int total = 0, failures = 0;
    for (const auto& vec : vectors.asArray()) {
        total++;
        std::string name = vec.find("name")->asString();
        const jsonmini::Value& input = *vec.find("input");
        const jsonmini::Value& expected = *vec.find("expected");

        std::vector<double> raw = extractRawDistances(input);
        double tLiquid = getOrDefault(input, "tLiquid", 4.0);
        double tLid = getOrDefault(input, "tLid", 45.0);
        double secondsDelayed = getOrDefault(input, "secondsDelayed", 4.0);

        TelemetryResult actual = telemetry::processTelemetryPayload(raw, tLiquid, tLid, secondsDelayed);

        bool ok = true;
        std::string expStatus = expected.find("status")->asString();
        if (actual.status != expStatus) ok = false;

        if (expStatus == "HHTR_INVALID_INPUT") {
            std::string expField = expected.find("invalidField")->asString();
            if (!actual.invalidField || *actual.invalidField != expField) ok = false;
        } else {
            double expWarp = expected.find("thermalWarpMm")->asNumber();
            double expSlosh = expected.find("sloshMultiplier")->asNumber();
            double expSamples = expected.find("sampleCount")->asNumber();
            double expVolMl = expected.find("volumeMl")->asNumber();
            double expVolFloz = expected.find("volumeFlOz")->asNumber();

            if (!actual.thermalWarpMm || !approxEqual(*actual.thermalWarpMm, expWarp)) ok = false;
            if (!actual.sloshMultiplier || !approxEqual(*actual.sloshMultiplier, expSlosh)) ok = false;
            if (!actual.sampleCount || *actual.sampleCount != static_cast<int>(expSamples)) ok = false;
            if (!actual.volumeMl || !approxEqual(*actual.volumeMl, expVolMl)) ok = false;
            if (!actual.volumeFlOz || !approxEqual(*actual.volumeFlOz, expVolFloz)) ok = false;
        }

        if (!ok) {
            failures++;
            std::cout << "MISMATCH [" << name << "]\n";
        }
    }

    std::cout << "\n" << (total - failures) << "/" << total << " vectors match\n";
    return failures == 0 ? 0 : 1;
}
