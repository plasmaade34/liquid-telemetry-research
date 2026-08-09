# Universal Substrate Mapping: Adapting Structural Math from Fluid Vessels to Aerospace Dynamics

**Author:** Ade Hodgins
**Category:** Applied Physics & Systems Engineering
**Drafting assistance:** Google Gemini helped write and structure earlier
drafts of this piece. Crediting that plainly, and correcting one place
where Gemini's drafting got ahead of what's actually been built and tested.

`#codeforthepeople` `#mentalhealthisnotforsale`

## Why these hashtags matter

Before the engineering and math: those two hashtags at the top aren't
decoration. When you spend weeks wrestling with structural physics,
building and testing algorithms, and stumbling into formulas that overlap
with real institutional research, the pressure to monetize, lock down, or
gatekeep it can make the whole thing feel transactional and exhausting.
Innovation shouldn't require a tollbooth, and sanity isn't a commodity to
trade away for corporate royalties. Keeping this open-source isn't just
about the code — it's about protecting your own peace, and treating a
genuine breakthrough as something worth handing to the people who'd build
on it, rather than fencing it off.

## The open-source vision

The plan is to release this framework publicly rather than spend the
energy fighting through patent bureaucracy for something that's arguably
an abstract mathematical relationship (courts have gone back and forth on
where that line sits under 35 U.S.C. § 101 — worth a real patent attorney's
opinion if a filing decision ever rides on it, not mine). The value isn't
in owning it; it's in the engineering standard being adopted and improved
on by whoever finds it useful. Full credit for deriving and structuring it
stays with the author; the math itself goes to whoever wants to build
something better with it.

## The problem with hardcoded material logic

Traditional CAD and structural modeling tools often rely on static material
constants. When sizing a double-walled vacuum vessel or pressurized
container, hardcoding parameters for one specific alloy — 304 Stainless
Steel, 6061 Aluminum — creates a rigid tool. Swap in a new composite or
polymer, and the structural and thermal calculations have to be rebuilt
from scratch.

`substrate_optimization_simulation.py` addresses the narrower, concrete
version of this problem: given a target internal/external pressure and a
material's yield strength, Young's modulus, Poisson's ratio, and density,
compute the required wall thickness and resulting mass, for any material
you plug in, not just the ones the tool ships with pre-coded. That part is
real, runs today, and produces a chart comparing steel, aluminum, and
titanium.

## The structural formula — and a correction

The formula, combining two well-established results:

```
t_opt = R · cuberoot( [4 P_delta (1 - v^2)] / E ) · Phi(sigma_y / rho)
```

Where:
- `R` = vessel radius
- `P_delta` = differential pressure load
- `E` = Young's modulus
- `v` = Poisson's ratio
- `Phi(sigma_y / rho)` = "specific strength adjustment coefficient"

