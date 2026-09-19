# Session log, part 28 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-26 to 2026-07-27; undated entries keep their original place.

## 2026-07-27 — SEEDFALL: five technologies, not one

- **Hull roster 21 → 35, stations 12 → 19**, across five technology families
  rather than three. The GESTALT grown fleet is now one option among several
  instead of the only real choice.
- **Two new families.** *Synthetic* — Dry Choir vessels (CANTOR, LATTICE,
  ORDINAL, THEOREM): crewless, no atmosphere plant, a photonic skin over a
  spaceframe wrapped around a substrate vault, superb instruments and no
  self-repair whatsoever. *Xeno* — REVENANT and ANTIPHON, laid down to a plan
  nobody in the Verge wrote; they mend like a grown hull and ring audibly when
  something large moves nearby.
- **Seven new fabricated hulls** filling the gaps the Yards line had — TENDER
  (tug), AWL (smuggler), KILN (mobile refinery), CARAVEL (passenger liner),
  SPINDLE (deep survey), PORTCULLIS (system monitor), HAMMERFALL (siege) — plus
  the MIDDEN hybrid ship-breaker.
- **Eight new stations spanning the technologies**: Orbital Drydock, Refinery
  Platform, Monitor Station and Helium Skimmer (fabricated), Free Port (hybrid),
  Relay Choir (synthetic) and Reactivated Array (xeno).
- **Two new station mechanics.** A **Free Port** opens a market in a system that
  had none, which is worth considerably more than its docking fees. A **Monitor
  Station** wards its system: it slows the Bloom, burns back what it can reach,
  and — since it is the thing with the guns — defends itself far better than the
  farm next door. Averaged over eight trials, two unattended years take a system
  from 0.24 to 0.75 infestation; watched, it falls to 0.20.
- **Three new technologies** (Autonomous Munitions, Synthetic Cognition, Xenolith
  Metallurgy) and ten new parts, including a smelter bay that turns ore into
  alloy in the hold on the way home.
- **Structural change**: hulls moved out of `data/chassis.py` into
  `hull_types.py` (layer stacks and the family rules), `hulls_grown.py` and
  `hulls_built.py`, with `chassis.py` reduced to the registry. Every import site
  in the game was left untouched, and no file crossed 500 lines.
- **Six new checks** covering the new ground: every family complete and coherent
  (layer weights summing to one, a critical layer, a build requirement, a tint);
  the graft rules that let a hybrid take an intima and refuse a coherent beam;
  only the mechanical families refusing to heal; every station's effect keys
  drawn from a closed vocabulary; the Free Port opening a real market; and the
  monitor ward. That last one caught two real bugs — the station was being eaten
  by the Bloom before its ward could apply, and the hull picker kept editing a
  SPORE while showing you synthetic hull cards. Suite now 27 simulation + 15
  interface checks.

## 2026-07-27 — SEEDFALL: the programme as a playable RPG (PyQt6)

- **New `seedfall/` package**: a native desktop space exploration / trading /
  combat RPG — a modern Starflight with a Civilization layer — built entirely on
  the thirteen documents. PyQt6, 53 modules, every file under the 500-line limit,
  no server and no build step. `python -m seedfall`.
- **The documents are the mechanics, not the flavour.** The Class Reference
  becomes 21 hull chassis; the Dossier's six-layer hull becomes the damage model
  (shots ablate epidermis → rind → mycelium → osteoid, and the crew only starts
  dying when the pneumostat opens); Metabolism becomes the economy, with
  phosphorus scarce because chondrite is 0.1% P; the Cell Atlas becomes the
  fittings; the Nervous System becomes a cognition branch where you must *buy*
  silicon because nobody can grow a processor; the Compendium becomes a 58-node,
  ten-branch tech tree; and the Registry's six named containment failures become
  the six factions — including the Bloom, a lineage with its Hayflick counter cut
  out, which simply grows.
