# Tests — what each suite holds and why (2 of 2)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

- **`test_conn.py`** flies every contact in five chronicles to a berth or an
  orbit, and is the check that found the closing-rate fault: before it, none
  of them arrived. It compares the conn's forecast against the burn over 2,272
  cases, plays the chronicle forward to see whether the plot's predictions
  come true, and holds the board and the helm to the same arithmetic. Two
  checks earn their place by what they caught in a mutation sweep: disabling
  the branch that kills velocity *across* the approach passed everything else,
  because `start` always puts the ship dead ahead — so there is now a check
  that arrives off-axis on purpose, and it failed on the first run.
- **`test_public.py`** holds the rule that every public act pays for being
  public. Its general check derives who *ought* to mind from the relations
  matrix rather than from `offended_by` — sharing the code's own list would
  prove nothing. Its first sweep missed three, all holes in the checks: the
  preview-versus-act agreement had been measured at 3,456 comparisons while
  the fix was built and never written down, nothing held the two principals
  exempt from each other, and the Bloom-partisan check was asked of a Bloom
  with no relation to anybody, so it scored zero devotion and dropped out on
  its own. Sweep: 8/8.
- **`test_weave.py`** holds the gate network. Its first sweep missed three
  mutations and all three were the same defect in the *checks*: the standing
  block sat behind `if far.faction:` and silently ran nothing where the far
  end had no owner, and the helper that builds a rich captain always granted
  Weavecraft, so removing the requirement broke nothing. The far end is given
  an owner now, and a separate check asks a captain who has not done the
  reading. Sweep: 11/11.
- **`test_thrusters.py`** holds the propulsion model, and its general claim
  is the one that caught all three faults above: **more thrust is never
  worse.** Each time a hull flew *worse* for a better engine, that check
  named it. A second — "a full hold is felt on the helm" — exists because the
  mutation sweep found nothing holding *mass* as opposed to size: fixing the
  moment of inertia to a constant, and dropping cargo from the reckoning
  entirely, both passed everything else. Sweep: 12/12.
- **`test_berthing.py`** holds what an approach costs: that the tank is the
  ship's, that committing spends it, that the clock hears about it, that a
  berth writes `orbit_body` and a lost approach does not, and that an impact
  is paid for in proportion to the speed. Its mutation sweep is 13/13 — with
  one deliberate exception recorded in `test_helm.py`: changing `QUAY_OFFSET`
  is *not* caught, because the painter and the hit test both read it and move
  together, which is the whole point of having one number. The rule that is
  held is that a world and its quay each select themselves.
- **`test_cameras.py`** holds the screens rather than the flying, and measures
  them in pixels: the nose camera must be full of a target the tail cannot see
  at all, and five repaints of a still ship must give one picture. Asking
  `viewport.project` whether the aft camera can see something in front would
  be asking the code to confirm itself.
- **`test_gunfire.py`** ties the picture of an exchange to the resolver that
  produced it: every point of damage must come from a recorded shot (2,138.9
  recorded against 2,138.9 taken over six chronicles), refusals are recorded
  rather than merely logged, and the plot is differenced against the identical
  frame with the shots removed.
- **`test_connwindow.py`** holds the window against the ship: that "close and
  berth" flies the last kilometres rather than running four hundred ticks
  inside the click, and that a conn notices the hull being flown from the helm
  instead of showing an approach on somewhere it has left.
- **`test_screening.py`** holds the screening trade: that a blow meant for the
  flag is worn by whatever is standing in front, that a screen keeps a station
  it can actually hold, that screening protects the flag *and* costs the
  escorts, that it saturates rather than stacking to invulnerability, and that
  every point diverted is a point some hull took.
- **`test_declared.py`** is the standing guard that nothing in `data/` is
  declared and read by nobody, plus the four revivals it forced. Its allowlist
  carries a reason per entry and fails on stale excuses in both directions.
  Mutation sweep 15/15 on source, after a first pass at 11/17 whose four real
  misses were all the same fault — measuring near the thing rather than the
  thing. Notably the corona was checked in the tables and never in a picture,
  and the tedium floor was checked as `THRESHOLD - 1`, which cannot fail for any
  value of the threshold.
