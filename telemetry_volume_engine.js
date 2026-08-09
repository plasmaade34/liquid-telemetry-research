
/**
 * Hodgins Holdings -- Liquid Telemetry Research
 * Thermal-compensated volume engine for a time-of-flight (ToF) laser
 * liquid-level sensor. Reports volume rounded to the nearest 0.05 mL.
 */

const METROLOGY_CONSTANTS = {
  TOTAL_NOMINAL_HEIGHT_MM: 220.0,
  // Height where the body cylinder meets the neck. Shared by the volume
  // geometry and the thermal-expansion model so the two can't drift apart.
  BODY_HEIGHT_MM: 180.0,
  RADIUS_BODY_MM: 33.5,
  RADIUS_NECK_MM: 25.0,
  CTE_STEEL: 12.0e-6,
  CTE_PEEK: 47.0e-6,
  NOMINAL_LID_HEIGHT_MM: 40.0,
  BASELINE_TEMP_C: 20.0,
  MAX_CAPACITY_ML: 710.0,
  FL_OZ_TO_ML: 29.5735295625
};

function simulateTemporalSettlement(secondsDelayed = 4.0) {
  const requiredSettlement = 4.0;
  if (secondsDelayed >= requiredSettlement) return 1.0;
  return 1.0 + ((requiredSettlement - secondsDelayed) * 2.5);
}

function calculateThermalExpansionDelta(tLiquid, tLid) {
  const deltaTLiquid = tLiquid - METROLOGY_CONSTANTS.BASELINE_TEMP_C;
  const deltaTLid = tLid - METROLOGY_CONSTANTS.BASELINE_TEMP_C;
  const steelExpansionMm = METROLOGY_CONSTANTS.BODY_HEIGHT_MM * METROLOGY_CONSTANTS.CTE_STEEL * deltaTLiquid;
  const peekExpansionMm = METROLOGY_CONSTANTS.NOMINAL_LID_HEIGHT_MM * METROLOGY_CONSTANTS.CTE_PEEK * deltaTLid;
  return steelExpansionMm + peekExpansionMm;
}

// NOTE: this models the vessel as two stacked constant-radius cylinders with
// an abrupt radius change at BODY_HEIGHT_MM, not a curve-accurate integral
// over the real tapered shoulder profile. Volumes for fill levels right at
// BODY_HEIGHT_MM are an approximation.
function calculateStepCylinderVolume(rawLaserDistanceMm, structuralWarpMm) {
  const calibratedTotalHeight = METROLOGY_CONSTANTS.TOTAL_NOMINAL_HEIGHT_MM + structuralWarpMm;
  let fluidHeightMm = calibratedTotalHeight - rawLaserDistanceMm;
  if (fluidHeightMm <= 0) return { volumeMm3: 0.0, heightClamped: false };

  let heightClamped = false;
  if (fluidHeightMm > calibratedTotalHeight) {
    fluidHeightMm = calibratedTotalHeight;
    heightClamped = true;
  }

  const areaBody = Math.PI * Math.pow(METROLOGY_CONSTANTS.RADIUS_BODY_MM, 2);
  const areaNeck = Math.PI * Math.pow(METROLOGY_CONSTANTS.RADIUS_NECK_MM, 2);

  let volumeMm3;
  if (fluidHeightMm <= METROLOGY_CONSTANTS.BODY_HEIGHT_MM) {
    volumeMm3 = areaBody * fluidHeightMm;
  } else {
    const volumeBodyChunk = areaBody * METROLOGY_CONSTANTS.BODY_HEIGHT_MM;
    const heightRemainingInNeck = fluidHeightMm - METROLOGY_CONSTANTS.BODY_HEIGHT_MM;
    const volumeNeckChunk = areaNeck * heightRemainingInNeck;
    volumeMm3 = volumeBodyChunk + volumeNeckChunk;
  }

  return { volumeMm3, heightClamped };
}