- **Design intent — many paths.** Grown / fabricated / hybrid hull families with
  real trade-offs (grown heals but gestates for months and eats phosphate;
  fabricated is instant, expensive and never repairs itself). Combat on a
  five-band range track where destruction is only one win condition: resolve lets
  a TESTUDO with no weapons at all win by outlasting, which is the programme's
  actual doctrine. Five simultaneous victory conditions (Containment, Exodus,
  Concord, Genesis, Dominion).
- **Built first as a browser build, then ported to PyQt6 and the web build
  retired**, so there is exactly one implementation of the rules and no chance of
  the two drifting apart. The `/game` viewer route was removed with it.
- **Tested headlessly, and it mattered.** `python -m seedfall.tests` runs 21
  simulation checks and 15 interface checks; the interface suite builds the real
  `MainWindow` on Qt's `offscreen` platform and paints every screen and tab,
  including a live engagement. Between the two builds the suites caught nine real
  defects, several of them unplayable: sector generation that could **strand the
  player with nothing in jump range** (fixed with a lane-relaxation pass
  guaranteeing every star has a neighbour within a starting jump); combat that
  **never terminated** because armour could fully null a weapon (armour now floors
  at 15% leak-through, plus late-onset resolve attrition and a turn cap); weapon
  mounts beyond the first doing nothing (added the full-salvo order); hulls so
  large relative to damage that an escape pod drove off a battleship (hull scale
  retuned — fights now run ~18 turns and span destroyed / driven-off / lost);
  derived ship stats being written into save files; a negative ice-harvest rate
  from the reaction organ's fuel draw; and a clipped HUD caption.
- `seedfall/INTERFACE.md` documents the module map, the one-directional layer
  rule (`data → world → sim → ui`), and the constants that will bite anyone
  retuning it. Root `INTERFACE.md` and `README.md` updated.

## 2026-07-26 — Working 3D models (glTF/OBJ/STL) + an interactive viewer

- **New `models3d/` package**: builds solid, colour-coded 3D meshes of the
  seven main designs (trimesh) and exports each to **three working formats** —
  `.glb` (glTF, coloured), `.obj`, and `.stl` (printing) — into
  `assets/models3d/`, plus a preview PNG. Modular: `build.py` (per-design mesh
  builders), `render.py` (matplotlib preview), `run.py` (CLI
  `python -m models3d.run [--check]`). `dome_half` is hand-triangulated so it
  needs no external triangulation engine; each GLB is round-trip-validated.
- **Interactive gallery in the local viewer**: added a `/models` route
  (`viewer/models_page.py`) that shows the models lit, rotatable and AR-capable
  via `<model-viewer>`, with download links, plus static serving of the
  glb/obj/stl at `/models/<file>` (path-traversal guarded) and a "Working 3D
  Models" card on the landing page.
- README gains a "Working 3D models" section with the seven previews. Verified
  every mesh by eye from a rendered frame (fixed the preview's cross-part depth
  sorting so the LICHEN/TESTUDO domes show).

## 2026-07-26 — Nervous System (13th document): sensing, cognition, comms

- **New 13th document — Nervous System** (`gestalt-nervous.html`): how a grown
  vessel senses, thinks, controls and communicates. Its thesis: a km-scale ship
  needs both a **grown "wet" nervous system** (real sensory organs, bioelectric
  signalling, grown neural computation — DishBrain-style) for sensing,
  homeostasis, reflex and learning, and a **fabricated "dry" silicon core** (fast
  deterministic compute, navigation, comms, the human digital interface) —
  because biology can't grow a fast transistor or a radio, and silicon can't
  self-repair or sense. The two are joined by a real bio-electronic **interface**
  (OECTs, microelectrode arrays, electrogenetics, optogenetics, conductive
  nanowires). It is, honestly, a cyborg. Covers senses, the signalling
  speed-limit, the four kinds of organic computation, the silicon side & the
  interface, communication (crew + fleet), and a worked docking control loop.
  Three house-style figures (control stack, bio-electronic interface, docking
  loop), 14 citations. Registered in the catalog (slug `nervous`); canonical nav
  regenerated to **thirteen** entries across every document; all thirteen
  artifacts republished.

## 2026-07-26 — Python simulations of the designs' major systems (animated 3D)

