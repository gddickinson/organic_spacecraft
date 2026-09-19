# The parts that will bite you (2 of 5)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

  **Put heat in with `ship.add_heat`, which clamps on the way in.** This used
  to say "call `cook()` wherever heat is added; there are exactly two such
  places" — and there were six. A crossing watch, a flight incident, an
  action's own effects and taking a hit in combat all added heat raw, so a
  fault alone took a hull sitting at the ceiling to 2.36x its cap. Asking
  callers to remember is what four of six did not do.
  `tests/test_thermal_doors.py` fails on any `\.heat +=` outside `ship.py`.
  (`sim/customs.py` has its own unrelated `add_heat` — scrutiny from the
  revenue, not thermal load.)
- **Heat is bounded by `HEAT_CEILING`, and that is load-bearing.** It used to
  be unbounded, and because the overheat penalty scales with how far over the
  cap you are, it compounded: a Bastion firing the five heavy mounts it has
  slots for went 68 → 132 → 187 → 243 → 279 and routed itself on turn five at
  93% hull. `cook()` is called from `_fire`, which is the only thing in the
  game that adds heat, so one clamp at the source covers every hull. An
  end-of-turn clamp was tried too and measured to change nothing at all, so it
  was removed rather than left in looking useful.
- **Every tuning constant is pinned, and that is measured rather than
  assumed.** All 153 module-level numeric constants across `data/`, `sim/` and
  `core/` were swept: doubled, halved and zeroed, and every one is noticed by
  a check. The sweep also reports *where* the protection comes from — a
  constant caught only by the wide set is held up by a suite that happened to
  walk past, which is a thinner thread than a check written for it.
  `consorts.WITHDRAW_AT` was the only one in that state and now has its own.
  Re-run with `python3 -m seedfall.tests.tripwire`; about seventy minutes, and
  never alongside the suite, because it rewrites source while it works.
- **A forecast has to clamp what the hull clamps.** `order_preview` quotes
  what the heat *becomes*, not the raw sum: a salvo worth 74 on a hull at 30
  with a 50 cap stops at the ceiling, so the line reads "heat 30 → 100 of 50 —
  pinned at the ceiling" and not "→ 104". My first draft quoted the sum, which
  is the same defect the function exists to fix, one layer up.
- **A screen with two buttons has to price both of them.** The ventures panel
  showed the odds as they stood, priced *backing*, and left "Work against it"
  bare — no standing cost, and no hint that either button moves the odds by
  `SWAY`: measured, a 51% venture becomes 81% backed and 21% opposed. It never
  mentioned that being right afterwards pays again either. `RIGHT_BACKED` and
  `RIGHT_OPPOSED` were bare numbers inside `_resolve`; they are in
  `data/ventures.py` now and `ventures.preview` reads the same ones.
- **`tripwire.KIN` is hand-written, and a stale entry fails silently.** The
  tool runs a constant against its own neighbourhood first and only pays for
  the wide sweep if that passes. An entry naming a suite that no longer
  exists makes `python -m seedfall.tests <name>` run nothing and exit zero, so
  the fast stage "passes" every time and every constant quietly costs the full
  run — measured, `ship` swept in 17s with a fast path and 240s without. An
  entry naming a `SLOW` suite is worse: the verdict then depends on whether a
  module has an entry at all. `test_harness_guard` holds both, and requires
  every module with constants either to have a fast path or to be named as
  having no suite that covers it. It caught its first live case in
  `SETTLED_IN_DAYS`: `tutorial` was on the `SLOW` list **for building a
  window**, which cost the constant its only witness. That list means "too
  expensive to run once per constant" — and the tutorial suite sets the
  offscreen platform itself and runs in two seconds. Needing a window is not a
  reason to exclude a suite; costing thirty is.
- **Every action that spends a turn must run the seats.** `take_turn` takes
  two shapes: `{"type": "station", "order": ...}`, which runs the crew-station
  system, and the older `{"type": "fire", "weapon_id": ...}` family, which the
  battle screen still uses for the firing picture's per-mount buttons and the
  ability buttons. The older shape never called `_run_stations`, so picking a
  mount meant nobody flew the ship and nobody stood in engineering that turn —
  measured, heat 30 ended at 24.0 through the old door and 19.44 through the
  new, with `helm_order` still `None`. Only `move` had ever been migrated.
  `_run_seats` is now called from both. Note the helm runs *before* the guns
  on both paths, so a mount that bears when you press the button may not bear
  when the shot goes.
