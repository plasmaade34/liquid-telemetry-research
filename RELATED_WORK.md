# Related Work

This is different from the patent-claims bibliography this project's
drafting process also produced. That table was trying to manufacture
legal support for claims that overreached what's actually built (see
`STRUCTURAL_FRAMEWORK_NOTES.md` and the repo's history for that story).
This page does the opposite: it credits real, verified prior art and
foundational work in the fields this project touches or generalizes
toward, without claiming this project implements, surpasses, or is
affiliated with any of it. Everything below was independently checked,
not taken on faith from an earlier draft.

## Aircraft fuel systems (an adjacent field this project does not implement)

This project is a handheld-bottle liquid-level estimator. Aircraft fuel
sensing is a genuinely related but much more mature and demanding field,
and it's worth being explicit about what already exists there rather
than implying novelty this project doesn't have:

- **US Patent 5,138,559 A** — Kuehl, J.W. & Capps, J.W. (assigned to The
  Boeing Company), *System and method for measuring liquid mass
  quantity*, issued 1992. Real prior art: aircraft fuel tank liquid
  mass/volume determination using pressure, temperature, attitude
  (roll/pitch), and acceleration sensors. This is the same underlying
  problem (infer liquid quantity from indirect sensor readings) solved
  decades ago at flight scale with a different sensor modality than the
  ToF laser used here.
- **US Patent 6,671,648 B2** — *Micro inertial measurement unit*, issued
  2003. Real prior art for MEMS IMU motion sensing. Relevant if
  tilt/motion compensation is ever added to this project — it currently
  is not (see README known limitations).
- **Hall, J., Rendall, T.C.S., Allen, C.B., & Peel, H. (2015).** "A
  multi-physics computational model of fuel sloshing effects on
  aeroelastic behaviour." *Journal of Fluids and Structures*, 56, 11–32.
  https://doi.org/10.1016/j.jfluidstructs.2015.04.003 — real, published
  research on fuel slosh dynamics. This project's `simulate_temporal_
  settlement` / slosh multiplier is a crude placeholder for the same
  underlying phenomenon (fluid motion after a disturbance), not a real
  slosh model in this sense.
- **MIL-STD-810H, Method 513.8 (Acceleration)** — U.S. Dept. of Defense,
  2019. Real environmental test standard for structural/operational
  testing under steady-state and transient inertia loads. Cited here for
  context on what a real acceleration-qualified system is tested against
  — not a standard this project meets or claims to meet.
- **14 CFR § 25.955 (Fuel flow)** — FAA airworthiness regulation
  requiring at least 100% of required fuel flow under intended operating
  conditions. Cited for scale/context on the regulatory bar that exists
  in real aviation fuel systems.

## Volumetric metrology standards

- **ISO 4787** — *Laboratory glassware — Volumetric instruments —
  Methods for testing of capacity.* Establishes 20°C as the standard
  reference temperature for volumetric calibration — matching
  `BASELINE_TEMP_C` in this project's thermal model.
- **ASTM E542** — *Standard Practice for Calibration of Laboratory
  Volumetric Apparatus.* Same 20°C reference-temperature convention.
- **NIST Handbook 44** — *Specifications, Tolerances, and Other
  Technical Requirements for Weighing and Measuring Devices.* Free and
  public (nist.gov). The real U.S. legal-metrology standard already
  invoked by name in this project's original status strings, and the
  source convention for the exact NIST fluid-ounce-to-milliliter factor
  (29.5735295625) used throughout.

## Materials selection methodology

- **Ashby, M.F. (2005).** *Materials Selection in Mechanical Design*
  (3rd ed.). Butterworth-Heinemann / Elsevier. This is the actual
  methodology `material_efficiency_index.py` implements: deriving a
  material index (e.g. σ_y/ρ for a yield-limited member, E^(1/3)/ρ for a
  buckling-limited shell) from the governing failure mode to identify
  the minimum-mass material for a given constraint. Used directly but
  not previously credited by name.
- **Timoshenko, S.P. & Gere, J.M. (1961).** *Theory of Elastic
  Stability* (2nd ed.). McGraw-Hill. The standard reference for the
  elastic buckling formula used in `substrate_optimization_simulation.py`.
- **Barlow, P. (1836/1837).** Formula presented to the Institution of
  Civil Engineers in 1836, published in *A Treatise on the Strength of
  Timber, Cast Iron, and Wrought Iron* (1837). The hoop-stress formula
  used alongside Timoshenko buckling in the same script.
