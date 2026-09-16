// Cross-language golden vector test runner (JavaScript side).
// Run: node tests/run_vectors.js
// Companion: tests/run_vectors.py must produce identical results against
// the same tests/test_vectors.json -- that agreement is the whole point.

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { processBatchTelemetry, processTelemetryPayload } = require('../telemetry_volume_engine.js');

const vectorsPath = path.join(__dirname, 'test_vectors.json');
const vectors = JSON.parse(fs.readFileSync(vectorsPath, 'utf8'));

let failures = 0;

async function main() {
  for (const v of vectors) {
    const i = v.input;
    const actual = processTelemetryPayload(i.rawLaserDistanceMm, i.tLiquid, i.tLid, i.secondsDelayed);
    try {
      assert.deepStrictEqual(actual, v.expected);
    } catch (e) {
      failures += 1;
      console.log(`MISMATCH [${v.name}]`);
      console.log(`  expected: ${JSON.stringify(v.expected)}`);
      console.log(`  actual:   ${JSON.stringify(actual)}`);
    }
  }

  const defaultArgsExpected = vectors.find(v => v.name === 'default_args_only').expected;
  const invalidExpected = {
    status: 'HHTR_INVALID_INPUT',
    invalidField: 'rawLaserDistanceMm',
    thermalWarpMm: null,
    sloshMultiplier: null,
    sampleCount: null,
    volumeMl: null,
    volumeFlOz: null
  };
  const batchCases = [
    {
      name: 'batch_handles_malformed_items',
      payloads: [{ rawLaserDistanceMm: 50 }, null, 7, ['bad']],
      expected: [defaultArgsExpected, invalidExpected, invalidExpected, invalidExpected]
    },
    {
      name: 'batch_handles_non_array_input',
      payloads: null,
      expected: [invalidExpected]
    }
  ];

  for (const t of batchCases) {
    const actual = await processBatchTelemetry(t.payloads);
    try {
      assert.deepStrictEqual(actual, t.expected);
    } catch (e) {
      failures += 1;
      console.log(`MISMATCH [${t.name}]`);
      console.log(`  expected: ${JSON.stringify(t.expected)}`);
      console.log(`  actual:   ${JSON.stringify(actual)}`);
    }
  }

  const totalCases = vectors.length + batchCases.length;
  console.log(`\n${totalCases - failures}/${totalCases} vectors match`);
  process.exit(failures === 0 ? 0 : 1);
}

main();
