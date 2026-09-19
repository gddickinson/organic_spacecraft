# Session log, part 14 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: four ways not to smooth a sphere

Graphics, as asked. At 22 rings by 30 segments a world filling the window read as
the polyhedron it is — flat shading gives each face one colour, so the quads were
countable across the terminator.

The obvious answer is Gouraud, and `QPainter` has no per-vertex colour, so I tried
to reach it with a `QLinearGradient` per face. **It cannot be done and it took me
four attempts to understand why.** A linear gradient is constant perpendicular to
its own axis where real Gouraud varies, and that error alternates with a quad's
orientation — so every version put a checkerboard on the sphere. Corner to corner;
then with the axis taken from the projected light; then with the ends chosen
geometrically along that axis; then ordered by latitude so the colour could never
reverse. Checkered every time. It was not the rim term — forcing that to zero left
the pattern untouched, which is what finally identified the cause. I also
reintroduced, in passing, the exact wireframe the original code documents removing,
by stroking each face with its palest colour. All of it reverted.

**Geometry is what worked.** 22x30 is plainly faceted; four times finer is smooth;
and the cost is in faces rather than pixels — 6.7 ms against 20 ms for the same
world whatever size it is on screen. So worlds are built at two resolutions and the
viewport spends the fine one only above 90 px of radius. The whole conn window
repaints in 102 ms against a 700 ms timer, and a distant world still costs 8 ms.

Where the faces go matters as much as how many: at equal cost 44x58 bands
horizontally (colour runs with latitude, rings sample it) while 70x36 and 96x26
stripe the limb (segments round the silhouette). 60x44 reads smooth in both.

**It is better rather than beautiful.** The residual banding is inherent to
flat-shaded polygons with one colour a face. The real fix is to stop treating a
sphere as geometry — project it to a disc and shade it analytically with an offset
radial gradient, exact for a Lambertian sphere and cheaper than either mesh. Filed
as #97 rather than started at the end of a cycle.

`test_worlds.py` went past five hundred with the new check, so the stars, rings
and catalogue moved to `test_sky_kit.py`. And the reachable guard caught me on the
way out: I had left two "kept for callers that want one mesh" wrappers behind the
paint-function split, and there are no such callers. Deleted.

One more honest note: 5 of 6 mutants bite. The sixth drops the sky path's request
for detail, and I could not establish whether a peripheral body ever gets large
enough for it to show — my probe found no sky shapes at all, so it measured
nothing. Left unpinned and said so rather than dressed up.

Full suite green.

## 2026-07-29 — SEEDFALL: the register never said what the flight cost

Trading picked for breadth. The market itself came out sound: across all thirteen
goods there is a 20% spread and no same-counter money pump, and the depth is real —
buying 280 t of ore drove the price 36 → 43 and drained the stock to nothing, which
relaxed back over a year. The fault was in the *information*.

`best_markets` returned a price, an age and a confidence, and the panel drew a
straight-line light-year count beside it. No hops, no days, no notion of whether
the ship could get there at all. Over six sectors and six commodities:

- **32% of the recommendations were to systems the ship cannot reach** — not far,
  not dear, unreachable, and nothing said so.
- **44% of the lists put a worse port first**, the worst ranking a port worth 0.5
  a day above one on the same list worth 3.9.

`reach.route_to` has existed since the contract board needed it, and its docstring
names this exact lesson — the board "named a reward and a deadline and never once
said where the work *was*". The rows carry hops and days now; selling ranks on
revenue a day, buying on price with days breaking ties. The unreachable stay,
marked and last, because a jump drive is a thing a captain can buy. On one board
that puts Lumen Mouth — paying the *highest* price for ore at ₡31 — at the bottom
reading "beyond your jump", while the reachable port shows "1 hop, 7 days · 4 a
day". `reach.routes_from` does the walk once for the whole list.

**Two latent faults fell out of the reordering:**

