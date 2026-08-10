# Contributing

Thanks for considering a contribution. This project's whole reason for
existing is a case study in *not* trusting confident-sounding claims
without checking them (see "Why this repo exists" in the README) — so the
bar for contributions is the same standard the existing code was held to,
not a formality layered on top of it.

## The one real rule: show your work

- **If you add a formula, constant, or claim, source it.** A citation is a
  standard, a datasheet part number, a textbook edition, or a link to a
  paper — not "this is standard practice" asserted without a reference.
  See `RELATED_WORK.md` for the shape this should take.
- **If you add a number (an accuracy figure, a failure rate, a
  percentage), show how it was computed**, ideally with a script anyone
  can re-run, the way `accuracy_validation.py` and
  `material_efficiency_index.py` do. A single run isn't a claim — see the
  multi-seed validation methodology in `accuracy_validation.py` if your
  change touches anything statistical.
- **If you're not sure a claim holds, say so in the PR description**
  rather than asserting it confidently. Honest uncertainty here is a
  feature, not a weakness — it's the entire reason `simulation_reference.py`
  is kept around as a "before" example instead of deleted.

## Before opening a PR

1. **Run the golden vector tests** — all three ports need to agree:
   ```
   node tests/run_vectors.js
   python tests/run_vectors.py
   g++ -std=c++17 -O2 -o run_vectors_cpp tests/run_vectors.cpp && ./run_vectors_cpp
   ```
   All three should report 24/24 (or more, if you added vectors — see
   below).
2. **If you touch `telemetry_volume_engine.{js,py,hpp}`**, add or update a
   case in `tests/test_vectors.json` covering it, and confirm all three
   ports still agree on the new case. A change that only one port
   reflects is exactly the kind of silent divergence the golden vectors
   exist to catch (see the README's "Known limitations" for two real bugs
   found this way: a rounding-tie mismatch and a C++ bool-coercion bug).
3. **Run the Python scripts you touched** (`accuracy_validation.py`,
   `substrate_optimization_simulation.py`, `material_efficiency_index.py`)
   and confirm they still run clean.
4. **Don't fix `simulation_reference.py`.** It's deliberately preserved
   as a flawed "before" case study (see the README's file description) —
   if you find something else wrong with it, note it in a PR comment or a
   doc instead of patching it in place.

## Style

- Prefer explicit derivations over asserted formulas — see
  `material_efficiency_index.py`'s docstring for the shape ("derived, not
  assumed").
- Match the existing tone: state what's real and verified plainly, and
  flag what's assumed, untested, or speculative just as plainly (see
  STRUCTURAL_FRAMEWORK_NOTES.md's "open questions, not shipped
  capabilities" section for the pattern). Avoid certification, compliance,
  or "grade" language (e.g. "aviation-grade," "certified," "flight-ready")
  unless the project has actually been through that specific process --
  none of it has, so far.

## Questions

Open an issue. If it's about whether a claim in this repo actually holds
up, that's a genuinely welcome kind of issue to open here specifically.
