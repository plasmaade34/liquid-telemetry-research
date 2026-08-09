"""
Cross-language golden vector test runner (Python side).
Run: python tests/run_vectors.py
Companion: tests/run_vectors.js must produce identical results against the
same tests/test_vectors.json -- that agreement is the whole point.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from telemetry_volume_engine import process_telemetry_payload

VECTORS_PATH = os.path.join(os.path.dirname(__file__), "test_vectors.json")


def main():
    with open(VECTORS_PATH) as f:
        vectors = json.load(f)

    failures = 0
    for v in vectors:
        i = v["input"]
        raw = i.get("rawLaserDistanceMm")
        t_liq = i.get("tLiquid", 4.0)
        t_lid = i.get("tLid", 45.0)
        sec = i.get("secondsDelayed", 4.0)
        actual = process_telemetry_payload(raw, t_liq, t_lid, sec)
        expected = v["expected"]
        if actual != expected:
            failures += 1
            print(f"MISMATCH [{v['name']}]")
            print(f"  expected: {expected}")
            print(f"  actual:   {actual}")

    print(f"\n{len(vectors) - failures}/{len(vectors)} vectors match")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
