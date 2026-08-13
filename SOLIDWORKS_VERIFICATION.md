# SolidWorks verification for `vacuum_wall_example.py`

**Important: this has not been run in SolidWorks by me.** I have no access
to SolidWorks and no way to test or confirm this myself -- these are exact,
reproducible steps for you (or anyone else) to independently check the
predicted numbers against a real CAD/FEA tool. Treat every number below as
a prediction to be checked, not a verified result, until you've actually
run it.

## What to check

`vacuum_wall_example.py` predicts, for the real bottle body radius
(33.5 mm) under 1 standard atmosphere of external differential pressure
(a vacuum-insulated double wall), in 304 Stainless Steel:

- **Required wall thickness: 0.4769 mm** (governed by buckling, not hoop
  stress -- Timoshenko's formula gives a larger required thickness than
  Barlow's here)
- Buckling governs because the wall is thin relative to the radius; hoop
  stress alone would only require 0.0237 mm

## Steps to verify in SolidWorks

1. **Build the part.** A thin-walled cylindrical shell, R = 33.5 mm outer
   radius (or R = 33.5 mm to the shell's mid-surface -- decide which
   convention and stay consistent), any reasonable length (the formulas
   here treat it as effectively infinite/long, so buckling per unit
   length -- a length of a few times the radius, e.g. 150-200 mm, avoids
   short-cylinder end effects).
2. **Assign the material.** 304 Stainless Steel from the SolidWorks
   material library (or input manually: yield strength 215 MPa, Young's
   modulus 193 GPa, Poisson's ratio 0.29, density 8000 kg/m^3 -- these
   should match the library value closely; if they don't, that's worth
   noting, not ignoring).
3. **Apply the load.** External pressure, 101325 Pa (14.6959 psi) — SolidWorks
   accepts either unit directly in the load dialog, so this step alone
   double-checks the unit_conversion.py output too.
4. **Run a Linear Buckling study** (not just static stress) — this is the
   governing failure mode per the prediction, so a static-only study
   would miss it. Use a wall thickness of 0.4769 mm and check the
   reported buckling load factor (BLF).
5. **What "verified" looks like:** a BLF at or near 1.0 (not comfortably
   above or below it) at t = 0.4769 mm indicates the prediction and the
   FEA result agree, since the safety factor (1.5) was already built into
   the predicted thickness -- BLF should land close to 1.0/1.5 ≈ 0.67 if
   you re-apply the raw (non-safety-factored) pressure, or close to 1.0
   if you apply pressure × 1.5 directly. Decide which convention you're
   checking and be explicit about it.
6. **If the numbers disagree by a lot** (not just FEA-vs-closed-form
   noise, which is normal and usually small for thin shells), that's a
   real finding worth writing up -- it would mean either the formula
   application here has an error, or there's a real modeling
   discrepancy worth understanding. Don't just discard whichever number
   is inconvenient.

## Why this matters for credibility

Anyone at Google (or anywhere else) who actually checks this in a real
tool and gets a matching result has independently confirmed the claim
themselves, not just trusted a script's own output. That's a stronger
form of verification than anything I can produce alone -- worth doing
before this number goes into anything more formal than a repo example.