- **New `sim/` package**: dependency-light Python (numpy + matplotlib) that
  models the major systems of the four main designs and renders them as
  **animated 3D GIFs** (`assets/sim/`). Modular — `params.py` (canonical
  numbers, single source of truth), `systems.py` (grounded dynamics: growth,
  life support, spin gravity, thermal, gestation), `geometry.py` (3D meshes),
  `animate.py` (per-design 3D-scene-plus-gauge builders), `run.py` (CLI:
  `python -m sim.run [design] [--fast] [--check]`).
- **Four simulations**, each a 3D scene + live gauges: **NAVIS** grows from a
  seed to ~24,000 t on the mining-limited curve with day/night intima glow;
  **ARCA** spins to 1 g at the rim with crew on the inner surface, a Coriolis
  drop, and a stable ~125-yr O₂ reserve; **LICHEN** swings ~160–265 K on the
  Martian surface while the interior holds 293 K; **GRAVID** gestates vessels in
  staggered cradle cycles. Each verified by eye from a rendered frame.
- Added `sim/INTERFACE.md`, a README "Simulations" section (the four GIFs), the
  project INTERFACE tree, and a gitignore for the preview frames.

## 2026-07-26 — Metabolism (12th document): ingest → digest → metabolise → excrete

- **New 12th document — Metabolism** (`gestalt-metabolism.html`): the nutrition-
  and-waste physiology of a grown vessel across four acts. Python-grounded
  mass-and-energy budget yields the document's thesis: photosynthesis on the hull
  makes only ~0.45 t/day of biomass (matching 13 t/day growth would need 29× the
  hull area), so the intima only makes the crew's **air** — the **body** is grown
  by *eating the rock* (digesting a carbonaceous asteroid's reduced organic
  carbon, ~1.4 MW, and oxidising its minerals), which is why growth is
  mining-limited. Covers the two mouths, the mineral gut (bioleaching →
  separation → refinery → organics → absorption), the two-sap bloodstream, and
  the four waste streams (only heat truly leaves; ~100 t/day tailings re-used as
  shielding; C/H₂O/N closed). Five house-style figures (whole-body flow,
  ingestion, digestive tract, energy budget, excretion streams), 13 citations.
  Registered in the catalog (slug `metabolism`); canonical nav regenerated to
  **twelve** entries across every document and all twelve artifacts republished.
  (Recovered mid-build from a botched in-place figure swap by rebuilding the doc
  from source and re-injecting figures cleanly.)

## 2026-07-26 — Cell Atlas (11th document) + richer 3D interiors

- **New 11th document — the Cell Atlas** (`gestalt-cells.html`): a cell-level
  cytology of a grown vessel. Grounds the census in Python (~10¹⁹ cells per
  hull; ~42 distinct types across 8 functional classes) and catalogues every
  type — role, survival, chassis, metabolism, life-cycle, coordination and
  distribution — plus the internal ecosystem/trophic web, and how each type is
  engineered, grown and tested (cross-linked to the Compendium and Earth
  Program). Three new house-style figures (lineage tree, trophic web, hull
  cell-distribution map), 19 citations, honest `gap:` flags on the three big
  integration bets. Registered in the viewer catalog (slug `cells`); the
  canonical nav is regenerated to **eleven** entries across every document and
  all eleven artifacts republished.
- **3D models — richer cutaway interiors**: multi-level decks, habitation
  compartments, vascular cores, ARCA terraces/settlements/sun-cord nodes,
  LICHEN floors + taproot, GRAVID embryos at two growth stages with umbilicals,
  and SPORE/LEVIATHAN/TESTUDO occupants. All 14 builds node-verified.

## 2026-07-26 — Detailed illustrated README (+ a broken figure found & fixed)

- **Rewrote `README.md`** into a detailed, illustrated guide: hero, a mermaid program
  map + closed-loop-metabolism diagram, a per-document tour with real figures, a
  "by the numbers" table (python-verified), the honesty conventions, and run/structure
  sections.