- **`test_programmes.py`** holds the endgame bench: that nothing accrues on a
  finished tree that cannot be spent, that every round costs more than the last,
  that all three doors are live and none dominated, that every point of standing
  and every credit traces to a *consumed* finding, that a programme opens only
  when its branch is done, that the screen says which situation it is in, and
  that findings survive a save.
- **`test_orbits.py`** (9 checks, mutation sweep 17/17) holds the gravity model
  and the orbit ladder: that a
  world's year is its *star's* (645 days at one AU round an M dwarf against 272
  round an A-type), that every height the conn offers can be flown to and the
  ones withheld genuinely cannot, that the height is a trade in both
  directions, that the fuel the helm quotes for leaving an orbit is the fuel
  the transfer spends, and that the panel and the sim never disagree about
  whether this is an orbit. Two checks were added when `apply`'s signature was
  fixed: **every offered height resolves on the tank a hull actually carries**
  (32 approaches, all inside 6,000 ticks, 31 in orbit and one run dry — where one
  used to run 60,000 ticks and never resolve), and **a dry hull is told what it
  has** rather than left ordering refused burns.
- **`test_climbs.py`** flies the *offer* rather than the ladder, on the tank
  `conn.start` finds rather than the unlimited one, and fails unless every rung
  the conn sells can be reached and no climb costs more than its price. It also
  reads the console: a refused rung has to be **visible, priced and dead**, and
  hiding one is a mutation the check catches. Its two constants are measured
  rather than chosen — `QUOTABLE` from the gap between the worst rung whose spend
  ran away (25.7 pulses of authority, nine times its quote) and the best one that
  did not (100.7, 1.4×), and `CLIMB_MARGIN` from the worst real climb in seven
  sectors (2.03× the ideal, at Quill Rise II). Both first drafts were caught by
  this suite: 25 let through a rung that ate a tank, and 1.4 promised a price it
  could not keep.
- **The orbit law's two dead ends are recorded in `sim/autopilot.py`** rather
  than in a task, because both were measured and both are counter-intuitive: a
  purely tangential demand asks for zero radial velocity and so spends its whole
  authority *braking* an orbit's natural breathing, which removes energy and
  drove a hull aground; and demanding circular speed at the current radius pumps
  energy into an eccentric orbit, because the ship lingers near apoapsis where
  that demand says go faster. An apsidal law fixes both and flew an asteroid for
  3.1 t against the shipped law's 1,205 — **and is still not shipped, because on
  a 20 t tank it is no better and it goes aground where the shipped law
  survives.** Task #101's plane change does not exist: `hz/|h|` is 1.000 and the
  plane-change Δv is 0.0 m/s at every arrival.
- **`test_tutorial.py`** gained three: a veteran restarting it from the Help
  screen opens at **step 3 of 8 with 2 already done** and is still taught the
  five the chronicle cannot vouch for, only those four lessons carry a
  `skip_if` (the chronicle keeps *state*, and "was cargo ever sold" is
  *history*), and a window can be built around a tutorial that is already
  running — which used to raise
  A fourth brackets the settling-in month from both sides — a captain a week in
  is assumed nothing, one six weeks in has their survey counted — because zeroing
  and halving `SETTLED_IN_DAYS` were caught and **doubling was caught by
  nothing**: the veteran check stands at day 700, so a two-month gate passed
  while a captain a season in was still sent to survey another body.
- **`test_settlement.py`** runs a sector for five years and watches it fill:
  **4 → 13 → 23 → 40 → 59 settlements** across 21 systems and all four workable
  goods, the ground deciding what each one works, the worked good cheaper where it
  is worked than where it is not (ore 32 against 43, phosphate 310 against 362), a
  settled system hungrier for everything it does not make, `Stock.works` composing
  a licence on top of a settlement rather than overwriting it, and a settlement
  costing its founder before it pays.
- **`test_biology.py`** measures the metabolism pairing by surveying rather than
  by reading the table: every biochemistry has its own explaining node and no node
  explains two, a specimen is worth 18 points unread and 30 read, two of eight
  biochemistries are legible on day one and the dearest costs 880 points, the
  catalogue groups only what you actually catalogued and deepest-first, the line
  naming a technology spells it the way `data/tech.py` does — and no body plan
  claims a biochemistry.