- **`TREATY_WEIGHT` is read by both doors into signing one.**
  `diplomacy.perform` charges the signatory's enemies through
  `sim/allegiance.py`; `approach.answer` did not, so the same instrument with
  the same signatory cost −6 with each of three powers when you proposed it
  and **nothing** when you accepted their offer. Waiting to be asked was how
  you signed a treaty for free. Both read the one constant now, and
  `preview` states the price.
- **`preview["credits"]` is money moving; `preview["offer"]` is the price on
  the table.** They were one field, and the envoy screen rendered a haggle as
  "Treasury: +794" — a captain reading that row believed they had been paid
  for asking. Nothing is paid until the offer is accepted.
- **A fixture that names something the game does not know is invisible.**
  `inquiry.add` returns 0.0 for an unrecognised kind — silently, which is
  right for a sim that must survive an old save. `test_provisional` typed six
  evidence kinds by hand; three (`field`, `relic`, `trade`) do not exist and
  one that does (`reading`) was missing. Six of the ten branch mixes want
  `reading`, cognition 35% of it, so the suite that decides whether any
  research approach dominates measured those branches 20–30% slow. Derive
  from `EVIDENCE`, as `test_bench` always did. `tests/test_bench_kinds.py`
  checks the call sites **and** any hand-written `*KINDS` list, because the
  call site passed a variable and no search of call sites could have seen it.
- **A returned value nobody reads is a feature nobody gets.** `crew.grant_xp`
  hands back the officers it has just promoted — that is what the return is
  *for* — and all eight call sites dropped it, so `promoted` (+5 to everyone
  aboard, it is in `UNIVERSAL`) never once fired and a promotion was not even
  logged. Pass `game=` and it reports itself: the ship feels the event, the
  officer gets `PROMOTION_OWN` on top, and it goes in the log.
- **An event whose name is composed cannot be found by searching for it.**
  `loyalty.served` builds `f"{conviction.id}_served"`, so the audit in
  `tests/test_conviction.py` keeps an explicit `COMPOSED` allowance and proves
  those separately by behaviour. Anything else must appear literally in
  `sim/`, `core/`, `ui/`, `world/` or `bridge/`.
- **Two doors into the same event will drift, and the drivers use the working
  one.** Surveying a body can be reached through `actions.survey` — which the
  remote bridge and every test driver call — and through `survey.perform`,
  which the screen calls. Only the first dated the finished chart, so
  `charts.freshness` returned 1.0 for every chart a player ever made:
  `FRESH_DAYS` and `STALE_FLOOR` decided nothing, and the survey office's
  "Age of the survey" row sat behind `if fresh < 0.95` and could not fire.
  Nothing caught it because every driver in the suite went through the door
  that worked. `tests/test_charting.py` asserts both doors leave the same
  state.
- **Order the penalties after the limits, not instead of them.**
  `haul_kept` applied the carrying limit on the way home and skipped it
  entirely when the party stranded, so stranding returned 40% of an *uncapped*
  pile: 500 t collected came home as 200 t stranded against 60 t returned. The
  penalty was a reward by a factor of twenty-three, and the way to play the
  ground was to strand the party deliberately. Cap first, charge second.
- **`tests/ground_ai.py` is to the ground what `captain_ai` is to combat.**
  Walking a party at random and grabbing whatever is underfoot measures
  nothing, because it never returns to the lander, so every policy strands and
  scores the same. `margin` — supply held back for the walk home — is the one
  decision the ground poses, and sweeping it should show a peak in the middle:
  measured 29 t at margin 0, 35 t at 4, 23 t at 14.