- **Extracted 13 figures** straight from the documents' own inline SVGs into
  `assets/figures/` as PNGs. Each figure is made self-contained (the docs' CSS
  variables are resolved to literal dark-theme values, since librsvg does not evaluate
  `var()`; stray `&` escaped; a dark ground added) and rasterised with `rsvg-convert`,
  then eyeballed. Class-styled drawing sheets (Starship/Habitat/GRAVID/LICHEN) carry
  their doc's class rules so they render faithfully.
- **Found and fixed a real defect:** the Compendium's *defence-in-depth* cancer-control
  figure was an unfilled `{fig}` placeholder in the published doc. Rebuilt it from
  scratch as a python-grounded waterfall (10¹² → 0.1 uncontrolled tumour lineages
  across seven layered controls, ~10¹³× suppression, below the 1-per-lifetime
  threshold) and republished the Compendium.

## 2026-07-26 — Two new documents, consistency pass + GitHub

- **Grew to ten documents.** Added the **Fleet Class Reference**
  (`gestalt-classref.html`, 9th) — a detailed profile of all 18 grown-vehicle
  classes with a master comparison table — and **3D Models** (`gestalt-3d.html`,
  10th) — interactive, rotatable/zoomable solid models of all seven main forms,
  drawn by a self-contained (WebGL-free) software renderer with cutaway views,
  interior components, a live scale bar and labelled hotspots.
- **Consistency pass across all 10 docs.** The per-document navigation bars had
  drifted (each listed a different 5–8 subset of the set). Regenerated every
  `prog-nav` to one canonical 10-entry bar so all documents cross-link the whole
  program; verified 9 links + 1 current marker and balanced tags in each.
  Re-published all ten artifacts to their canonical URLs. Updated `README.md`,
  `INTERFACE.md`, and `viewer/catalog.py` to reflect ten documents.
- **Published the project to GitHub** (`git init` + first commit).

## 2026-07-26 — Persisted to project folder + Python viewer

- Copied all eight published documents from the (session-only) scratchpad into
  `docs/`, plus the design-loop state file `deepen-roadmap.md`.
- Built a zero-dependency **Python viewer** (`viewer/`, stdlib only):
  - `catalog.py` — document registry (source of truth).
  - `wrap.py` — wraps each artifact fragment into standalone HTML and rewrites
    cross-document `claude.ai/code/artifact/<id>` links to local `/d/<slug>`
    routes (preserving `#anchors`).
  - `index.py` — themed landing page (document grid, GESTALT identity, light/dark).
  - `app.py` — `http.server` app + CLI (`--check`, `--open`, `-p`).
  - Verified: `--check` passes for all 8 docs + index; live server returns 200 for
    `/` and `/d/<slug>`, 404 for unknown slugs; 0 residual external artifact links
    after rewriting.
- Added `INTERFACE.md`, `README.md`, and this log.

## Program state (design loop)

The documents are produced and refined by a recurring "deepening" design loop
whose full round-by-round history and queue live in `deepen-roadmap.md`.

- **Phase A** (rounds 1–20): deepen each document element; ground every figure
  in Python. Complete.
- **Phase B** (rounds 21–30): build the Earth Program (ground R&D roadmap) —
  six work packages, integration ladder, Gantt + budget, gated go/no-go. Complete.
- **Phase C** (rounds 31–44): cross-link all documents bidirectionally; audit and
  reconcile every figure against the Compendium §08 canonical-parameters table.
  Caught and fixed several real errors (ARCA atmosphere 828→113 Mt and its O₂-buffer
  cascade; LICHEN membrane 6.5→7.4 MN/m; the pressure-wall 6.5 cm→6.5 mm; the O₂
  buffer 160→140 yr to match the canonical 34% O₂; stale cross-doc phrasing).
- **Phase D**: upgrade all figures to professional architectural-diagram
  standard, and add real citations throughout (~108 references across the set).
- **Phase E** (user-directed): subsystem deep-dives (light delivery, healing &
  regeneration, sustainability) documented as chat answers + python-grounded
  figures; the **Fleet Class Reference** and interactive **3D Models** documents;
  and a whole-program consistency + cross-linking pass. Program now ten documents.

## The honest clock lands (#116, #121) — eight cycles

