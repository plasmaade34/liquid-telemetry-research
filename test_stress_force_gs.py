"""
Tests for the stress_force-Gs.ipynb dynamic telemetry benchmark.

The notebook's code cell is executed (without its __main__ block) so the
tests always exercise exactly what ships in the notebook.
Run: python3 test_stress_force_gs.py
"""

import json
import os
import sys

import numpy as np

NOTEBOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stress_force-Gs.ipynb")


def load_notebook_namespace():
    with open(NOTEBOOK, encoding="utf-8") as f:
        nb = json.load(f)
    code = "".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    ns = {"__name__": "stress_force_gs"}
    exec(compile(code, NOTEBOOK, "exec"), ns)
    return ns


NS = load_notebook_namespace()
simulate, to_vol, metrics = NS["simulate"], NS["to_vol"], NS["metrics"]
kalman_1d, ekf, ekf_v10 = NS["kalman_1d"], NS["ekf"], NS["ekf_v10"]
transition, noisy_inputs = NS["transition"], NS["noisy_inputs"]
predicted_distance, observation_jacobian = NS["predicted_distance"], NS["observation_jacobian"]
monte_carlo = NS["monte_carlo"]
N, DT, WN, ZETA, A1 = NS["N"], NS["DT"], NS["WN"], NS["ZETA"], NS["A1"]

S42 = simulate(42)


def test_simulate_is_deterministic():
    a, b = simulate(7), simulate(7)
    assert all(np.array_equal(a[k], b[k]) for k in a)
    assert not np.array_equal(simulate(7)["d"], simulate(8)["d"])


def test_simulate_shapes_and_ranges():
    for k, v in S42.items():
        assert v.shape == (N,), k
        assert np.all(np.isfinite(v)), k
    assert S42["vol"][0] == 650.0 and S42["vol"][-1] == 450.0
    assert np.all(np.diff(S42["vol"]) < 0)
    assert np.all(S42["tilt"] >= 0)


def test_to_vol_clips():
    assert to_vol(np.array([-5.0]))[0] == 0.0
    assert to_vol(np.array([1e6]))[0] == 800.0


def test_metrics_perfect_and_offset():
    h_true = S42["h"]
    m = metrics(h_true, S42["vol"])
    assert m["mae"] < 1e-9 and m["max"] < 1e-9 and m["comp"] == 100.0
    off = metrics(h_true + 1.0 * 1000.0 / NS["AREA"] * 5, S42["vol"])  # +5 mL
    assert abs(off["mae"] - 5.0) < 1e-6 and off["comp"] == 0.0


def test_noisy_inputs_identity_and_determinism():
    tl, fi = noisy_inputs(S42, 1, 0, 0)
    assert np.array_equal(tl, S42["tilt"]) and np.array_equal(fi, S42["f_in"])
    a, b = noisy_inputs(S42, 1, 0.5, 0.1), noisy_inputs(S42, 1, 0.5, 0.1)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert not np.array_equal(a[0], S42["tilt"])


def test_transition_matches_simulator_recurrence():
    """C2: EKF slosh block must reproduce the simulator's symplectic Euler step."""
    F, B = transition()
    th, om, f = 0.013, -0.07, 0.4
    om_n = om + (f - 2*ZETA*WN*om - WN**2*th) * DT
    th_n = th + om_n * DT
    x = F @ np.array([100.0, th, om]) + B * f
    assert np.allclose(x[1:], [th_n, om_n], atol=1e-12)
    assert x[0] == 100.0


def test_transition_stability():
    """C2: v1.1 slosh block is stable; the v1.0 explicit-Euler one was not."""
    F, _ = transition()
    assert np.max(np.abs(np.linalg.eigvals(F[1:, 1:]))) <= 1.0
    F10 = np.array([[1, 0, 0], [0, 1, DT], [0, -WN**2*DT, A1]])
    assert np.max(np.abs(np.linalg.eigvals(F10[1:, 1:]))) > 1.0


def test_transition_rate_state():
    F, B = transition(rate=True)
    assert F.shape == (4, 4) and B.shape == (4,)
    assert F[0, 3] == DT and F[3, 3] == 1.0


def test_observation_model_inverts_sensor_model():
    """C1: with no noise/spikes the sensor and EKF models agree exactly."""
    k = 500
    h, th, tilt = S42["h"][k], 0.0, S42["tilt"][k]
    clean = (NS["H_TOT"] - h)/np.cos(tilt) + NS["YO"]*np.sin(tilt)
    assert abs(predicted_distance(h, th, tilt) - clean) < 1e-12
    assert abs(NS["H_TOT"] - predicted_distance(h, 0.0, 0.0) - h) < 1e-12


def test_jacobian_matches_finite_difference():
    eps = 1e-6
    for h, th, tilt in [(150.0, 0.0, 0.1), (120.0, 0.02, 0.3), (180.0, -0.03, 0.05)]:
        J = observation_jacobian(h, th, tilt, 4)
        dh = (predicted_distance(h + eps, th, tilt) - predicted_distance(h - eps, th, tilt)) / (2*eps)
        dth = (predicted_distance(h, th + eps, tilt) - predicted_distance(h, th - eps, tilt)) / (2*eps)
        assert abs(J[0, 0] - dh) < 1e-6 and abs(J[0, 1] - dth) < 1e-5
        assert J[0, 2] == 0 and J[0, 3] == 0


def test_estimators_output_shape_and_finite():
    for est in (kalman_1d(S42), ekf_v10(S42), ekf(S42), ekf(S42, rate=True)):
        assert est.shape == (N,) and np.all(np.isfinite(est))


def test_stage_ordering_regression():
    """Each corrected stage must beat the previous one; v1.0 EKF is the broken baseline."""
    mae = lambda h: metrics(h, S42["vol"])["mae"]
    raw, cos, k1 = mae(S42["h_raw"]), mae(S42["h_cos"]), mae(kalman_1d(S42))
    e3, e4, e10 = mae(ekf(S42)), mae(ekf(S42, rate=True)), mae(ekf_v10(S42))
    assert raw > cos > k1 > e3 > e4
    assert e10 > raw * 0.5
    assert e4 < 0.5 and e3 < 2.5
    assert metrics(ekf(S42, rate=True), S42["vol"])["comp"] > 95.0


def test_splash_gate_rejects_spikes():
    s = simulate(3)
    clean = dict(s); d = s["d"].copy(); d[100:110] += 20.0; clean["d"] = d
    spiked = ekf(clean, rate=True)
    base = ekf(s, rate=True)
    assert np.max(np.abs(spiked[100:110] - base[100:110])) < 3.0
    assert np.allclose(spiked[:100], base[:100])


def test_monte_carlo_structure_and_determinism():
    lv = [("ideal", 0, 0), ("0.5 deg", 0.5, .10)]
    a = monte_carlo(seeds=range(2), levels=lv)
    b = monte_carlo(seeds=range(2), levels=lv)
    assert list(a) == ["ideal", "0.5 deg"] and a == b
    for r in a.values():
        assert set(r) == {"1D", "3st", "4st"}
        assert all(len(v) == 2 and all(0.0 <= x <= 100.0 for x in v) for v in r.values())
    # 1D Kalman ignores IMU inputs, so it is identical across noise levels.
    assert a["ideal"]["1D"] == a["0.5 deg"]["1D"]
    # Rate-state EKF dominates the 3-state EKF in the ideal case.
    assert np.mean(a["ideal"]["4st"]) > np.mean(a["ideal"]["3st"])


def main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAIL {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