- **Establishing state by hand can make a check unreachable.**
  `test_officials` proved the office rate worked by writing it into the dated
  `favours` dict directly. It does not get there that way: a quiet price is
  granted "this once", carries `lasts=0`, and `ask()` recorded favours under
  `if favour.lasts:` — so a zero-day favour fell straight through and the
  price code could never fire in a real game. The check exercised a state the
  game could not produce and read as coverage. Grant through the same call the
  player uses.
- **One helper for the price, and nothing applied at the till.** The office
  rate was applied inside `trade.buy`/`trade.sell`, so the board showed 36/t
  while the counter charged 31.68. `market.quote_buy`/`quote_sell` are the
  price — office rate, grudge bias and all — and `tests/test_counter.py`
  sweeps the two against each other.
  **And there was a third door nobody had swept.** The market grid on
  `ui/port_view.py` called `world.economy.buy_price` directly, so it carried
  neither the office rate nor the grudge bias, while the comment forty lines
  above it said "now it is in the quote, and the board says so". Measured with a
  quiet price in hand: the grid printed 36 and 29 while the counter charged 32
  and paid 33. A check that reads the helper can never see this — the new one
  reads the labels out of the rendered grid.
- **Wharfage is charged on top of the price, not folded into it.**
  `sim/wharfage.py` takes a share of every deal for whoever holds the quay, and
  the money moves in `collect`, which debits the captain and credits the purse in
  one function so the two cannot disagree. It is deliberately *not* inside
  `quote_buy`/`quote_sell`: a price the board can print stays a price, and the
  charge is named separately — on the board, in the ship's log, and on the
  freight desk's forecast of a run. So `res["paid"]` is the goods and
  `res["due"]` is the quay, and anything measuring what a trade cost has to add
  them.
- **A forecast of an act is not a forecast of the turn that contains it.**
  `stations.order_preview` costed each order against its own act, and
  `test_orderplan` checked it that way — by calling `run_engineering` directly.
  Both agreed, and both were answering a question the captain never asks. On a
  Bastion at 45 of a 50 cap, sitting down at engineering and ordering *vent*,
  the panel said `heat 45 → 20` and the turn ended at **74**: the gunner left at
  the guns fires everything that bears, always, whatever the heat. That is
  deliberate — it is what a battle computer is bought to fix — but quoting it
  at nobody was not, and it left the one order whose purpose is cooling
  advertised with the wrong sign while *hold fire*, which cools by 10, read as
  the order that does nothing. The forecast now steps the turn the way
  `combat.take_turn` steps it and is exact to the hundredth over 2,095 played
  turns. **The general form: ask what the player is actually choosing between,
  and forecast that.**
- **A dry run beats a better formula.** The residual error after folding in the
  other seats was the geometry moving under the forecast — worst at *present
  the broadside*, whose own blurb says everything on the flanks bears, and which
  was therefore quoted as *cooling* on eight turns in a thousand. Our guns fire
  after our own helm has moved us and before the enemy moves at all, so flying
  the order on a copy of the body is not an approximation of the answer, it is
  the answer. Copying two dataclasses retired the whole error class.
- **The ceiling belongs to the one function that adds heat.** `ship.add_heat`
  clamps; shedding is a plain `max(0, heat - x)` and never consults the ceiling.
  Reproducing that in a forecast, I clamped on every step *and on a step of
  zero* — which cooled a hull sitting above a ceiling lowered by radiator damage
  by five points a turn it never lost. `delta >= 0` and `delta > 0` are
  different programs when the hull is already over.
- **A mutation that changes nothing is not a coverage gap.** Replacing the
  salvo's arc-and-band test with arc alone failed to break any check, and the
  reason was that the two never differ at any range these hulls fight at:
  0 turns in 89. The real gap was next door — the count check ran only with full
  magazines, where "what trains" and "what burns" are the same list. Both
  mutations bit once it ran with an empty one.
- **Cost that does not scale with the widget.** Six conn camera feeds of
  **170x92 pixels** cost 31 ms of a 44 ms frame — more than the 782x455 main
  view at twenty times the area — because each one drew all ninety-six latitude
  bands of a world whose disc was 301 px across and of which it showed a corner,
  and asked for an outline for every blotch of the ground lattice regardless of
  where it landed. The renderer's work was geometry-bound, not pixel-bound.
  Culling both against the frame took the conn window from 21 to 32 frames a
  second. **When a small view costs as much as a large one, the cost is not in
  the pixels.**