`core/clock.MAX_STEP = 1`: `advance_days(N)` now chops into single days, so a
jump of N days equals N jumps of one for **every** N. Full suite green at
**1,231 checks**.

The fix itself was 15 lines and was written, verified and reverted five times
across seven earlier cycles. Every revert was on the strength of one red check,
and every one of those checks turned out to be a **real defect the honest clock
exposed** rather than a fault in the clock: free hull repair, artefact zeros in
mining, a probe that would not sell, a freight desk that never priced time,
loyalty's scale floor, the exchequer deciding once per call. This cycle closed
the last two.

**#121 was wrongly premised, and the measurement said so.** `lifespan.tick` does
`officer.age = was + years * lineage.ageing * slowed` — a pure rate, correct as
written. Against the days that actually elapse: wet 5.75 y over 2100 days,
grafted 4.39 over 2760, dry 1.40 over 3650 — every one exact on its table rate.
Two things had been masquerading as a per-call defect. Instrumented, of 2130
days handed to `lifespan.tick` the wet officer was **absent from the roster for
918 of them**: the fixture cannot pay wages and the last officer quits on day
1220, so `age_of` went on reporting a three-year-stale age. Separately, an
unattended chronicle reaches `victory="ruin"` on day 2100 and `advance_days` has
always stopped there — "ten years passed" was never true. Fixed in the check,
not the sim: it now asks for a **rate** (+/-0.01 against `lineage.ageing`) and
asserts the officer is still aboard.

**Thermal: a hull was regrowing the layer its own radiators were cooking.** Over
fourteen hard burns: 225.8 hp cooked against 239.7 healed, so a crossing bought
in 87 days instead of 234 cost 7.5% of hull. `cool` knew what "over the cap"
meant; `repair_tick` never asked. Closed with `ship.excess_heat`, read by both.
Gap went 7.5 points -> 77 (hard ends at 23% hull, economy at 100%).

**Chronicle: "fought something" was covered by one lucky die.** One fight in a
decade under the old clock, zero under the honest one — and separately **zero
encounters in 360 in-system arrivals across 30 seeds**, so every fight the
driver ever had came from an interstellar jump. `_seek_trouble` now asks
`encounters.roll_encounter` directly where `sim/piracy` says raiders work.

### Wrong turns worth keeping

- **The `MAX_STEP` docstring claimed step 10 sat "5.3% from playing it out day
  by day". That was dice noise read as error.** `game.rng("tick")` is drawn once
  per step, so a different step is a different stream. The drift is not
  monotonic — step 10 drifts 1,367 where step 2 drifts 11,417 and step 5 drifts
  13,306 — and the player's own credits come out identical (191,909) at every
  step. The justification for 1 is exact, not statistical.
- **A timed-out mutation run left `excess_heat` stubbed to `return 0.0`, and the
  "backup" was then taken from the mutated file** — so the first restore
  restored the mutation. Caught only because the restored run was still red.
  A backup taken mid-mutation is worthless.
- **"The surveyor/navis opening leaves you with 1 credit" was wrong.** 1 credit
  was the purse *after* 1,160 days of an unflown chronicle. Measured properly,
  all 12 legal openings start at 6,000-32,000 credits, which is 600-2,133 days
  of payroll at 10-15/day.

## The orrery's labels stop printing across each other (#127)

Measured through the painter rather than the code: every `drawText` the chart
issues is caught and turned into the rectangle its glyphs will actually occupy.
Over ten seeds, before:

    83 labels drawn, 3 overlapping pairs, worst 100% of the smaller box

Every one of the three was `Fleet Hub` under a hull name. The cause was a
one-door failure: the plot had **three** label families and only traffic
de-cluttered, against a list (`labelled`) that collected hull names and nothing
else — so a hull could not see the quay label it was about to print across.

Now one `_room_for` serves all three. Bodies and quays register their ink but
are never refused (a planet whose name went missing is a worse chart than a
crowded one); traffic yields to them, which is the trade the original rule
already made — the panel below the chart names every hull anyway.

After: **0 overlapping pairs over 40 seeds, 295 labels.**

### Wrong turns worth keeping

