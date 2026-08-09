// Cross-language golden vector test runner (JavaScript side).
// Run: node tests/run_vectors.js
// Companion: tests/run_vectors.py must produce identical results against
// the same tests/test_vectors.json -- that agreement is the whole point.

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { processTelemetryPayload } = require('../telemetry_volume_engine.js');

const vectorsPath = path.join(__dirname, 'test_vectors.json');
const vectors = JSON.parse(fs.readFileSync(vectorsPath, 'utf8'));

let failures = 0;

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

console.log(`\n${vectors.length - failures}/${vectors.length} vectors match`);
process.exit(failures === 0 ? 0 : 1);