function applyRoundingProtocol(integratedVolumeMm3) {
  const rawMl = integratedVolumeMm3 / 1000.0;
  let quantizedMl = Math.round(rawMl * 20) / 20; // nearest 0.05 mL
  let capacityCapped = false;
  if (quantizedMl > METROLOGY_CONSTANTS.MAX_CAPACITY_ML) {
    quantizedMl = METROLOGY_CONSTANTS.MAX_CAPACITY_ML;
    capacityCapped = true;
  }
  return { volumeMl: quantizedMl, capacityCapped };
}

function findInvalidTelemetryField(rawLaserDistanceMm, tLiquid, tLid, secondsDelayed) {
  if (Array.isArray(rawLaserDistanceMm)) {
    if (rawLaserDistanceMm.length === 0 || !rawLaserDistanceMm.every(Number.isFinite)) {
      return "rawLaserDistanceMm";
    }
  } else if (!Number.isFinite(rawLaserDistanceMm)) {
    return "rawLaserDistanceMm";
  }
  if (!Number.isFinite(tLiquid)) return "tLiquid";
  if (!Number.isFinite(tLid)) return "tLid";
  if (!Number.isFinite(secondsDelayed)) return "secondsDelayed";
  return null;
}

// Real ToF laser sensors reduce single-shot noise by averaging multiple raw
// readings per event ("burst sampling") -- see accuracy_validation.py for
// the measured effect (a ~6.7% real failure rate against a 1.0 mL/99%
// target drops to 0% at N=4 samples). Accepts either a single reading
// (unchanged behavior) or an array of raw readings to average.
function averageRawLaserDistance(rawLaserDistanceMm) {
  if (Array.isArray(rawLaserDistanceMm)) {
    const sum = rawLaserDistanceMm.reduce((total, sample) => total + sample, 0);
    return { averagedMm: sum / rawLaserDistanceMm.length, sampleCount: rawLaserDistanceMm.length };
  }
  return { averagedMm: rawLaserDistanceMm, sampleCount: 1 };
}

function processTelemetryPayload(rawLaserDistanceMm, tLiquid = 4.0, tLid = 45.0, secondsDelayed = 4.0) {
  const invalidField = findInvalidTelemetryField(rawLaserDistanceMm, tLiquid, tLid, secondsDelayed);
  if (invalidField) {
    return {
      status: "HHTR_INVALID_INPUT",
      invalidField,
      thermalWarpMm: null,
      sloshMultiplier: null,
      sampleCount: null,
      volumeMl: null,
      volumeFlOz: null
    };
  }

  const { averagedMm, sampleCount } = averageRawLaserDistance(rawLaserDistanceMm);

  // sloshMultiplier is reported for observability only -- it scales
  // simulated sensor noise in the research/test harness, never the
  // measured volume itself. See accuracy_validation.py for why: unsettled
  // fluid means a noisier raw reading, not a bigger real volume.
  const sloshMultiplier = simulateTemporalSettlement(secondsDelayed);
  const warpMm = calculateThermalExpansionDelta(tLiquid, tLid);
  const { volumeMm3: integratedMm3, heightClamped } = calculateStepCylinderVolume(averagedMm, warpMm);
  const { volumeMl, capacityCapped } = applyRoundingProtocol(integratedMm3);
  const volumeFlOz = Number((volumeMl / METROLOGY_CONSTANTS.FL_OZ_TO_ML).toFixed(2));
  const status = (heightClamped || capacityCapped) ? "HHTR_READING_CLAMPED" : "HHTR_READING_OK";

  return {
    status,
    thermalWarpMm: Number(warpMm.toFixed(5)),
    sloshMultiplier: sloshMultiplier,
    sampleCount,
    volumeMl: volumeMl,
    volumeFlOz: volumeFlOz
  };
}

async function processBatchTelemetry(payloads) {
  return Promise.all(payloads.map(p => {
    return processTelemetryPayload(p.rawLaserDistanceMm, p.tLiquid, p.tLid, p.secondsDelayed);
  }));
}

module.exports = { processTelemetryPayload, processBatchTelemetry };
