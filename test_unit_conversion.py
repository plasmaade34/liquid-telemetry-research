"""
Golden test cases for unit_conversion.py, same pattern as the telemetry
engine's tests/test_vectors.json: known, independently-verifiable real
values, not just re-checking the code against itself.
"""
import sys
from unit_conversion import convert, convert_response

PASS = 0
FAIL = 0


def check(label, actual, expected, tol=1e-4):
    global PASS, FAIL
    ok = abs(actual - expected) < tol
    print(f"{'PASS' if ok else 'FAIL'}: {label} -> got {actual}, expected {expected}")
    if ok:
        PASS += 1
    else:
        FAIL += 1


# Pressure: verified against 1 psi = 6894.75729 Pa (exact, from lbf/in^2 definitions)
check("150 psi -> bar", convert(150.0, "psi", "bar"), 10.342135935)
check("100 psi -> bar", convert(100.0, "psi", "bar"), 6.8947573)
check("1 bar -> psi", convert(1.0, "bar", "psi"), 14.5037738, tol=1e-3)
check("1 bar -> pascal", convert(1.0, "bar", "pascal"), 100000.0)
check("101325 pascal -> psi (1 atm)", convert(101325.0, "pascal", "psi"), 14.6959, tol=1e-3)

# Temperature: verified against known reference points (water freeze/boil, human body temp)
check("32 F -> celsius (water freezes)", convert(32.0, "fahrenheit", "celsius"), 0.0)
check("212 F -> celsius (water boils)", convert(212.0, "fahrenheit", "celsius"), 100.0)
check("32 F -> kelvin", convert(32.0, "fahrenheit", "kelvin"), 273.15)
check("98.6 F -> celsius (human body temp)", convert(98.6, "fahrenheit", "celsius"), 37.0, tol=0.05)
check("0 celsius -> kelvin", convert(0.0, "celsius", "kelvin"), 273.15)

# Dimensionality guard: must reject incompatible units
try:
    convert(1.0, "psi", "fahrenheit")
    print("FAIL: dimension guard did not raise for psi -> fahrenheit")
    FAIL += 1
except ValueError:
    print("PASS: dimension guard correctly rejects psi -> fahrenheit")
    PASS += 1

# Full response shape, matching the example API output
resp = convert_response(100.0, "psi", "bar", precision=2)
check("response output.value", resp["output"]["value"], 6.89)
check("response canonicalSI.value", resp["canonicalSI"]["value"], 689475.73, tol=0.01)
assert resp["dimension"] == "Pressure [M1 L-1 T-2]", f"wrong dimension label: {resp['dimension']}"
print("PASS: response dimension label correct")
PASS += 1

print(f"\n{PASS}/{PASS + FAIL} checks passed")
sys.exit(1 if FAIL else 0)