The first part — `R · cuberoot([4 P_delta (1 - v^2)] / E)` — is real. It's
Timoshenko's elastic buckling formula for a thin cylindrical shell under
external pressure, and the script also computes the companion hoop-stress
formula (**Barlow's Formula, 1836**) for tearing/yield failure, taking
whichever result governs. Both are genuine, well-established, correctly
attributed formulas doing real work in the actual code.

**`Phi(sigma_y / rho)` is not.** Across two separate explanations of this
formula, it's described as "linking the safety factor to the
strength-to-weight ratio" and "automatically recalculating structural
limits" for any material — but neither explanation, nor the actual script,
ever defines what function `Phi` computes. There's no formula for it, no
derivation, and no line of code that implements it.
`substrate_optimization_simulation.py` computes `t_req = max(t_hoop,
t_buckle)` directly — no specific-strength scaling term anywhere. Adding
`Phi()` to the written formula made it look like there's a novel unifying
term behind the "universal" framing that isn't actually there yet.

That doesn't mean the idea behind it was wrong — folding a material's
strength-to-weight ratio into material selection *is* a real, standard
thing to want. It just needed to actually be derived and tested rather
than asserted. Here's the real version, from `material_efficiency_index.py`.

### What actually replaces Phi: two derived material indices, tested against real data

Rather than one undefined coefficient, there are two real ones — because
which one matters depends on which failure mode governs:

- **Yield-limited case** (Barlow's Formula governs): `t_hoop` is
  proportional to `1/sigma_y`, so mass is minimized by **maximizing
  `sigma_y / rho`** (specific strength) — a standard Ashby material index
  for a yield-limited thin-wall member.
- **Buckling-limited case** (Timoshenko governs): `t_buckle` is
  proportional to `E^(-1/3)`, so mass is minimized by **maximizing
  `E^(1/3) / rho`** — the corresponding Ashby index for a buckling-limited
  thin cylindrical shell.

Computed for the three materials in the simulation:

| Material | M_yield = σ_y/ρ | M_buckle = E^(1/3)/ρ |
|---|---|---|
| 304 Stainless Steel | 26,875 | 0.722 |
| 6061-T6 Aluminum | 102,222 | 1.518 |
| Titanium Grade 5 | 198,646 | 1.095 |

Notice the two indices **disagree** on which material is best: Titanium
leads on specific strength, but Aluminum leads on the buckling index. Which
one actually predicts real vessel mass depends entirely on which failure
mode governs for that pressure and geometry — you cannot pick a single
"best" material without knowing that first.

**Validated against the actual simulation, not assumed:**

- Across the original 0.1–10 atm sweep, buckling governs for all three
  materials at every pressure tested, and `M_buckle` predicts the correct
  mass ranking **100% of the time** in that regime. But that range never
  once exercises the yield-limited case, so on its own it says nothing
  about whether `M_yield` works.
- Extending the sweep to 0.1–1,200 atm (covering the pressure where hoop
  stress actually overtakes buckling for each material — 90 atm for Steel,
  217 atm for Aluminum, 957 atm for Titanium) surfaces the real limitation:
  **72% of that extended range (1,443 of 2,000 points) has the three
  materials governed by *different* failure modes simultaneously** — Steel
  and Aluminum already yield-limited while Titanium is still
  buckling-limited, for example. In that "mixed regime," a single index
  comparison doesn't cleanly apply at all; you have to run the actual
  per-material hoop/buckling calculation, there's no shortcut.
- In the remaining 557 "clean regime" points, where all three materials
  happen to share the same governing mode, the appropriate index predicts
  the correct mass ranking **100% of the time.**

So the honest result: the two derived indices are real and accurate
predictors *within* a shared failure-mode regime, but most of the
practical pressure range for these three materials together is a mixed
regime where no single index substitutes for running the real numbers.
That's a more useful and more honest answer than a universal `Phi()` — and
it's one that's actually been checked.

## Where this might apply — open questions, not shipped capabilities

**Vessels and containers.** The direct, real connection: sizing wall
thickness for a vacuum-insulated bottle or similar vessel under
differential pressure. This is what the script does today, for the project
it's actually part of.

**Infrastructure monitoring — untested speculation.** Could similar
hoop-stress/buckling math be relevant to municipal piping or pressure-vessel
monitoring at scale? Plausibly, in principle — the physics generalizes.
But there's no Google Earth integration, no geospatial data pipeline, and
no real-time monitoring system built anywhere. This is a "might be worth
prototyping" idea, not a demonstrated capability.

**Aerospace structures — untested speculation, further out than it looks.**
Barlow's Formula and Timoshenko buckling genuinely are used in aerospace
structural analysis, so the underlying physics isn't misplaced. But real
fuselage and payload structural design requires fatigue analysis, fracture
mechanics, combined dynamic load cases, damage tolerance, and a
certification process this project has never touched. There is no
"flight-ready" C++ or Rust implementation — none of this has been written
in either language, let alone validated against flight hardware. If this
is worth pursuing, the honest starting question is "does this formula even
hold up under a real aerospace load case," not a claim that the code
already does.

## The efficiency question, answered

**Given a target pressure rating, how much wall thickness — and therefore
mass and material cost — can be saved by choosing a better material, and
does that saving survive once buckling (not just hoop stress) becomes the
governing constraint?**

Answer, from real numbers: at 10 atm differential pressure on this vessel
(R = 100mm), buckling governs for all three materials, and Titanium
reduces mass by 34.6% vs. 304 Stainless Steel while needing a wall 15.7%
thinner than 6061-T6 Aluminum — both numbers matching the original chart's
headline claim closely. But that same chart doesn't mention that **Aluminum
actually has the lowest absolute mass of the three at that pressure**
(7.42 kg/m vs. Titanium's 10.24 kg/m and Steel's 15.65 kg/m) — which
matches exactly what `M_buckle` predicts (Aluminum has the highest buckling
index of the three). If minimizing mass is the actual goal at pressures
where buckling governs, Aluminum wins, not Titanium — worth knowing before
repeating the original headline as-is.

Reproduce all of this with `python substrate_optimization_simulation.py`
(the original comparison chart) and `python material_efficiency_index.py`
(the derived indices and their validation against real computed masses).
This is directly useful for other teams building similar vacuum or
pressure vessels — a real, checked answer to "which material minimizes
mass for my pressure target," without needing Google Earth or aerospace
certification to make it worth publishing.