- `freight.runs` said "a price you wrote down beats a price somebody described to
  you" and did not do it — it kept whichever run had the higher `worth`, and the
  register won often enough that the check on it passed. Measured, **18 of 44 runs
  known both ways have the desk quoting the better number.**
- `from_register` inherited a *display* limit of four, so what work existed at a
  desk depended on how many rows a panel draws. 549 register-known runs are
  offered where four used to be.

**Three of my own mutants were wrong before they were right.** `elif False` on the
preference branch left no cross-source path at all, so the register still won by
insertion order and the mutant proved nothing; the limit mutant was masked because
the check derived its overlap from the same shrunken function; and `route_to`'s
None-for-unreachable was pinned by nothing, because my new checks read
`routes_from` directly. Rewritten, all three bite — ten of ten now.

Full suite green.

## 2026-07-29 — SEEDFALL: one asteroid gave up 8,427 tonnes instead of 140

Mining picked for breadth — nothing had touched it, trading or expeditions for
many cycles — and it turned up the largest arithmetic hole in the game so far.

`raise_rate` lifts material with four rigs: `mine` for ore, `phos` for phosphate,
`drink` for volatiles, `graze` for biomass. `actions.extract` wore the body down
with **two of them**, `st.mine + st.drink`. So a phosphate rig and a harvest
tendril raised material and depleted nothing at all. Fit a token mining root
beside them and one body gave up **8,427 t over 283 spells, against an ordinary
hull's 140 t over 8** — sixty times its worth.

`mining.RIGS` is one table now — the pairs `raise_rate` itself walks — and
`rig_of` sums it, so a rig that lifts material wears the body down by
construction rather than by two lists agreeing. After: 159 t against 128 t, which
is fittings mattering rather than a fountain.

**The forecast was biased by the very option it was there to compare.**
`prospect` estimated the average rate at the midpoint of what was left, times
days, times a `WORKING_LOSS` fudge. Against actually working the body out it came
in 2% low on a bioleach and **45% low on a bore** — the error tracking how fast
the method depletes. And the days were a fifth too long, because `prospect` used
`max(mine, drink)` where `extract` used the sum.

It is a dry run now, walking the body down in five-day steps through the same
`raise_rate` and depletion arithmetic — it cannot disagree with the act because it
*is* the act with the ship left at home, which is the same reason `sim/preview.py`
flies a throwaway twin rather than predicting a burn. With events silenced the
error across all four methods is −0.0%, +0.0%, +0.2%, +0.1%. With events live it
moves ±6% either way, a windfall and an accident behaving like noise.

The point of all that is a legible choice, and now a true one. On one ice body the
screen reads: a cut and a bore both recover about 98 t, but the bore takes 64 days
against 135; a bioleach recovers **254 t** over 386. Speed against total.

**Four things I got wrong, and one that cost real time:**

- **I claimed an infinite source and had to withdraw it.** A phosphate-only hull
  raises material and depletes nothing — but `extract` refuses a hull with no
  mining root *and* no harvest tendril, so it is unreachable. The exploit needed a
  token mine beside it, and is sixty-fold rather than unbounded. I wrote the
  check on the wrong claim first and it failed, which is how I found out.
- **My first two measurements compared the wrong things.** One drove
  `raise_rate` in my own loop rather than the game's `extract`; the next passed
  its own rig into `deplete`. Both produced tables I nearly reported.
- **I segfaulted nothing this time but I did hang the sweep.** The dry run's
  `while` loop exited only when the depletion arithmetic advanced, so the mutation
  that removed the advance spun for ever. I had to kill the sweep — and killing it
  left the mutation sitting in the tree, which I caught only by checking the file
  afterwards. There is a hard step bound beside the depletion test now. A loop
  whose termination depends on arithmetic is a hang waiting for someone to break
  the arithmetic, and a check that hangs costs everything and tells you nothing.