- **The task claimed "an unreadable cluster ~60px across" of five labels. It was
  one pair.** That came from reading a 1560px render scaled down. Measured on
  the actual glyph boxes, the labels near the star are a dense *stack* with
  ~10px gaps — legible — plus one genuine 26% overlap. The defect was real and
  the description was overstated.
- **A point-distance rule was not enough, and the first fix shipped with that
  flaw.** Merging the three lists but keeping the inherited thresholds (58
  across, 11 down) left 2 overlaps in 20 seeds, both a body label under a hull
  name: the rule compares *draw anchors* while ink runs ~110px to the right of
  its anchor, so a neighbour just outside 58 still printed across. Replaced with
  an exact rectangle-intersection test on the ink.
- **"Comparing the ink is looser, so it shows more hull names" was wrong, and
  the count said so.** Over the same ten seeds: 83 labels before, 78 with the
  merged point rule, **71** with the exact test. Twelve names went, three of
  which were illegible anyway. The docstring was corrected to the measurement.
- **The quay-stacking half was unguarded and a mutation proved it.** Cutting the
  candidate ladder to a single position left the new check green, because none
  of the ten `orrery` seeds has two quays at one body. Seed `lab8` — the only
  one in twenty-two that does — is now named explicitly in the check.

Filed #128: `place_mark` offsets from the *planet*, so two quays at one body get
the same point. The labels are fixed; the marker is still single, which means
the chart shows one station where there are two and one of them cannot be
clicked at all.

## Every quay gets its own mark, and its own mark selects it (#128)

`ui/orbit_chart.place_mark` offset from the **planet**, not the quay, so every
anchorage sharing a `body_index` landed on the same point. Measured across 22
seeds, one has it: `lab8` puts `Fleet Hub` and `Third Silence` both at body 0 of
Marrow Fall, at exactly (517.25, 211.07) — **2 anchorages, 1 distinct mark**.

It serves the painter and the hit test alike, which is the right shape, so both
were wrong together. `mousePressEvent` takes the nearest mark under 13 px with a
strict `d < pd`, so the second quay tied and lost every time. Measured by
driving a real `QMouseEvent` at each quay's own mark:

    clicking Fleet Hub's own mark     -> 'port-21'   OK
    clicking Third Silence's own mark -> 'port-21'   WRONG

`Third Silence` could not be selected from the chart at all.

Quays now fan around their body on a fixed quarter-turn step, sorted by id.
Seat 0 sits exactly where the single offset used to, so every body with one
quay — nearly all of them — draws unchanged. On `lab8` the two marks are now
**22.0 px apart against a 13 px hit radius**, and both select correctly at their
own mark and 4 px either side of it.

`QUAY_HIT = 13.0` was a bare number in the hit test and nowhere else, so nothing
could check the fan against the very thing the fan exists to clear. It is named
now and the check reads it.

### The 500-line rule, broken by me and then fixed

`ui/helm_view.py` was 471 lines before this session. **My #127 commit took it to
535 and I did not notice**; #128 would have made it 579. Split: the chart moved
to `ui/orbit_chart.py` (376 lines) and `helm_view.py` came back to 234, with
fifteen now-dead imports removed. The orrery's checks moved with it into a new
`tests/test_orrery.py`, which also brought `test_ui.py` back from 468 to 401.

### Wrong turns worth keeping

- **A mutation that does not parse is not a mutation.** Reversing the sort in
  `_quay_seat` was written with an unbalanced paren; the module failed to
  import, the optional suite was *skipped*, and the run printed nothing at all.
  Read as "no output" rather than "green", which is the only reason it was
  caught. Mutations are now parsed with `ast.parse` before the suite runs.
- **Two checks did not bite when first written, and both gaps were real.**
  Shrinking the fan to 4 px left the mark check green, because it only clicked
  marks *exactly* — a captain clicks near one. Fixed by demanding quays at one
  body sit at least `QUAY_HIT` apart and by clicking 4 px either side. And
  dropping the sort entirely left it green too, because reversed seats are
  still distinct and still clickable; the stability claim is now checked by
  handing the same game back with `in_system` reversed and demanding the same
  marks.