- **A cull that changes the picture is not a cull.** Both first attempts were
  optimistic: the band test compared the frame's *centre* against the cap's,
  which is the real test with the boundary ellipse shrunk to a point; and the
  feature test bounded a blotch by the longer of its two conjugate radii rather
  than by `hypot(ax, bx)`, and forgot the wobble stretches every radius by up to
  1.6. Sixteen pixels of a 782x455 approach moved. The check that matters here
  renders each frame twice — culled and unculled — and demands *zero* differing
  pixels, and the seed that first exposed the bug is one of the four it flies.
- **A rule is better asked of the rule.** Reading zero bands drawn, seed after
  seed, I took it for a broken monkeypatch; it was the cull correctly rejecting
  all ninety-six of a world the frame happened to miss. How much a cull saves
  depends entirely on the geometry — 81 of 97 kept with the disc centre in
  frame, all 97 with it off frame and nothing to save, 42 with the world larger
  than the picture. A bar set on the best case would have called the honest
  middle case a failure.
- **The catalogue screen was the last place with no catalogue in it.** The
  Codex listed thirty-five hull classes and nineteen colony classes as text —
  name, binomial, tier, blurb, role, crew, mass, hull, hold, jump, build time —
  while the sky had been drawing five hull silhouettes, four berths, nine star
  classes and seven kinds of world for cycles. Everything needed to show them
  existed; nothing pointed at the page whose job it is. **When a renderer lands,
  ask which screens still describe what it now draws.**
- **Five pictures across thirty-five entries is not a catalogue either.** A
  class's proportions come from its own card now — hold against mass gives
  beam, jump range gives length — so the portrait and the specification are the
  same facts twice. Both anchors were measured: the first pair, guessed, put
  nearly every class against the beam cap because the median hull carries twice
  the assumed hold and jumps nearly twice as far.
- **Never bound a constant with itself.** The check that claimed the class
  spread was bounded asserted `1 - CLASS_SPREAD <= beam <= 1 + CLASS_SPREAD`,
  which moves with the constant it is guarding and passed with the spread set
  to nine. `tests/tripwire.py` exists because of exactly this habit, and it
  still turns up in freshly written checks — the written figure is the only
  form that holds.
- **A check that asks the helper cannot see the call.** Nine mutations went
  into `ui/battle3d`'s hull drawing and **four passed at once**, because every
  check in the new suite asked `hulls3d.mesh_for`, `battle3d._family` or
  `_hull_scale` directly. Pinning the *call* in `paintEvent` to a fixed family,
  a fixed size, a flat tilt or a fixed yaw changed nothing any of them looked
  at. The fix was a check that renders the widget and reads the picture — and
  then two more rounds of it, because comparing a NAVIS with an ANTIPHON also
  varies their *mass*, so a mutation that fixed only the family still moved the
  frame. A CORAL and a CARAVEL are both exactly 9,000 t in different families,
  and that pair leaves the shape as the only variable.
- **Hold the QApplication.** `_app()` returns it; calling `_app()` and throwing
  the result away lets Python collect it, and the next QWidget aborts the whole
  process with "Must construct a QApplication before a QWidget" — which reads
  like a setup error and is really a reference count. The suite output vanished
  with it, so there was nothing on screen to diagnose from either.
- **The same defect twice, in the same file, and only half of it noticed.**
  `ui/viewport._star` worked out a star's `tint` from its class and drew the
  disc as a hard-coded `QColor(255, 253, 244)` — the same off-white for all nine
  classes, so **a black hole rendered as brightly as an A-type** while its own
  entry says there is nothing to see. Two lines above the offending fill sits a
  comment congratulating an earlier cycle for catching that the *corona* colour
  was unused. That cycle fixed the halo, left the core, and wrote a note about
  it. A guard against unconsumed *fields* would not have caught this: `core` is
  read, into a local, and dropped. **When a cycle finds one dropped value, look
  for its sibling in the same expression.**