- **One mutation in the sweep mutates nothing observable** — taking the step bound
  off changes no behaviour while the advance still works. That is defence in depth,
  not a hole in the checks, so the honest score is 7 caught of 8 tried rather than
  a claim of 8.

Full suite green.

## 2026-07-29 — SEEDFALL: "grievances are counted", and they were not

Picked diplomacy for breadth — the last three cycles were piloting, combat and a
cross-cutting guard.

**The screen promises this in three places and the code did none of it.**
`approach.preview` tells a captain refusing a levy that "they will file it as a
grievance, and grievances are counted"; the levy's `costs` line says "they collect
grievances". What happened was
`dip.ensure(game).grievances = getattr(..., "grievances", 0) + 1` — a counter on
a field `DiplomaticState` **does not declare.** Nothing read it, and being
undeclared the save's decoder dropped it: set it to seven, save, reload, and it
is gone.

**An existing check covered it and passed.** `test_envoy` asserted the counter
went up, read through `getattr(state, "grievances", 0)` — which is exactly how an
undeclared attribute passes for a field — and never saved. The number moved, the
check was satisfied, the feature was absent. A `getattr` with a default is what
let the two look the same.

The real fault underneath was an asymmetry. An overture is remembered, and so is
an answer to a demand for ground — `territory.answer` notes pay, cede and refuse,
and `grudge.because` puts them on the diplomacy screen. **An envoy's answer was
the one dealing with a power that left no trace at all**, so a captain who had
refused four levies met a power that priced him badly and a screen that could not
say why.

So a grievance is a *memory* now — the machinery that already turns dated things
into a price bias and into whether a power will deal with you, and which
persists. Refusing levies takes the Charter from **0.0 to −28.6** feeling and its
prices from x1.000 to **x1.051**; the screen reads "Their feeling −34 · Their
prices to you +6% on what you buy · Y1 D001 · you left our levy unpaid (−14)".
Accepting a requisition is deliberately not remembered: a power recording every
barrel of ore would have a ledger nobody could read.

Three dead fields went with it — `Envoy.choice` and `territory.Demand.choice`,
both redundant now the memory carries the answer, and `DiplomaticState.favours`.

**The guard I extended last cycle had a hole, and `favours` was in it.** The
accessor hatch credited any dict subscript as reading a field, so `favours` — read
nowhere — was excused because `sim/officials.py` keeps an unrelated per-official
favours dict and reaches it as `store["favours"]`. A field excused by a dict that
happens to share its name is a guard doing nothing. What counts now is a named
accessor reaching a field by string: `getattr`/`hasattr`/`setattr`, and a
two-argument `get`/`set_to` with the subject first — the shape of
`options.get(game, "hints")`, whose body is a `getattr`. The credited-name set
fell from **538 to 153**.

**And I chased a mirage for a good while, which is worth the record.** I came at
diplomacy by asking whether the four powers ever move among themselves, watched
the relations matrix freeze after year six and the venture count stop dead at 36,
and built a detailed case that the powers stall. **They do not.** `advance_days`
returns early on `game.victory`; the unattended chronicle had reached the "ruin"
ending and the clock was correctly waiting for the player to take it or carry on
into the epoch. Two wrong turns on the way there, too: I first read the venture
total as the live count, and I reported four ventures as "stuck" when their
`until` days were plainly in the future. The lesson is about measurement — a
headless probe that advances years without driving the ending measures a stopped
clock — and `tests/chronicle.py` already knew it, guarding on
`not game.victory` and asserting it got twenty rounds in.

8 mutations, **8 caught**. Full suite green.

## 2026-07-29 — SEEDFALL: seven officer traits that did nothing

Task #88 pointed the declared-field guard past `data/` into `sim/`, `world/` and
`core/` — 1,167 fields — and the richest seam was the crew.

