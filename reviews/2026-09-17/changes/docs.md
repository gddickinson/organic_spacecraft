# Stream E · documents — changes (review 2026-09-17, items #44–53, #59)

Everything here is in the working tree, uncommitted. Nothing has been republished.

## Checks

```
python3 viewer/app.py --check     # all 13 documents + index load
python3 -m calcs --check          # 291 tagged numbers in 11 documents, 173 keys, 0 problems
python3 -m sim.run --check        # models run; params vs documents: 19 checks, 0 mismatches
```

An anchor and link scan found every in-document and cross-document `#anchor` resolving. The
13-entry navigation is identical in all documents, and every file is still a fragment that
starts at `<style>`.

## Documents to republish

All 13: `gestalt.html`, `-drawings`, `-habitat`, `-lichen`, `-gravid`, `-fleet`, `-classref`,
`-compendium`, `-cells`, `-metabolism`, `-nervous`, `-earthprogram`, `-3d`.
The 3D page changed only for accessibility and two spec strings. Every document had its
light-theme accent colours and theme overrides changed (#52).

## Assets

- **Regenerated with `rsvg-convert`:** `assets/figures/metab-energy.{svg,png}` and
  `metab-excrete.{svg,png}`.
- **Regenerated with `python -m sim.run`, about 25 s:** all four `assets/sim/*.gif`.
- **No stale PNGs.** The other figure SVGs differ from the documents only in `&amp;` escaping
  and an invisible `data-calc` attribute.
- **Redrawn in place, with no PNG:** the light-shield figure (Dossier), the Plate IV rim stack
  (Habitat) and the leverage chart (Fleet).

## New code

- `calcs/`: pure standard library, every file under 130 lines. See `calcs/INTERFACE.md`.
- `sim/doccheck.py`
- `sim/params.py` and `sim/systems.py`, reworked.

## README text to paste

**Contents list (line 23), fixing the broken anchor:**

    - [The thirteen documents](#the-thirteen-documents)

**Document table:**
- Row 1: "— 18 citations" → "— 19 citations".
- Row 2: "of the 120 m grown vessel" → "of the grown vessel (100 × 50 m body, ~120 m overall)".

**Growth-curve caption (line 120), append:**

> The five years assume the ship can power that growth; the rock alone can't (see Metabolism).

**GRAVID caption (line 147), replace the last sentence with:**

> Controlled feeding lifts the mining ceiling to ~26 t/day but cannot hurry the embryo's
> first, exponential year, so a NAVIS takes ~3.5 years in a cradle against ~5 in the wild.

**"How it makes a living" (lines 214–220), replace with:**

> A NAVIS grows at ~13 t/day, but photosynthesis on its whole lining can build only
> ~0.25 t/day; matching growth with sunlight would need **~33× the hull area**. So the ship
> does *not* photosynthesise its body. It eats the rock — but the rock is a fuel with almost
> no oxidiser. Its ferric iron and the intima's spare O₂ unlock only ~0.2–0.5 MW of the
> ~1.7–5.4 MW that growth needs. The five-year gestation therefore rests on a named bet: an
> electro-organ that imports sunlight-derived energy at ~10% efficiency.

- Figure alt text: "photosynthesis makes 0.25 t/day but growth needs 13; growth needs
  1.7–5.4 MW and the rock's own oxidants unlock only 0.2–0.5".
- Caption: "…growth is set by mining *and* by an energy supply the rock alone cannot give."

**Simulation table (lines 283–287):**
- ARCA: "the ~125-year O₂ reserve holding steady" → "a ~142-year O₂ reserve that the crew's
  RQ of 0.92 slowly drains (~1.8 points a century) unless mined carbonate tops up the CO₂".
- LICHEN: "stays a stable 293 K" → "is a thermal RC circuit (τ ≈ 0.5 yr), settling near 280 K
  with its people's heat".

**"By the numbers" (lines 321–340):**
- Intro: "grounded in a Python calculation" → "recomputed by `calcs/` and checked against the
  documents (`python -m calcs --check`)".
- NAVIS row: "**100 × 50 m body (~120 m overall) · ~24,000 t · crew 50 · grown ~5 yr**".
- New row: "| NAVIS wall | **5.5 m · ~215 g/cm² · ~13,400 m²** | Dossier |".
- GRAVID row: "**12–24 cradles · ~26 t/day each · ~3.5 yr per ship**".
- Feeding row: "**mines ~240 t/day rock → 13 t/day tissue (~18:1, phosphorus-set); energy must be
  imported; photosynthesis only breathes**".
- This documentation: "**13 documents · 162 reference entries (~98 distinct works, 96 DOIs)**".

**"Honest by construction" (lines 352–357):**
- Replace the "Python-grounded" bullet with:

  > **Checked, not asserted.** 291 numbers across 11 documents carry a `data-calc` tag, and
  > `python -m calcs --check` recomputes each from the physics and fails on any drift. The
  > 2026-09 review caught a 50 m sphere standing in for the drawn 100 × 50 m hull, a
  > micrometeoroid flux 10⁴ too low, an unclosed energy budget and a spinning drum whose own
  > weight was missing from its hoop load.
- "~108 references" → "~98 cited works (162 reference entries, 96 with DOIs)".

## By item

#44 reference body; #45 micrometeoroids; #46 energy budget; #47 ARCA; #48 conflicts;
#49 growth; #50 citations; #51 `calcs`; #52 accessibility; #53 small fixes; #59 root `sim/`.
The report to the coordinator gives the details.