- **Check at the size the thing is actually seen.** The first version of the
  star checks sampled off-centre, where the class colour dominates — and a
  mutation that pinned the *innermost* stop to white walked straight past, even
  though most stars in the game are three pixels across and are nothing but
  their middle. The second version compared two classes at three pixels and it
  walked past that too, because it moved a warm class toward white without
  moving a hot one. What caught it was a property with a measured margin: an
  M dwarf's centre carries 98 points of red over blue, and the mutation leaves
  46.
- **How far away is not how far ahead.** `camera.project` returns the point and
  the component of the offset *along the view axis*, and `ui/spheres.py` passed
  that second value to `screen_radius` as the range. On the axis they agree,
  which is why every synthetic render of a world this project ever judged looked
  right. Off it, `ahead` falls toward zero however distant the world is, and
  `tan(asin(r/d))` runs away as `d` drops under `r`. Measured in the conn on an
  ordinary approach: a 2,419 km world 2,981 km off and 73° from the axis was
  drawn at a screen radius of **5,611 px instead of 335**, filling 99% of the
  frame with ground that should cover 15% of it. Every berthing approach looked
  out at a featureless wall of planet — and two cycles of surface detail went
  into ground being drawn thirty metres from the lens. The same mistake, in the
  same shape, was in the span calculation one module over: **when a question is
  about a direction, do not answer it with a centre.**
- **A sphere's outline is a circle only head-on.** Off-axis the silhouette is an
  ellipse, and the projected centre can be off the frame while the world still
  fills a corner of it. `surface.limb` projects the tangent circle itself — the
  points where the line of sight grazes, at `r²/d` back from the centre with
  radius `r·sqrt(1 - (r/d)²)` — which is exact at any angle. Its first version
  returned nothing as soon as one of those points fell behind the lens, which is
  precisely the close approach it was written for; it clips against the lens
  plane now.
- **A field carried and thrown away is a catalogue that never arrives.**
  `track.Contact.berth` has said quay / hub / holding / gate since it was
  written, with a docstring insisting "a screen should not have to read an id to
  know whether it is looking at a shipyard or at something older than the
  Charter" — and `sky.build` set `look=""` for every anchorage and every hull it
  produced, so `ui/viewport._sky` had a kind and nothing else and drew **all of
  it with `models3d.SHIPYARD`**. Across four sectors: 67 quays, 36 gates, 16
  Fleet Hubs and five errands of traffic, every one of them the same shipyard.
  Not the same shape recoloured — the same shape.
- **A silhouette nobody can see is not a silhouette.** Having given nine sorts
  nine shapes, rendering them showed all five ships as the same foreshortened
  lump: hulls are authored nose along +z and the sky drew them at a tilt of
  0.42, twenty-four degrees off dead ahead. `models3d.ATTITUDE` holds a ship
  broadside, because a ship is a profile. The shapes had been real and invisible
  — which is worth remembering the next time a cycle ships content without
  looking at it.
- **Compare pictures, not tuples.** Two meshes can differ in every vertex and
  render as the same blob. `tests/test_silhouettes.py` rasterises each sort and
  compares the *silhouettes*: as shipped the closest pair shares 66% of its
  outline, and before the cycle every pair shared 100%. That check is also what
  found the prospector, which at 73% against the trader was a chunky can with a
  bell like the trader's — the fix was the mesh, not the threshold.
- **The same shape *unrecoloured*, one layer down.** `berths3d` fixed the sky
  for quays, hubs, holdings and gates — and every one of the nineteen colony and
  station classes was still the holding. Measured through the game's doors: plant
  one of each, ask the sky, and `19 anchorages → 1 mesh`. An ARCA Habitat holding
  a million people and a VESPER Picket were the same four tanks in a frame, in
  the sky, on the approach and at the berth. `data/works3d.py` builds one
  structure per class **out of the class's own entry** — ore gives it roots,
  volatiles a condenser bell, research a dish, `gestation` a womb, `drydock` a
  slipway cradle, `megastructure` a drum people live inside, `drift` the vanes of
  something not station-keeping — so the portrait and the specification are the
  same document, and a new class in `colonies.py` gets a structure without
  anybody drawing one.