`crew.TRAITS` has declared seven officer traits since it was written, each with an
effect key and a magnitude: Charter-raised +0.04 diplomacy, Yards-trained +0.05
repair, Freehold-born +0.05 trade, Bloom veteran +0.05 tactical, Wet-wired +0.03
accuracy, Quiet +0.04 scan, Reckless +0.04 evade. **Not one of them was ever
applied.** `Officer.trait_id` was written when a candidate was generated and read
by nobody — `trait_name` and `trait_note` reached the crew screen, so a Bloom
veteran said "Was at Kessel's Reach and came back" and fought exactly like anybody
else. And it is priced: `make_officer` charges 25 a month for a trait, so a
captain had been paying for seven effects that did not exist.

`crew.trait_effects` sums them and `ship.stats` adds each into the stat it names.
**My first wiring of the seventh was wrong and measuring caught it.** Six keys
name a stat computed in `stats`; `tactical` names the *skill* the combat numbers
derive from, so I converted it into levels — which moved accuracy by 0.0026 where
every other trait moved its stat by 0.03 to 0.05. A magnitude declared in stat
units is a stat. It adds to accuracy and evade directly now, and the constant I
had invented for the conversion is gone.

Two more findings landed on the gunner's board, which is the one screen whose job
they were. **`firing.Shot.band_shift`** — "bands to close or open to reach its
envelope" — was read by nobody, so a mount out of range said "range" and left the
captain to work out which way; it says "open 3" now, which is an order for the
helm rather than a complaint. **`gunfire.Shot.frm`, `.to` and `.weapon`** recorded
who fired, at whom, with what, and nothing read any of them — so which gun did
what existed only as prose in the log while the gunner saw a heat number change
and nothing else. There is a Last exchange list now, both directions.

