# Review 2026-09-17 — GESTALT documents — content (#44–53)

Part of the [whole-project review](README.md).

## P1 — GESTALT documents (content)

Plumbing is clean: identical 13-entry nav everywhere, all 45 cross-document
anchors resolve, no external resources, and about 40 citations spot-checked
are all real papers. Many paragraph-level numbers re-derive correctly: ARCA
1.006 g, LICHEN loads, hull equilibrium temperatures, the $32.9B budget.

44. **NAVIS is computed as a 50 m sphere and drawn as a 100–120 m spheroid.**
    *Re-checked.*
    - **The sphere:** `gestalt.html:987,1018` uses `4πr² = 7,854 m²`, giving
      24 kt.
    - **The spheroid:** the drawings, the cells doc and `params.py` use
      100–120 × 50 m, which has 13–16k m². At 3,050 kg/m² that is **41–48
      kt**.
    - **Knock-on:** hoop tension is 1.14–1.19 MN/m (not 0.65), and the
      thermal paragraph mixes both bodies.
    - **Fix:** pick one body and propagate it everywhere. **M**

45. **Micrometeoroid flux is about 10⁴ too low.** *Re-derived from Grün
    1985.*
    - **The error:** particles over 1 µg arrive at about 1.5 /m²/yr, against
      `~10⁻⁴` in the doc (`gestalt.html:675`). That is about 10⁵ hits per
      decade, not "~8".
    - **The same table** in the compendium (L817) has the same error.
    - **Fix:** replace the table and describe self-heal as continuous
      ablation. **S**

46. **The Metabolism energy budget doesn't close.**
    - **Oxygen:** oxidising 1.4 MW of organics needs about 9 t O₂/day, and
      the intima makes about 0.45 t. Electrolysing the rest costs more than
      the organics release.
    - **The ledger:** outputs exceed inputs.
    - **Fix:** name an oxidant in the rock (Fe(III), sulfate), or concede
      that growth is energy-limited. Drop "thermodynamically sound". **M**

47. **ARCA's shield and hoop load don't agree.** 10 m of slag is 1,500–3,000
    g/cm², not the stated 300. The drum's own mass adds about 300 MN/m, so
    the total is about 430 MN/m, not 230. **Fix:** make the shield
    non-rotating, or 1 m thick. **M**

48. **Cross-document conflicts.**
    - Ore:ship is 9:1 in Metabolism and 18× in the Compendium and Earth
      Program; the phosphorus arithmetic supports 18×.
    - Cells per hull: 10¹⁹, 5×10¹⁸ or 10²⁰, from hull volumes of 43k or
      87k m³.
    - TRL scores differ between the dossier and the fleet registry.
    - The Earth Program puts ITER at "$45B" in one place and "$25B" in
      another.
    - **Effort:** S each.

49. **Growth arithmetic contradicts the model.**
    - TESTUDO (150 kt in 2–3 yr) needs 164 t/day against a 26 t/day cradle.
    - SPORE doubles every 1.5 days, against the dossier's 38-day biology.
    - The dossier's own model reaches 6 kt at year 2.0, not year 1.
    - GRAVID gestation comes out at 3.6 years, not 2.5.
    - **Effort:** S–M.

50. **Citation quality.**
    - **Wrong numbers:** figures don't match their cited sources. BVAD REV1
      gives 0.816, not 0.84. "1 EB ≈ 5 g DNA" is Erlich 2017, not Church
      2012. LICHEN's Mars surface dose is Hassler 2014, not Zeitlin 2013.
      Biosphere 2's O₂ fell over 16 months and was then injected.
    - **Placeholders:** 15 references in Cells, Metabolism and Nervous are
      topic labels with no author, year or venue.
    - **Made-up titles:** several real papers carry invented titles (e.g.
      Ducat 2012).
    - **No DOIs** anywhere.
    - **Effort:** M.

51. **"Every claim is Python-grounded" can't be checked.**
    - No committed script reproduces the documents' numbers. `sim/` covers
      five systems, and nothing mentions Grün, 7,854, perchlorate or
      hydroxyapatite.
    - The README says "~154" citations in one place and "~108" in another;
      the actual count is about 80 unique works.
    - **Fix:** commit a `calcs/` module plus a check that compares its
      numbers with the documents. **M**

52. **Document accessibility.**
    - 11 SVGs with `role="img"` have no name (Cells, Metabolism, Nervous).
    - Light-theme accent text fails AA: chloro 3.09:1, osteo 3.78:1.
    - `[data-theme]` overrides are incomplete in 6 docs.
    - 61 tables have no `<caption>`, and headings skip h2→h4.
    - The 3D canvas has no label or keyboard control.
    - Phone width is fine.
    - **Effort:** M.

53. **Smaller document fixes.**
    - Three Class Reference profiles stop mid-sentence (L230, 262, 310),
      where the generator dropped text after an inline `<i>`.
    - The ARCA Coriolis drop lands anti-spinward, not spinward.
    - Habitat Plate VI says 1:20,000 in one place and 1:200,000 in another.
    - The perchlorate figure (0.5–1%) disagrees with its own source.
    - Speculation is stated as fact: seed viability "untouched", nerve
      conduction "tens of m/s".
    - Metabolism and Nervous lack the "concept, not a build spec" line.
    - The LEVIATHAN mass looks about 3× low *(suspected)*.
    - **Effort:** S each.