- **A difference that is drawn and invisible is not a difference.** The Jaccard
  check found three of them in a row, each a case of one feature sitting inside
  another's outline: masts at 0.24 hid in the mouth of a dish (a Relay Choir
  rendered **93%** the same as a CHORUS Node), stacks at 0.30 hid inside a cradle
  cage (Fabricator Yard **90%** against a GRAVID Nursery), and a ring at 0.66 hid
  inside the same cage. Two of the three fixes were better *models* rather than
  bigger numbers — a nursery gestates and a yard welds, so one is a shell and the
  other a cage; a megastructure is a drum, not a ring on a keel. Worst pair is
  now 69%, and it is the two things that genuinely are both slipways.
- **A right way up is a thing a structure has and a ship does not.**
  `ATTITUDE["berth"]`'s 0.42 is right for rings and arms and wrong for anything
  built along its own axis: all nineteen works came out as the same lumpy egg
  with fittings stuck on. And the *sign* mattered — a positive tilt sends model
  +z down the screen, which is nothing to a ship shown broadside and turns every
  dish in the sector upside down into a skirt.
- **How big a thing is, is a fact, and it was two facts.** `sim/sky` drew every
  anchorage at 0.6 km while `sim/targets` handed the approach 0.4 km for the same
  object — so what you picked out at forty kilometres was half again the size of
  what you came alongside. `berths3d.radius_km` is the one door; the scale is
  pinned to the one habitat whose true size the GESTALT documents state, and ARCA
  comes out at the 2.5 km the documents say.
- **A rung that fails at the one job its class exists for is a wrong number,
  not a hard trade.** `sim/robots.grip` began as pure decay: whatever a machine
  was rated at, the light-lag to the ship ate it. Which made an Anchorite —
  a mind racked in a holding, sold on being *left there* — worth a thousandth
  of itself the moment the hull sailed. The ECSS ladder the design is built on
  does not describe how well a robot obeys; it describes **how much mission it
  executes on its own**. `STANDING` is that half, and what the distance costs
  is only the share that needed you. The check caught it, and the fix was the
  model rather than the constant.
- **A check that tests a screen's helpers has not tested the screen.**
  `test_robots` verified `robots_panel.where_line` and `lag_line` and computed
  the effective level itself — so a mutation that made the panel print a
  machine's *rating* instead of its *reading*, which is the one lie that panel
  exists to prevent, passed clean. It builds the widget and reads the pills
  now. Same shape as the standoff-drawing miss: measure the artefact, not the
  arithmetic beside it.
- **Look for the spine before adding one.** The robots cycle wanted crew that
  are not people, and `data/lineages.py` already opened with "a lineage is a
  substrate" and shipped a Dry Choir *recording* that eats silicon and
  magnetite and does not breathe; `hullforms` already had a crewless synthetic
  family. So a machine standing a bridge watch goes through `ship.stats` as a
  hand, with no second capability system beside the first — and the one place
  that computes what the ship can do, `state.recompute`, is the only line that
  had to change.
- **The same condition written twice is a rule you will forget to update
  once.** `crew <= 0 and not lifespan.active(officers)` was the test for "this
  hull is deserted", in `core/clock` and again in `sim/upkeep`, and neither
  asked whether anything mechanical was standing a watch — while
  `state.recompute` was already computing the ship's repair and research rates
  off exactly those machines. `robots.watchkeepers` is the one door now.
- **A guard that returns the right answer for the wrong reason is a bug
  waiting.** `dormancy.awake_share` gave a full work share to a complement of
  zero through its `total <= 0` line, which read as "a crewless hull is
  manned" and was really "divide by nothing". Counting machines makes it true
  on purpose — and produced the consequence that had been missing all along: a
  sleeping crew's bench keeps turning at whatever share the machines are of the
  complement.
- **One field doing two jobs is two bugs waiting.** `Target.radius_km` was how
  big a structure is *drawn* and also what a ship could *hit*, and the moment
  `works3d` gave each holding real furniture the two came apart: seven of
  nineteen had berths inside their own contact sphere and could not be docked
  with at any speed. A berth is a fitting on the **outside** — a mast, a
  gantry, an arm — so a berth inside the bounding sphere is the normal case,
  not the impossible one. `sim/bays.hull_km` is the one door, and it was asked
  in two places before it existed.