Two were deleted rather than wired: `anchorage.Anchorage.extras`, a dict built in
three places holding a redundant copy of things reachable from the objects
themselves, and `territory.Demand.holdings`, a stored count beside a live
`holdings_in()` — the two-doors fault this project has hit more than any other.
The six that remain are allowlisted against three new tasks (#92 answers a power
remembers, #93 familiarity and a rumour's provenance, #94 the Chorus Node's drift).

**Four things went wrong on the way, all mine:**

- **The guard was counting writes as reads.** A regex for `.name` matched
  `self.x = 1`, so a field only ever assigned looked alive. It walks the AST for a
  `Load` now — and three of the findings were exactly that shape: written once, at
  construction or on an answer, and consulted by nobody after.
- **A field only the suite reads is still dead.** Deleting `extras` broke
  `test_anchorage`, which was its sole reader in the whole tree. The check now
  finds that colony berth by its id, and the guard's exclusion of the tests is
  the reason it found the field at all.
- **Constructor keywords are invisible to an attribute walk.** Both deletions
  broke on `Anchorage(extras=…)` and `Demand(holdings=…)`, which my audit had
  classified as "never touched" when they were written every time one was built.
  The verdict was right — a write is not a read — but I twice reported a
  classification I had not earned, and had to go and find the writes.
- **And I segfaulted the suite.** The new board check reads labels off the
  rendered window, and my helper swept `findChildren(object)` and called `text()`
  on whatever came back inside a bare `try` — which is how you reach a Python
  wrapper whose C++ object has already been destroyed. The whole run died with
  **exit 139 in the 3D renderer, three suites later**, with nothing in the file
  that caused it failing. Stashing the changes and running HEAD clean is what
  established it was mine rather than a flake. Ask for the types you want.

`test_declared.py` covers four packages now: 1,167 fields, 8 unread and every one
explained. The guard and the behaviour it revived split into `test_declared.py`
and `test_revived.py` when they went past five hundred lines together, and
`test_volley.py` shed its window checks into `test_gunboard.py` for the same
reason — the seam being sim on one side and the seat on the other. 12 mutations,
**12 caught**. Full suite green: 863 checks across 115 suites.

## 2026-07-29 — SEEDFALL: the gunner had no middle

`combat` offered two ways to shoot. One named mount, or `_salvo` — "everything
that can bear, fired together" — whose docstring says the cost is heat and
ammunition, "which is why a single aimed shot stays a real option". That reads
like a trade until it is measured.

**A HAMMERFALL with five mounts puts 69 points of heat into itself in one salvo,
against a fault line of 40 and a vent of 6 a turn.** It faults on turn one and
never comes back: across ten turns resolve bled from 92.9 to −34 on its own
radiators, in a fight it was winning on damage. The alternative was one mount out
of five. So **buying armament made the salvo button worse** — the question this
project asks of every good thing, and here the answer was yes.

`sim/gunnery.py` is the missing control: fire *some* of them. `quote` says what a
set will do to the hull before the trigger, modelled on the turn as it actually
resolves — heat in, clamp, vent, then the fault test — because a volley that
lands a point over and vents six is not a fault. `advise` takes the most damage
of any set that will not fault, found exhaustively, since no chassis carries more
than five mounts and 32 subsets is nothing.

On the hot hull the advised volley won **6/12 and 4/12 against 1/12 and 2/12** for
firing everything, and faulted on none of its turns against 53% and 57%. On a
cooler LONGSHOT the three options are level inside a twelve-seed sample, and
firing everything still cooks the ship half the time.

**Almost all of this cycle went on being wrong carefully, so it is worth the
record.**

- **My harness measured nothing, twice.** Five of the eighteen weapons draw
  `alloy` and a new captain carries none, so every one of them reported dry: I
  produced two full tables of win rates from fights in which *zero mounts fired*.
  Worse, my "one best mount" branch fell through to `brace` when nothing could
  fire, and bracing *raises* resolve — so the mode I was holding up as the
  benchmark was winning by not shooting. Both tables were discarded.
- **`advise` was wrong twice.** First it ordered by damage *per point of heat* —
  heat is the constraint, so economise heat — which favours the small guns and
  left the main armament cold: 3 wins in 12 against 6 for firing one Fusion Lance
  every turn. Economising heat is not the job. Then it could advise firing
  *nothing*, and played out it said fire, hold, fire, hold, shooting half as often
  as the enemy. `ship.py` records the same lesson beside `HEAT_CEILING` from the
  last time: they "lost to their own radiators, in a fight they never shot in."
- **I read the fault line the wrong way round.** It is `heat_cap`, not
  `heat_cap * HEAT_CEILING` — the ceiling is the physical clamp, half again as
  far away. A board built on the clamp would have called every faulting volley
  safe. `gunnery.fault_line` is one function now and `_end_of_turn` asks it too.
- **`Shot.mount_id` is a part id and is not unique.** Three Fusion Lances all
  answer to `fusion_lance`, so five mounts came back under three names. They are
  genuinely interchangeable, so a selection is a **multiset** — and my
  `firing_set` would happily have fired six lances off a hull with three and
  charged the heat for all six.
- **My boresight drew half an arc.** `firing.arc_span` returns *half-angles* —
  its docstring says so — and I drew a single wedge from `low` clockwise, putting
  a fore arc entirely to starboard. `ui/tactical_plot.py` had been fixed for the
  same thing already and left the reason: "drawing only one of them is a lie
  about the ship." Looking at the screen did not catch it, because the target
  happened to be near dead ahead.
- **The sweep found three holes in my checks**, each for a specific reason: with
  a 2-heat PDC aboard the advice never reaches its floor, so the hold-fire
  mutation survived; both orderings happened to include a lance, so "beats one
  mount" could not tell them apart; and on the mixed-arc hull the advice takes
  every bearing mount, so a trigger replaced by a full salvo fired the same
  shots. Fixed with a heavy-guns-only loadout, an exhaustive brute-force optimum
  as the yardstick, and the hot hull for the trigger. 12 mutations, **12 caught**.

`ui/gunner_window.py` is the seat: a boresight per mount, the tactical plot, a
board of every mount with what stops it and what it costs, and the trigger with
the heat quoted first. `MainWindow.battle_act` is now the one door for resolving
a turn, since there are two seats on one engagement and the second copy is where
the `b.player.st = ship_stats` line gets left out.

`test_volley.py`, 9 checks, two of them driven through the window and one reading
pixels off a rendered sight. Full suite green.

## 2026-07-29 — SEEDFALL: the pilot could not throttle

`sim/conn.apply` has taken a `throttle` since the drive learned to throttle and a
`ticks` since it was written. **The conn could reach neither.** The window fired
`apply(conn, axis, main=use_main)` and nothing else, so the human's main drive was
a switch — full power, one minute — while the flight computer sitting beside it
throttled freely. `apply` still carries the note explaining why the *computer*
needed it: "one tick of a fusion torch on a SPORE is 124 m/s, so the computer lit
it to trim ten, overshot, corrected the overshoot, and never converged." The
human was left with the firework.

Flown by hand that is not a rough edge, it is a hull that cannot be berthed. A
SPORE under a Fusion Torch moves **41.9 m/s a press**, so a pilot carrying ten
metres a second of way on has no move that helps: every press overshoots by more
than the error. A greedy hand pilot with only full power stays **stuck at 10.00
m/s**, outside the 1.5 m/s berthing limit, for ever. With the ladder — a tenth, a
quarter, a half, everything — the same pilot reaches **0.48 m/s** and berths.

Two controls, not one, because `apply` does two things: it fires *once* and then
steps time `ticks` times. So the second is a **coast** (1, 5 or 15 minutes) and
not a burn length, and there is a check pinning that, because the button's name
is all a pilot has to go on and calling it a burn length would be a lie.

**A real fault fell out of routing the cost through one door.** `can_burn`
demanded a whole `MAIN_COST` whatever the throttle, so a hull holding 0.119 t was
told "No reaction mass for the drive" for a burn costing 0.012 — a gate refusing
an act it could well afford, which is the fault this project has swept every
other gate for. It survived because the throttle was unreachable, so nobody had
thought to ask. `pilot.burn_cost` is the only door now and `apply` spends through
it too.

Three things worth recording about the checks rather than the code:

- **The sweep found two holes in my own checks.** `apply` has its *own*
  `can_burn` call, and asking it at full power left `can_burn` correct and the
  burn still refused, with nothing failing. And nothing compared
  `quote()["dv"]` against the act — every check either called `dv_of` directly
  or compared range and closing. Both closed; both then caught.
- **One of my mutants was aimed at the wrong file** and mutated nothing. That is
  a wasted line, not a missed check, and it is worth telling the two apart.
- **A correction to yesterday.** I wrote that a LEVIATHAN shrugs a missing engine
  off entirely because its inertia beats the torque. Measured on one engine and
  generalised too far: a LEVIATHAN holds 1.00 under a Reaction-Mass Organ and
  **0.20 under a Fusion Torch**, and a NAVIS with one Fusion Torch sits on the
  0.15 floor. What decides the cap is off-axis thrust against attitude authority
  — mass helps at equal thrust, but thrust is the term that varies most. So the
  rule is that **a big engine on a hull with few stations is the liability**,
  which is a better rule than the one I first wrote. The check has been rewritten
  to claim that instead, across both engines.

`ui/conn_controls.py` is the console, split out of `ui/conn_window.py` (519 lines)
along the seam already there: the window owns the cameras, the panel and the
clock. `sim/pilot.py` holds the ladders and the doors. The panel names both
settings in m/s, because "10%" of a number the pilot cannot see is not
information.

`test_pilot.py`, 9 checks, plus one driven through the window itself — pressing
the buttons rather than calling `apply`, since a check that called
`apply(throttle=...)` would have passed for as long as the bug existed.
Thirteen mutations, **thirteen caught**. Full suite green.