- **`test_mesh.py`** holds the picket mesh to what its descriptions promise:
  without a node only the system you are in is plotted *while the traffic
  elsewhere really is there*, a node aboard plots the systems you have stood in
  and no others, a Node planted somewhere plots that system and stops when it
  goes offline, what the mesh shows is what standing there shows (same hulls, same
  names, one derivation), and the chart's warning is true — every hostile count it
  reported was what was actually waiting on arrival.
- **`test_options.py`** is the guard `sim/options.py` had been claiming since it
  was written — its docstring said "`test_options` fails if one stops being
  [read]" and there was no such suite, which is the module's own rule broken one
  level up. Each of the eight settings is **turned on and off and something a
  player would notice has to differ**: the window stops asking, the explanations
  disappear, an open instrument's timer moves from 400 ms to 1,500, the chronicle
  is written at once at zero days and not until day 21 at twenty, the three
  speech settings each push to `core/llm` and the other five do not, and the
  tutorial is offered only with its switch on. Plus the structural pair — every
  field is on the screen and every screen row is a field — and the bounds, which
  are enforced in `set_to` so a second UI cannot disagree with them.
- **`test_provenance.py`** measures both revived fields over samples big enough
  to see a rate in: 2,214 stories from six sectors come true 77% of the time from
  a local source and 45% from the far side, the trust figure the desk prints
  tracks the rate it observes to within 2%, moving `heard_at` alone changes the
  answer, a hub's word beats an outpost's by exactly `QUAY_TRUST` a level, the
  price the panel quotes is the price the counter takes, and a buyer who knows
  the captain pays 30% more for a survey — with both halves of knowing counted,
  so twenty-four dealings inside a month is worth less than the same business
  spread over years.
- **`test_industry.py`** licenses processes and then goes and looks at the
  prices: the buyer's treasury pays to the credit, the gate agrees with the act
  across all 48 process/power pairs, the industry comes up and alloy falls from
  134 to 118 at the licensee's berths against 187 elsewhere, the forecast lands
  within 8% of where the market settles a year later across 21 berths, it costs
  the captain 157 a tonne at that counter against 168 quoted, a berth founded
  afterwards comes up with the industry already running, licensing twice is
  refused and bringing an industry up three times changes nothing, every rival
  notices, and a good a port does not trade stays untraded.
- **`test_exchequer.py`** measures the public purse by running a sector for
  eight years rather than by calling `promote` and observing that it promotes: a
  day moves each purse by exactly what the ledger says, a surplus builds, a
  deficit gives a step up and *recovers the upkeep*, a power that cannot find
  the stake starts no ventures, a blockade costs its target income through the
  same `yield_of` the screen reads, a founded berth quotes prices the player can
  trade at, a closed berth is marked in the register, nobody pulls a berth down
  with the player's hull alongside, and a Free Port of the player's pays them a
  harbour due. The last check is the tripwire set: every constant in
  `data/exchequer.py` is pinned by a consequence — an outpost and a station
  clearing about the same, a promotion being a season of surplus away — rather
  than by repeating its own value.
- **`test_worlds.py`**, **`test_sky_kit.py`** and **`test_lighting.py`** hold the
  astronomical catalogue, and measure it in pixels rather than asserting it from
  the tables that made it. `test_worlds.py`: no two kinds of world render alike, a
  gas giant is banded and nothing else is, and faces meet with no seams between
  them. `test_sky_kit.py`: a star's size is its class's, rings are concentric *in
  the mesh* and belong to the world rather than to its number in the system, a
  ringed giant keeps them when you fly at it, and every kind the galaxy makes has
  a mesh. `test_lighting.py`: a painted world is smooth and its phase follows the
  star, the terminator is where the star puts it — moving with it, monotone into
  the shadow, **brighter than the surface's own colour at full day**, and a
  falloff with width rather than a cliff — and the paint covers the disc at every
  tilt. The three were one file until it passed 500 lines; each of the three
  claims in `test_lighting.py` exists because a mutation of `ui/spheres.py`
  survived without it.
- **`test_ui.py`** builds the real `MainWindow` on Qt's `offscreen` platform and
  paints every screen and every tab, including a live engagement. It stubs
  `win.dialog` because `QDialog.exec()` would block. One check builds its own
  window: grabbing a widget forces a layout pass, so a check for first-frame
  layout cannot reuse one every earlier check has already painted.