- **A constant chosen for one problem will break another.** The first fix
  applied a single 0.55 share to every structure. It rescued the seven and it
  also halved the solid radius of a quay, a hub and a Weave gate — whose berths
  sit at 0.91 to 1.11 of their radius and never needed it — so a hull rammed
  into a station at 45 m/s came away *adrift*. Three suites caught it at once.
  The rule that survives is derived per structure from the mesh's own numbers:
  the hull stops just inside its nearest berth.
- **A guard that matches bare names is a guard with a blind spot the size of
  your naming conventions.** `test_reachable` held `module.func` on one side
  and bare `func` on the other, so any module's `summary` being called covered
  every other module's. It hid thirteen orphans, two of which were a *second
  door* onto collision damage. Resolving properly means crediting four things a
  naive version misses — a call where the function lives (220 false alarms on
  its own), an aliased import, a re-export, and a reference that is not a call
  — plus decorators, which register a function with something that dispatches
  by name. What cannot be placed stays loose and credits everything, so the
  check under-reports rather than crying wolf.
- **A generated thing needs a generated picture.** There is no bestiary in this
  game to illustrate: `world/planets._make_lifeform` assembles an organism from
  a body plan, a metabolism and up to two traits, so `data/life3d.py` assembles
  the portrait the same way — off the record itself, since `Lifeform.name` *is*
  the plan. Sixteen plans, eight liveries, five visible traits, and an organism
  nobody drew still arrives with a body.
- **A mark is sized to the creature, not to one of its axes.** Scaled by
  `height`, every trait on a long low animal came out between three and sixteen
  pixels — an armoured grazer's glass spines were three pixels of glass. And
  before that, a magnetotactic organism's aligned chains were drawn *inside* the
  body and changed **zero**: the one thing that trait means is that everything
  lines up, and you can only see that if the line leaves the animal.
- **Say what the picture cannot show.** Five of the ten traits are visible;
  damage-suppressed chromatin and obligate symbiosis are real and are not. The
  catalogue names both — "drawn" against "real, and nothing a portrait can
  show" — because a page that implies the portrait is the whole organism is
  lying in the small way this project keeps finding.
- **Write the check to the claim the picture can actually make.** Eighteen
  defensive plates cannot be eighteen pictures, and asserting they were would be
  the same lie as five silhouettes across thirty-five hull classes, pointing the
  other way: a distinction drawn where none exists. `data/parts3d.py` promises
  three things a captain needs at a glance — what kind of thing it is, whose
  yard built it, how much hull it eats — and `test_parts3d` measures exactly
  those. All five checks passed first time, which is what happens when the
  claim is honest before the code is written.
- **A record nobody reads is a rule nobody obeys.** `Conn.cleared` carried the
  whole `Clearance` from the day the protocol landed, with a docstring
  promising a berth "cannot be quietly swapped for one the ship preferred" —
  and no code downstream read the field. Flown: cleared for mast 4, moored to
  mast 3. Enforcing it turned out to need no rule at all: once
  `moorings.assign` returns the granted berth, `nearest` measures the gap to
  *that* fitting and no other, so sitting on somebody else's is simply 352 m
  from the only berth that counts. The extra condition written into
  `control.withheld` came straight back out.
- **A station's patience is the range, not the calendar.** The first ladder
  advanced a rung every six ticks, so a hull pressed in at full drive covered
  twelve kilometres in twenty ticks and collected a hail and a warning, while
  one merely *drifting* in took two hundred ticks and collected all four rungs
  — barrelling at a station was safer than approaching politely. `control.haste`
  spends patience against `Clearance.max_closing`, the rate the structure
  already asks you to hold: pressed in, *repelled* in 25 ticks and 71 damage;
  drifted, 123 ticks and 2.
- **The quiet defence is the one every dock has.** A structure that does not
  want you need not shoot: it declines to swing the boom out, and a standoff
  berthing cannot be completed. The machinery was already there —
