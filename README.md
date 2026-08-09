# Liquid Telemetry Research

Open research on thermal-compensated volume estimation from a time-of-flight
(ToF) laser liquid-level sensor, published by **Hodgins Holdings**.

The core problem: estimate how much liquid is in a vessel from a single
distance reading off the fluid surface, correcting for thermal expansion of
the vessel body and lid, while staying within a target accuracy (1.0 mL,
99% reliability).

## Who this is for

Developers and engineering teams building or reviewing sensor-based
measurement pipelines -- liquid-level, fill-volume, or any other physical
quantity estimated from a noisy single-shot reading. Two things here are
meant to be reusable outside this specific bottle-and-laser problem:

- **The statistics**: multi-sample averaging as a real noise-reduction
  technique, and the multi-seed validation methodology (`run_multi_seed_
  validation`) for telling a true failure rate apart from a single lucky
  or unlucky draw.
- **The cautionary pattern**: a filter that rescales a *reported* error
  metric without touching the underlying measurement. If you maintain a
  QA/telemetry pipeline, `simulation_reference.py`'s "Kalman filter"
  section is worth reading as a checklist item for your own code, not
  just this one.

## Why this repo exists

Working through this problem surfaced a case study worth publishing on its
own: a "Kalman filter" step in an earlier iteration of the simulation
turned out not to improve measurement accuracy at all. It rescaled the
*reported* error by a fixed factor before checking it against the pass/fail
threshold, without changing the actual computed volume. The QA report said
"100% accurate" while the underlying measurement was exactly as noisy as
before.

That's a general trap, not specific to this problem: it's easy to build a
filter that makes a metric look better without making the thing the metric
measures better. This repo keeps both versions side by side — the flawed
one and the real fix — so the difference is visible and checkable, not just
asserted.

## Root cause and the real fix

A single ToF laser reading carries about 0.15mm of Gaussian noise. In the
vessel's wide body (cross-sectional area ~3526 mm²), that noise is amplified
by the cross-section into ~0.53 mL of volume noise per reading — enough to
exceed a 1.0 mL / 99%-reliability target roughly 5-7% of the time, from
sensor physics alone.

The real fix is averaging multiple raw laser samples per reading before
computing volume ("burst sampling," standard practice for real ToF
sensors), which reduces noise by `1/sqrt(N)`.

A single seeded 1,000-sip run is one draw from a distribution, not the
true failure rate -- an earlier version of this README reported "N=4:
0/1000 failures (0.00%)" from exactly one such draw, which overstated the
case. The honest number comes from aggregating 200 independent trials
(200,000 total readings per N), judging pass/fail on real, unmodified
error the whole time:

| Samples averaged (N) | Mean failure rate | Worst single trial | 95% upper bound |
|---|---|---|---|
| 1 | 5.268% | 7.90% | 5.37% |
| 2 | 0.663% | **1.30%** | 0.70% |
| 3 | 0.094% | 0.60% | 0.11% |
| 4 | 0.016% | 0.20% | 0.023% |
| 5 | 0.004% | 0.10% | 0.007% |

`N=4` is used throughout because it holds a consistent margin under the 1%
target across all 200 trials tested -- not because a single run happened
to show zero failures. `N=2`'s worst observed trial (1.30%) actually
breaches the 1% reliability target, so it does not reliably meet the goal
the way a single lucky 0.90%-failure draw would suggest. Reproduce this
with `python accuracy_validation.py` (`run_multi_seed_validation`).

## Files

- **`telemetry_volume_engine.js`** — the production-shaped volume engine:
  thermal expansion model, step-cylinder volume integration, rounding, and
  input validation. Accepts either a single raw distance reading or an
  array of readings to average (the real fix, applied in the engine
  itself).
- **`telemetry_volume_engine.py`** — a deliberate line-for-line Python port
  of the JS engine above (same constants, same status strings), kept
  separate from `simulation_reference.py`/`accuracy_validation.py` so it
  can be checked against the JS version with shared test vectors instead
  of just being assumed to agree.
- **`simulation_reference.py`** — the original reference simulation,
  preserved as a three-iteration case study: an honest loop, a
  rescaled-error loop that looks like an improvement but isn't, and a
  unit-conversion (mL / fl oz) report built on the same rescaling. Kept
  deliberately unfixed as the "before" side of the comparison.
- **`accuracy_validation.py`** — the "after" side: same reporting shape as
  `simulation_reference.py`'s unit-conversion report, but using real
  multi-sample averaging and judging pass/fail on unmodified error. Run it
  directly (`python accuracy_validation.py`) to reproduce the table above.
- **`telemetry_volume_engine.hpp`** — header-only C++ port of the same
  engine. C++ is statically typed, so the "non-numeric input" invalid
  cases in the shared vectors don't have a literal equivalent (that class
  of error is a compile error here, not a runtime one); `NaN` is used as
  the natural stand-in, mapped from the vectors' string sentinels by the
  C++ test runner. See the file's header comment for the full reasoning.
- **`tests/test_vectors.json`** — 24 golden input/output pairs covering
  both zones, height and capacity clamping, extreme temperatures, every
  settlement state, multi-sample arrays, and every invalid-input path.
  Generated from the JS engine and independently verified against the
  Python and C++ ports. Run `node tests/run_vectors.js`,
  `python tests/run_vectors.py`, and
  `g++ -std=c++17 -O2 -o run_vectors_cpp tests/run_vectors.cpp && ./run_vectors_cpp`
  (all from the repo root) — all three currently report 24/24.
- **`substrate_optimization_simulation.py`** — separate from the telemetry
  question: sizes vessel wall thickness for 304 Stainless Steel, 6061-T6
  Aluminum, and Titanium Grade 5 under external pressure, using Barlow's
  Formula and Timoshenko's elastic buckling equation.
- **`material_efficiency_index.py`** — derives and validates the actual
  material indices for minimum-mass vessel design (`sigma_y/rho` for
  yield-limited walls, `E^(1/3)/rho` for buckling-limited walls), tested
  against the simulation above rather than asserted. See
  `STRUCTURAL_FRAMEWORK_NOTES.md` for the full write-up, including what
  this replaced (an undefined "universal" coefficient from an earlier
  draft) and where the indices do and don't apply.

## Known limitations

- The volume model treats the vessel as two stacked constant-radius
  cylinders with an abrupt radius change at the shoulder, not a
  curve-accurate integral over the real tapered profile. This is an
  approximation near the shoulder transition.
- The thermal expansion model assumes the steel body tracks liquid
  temperature and the lid tracks ambient/lid temperature; it hasn't been
  validated against real thermal-soak measurements.
- The 0.15mm single-shot laser noise figure is an assumed value carried
  over from the source material, not a cited sensor datasheet spec or a
  measured value from real hardware. Treat every accuracy number here as
  conditional on that assumption.
- The multi-sample averaging validation generates its own "ground truth"
  by inverting the same step-cylinder volume formula it tests against.
  That's sufficient to prove the statistics (averaging N i.i.d. Gaussian
  samples reduces variance by `1/sqrt(N)`), but it does not independently
  validate the geometry or thermal model against a real vessel or sensor.
- Burst-sample averaging assumes each raw reading's noise is independent.
  Real ToF sensors can have correlated noise across a burst (ambient light
  drift, thermal drift during the capture window), which would erode the
  `1/sqrt(N)` gain below what's reported here.
- All three ports (`telemetry_volume_engine.js`, `.py`, `.hpp`) agree on
  all 24 golden vectors, but getting there required explicitly matching
  JS's round-half-away-from-zero (`Math.round`/`toFixed`) in both other
  ports, instead of Python's default round-half-to-even (`round()`) or
  relying on `std::round`'s own tie-breaking rule in C++ (which, as it
  happens, differs from JS `Math.round` at *negative* ties: JS rounds
  -2.5 to -2, `std::round` rounds it to -3 -- see the header comment in
  `telemetry_volume_engine.hpp`). All three ports now use the same
  explicit round-half-away-from-zero helper rather than trusting each
  language's default.
- The C++ test runner (`tests/run_vectors.cpp`) includes a small
  hand-written JSON parser (`tests/json_mini.hpp`) scoped only to this
  repo's test vector format -- it's not a general-purpose library and
  shouldn't be treated as one.
- `simulation_reference.py` was transcribed from a PDF export of a
  research notebook (not a raw `.ipynb`); a handful of long lines were
  clipped at the page edge in that export and are reconstructed inline
  (marked `# [reconstructed: clipped in source]`).

## License

MIT — see [LICENSE](./LICENSE).
