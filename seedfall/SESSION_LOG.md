# Session log

Chronology only. **Why** each pass exists and what it measured is in
`IMPROVEMENTS.md`; how the code is laid out is in `INTERFACE.md`. This file
answers "what happened, in what order, and where did it land".

## The flight-deck campaign, 2026-08-02 → 2026-08-03

Opened with: the pilot window, flight control, conn and gunnery were not
integrated, were sluggish, contradicted each other, and the autopilot's
actions were not what the screens showed.

| # | Pass | Commit | What landed |
|---|------|--------|-------------|
| 0 | The screen, not the harness | `7811ef2` and two before it | #145's four items: the guns below the fold, a label sized by its own width, a window that told the truth |
| 1 | One flight deck | `a6393aa` | The armed state moved off the windows and onto the flight (`Conn.auto`); #148, #149, #153 |
| 2 | The deck's backlog | `c9335eb`, `d81eba7` | Bays flown, forecasts made true, the ground orderable; the backlog gets `IMPROVEMENTS.md` |
| 3 | Held engines, one clock | `84a0a00` | Hold-to-burn physics, a deck-aware universal clock, keyboard flying |
| 4 | The window shows the flying | `304941d` | Predicted path, prograde/retrograde, the aim chevron, the bay mouth |
| 5 | One computer | `4c66be4` | `sim/flightdeck.py` — one dispatcher, one bar on five surfaces |
| 6 | Flown rigorously | `c7242f7` | Three defects found by flying; the flying and non-flying halves meet |
| 7 | A curriculum | `874eb83` | Ten chapters, twenty-nine lessons; and a process-killing paint bug that only a full run could find |
| 8 | Contact is meant | `9dd0d50` | `sim/collision.py`: the guard, the safeties switch, braking that works under every mode |
| 9 | What the instruments see | *this pass* | `data/countermeasures.py`, `sim/detection.py`: range, quality, and things that hide |

## This pass, in one paragraph

The collision guard read `Conn.sky` — a perfect list — so every hull had a
perfect sensor and a raider running dark was tracked like a lit quay.
Detection is now a range (`SENSOR_KM` × array × signature) and a quality that
falls off toward the edge, poor fixes are read pessimistically rather than
trusted, and the array was stamped onto `Conn` so the instrument panel (which
holds a Conn and no Game) cannot read a different sky from the computer. The
rule it produces: **a cloak beats your brakes before it beats your eyes** —
lit contacts show at 16,800 km against 1,019 km of stopping distance, and a
cloaked one at 588.

The tutorial grew a thirtieth lesson to teach it, and the safeties switch —
which two windows were flipping themselves, with a copy of the wording each —
became one sim door. Two more things came off the back of it: `sim/conn.py` went over the 500-line
ceiling and was split at a real seam (`sim/conn_open.py` — opening a flight
reads the whole game; flying one does not), and the manual grew a topic that
quotes your own ranges off your own array.

## The ninth pass: orbits (2026-08-03)

Every orbit in the game was a circle in one plane going one way, because
`flight.position` had exactly one element to read. It now has six, derived
rather than stored, and positions are three-dimensional from the ephemeris
out to both charts and the conn's own windows. The rule that governs the
tables: every bound is a real Solar System body, so none of it is taste.

## The GUI play-test (2026-08-03)

Thirteen screens built, painted and resized; every button pressed; a
chronicle surveyed, flown, jumped, saved and reloaded. It found the defect
the orbit work had left behind and no suite had asked about: **a course could
not point out of the plane**, because `Conn.heading` is one angle. The flight
deck now has a pitch as well, and a run that used to sail past at 1,514 km
arrives at 14.

## Reported from play (2026-08-03)

*"The auto-pilot wouldn't move anywhere, and Fleet Hub could be seen in every
view at the same distance in every direction."* One fault, both halves: a
quay sat at its body's exact coordinates — the centre of the planet — so the
range to it was zero. Quays have places of their own now.

## Docking, end to end (2026-08-04)

"Run for Fleet Hub" used to stop 50 km off and hand back the conn. It now
carries through the hand-over, the clearance and the tug to lines across at
the granted berth — 18 of 18 chronicles. Fixing that exposed the boats towing
hulls straight through the structure, which is now a swing round it.

## Stellar remnants (2026-08-04)

White dwarfs, neutron stars and black holes stopped generating their systems
from the living-star table. Changing what a corpse keeps shifts the RNG
stream, so every seed grows a different sector — which flushed out three
seed-dependent fixtures, one of them a rule (`gate_body`) that had been
stated in a docstring and never enforced.

**A generator's draws are an interface.** Changing *how many* numbers the
sector generator takes reshapes every seed's galaxy. Anything new there has
to be derived after the fact, not rolled.

## The review, and the tenth pass (2026-08-04)

A four-agent review (combat, economy, strategic layer, player experience)
plus a live play-through over the bridge. The verdict, and it held up under
measurement: the flight deck is done and the systems layers were not. The
worst of it went in `IMPROVEMENTS.md` and the worst of *that* was fixed the
same day — the Help-screen session brick, Escape destroying saves twice,
trading never saved; the same-counter arbitrage (18,000 → 2.6M on day 0),
the prospect-contract fee farm, boards that never refreshed; the Bloom's
whole antagonist arc gated behind a burden only a losing player reaches;
the flash organ deciding every fight on its own; two diplomacy exploits.
Every fix carries a played claim in the suite.

Two lessons worth keeping. **The suite was green through all of it**,
because nearly every finding was about reachability and balance — code that
works and is never reached, numbers individually pinned and jointly
exploitable. The claims that catch these are *played* ones: a round trip
must lose money, an engaged captain must meet stage 3, a board must refill.
**And an invariant beats a corrected formula**: the spread fix is not a
repaired coefficient but a stated law — the same counter never pays more
than it asks — clamped at both layers, so every future modifier is covered
on the day it is added.

## The eleventh pass: the sector answers back (2026-08-04)

The top of the reassessed list. Waiting stands down on news worth a hand —
found by playing, where a year alongside a Fleet Hub starved three crew one
at a time while the log warned five times and nothing paused. Infestation
now costs the powers income, so their fleets, ventures and promotions all
feel it; they fit out containment flotillas, which is the first thing in
the game besides the captain ever to reduce `system.bloom`. Ruin has to be
*outlived* rather than waited out, and the loss fires when the harbours
drown rather than 180 days after Ruin was already available. An empire pays
administration that rises with its size, so colony spam has a ceiling and
the late game has a credit sink.

**A control that is not the thing you changed is not a control.**
`test_industry` asserted the licensee's berths were cheaper than *other
powers'* berths; the moment infestation began moving power economies that
inverted by one credit, while the effect under test was working exactly as
measured. Its own docstring already recorded recalibrating a comparison of
that shape once before. The claim is now the same berths over the same year
without the licence.

## The run that looked green and was not (2026-08-04)

The tenth pass was reported green and committed on a run that had a failing
check in it. The harness was fine — `python -m seedfall.tests` returns 1 on
failure and always did. The command was wrong:

    python -m seedfall.tests 2>&1 | tail -50; echo "EXIT: $?"

**`$?` after a pipeline is the exit status of the last command in it** — of
`tail`, which succeeds at printing whatever it is given, including a report
full of failures. Every "EXIT: 0" that command printed was `tail`'s.

This is the same failure the exit-139 hunt already recorded from the other
side: *grade a run on its exit code, never on a count of FAIL lines*. The
rule was right and the measurement was of the wrong process. Redirect to a
file and read `$?` from the interpreter itself:

    python -m seedfall.tests > run.log 2>&1; echo "EXIT: $?"; grep -c FAIL run.log

What it hid: `tests/test_ui.py` had gone to 530 lines, over the ceiling the
project holds by check, and rode into commit `0c98798` that way. The
eleventh pass added three more violations before anybody looked. All four
are paid off — the window's *application* behaviour (navigation refusal,
save on quit, dismissed dialogs, the unstubbed briefing) is
`tests/test_window.py`; the seed dialog is `ui/seed_dialog.py`; the
exchequer's screen queries are `sim/exchequer_ledger.py`, which took that
file under the limit and **off the debt list**; and the Bloom endgame is
`tests/test_endgame.py`.

Measuring properly then surfaced **fifteen** failures the pipe had hidden.
Four were real regressions, six were checks encoding rules deliberately
changed, and five were checks that had been measuring badly for a while —
a growth comparison run so long both arms saturated and read equal to the
decimal, two judged on samples coarser than the effect, and one that
counted a comment as a call. A check that cannot fail for the right reason
will eventually fail for the wrong one.

## The twelfth pass: played again (2026-08-04)

Five things, every one found by playing the committed tree rather than by
reading it. The ship's log — the game's only notification channel — had
become an unreadable smear of two-pixel slivers by day 226, which is the
same scroll-area fault `widgets.View` was fixed for and the one panel that
fix never reached. Standing down on *every* bad line had turned a long wait
into a wall, so "carry on" now means "I have read that". A driven session
deadlocked the moment a power sent an envoy, because the protocol could
neither see nor answer one. The containment bar told a captain who had done
nothing that they were nearly finished. And the endings panel still said
"five".

**Play the build you shipped.** The suite was green for all five: three
were interface behaviour no check looked at, one was a protocol gap, and
one was prose. A green suite says the rules hold, not that the game reads
well after two hundred days.

## The thirteenth pass: the flight deck, photographed (2026-08-05)

A deep dive through the real interface — a hull flown to Fleet Hub by hand
and then handed to the computer, every flying window opened, every
instrument photographed and looked at. Five defects, and the common thread
is that **not one of them stopped anything working**: a finished approach
silently replaced by a fresh one when the conn was opened, two controls
drawn in the same grid cell, a value clipped mid-word, and two plots that
wrote their labels on top of each other.

`test_flightops` presses every control in these windows and had been green
throughout. Pressing a control proves it fires; it says nothing about
whether the pilot can read what happened. `tests/test_flightpix.py` is the
suite for the second question — overlap, clipping, label crowding, and the
flight surviving the window that shows it.

**A picture is a test you can only run by looking.** Every one of these was
found in a screenshot, and three of them are invisible to any assertion
anybody would think to write about behaviour.

## The fourteenth pass: the fog, and two stolen flights (2026-08-05)

The Holdings panel was counting every infested system in the sector and
printing the sector-wide burden, directly under a picket sold on telling you
what happens where you are not. `threat.known_bloom` is the census now, and
`victory_progress(seen_only=True)` fogs the containment bar — but never the
achieved flag, because winning is decided by what is true and not by what
has been looked at.

Then a forty-six shot sweep: every screen, a flight photographed at five
stages, an orbit, a free flight, all six cameras. It found the conn stealing
live flights — opening the window while established in an orbit switched the
target to a quay and began again at twelve kilometres. Two causes, and the
second is the one worth remembering: **a `Target`'s id is not a `Contact`'s
id.** A quay is `quay:port-14` on both sides and compares equal; a body is
`body:0` as a contact and `0` as a target, so the question "am I already
flying to this?" answered *no* for every world in the game. Both sides go
through `targets.target_from_contact` before they are compared now.

And then the one that had been recorded rather than fixed: a world you are
standing at read 0 km, because `flight.ship_position` put the hull at the
body's exact centre. **A ship in orbit is not at the planet's core.** It
holds `flight.ship_orbit_offset` now — the radius the flight actually flies,
derived from the body's identity and the calendar, never stored — so the
world that read 0 km reads 7,449 km, its standard orbit radius, and the
conn's altitude agrees because both ask `orbits.height_km`.

That is the *third* defect of this shape: a quay at its planet's centre
(`anchorage.berth_orbit`), a hull sharing a body (`traffic.STATION_KM`), and
now the ship itself. **Anything that can be somewhere needs a place of its
own** — a position inherited from what you are near is a zero waiting to be
printed.

## The fifteenth pass: one way in to everything (2026-08-05)

A player asked how to use a Weave anchor, having flown to one. The answer is
that you do not use it there at all — a ring is ridden from the sector
chart — and the anchor they had flown to offered them "Open holdings",
because that is the anchorage card's fall-through for anything that is not a
quay.

Fixed at the anchor (what it is, whether it is lit, what waking wants), in
the manual (a topic with a fact that reads this chronicle), and then
generally: `sim/hail.py` answers "who is this, what do they say, and what can
I do about it" for anything `sim/track` can put a cursor on, and
`ui/comms_window.py` is the channel that shows it. Every option is a door
that already existed, so the menu cannot promise what the game will refuse.

**An object the player can fly to is a promise.** The acts existed for every
one of these things; they were scattered across screens that each knew about
one kind of object, so knowing what you could do depended on knowing which
screen owned it. That is not discoverability, it is a quiz.

## The sixteenth pass: played long (2026-08-05)

Fifty-odd headless chronicles across the economy, four long games through
the real GUI to day 2,600, and every dialog-gated flow driven directly. The
GUI play found nothing at all — no crash, no impossible state, in 500-odd
presses. The long economy runs found eight things.

The one worth remembering: **the game had no way to lose by neglect.** Three
modules agreed the chronicle ends when there is nobody left aboard, and the
test sat inside a branch that is only reached when the crew is short of
something — which cannot happen once there is no crew. Every do-nothing
chronicle emptied and sailed on for ever.

Fixing it immediately exposed two more, and both were the *test captain*
being naive rather than the game being unfair: the trading bot bought fuel
and never food, and once the bodies in reach ran out it had no income at
all. A real loss condition is a measuring instrument — it finds every place
something was quietly surviving on the game's failure to enforce a rule.

## 2026-08-05 — one ship, one place, one drive

Three reports from play, and all three were the same fault wearing different
clothes: a fact with more than one door.

The deep one was the ship's position. `flight.ship_position` answered with
the *recorded* place, which is not written again until `berthing.commit` —
so the helm's map, the plotting board and the tactical list held the hull at
the quay it left while the conn beside them counted the range down. It was
reported as four windows failing to update. It was actually one window
telling the truth and four faithfully reading a field nobody had written.

The first fix was wrong in an instructive way. I made `ship_position` add
`conn.pos`, reasoning that the conn knows where she has been flown to — and
two checks caught it within the hour. **`conn.pos` is not an offset from the
ship.** An approach's frame is anchored on its *target*, and `conn_open.start`
opens it at a canned arrival range, so `conn.pos` is already twelve
kilometres the instant the conn is taken. Adding it teleported the hull every
time a window opened; a played check watched a 110 km flight register as
0.0 km moved, because reopening the conn silently re-anchored the frame. The
quantity that is honest in both frames is the *difference* — `Conn.start_pos`
and the `flown_km` built on it — zero when a conn opens and exactly the
kilometres flown after. The lesson is the file's oldest one restated: a
number is only a fact once you know what frame it is measured in.

Two smaller ones, same shape. The engine button read "off" while the
computer was burning, because three windows each formatted that label
themselves and only the flight panel had learned to say FIRING. And speed was
on every panel already — under two names, "Speed" in a free flight and
"Relative" everywhere else, which reads as a missing instrument and was
reported as one.

`sim/flight.py` was at the 500-line ceiling before any of this, so
`ship_orbit_offset` and its constants moved to `sim/orbits.py`, where the
geometry already lived and where the lazy import it needed disappears. The
precedent was in the file's own comment about `sim/path.py`.

One old check went red, and it was worth the hour. `test_war` asks for six
sectors and a decade each; loss by neglect (added last pass) ends a
do-nothing chronicle at about day 1,360, and `advance_days` early-returns
after that — so the loop that says 3,600 days was quietly running 1,400. The
check had been measuring a third of a decade and still passing until the
margin finally went. Bisected it by reverting the uncommitted files in
halves, which took four runs and settled it; the alternative was reading
seven diffs and guessing. The fixture provisions the hull now, and reports
the span each sector actually got, because a silent truncation that still
passes is worse than a failure.

## 2026-08-05 — building a law for the Verge

Asked for a comprehensive governance system covering everything the survey
found missing. The temptation was a police force, and it would have been the
wrong game: the Charter "fields no armed vessel anywhere" and a sector-wide
constabulary is precisely the single authority the programme's charter exists
to prevent. So the design became **four powers, four legal cultures, and each
only as long as its own arm** — which turned out to be latent in
`data/factions.py` already. The Charter excludes and never shoots. The
Concordat wants property and has hulls. The Freeholds have no court and post
a price. The Dry Choir holds no hearing and stops answering. Same act, four
completely different afternoons; that check is the one I would keep if I could
only keep one.

The idea that made it a game rather than a tax was separating **witnessed**
from **charged**. An act nobody could see offends nobody, so where you work is
a real decision and the frontier is worth having.

Two faults, both found by playing rather than reading, both instructive.

The law re-entered itself: a patrol stop charged two days with
`advance_days`, which runs the clock, which runs the law. It surfaced as a
`RecursionError` raised in `settlement.maturity`, three modules from the
cause — re-entrancy never reports itself where it happens. There is a guard
flag now, and the rule is simply that nothing inside a tick moves the
calendar.

The second was worse and I nearly shipped it. Not answering a summons is
itself an offence — that is what stops the whole layer being escapable by
never going home — but a default charge decided in absence generates a default
charge, and the debt it creates generates arrears, which is also decided in
absence. One contraband bust, left alone for eight years: **61,820 charges
and ₡498 million owed.** Not a balance problem; a save file that will not
load. The fix is the honest one rather than a cap: a power has *one*
complaint about your silence at a time, and what escalates is the instrument,
not the paperwork. The same decade now ends at three charges and ₡45,000. The
lesson is the project's oldest in a new costume — any rule that generates its
own input needs a reason it terminates, written down.

## 2026-08-05 — the reviews' residue, closed in four sub-passes

Asked what the game's major weaknesses were. The honest answer was already
written down — the two review lists in IMPROVEMENTS.md had survived
eighteen passes — so the work was verification and then closure, in value
order: the economy exploits, the endgame arc, the combat arc, and the mute
sector. Three new suites (`solvency`, `prize`, `despatch`), additions to
eight more, and the details in IMPROVEMENTS.md's nineteenth-pass entry.

What the pass taught, beyond what it fixed:

**A probability where a pity timer belongs re-paces the whole game.** The
inert-Bloom fix started as "past the seeding cutoff, throw anyway at 0.35×
chance" — and every *saturated* system became long-range artillery the
moment its neighbourhood filled in, because "no clean ground in range" is
also the late game's normal state. Six long fixtures drowned ~40% faster
and a naive five-year captain starved in a sector 37/42 gone. The stall is
the *sector's* condition, so the answer is the sector's one move: a forced
throw after ~3 stalled years, deterministic, and slow sectors stay slow.

**A new outcome id breaks every tally that enumerates outcomes.** Adding
"struck" collapsed the easy tier's measured win rate to 62% overnight —
weak enemies were surrendering and the harness counted a surrender as a
loss. Grep for the result-id literal before shipping a new one.

**A check that passes on a frozen actor is not passing.** `test_play`'s
five-year solvency floor had held because the bot froze at day 1500 (a
stale `is_stranded` price refused its tow) and a frozen captain cannot die.
Making `is_stranded` honest un-froze it, and one seed's sector genuinely
drowns in year 4.8 — the loss rule working. The check now owns the economy
(nobody starves, nobody in debt) and lets the sector's own ending be the
one thing that stops a run.

**The suite must arrange its own silence.** The two speech checks assumed
no model answers on this machine, and this machine runs Ollama — so they
failed against a healthy game. A claim about behaviour-when-nothing-answers
has to point the probe at a dead port, not hope the developer never
installed anything.

And one small closure with a long history: the fifteen-screen rail finally
has digits that mean their position, W/A/S/D works wherever the flight
clock runs, and every stated count ("Eight things", "Five endings",
"Keys 1–8") is computed from the table it describes.

The first full run then surfaced four stragglers, each its own lesson:

- **A drawing keyed on a datum you retire loses its face silently.**
  `works3d` derived SOL-FORGE's mirror from the `"star"` site kind; fixing
  the site to sunward rock stripped the film and left a refinery clone at
  91% shared outline. The class is the fact now, not the site.
- **A lever must measure its own experiment.** The relation-drift probe
  took the *minimum over every pair* after twelve passive years — and once
  a passive sector can genuinely collapse, that minimum read the
  apocalypse, not the fade, and the direction inverted. It measures the
  pair it shoved now, over a horizon the sector survives, provisioned.
- **A capability check must count the act, not the survivors.** The decade
  chronicle planted eleven colonies and the Bloom ate every one; counting
  `len(game.colonies)` at the end read "never planted". And the driver had
  never cleared a combat fault in its life — an EMP took the seed bay in
  year two and `can_colonise` was False for the rest of the decade, which
  is the same probe-misses-the-move lesson as the bot's pantry, at a yard
  instead of a counter.

## 2026-09-17 → 18 — the whole-project review, fixed, and ten new systems

The review (`../reviews/2026-09-17/`) found 60 things; `STATUS.md` there maps
each to its fix and the suite that pins it, and `changes/` holds each work
stream's merge notes. In order:

- **Phase 0, the core.** A save resumed in a fresh process for the first time
  (`core/save.ensure_registry`), ids per chronicle (`core/ids`), no luck on a
  sub-day step, a crash handler, the screen keys alive, the tripwire on a copy.
  A headless probe overwrote the player's save during this; it was restored
  from the `.bak`, and `save_path()` now sends offscreen processes elsewhere.
- **Phase 1, five parallel streams** (rules, interface, engine, tooling,
  documents): exploits closed, every screen fits 1040×680, a parallel runner
  (17 min → 3), `pyproject.toml`, CI, every file under 500 lines.
- **Waves A and B, ten innovations:** the Far Reaches, the Kith, stellar
  phenomena, nemeses and the hunt, the living hull, freight lines, the
  Assembly, officer arcs, renown and the Voyage, a synthesised soundscape.
  Each has a design in `innovations/` and its merge notes in `changes/`.
- **Phase 3, upkeep:** generated package maps (`tests/maps.py`, the `maps`
  suite), the `exports` suite (a ruff sweep had removed six re-exports that
  callers read), INTERFACE 6,383 → 182 lines, IMPROVEMENTS 1,098 → 133,
  twenty screenshots, the renown chip given room in the menu-bar corner, and
  a column measured by height-for-width so wrapped text is whole on the
  first frame.

- **A final, independent play-test** (the first hour over the bridge, and
  three strategies for two years each) found eleven defects. Nine were
  fixed with checks, among them envoy deals that minted money, a test import
  that deleted the save its caller named, a sale that paid less than its
  button, a lesson that could stick, and three layouts. The open two (where
  one may trade from, and small words) are in `IMPROVEMENTS.md`.

Measured at the end: **235 suites, 1,763 checks, 0 failed, 201 s at `-j 8`**.
A two-year chronicle saved in one process and resumed in another hashes
identically, and still does 60 days on. The careful captain reaches Genesis
on 7 of 10 seeds inside five years with no deaths; a day costs about 1.4 ms
with everything on. Nothing was committed.

## 2026-09-19 — what a contact looks like

Opened by photographing one. A hull was flown into a Fleet Hub at 55 m/s —
**1,134 points off a hull that has 336**, the end of a starting chronicle —
and the only thing that changed on the screen was one line of nine-point
italic type along the bottom of the window. The structure was not even in
the camera the player was looking at: the nose was 180° off, so the whole
event happened in the *aft* feed while the main screen showed a starfield.

Everything needed to draw it already existed and none of it was drawn.
`sim/impulse` has worked out the energy, both sides' damage and both sides'
change of velocity since it was written; `sim/knock` carries the shove out to
the sector; `sim/moorings` knows which fitting was missed and by how far;
`sim/landing` tells a descent from an arrival; `sim/control` knows when a
station is shooting at you. The gap was a door between the fact and the
picture.

| Piece | What it is |
|---|---|
| `sim/shock.py` | The one door: reads a resolved flight (or a turn of an engagement) and hands back a `Shock` — kind, bearing, both sides' damage, severity, the words. No Qt, no writes, every figure the flight's own. |
| `ui/effects.py` | The timeline: how long a thing stays on the glass and how hard. Qt-free, so a check can ask what the shake is 300 ms in without waiting. `watch` reads the flight and spawns on a *change*, the way `soundmap` does. |
| `ui/effect_marks.py` | The hand: flash, blast front, sparks, tumbling debris, fractures on the camera glass, mooring lines coming taut, the rim arc for a blow from outside the frame. Deterministic in a seed — never `game.rng`. |
| `ui/effect_paint.py` | The composition: the first-person overlay, the outside view's, the wash, the words, the alarm border. |
| `ui/effect_clock.py` | A second 40 ms timer, because a collision *stops* the flight clock and the first frame of an explosion is not an explosion. It advances no calendar and draws no luck. |

What a captain now sees, all of it off numbers the sim already had:

- **A crash**: white-out, a shock ring and sparks at the point of contact,
  hull tumbling away, the camera thrown off true, fractures across the glass
  that stay, a rim arc when it happened behind you, and the figures large —
  `COLLISION · FLEET HUB · 55 m/s · 34,245 MJ · −1,134 off her · −68 off it
  · shoved 3.11 m/s · mast 4 missed`.
- **The conn turns to the camera that saw it.** The approach is over, so
  there is no manoeuvre left to spoil (`ui/viewport.best_view`).
- **A berthing**: lines going over and coming taut at the fitting, in green.
  An arrival is not a small collision and is not drawn as one.
- **The other side of it**, in the outside view: the shove as an arrow out of
  the structure, and a dashed line from where the frames went in to the mast
  that was missed.
- **Still-running contacts**: a boom closing, a cut going through, point
  defence biting — drawn without taking the pilot's camera off them.
- **An engagement**: what you *took* this turn shakes the picture and throws
  pieces of your own hull off it. Combat drew every round it fired and
  nothing at all of being hit.
- **Sound**: `impact` and `graze` cues, because a crash had none.

**One fault the full run found, and the suite now holds shut.** Caching the
found set of surfaces between frames — worth 6 ms of a 17 ms frame — left the
timer holding Python wrappers for widgets whose C++ objects had gone, because
every pop-out is `WA_DeleteOnClose`. `update()` on one of those raises inside
a timer slot, where PyQt cannot propagate it: **exit 134, five runs of five,
every check passing and nothing failing** — the exact shape `ui/painting.py`
exists to stop, in the one place that was not a `paintEvent`. `_repaint` now
drops a surface that has gone, and the window stops the clock on its way out.

Measured afterwards: **237 suites, 1,782 checks, 0 failed, 195 s at `-j 8`**.
One animation frame costs 10.7 ms against a 40 ms budget with three pop-outs
open. Nothing was committed.

## 2026-09-20 — the nightly, made green

The push workflow runs the fast suites and had been green for days. The
**nightly runs the lot, and had never once passed** — the same two checks on
3.10, 3.11 and 3.12, on every scheduled run since the workflow was written,
and neither of them was the game being wrong about anything a player does.
Both were "this only ever held on one machine", the class commit `4e8d032`
named.

**The bridge did not fit, and never had.** `test_bridge` asked that no
control be *entirely* below the fold at 1,360×880. On this machine the screen
came to 843 px in a 781 px view and cleared the bar by 19 px of a straddled
row; on a runner, where `fonts-dejavu-core` is the whole font set and
`theme.serif_family` falls through to Qt's generic serif, the same screen is
863 px — so two controls went under and the trigger was cut four pixels
short. Reproduced here by loading matplotlib's DejaVu copies into Qt, which
gives the runner's metrics exactly: 863 px and the same two buttons, named.

Two changes, both of which the screen wanted anyway:

- **The camera gives.** `pilot_panels.fit_feed`, through a new
  `view_base.Pane.fit` hook called before the screen is measured, puts the
  feed at its floor, asks the column what the rest of it needs, and hands the
  camera the difference. The bridge is a column of controls with a picture at
  the top; the controls' heights are their words and the picture's is
  nothing, so a taller font comes out of the picture. On a taller window the
  camera is now *bigger* than the 260 px it used to be pinned at.
- **"Fly at …" moved to the hands' column**, which is where this file's own
  rule always put the flying. It was under "In view" on the readouts' side,
  and the right column was the taller of the two, so those four buttons were
  what pushed the autopilot bar off the bottom.

The check is stricter than the one it replaces — *no control below the fold
at all*, not merely "not entirely hidden" — and it runs twice, once on this
machine's fonts and once on the runner's. 799 px in 781 here, 819 px there,
all 34 controls whole on both.

**A stopped bridge went on listening.** `Bridge.stop` set a flag and closed
the socket while the serving thread sat in `accept`. On Linux the blocked
call holds the kernel's listening socket open, so the port kept completing
handshakes after `stop` had returned; macOS wakes the accept, and the same
code passed here for a month. The listener now comes up for air every 200 ms
to ask whether it is still wanted, and `stop` waits for the thread before it
returns — so when it returns, the port is gone on either kernel. The check
asks that first, in words, before it asks the kernel.

`ui/pilot_view.py` passed five hundred lines on the way and was split at the
seam `ui/conn_moves.py` already cut for the conn window: `ui/pilot_acts.py`
holds what the bridge's own controls do when pressed.

Measured afterwards: **237 suites, 1,782 checks, 0 failed, 199 s at `-j 8`**.

## 2026-09-20 — a gun with hands on it

The game has had guns since the first engagement and never a *gunner*.
`sim/gunnery` picks which mounts speak in a turn and `sim/shooting` resolves
what they did; between the choice and the result there was nothing, because a
turn has no room in it for leading a target. This is that room — a real-time
layer at the other grain, in seconds rather than turns.

**The shape is FreeSpace 2's**, researched rather than remembered, because
that game settled the vocabulary of a space gunnery screen and nothing since
has improved on it: a reticle and a *separate lead pip*, a bracket round
every contact in the colour of whose it is, a target monitor with the
target's **subsystems** listed, a contact ball for the half of the sky you
are not facing, a directive list that ticks itself off while you fire, and a
debrief that says what you did rather than whether you won.

| Piece | What it is |
|---|---|
| `data/turrets.py` | Fourteen seats: traverse, elevation, arc, muzzle velocity, rate, spread, heat, magazine. What a gun is like to *aim*; what it does is still `data/armaments.py`'s. |
| `sim/gunsight.py` | Pure geometry: bearing and elevation in the hull's frame, and the intercept a round has to be led to. A beam is led nothing, and that is one branch rather than a special case at each call. |
| `sim/turret.py` | The mounting: the stick, the director, the trigger, heat, the magazine. |
| `sim/foes.py` | What is out there — hulls, blisters, batteries, rigs, domes, seekers, consorts — with **subsystems that can be shot off one at a time**. |
| `sim/skirmish.py` | The arena: everything in the hull's frame, a clock in tenths, contacts that shoot back, and racks whose missiles become contacts of their own. |
| `data/drills.py`, `sim/drills.py` | Ten training actions and the machinery that runs and judges them. |
| `sim/manning.py` | Taking over a gun on your own hull in a real engagement, and banking what it does back into the battle — once. |
| `ui/turret_*.py`, `ui/gunnery_view.py` | The window: a camera **at the muzzle looking down the bore**, so traversing swings the picture; the glass; the boards; and a Gunnery screen on the rail. |

The ten drills are the situations the Verge can actually put a captain in:
the range, the pass, the screen (point defence), the pack, the quay, the
shore batteries, the workings, the ground works, Boarded, and In the line.
Two of them are about *not* shooting something — the habitat ring on a
mining rig, a consort in a fleet action — because a gunner who cannot hold
fire is not a gunner.

**Subsystems are what make a structure worth attacking rather than merely
shooting.** A hub is four turrets, a mast and a reactor: silence it first,
blind it second, and the rest is arithmetic. `foes.silenced`, `foes.blinded`
and `foes.crippled` are read off the state, so the directive list cannot
drift from what happened.

**Three guards of this project's own caught dead code as it went in**, which
is the whole reason they exist: `declared` found three fields nothing read,
`reachable` two functions nothing called, and `thermal_doors` found the
mounting's temperature going in by the hull's door. The first five were
deleted or wired up; the last is a different quantity — a ceiling that
*jams a gun* against one that clamps a reactor — and the guard now says so.

Measured afterwards: **238 suites, 1,794 checks, 0 failed, 191 s at `-j 8`**.

## 2026-09-20 — a world in eight characters

*Traveller*'s Universal World Profile, researched and laid over the Verge's
own bones. It has been the best idea in science-fiction gaming since 1977 for
one reason: **one short string that a dozen unrelated systems can all read**.

    A209785-C   ·   Va Na Ni

SEEDFALL already knew almost all of it and kept it in eight places —
`world/planets.Body` has the radius, the gravity, the biome and the
temperature, `world/galaxy.Port` has the starport and who holds it,
`sim/piracy` has the lawlessness, the factions have the rest. So the profile
is **derived, never stored**: `sim/profile.profile(game, system, body)` reads
the sector and hands back eight characteristics, the trade classifications
they earn, the bases, and the travel advisory. Nothing new is saved, an old
chronicle grows one with no migration, and it cannot drift from the world it
describes. What the world does not determine, `RNG(f"{seed}:uwp:…")` settles
once — never `game.rng`, which a screen must not move.

It reads on the System screen under the body's own facts, and the checks hold
it to being a *description*: an asteroid is size 0 and atmosphere 0, an ocean
world is hydrographics 7 or better, a world with nobody on it has no
government and no law and earns `Ba`, and a fresh sector shows thirteen
classifications rather than one repeated.

**The prices are deliberately not wired to it yet, and that is the story.**
The obvious next step is Traveller's speculative trade — a world that grows
food sells it cheap, a vacuum world with a million people pays for it — and
it was built, measured and backed out in the same pass. Multiplying the
counter's two quotes by the world's classifications re-balances an economy a
dozen other checks are tuned against: it broke the freight desk's load clamp
(a port quoting 167 t of volatiles it did not hold), and it put the careful
captain's five-year ending out of reach. That is a balance pass with its own
measurement, not a line in a price function. What landed instead is
`uwp.trades` — what a world is *like* to trade with, which is true whatever
it charges. See `IMPROVEMENTS.md`.

Measured afterwards: **239 suites, 1,801 checks, 0 failed, 197 s at `-j 8`**.

## 2026-09-20 — two dice, and a life lived before the berth

The second stage of the Traveller programme, and the two pieces the rest of
it hangs off.

**One grammar** (`sim/checks.py`). Traveller has resolved every task the same
way since 1977 and it fits on one line: `2d6 + skill + characteristic DM +
difficulty DM ≥ 8`. SEEDFALL resolves a dozen acts a dozen ways — a
percentage here, a weighted pick there, a bespoke curve for digging — and
none of them can be compared, taught, or shown to a player as a number they
could improve. Six characteristics, a seven-rung difficulty ladder, −3 for
untrained, and **the Effect**: a check answers *by how much*, which is what
turns a roll into a sentence. `chance` is a count over all thirty-six
outcomes and is the same arithmetic `roll` uses, so a screen can quote the
odds before the button and be honest — *preview equals act*, applied to a
die. It replaces nothing on its own: an act with a tuned curve keeps it.

**A life lived** (`data/careers.py`, `sim/lifepath.py`). Eight careers of the
Verge — the Charter Service, the Concordat Yards, Freehold haulers, the
Orders, prospectors, the Picket, Kessel's Reach, and drifting — each with
what gets you in, what you have to survive, what you learn, what goes wrong,
and what you leave with. An officer's record is **derived, never stored**,
the same rule the world profile follows: a pure function of their id,
station, level, trait and age plus the sector's seed. No field added to a
saved dataclass, no migration, and an officer signed on two years ago has a
history the day this ships.

Measured across eighteen officers: five careers, seventeen skills, fifty-one
events, six mishaps over seventy terms, and skills reaching level 5. Two
things had to be fixed before it read as a person rather than a table:

- **Everybody came out flat.** Picking freely from a career's six skills over
  three terms gave a "Chief Engineer" Admin 0, Engineer 0, Vacc Suit 0 —
  somebody shown each job once. `DEEPEN` makes a term usually deepen
  something they already do, which is why Traveller characters specialise.
- **The same thing happened to people four times.** "Caught a fault nobody
  else had seen", three terms running: the pick had no memory.

It reads on the Ship screen's Crew tab beside each officer's own story —
characteristics with their DMs, skills with levels, the terms, what happened
in each, how it ended, and the worst year's odds when there was one.

`declared` and `reachable` caught four more pieces of dead code on the way
in: two fields the record never read back and two functions of the grammar
nothing walked through. The fields are read now (a term names its service
only when the service *changed*, which is the one thing worth seeing in a
record); the functions were deleted.

Measured afterwards: **240 suites, 1,809 checks, 0 failed, 195 s at `-j 8`**.

## 2026-09-20 — people with lives, and somewhere to spend money

Third stage of the Traveller programme, and the one that turns a crew list
into a list of people.

**Everybody aboard is now somebody** (`data/backgrounds.py`,
`sim/person.py`). Twelve homeworlds — read in the same trade classifications
`data/uwp.py` earns worlds, so a crew list and a world profile share one
vocabulary — ten upbringings, twelve ambitions, sixteen kinds of
relationship, and the berths they held before yours with why each one ended.
Ties are dealt *out of the career that made them*: a picket leaves rivals and
old shipmates, a drifter leaves creditors and people who are looking for
them, and anybody thrown out of a service left somebody behind who remembers
it. All of it derived, like the service record and the world profile, so
nothing is saved and an officer signed on two years ago has a family today.

**A hundred and one things to own** (`data/kit.py`), in twelve categories:
weapons, armour, suits, tools, medical, computing, survey, travel, luxuries,
keepsakes, papers and the illicit. Every one carries a tech level and a law
level, and **both hook into the world profile that already existed** — what
is on the shelf is where you are standing, and what the customs desk will
take off you is the same list read the other way. A gauss rifle is ordinary
at law 2 and contraband at law 9, from one table.

**Somewhere to spend it** (`data/venues.py`, `sim/shore.py`, the Port
screen's new Concourse tab). Twenty-two venues — chandlers from a shed to a
four-floor emporium, a back-room dealer who carries what the shelf will not,
banking from a hole in a wall to the Chartered Bank, six eating houses and
nine entertainments — every one gated on the starport class and the
population, so **where you put in decides what there is to do**. Measured on
a fresh sector: Fleet Hub carries 22 venues and 90 lines of chandlery, a
frontier Station carries 10 and 32.

A night ashore costs credits and buys morale, loyalty, standing and
sometimes a rumour that points at a world that really is what it says. The
bank **mints nothing** — it holds money and moves it, which is the only shape
of bank this game can have; the chandler keeps the market's spread, measured
over twenty round trips at no gain.

Three of this project's guards bit again, and all three were right:
`declared` found three table fields nothing read (a background's favoured
characteristic now costs a point of it, and an ambition says what serves it);
`uirules` caught the concourse drawing the chronicle's luck from a *screen* —
a night ashore is an act and the act draws now; and the shore's own check
found a chandler answering with a full catalogue in a system that has no
port, because a profile is a fact about a world and a shop is a fact about a
port.

Measured afterwards: **241 suites, 1,817 checks, 0 failed, 203 s at `-j 8`**.

## 2026-09-20 — a crew you can read

A crew was spread over four screens and none of them was about the crew. Who
was aboard was a grid of story cards on a tab of the Ship screen; hiring was
at a port; the long sleep was under the hold; the wage bill was a line on a
ledger; and the twenty years somebody lived before the berth had been
derivable since the morning and were printed nowhere. There was no answer at
all to the question a captain actually has — *what can these people do
between them* — short of opening six officers one at a time.

**The Crew screen** (`k` on the rail), four tabs, one question each.
*Roster*: the complement, the mood, the bill, and the watch bill with its
holes showing — a station nobody holds is printed as nobody, in red, with
what it costs beside it. Five orderings, because a crew list is read to
answer a question and the question picks the order. *Sheet*: one person,
whole — characteristics with their throws, every skill with what it is for,
the service record, where they are from, who raised them, what they are
after, the ships before yours, the people attached to them and what they own,
with a name bar so the next person is one click away. *Watches*: the bill
over a day, a month and a quarter, the bonus and shore leave, the mess deck,
the long sleep, the ship's own abilities, who the crew knows out there, and
what the watch is carrying that this world forbids. *The book*: who has left
the bridge, and the stories told to the end.

`sim/roster.py` answers all of it and writes nothing. The screen quotes a
bonus and the sim charges that number; the price and the charge are the same
call.

Two defects fell out of building it, both of them older than it:

- **A service record changed depending on which tab you opened first.**
  `lifespan.age_of` invents an age on the first ask *and stores it* — a
  migration for saves written before lineages existed — and
  `lifepath._terms_wanted` read the field. So a record derived before
  anything showed somebody's years had a different career, a different number
  of terms and different skills from the one derived after. Three of three
  officers changed on the second read. `lifepath.of` resolves the age through
  `age_of` now, so the first derivation pins it and every later one agrees.
- **A Chief Engineer who had never touched a drive.** A career is only
  *weighted* towards a station, so the dice could leave the ship's engineer
  with Vacc Suit 2, Admin 1 and nothing about an engine, under a crew list
  that said Chief Engineer. `careers.STATION_SKILLS` brings the station's own
  skill up to what the level claims and the one beside it to trained, and
  never takes anything away.

The Ship screen's Crew tab is the stories again, which is what it was for;
the service record it briefly grew is two lines now and a door to the sheet.

Measured afterwards: **242 suites, 1,823 checks, 0 failed, 197 s at `-j 8`.**

## 2026-09-21 — a concourse anywhere people are

Two passes on the one gap: **the game had an economy for hulls and none for
people.** A captain with forty thousand credits could buy a fuel bunker and a
hull refit, and the whole of what a *person* could be sold was a chandler, a
bank, somewhere to eat and somewhere to drink — all of it gated on
`system.port`, so an ARCA Habitat with a million people living in it offered
nothing at all, and neither did a holding of your own or any settlement a
power had put on the ground.

**`sim/places.py` is the missing noun.** A place is anywhere in a system with
people in it that a hull can be alongside — a quay, a habitat drum, a
holding, a works on the ground. Every one answers the same four questions,
because everything built on top only ever asks those four: *how many people,
how good is it, how advanced is it, how hard is the law.* Derived from what
the chronicle already holds, so an old save has a concourse in its habitats
on load.

Ninety-four doors over fifteen kinds, thirty pieces of bodywork over eight,
fourteen careers, forty-four skills, two new hulls and two new habitat
classes:

- **The concourse** (`data/venue_types.py` and three themed tables):
  chandlers, markets, tech and data, banking, offices and hiring halls,
  notaries and advocates, transport, lodging, eating houses, clinics, sport
  and training, the arts, entertainments, the houses, and the other
  concourse. The vice tier is gated **downwards**, on a *low* law level — a
  chop shop, a fence and a black clinic appear on the frontier rocks and
  vanish where the Charter actually runs.
- **The body** (`data/treatments.py`, `sim/clinic.py`): care, surgery,
  grafts, anagathics, cold berths, fitted hardware, the germ line, and
  instruction. Priced and gated exactly like `data/kit.py`. The good numbers
  charge **strain** — loyalty off the person, permanently.
- **What is bought is kept.** `game.fitted` and `game.taught`, keyed by the
  officer's id *as a string* because a save is JSON. `lifepath.of` folds both
  onto the record it derives, so a muscle weave reaches the gunnery check and
  the abilities table without either knowing the clinic exists.
- **Six civil careers** (`data/careers_civil.py`) — clinician, factor,
  entertainer, constable, magistrate, syndicate — because a sector with
  hospitals, courts and brokerages in it has people who worked in them, and
  they end up on bridges. Four new skills with doors that want them.
- **Who runs this** (`sim/authority.py`): the governance layer has been deep
  for a long time and was reachable only from the Law screen, which is about
  *your* charges rather than where you are standing. One call, one place,
  and the answer to the only question that matters at a gangway.
- **LAZARET and ARGOSY**, and the STACK Arcology and BASTION Post.

Three defects found on the way, and one refusal that was right:

- `WrapRow` is one row that goes across or down, **not a grid**. Eight doors
  side by side squeezed every one to nothing and the panel rendered blank.
  Four panels were using it that way, including the old concourse tab.
- A name bar read "Okonkwo · Adeyemi · Okonkwo": two officers shared a
  surname and both tabs looked like the same person.
- The harbourmaster panel printed a dataclass repr —
  `Temper(id='frightened', …, bend=1.5)` — straight onto the screen.
- **`tests/test_works3d` refused three habitat classes.** A resort, a
  hospital and a library all came out of the derived-silhouette renderer as
  the same ring with different small fittings, at 75–86% overlap against a
  72% bar. Two survived with parts of their own (`tower`, `wards`,
  `bunker`); the other three are venues instead, which is where a resort and
  a hospital belong — doors, open everywhere there are enough people.

Measured afterwards: **243 suites, 1,832 checks, 0 failed, 230 s at `-j 8`.**

## 2026-09-21 — the four left over, and a face for everybody

**The leftovers, closed.**

- **A hull is a place.** `sim/places.py` knew four kinds and none of them was
  a ship, so a LAZARET was a hospital with a drive that could not offer
  anybody a check-up. Ten doors aboard (`data/venues_aboard.py`), gated on
  the tier printed on the hull's card: a slop chest and a mess on anything
  with twelve hands, a surgery and a vat deck on a hospital hull, and the
  ship's own tech level rising with the research tree — which is what puts
  the vat deck on the list. A door is `aboard` or ashore and never both.
- **Anagathics are an arrangement.** A course takes years off on the day and
  the clinic bills five per cent of its price every month after it, followed
  by `core/shiptime`. While it is paid, `lifespan.tick` ages them at 45% of
  their lineage's rate — asked of `sim/clinic` rather than modelled twice,
  because that tick is the only thing in the game that moves an age. Miss a
  month and it stops, and the years start again.
- **Hiring halls hire.** Four kinds of door carried the `hire` tag and every
  one of them was a name on a list. `crew.pool_here` draws a board for a
  *place*, seeded on the place and the month like the quay's, so a habitat
  of a million people can offer you a navigator.
- **The silhouette vocabulary** is the one left open, and is recorded as such.

**And the thing the game had never drawn: people.**

The crew was rows of text under a name. Everything about somebody has been
derivable for two passes — what they did for twenty years, where they are
from, how old they are, what they think of you, what has been fitted into
them — and none of it had a picture.

- **`ui/portrait.py` and `ui/portrait_paint.py`** — a face for everybody,
  read from the same officer id the rest of it is read from. The lineage is
  the colour, the years are in the hair and the jaw, the service is the
  collar, the homeworld is what is behind them, the mood is the mouth, and
  **what a clinic has fitted is visible**: a lit optic, temple ports, plate
  under the cheek, a seam somebody did in an afternoon. Strain is a number on
  one screen and an argument on another; here it is a person you can see is
  partly a machine, which is the whole of what the Verge minds about.
- **`ui/body_plan.py`** — a standing figure with a mark at every site
  something has been put into, labelled out to the gutters. The sites come
  off `data/treatments.py`, and a check holds that everything fitted *into*
  somebody has somewhere to be.
- **`ui/place_scene.py`** — the concourse, drawn: the structure (a quay with
  booms, a drum, a stepped arcology, a bunker with guns, your own hull), the
  windows counted off the population digit, every open door in a frontage
  tinted by kind, and the crowd walking on the deck.

Four defects found in the drawing, all of them the same class — a widget
claiming more than it needs:

- The rim light was drawn over the hair, so everybody wore a bright skullcap.
- The body plate was scaled off the *width*, so a person in a 520×320 panel
  came out as wide as they were tall.
- `QSizePolicy.MinimumExpanding` takes `sizeHint` as the **floor**, so a
  160-tall banner with an 800 px hint made the Concourse 844 px of an 837 px
  column. `Preferred` lets `minimumSizeHint` govern and still takes every
  pixel offered.
- A `note()` does not fold, so the scene's caption made its own sentence the
  screen's minimum width.

And one behaviour: a ship is always `here`, so it won every tie and the
Concourse opened on the slop chest while you were docked at a Fleet Hub.

Measured afterwards: **244 suites, 1,836 checks, 0 failed, 233 s at `-j 8`.**

## 2026-09-21 — what a crew is made of

The Verge had five substrates and all five of them were **people**. There are
walking machines in `sim/robots.py` that nobody could put on a bridge, a
faction whose entire creed is *substrate is an implementation detail*, and
clinics that will grow a person to order — and a crew list could hold none of
it, because a crew list held one kind of thing.

**Eight substrates now** (`data/lineages.py`): the wet, the grafted, the Dry
Choir's recordings, xenoforms and Kith as before, and three new — a **frame**
(a walking machine with a hull number, which wears out rather than ages), an
**instanced mind** (running in the hull's compute, wearing whatever body the
watch needs), and the **vatborn** (grown to a specification somebody paid
for, cheap to hire and short of run).

**A creed is an attitude, and nobody had ever read one.** The four powers
have said what they think since the first commit — *One biology, many
bodies*, *Built, not bred*, *Whatever flies, flies for us*, *Substrate is an
implementation detail* — and none of it reached a hiring board or a customs
gate. `data/kindred.py` reads them: six categories anybody at a gate sorts
people into, four bands from welcome to refused, and three things that
tighten it in order — whose ground it is, what sort of government, and the
law level.

Two rules fell out of measuring it, and both are in the code with their
numbers:

- **A government tightens; only the law shuts a gate.** Without that, an
  ordinary Charter bureaucracy turned *watched* into *refused* and a Fleet
  Hub refused six substrates of eight outright.
- **The law shuts a gate the power already disfavours, and no other.**
  Without *that*, a law-10 doctrinal world refused everybody — the Dry
  Choir's own capital would not admit a Dry Choir recording.

**The hull decides who turns up.** A berth is somewhere to live: a fabricated
hull draws frames and minds to its board, a grown one draws the wet and the
vat-grown, a xeno hull draws xenoforms. And a board never holds somebody the
port would refuse at the gate — a port that will admit nobody simply has no
board, rather than a row of buttons that cannot be pressed.

**Somebody aboard may mind.** A new conviction, *one biology, and means it*,
and a friction that is nothing at all without both a purist and a mixed
bridge — and real money in goodwill when both are true. Plus the injury that
is actually an injury: being the one kept aboard while the rest of the watch
walks down the gangway.

And **a frame is drawn as a frame**: the portraits carry the category, so the
three built substrates get a visor, a vent and panel seams instead of eyes,
hair and a mouth. A crew list that drew a machine as a person with grey skin
was telling the lie this whole pass exists to stop telling.

Four defects, all of them measured rather than guessed:

- The ashore penalty charged for *papers* as well as refusals, and a
  well-run year took an officer from 62 to 46. It broke two checks that had
  been green for months. Only a refusal costs anything now, and only while
  the hull is actually alongside — a crossing is not somewhere anybody is
  being refused entry.
- The friction was scaled a hundredth too small: under a tenth of
  `loyalty.DRIFT_PER_DAY` the drift simply swallowed it and a month of it
  read as a *rise*.
- A board at a gate that admits nobody fell back to offering a wet
  candidate the same gate refused.
- `game._kindred_said` is an undeclared attribute, and `core/save.STRICT`
  took the save down. It lives in `game.flags` now.

Measured afterwards: **245 suites, 1,844 checks, 0 failed, 258 s at `-j 8`.**

## 2026-09-21 — two clocks

A person had one number for age and it did two jobs. `officer.age` runs at
the lineage's rate and is slowed by a cold berth and by anagathics, so it
was wear on the body, not years since birth. Now there are two clocks
(`sim/lifespan.py`, `data/stages.py`):

- **Aged** (`age_of`): what the years did to this substrate. It decides what
  somebody can still do.
- **Lived** (`lived_of`, from a new `Officer.born`): years since birth, which
  nothing slows. Old saves derive `born` once, from the age at the lineage's
  own rate.

Six **stages** measured against the lineage's own prime replace the old four
words: green, coming up, prime, seasoned, declining, past their span. Each
stage is worth something:

- characteristic deltas, folded onto the derived record in
  `lifepath._staged`;
- a learning rate, applied in `crew.grant_xp`;
- a wear rate, applied in `lifespan.tick`.

The **gap** between the two clocks is a fact in its own right: long-lived,
out of step, from another age. The Crew sheet shows the stage and years
lived.

The work arrived uncommitted with three checks red, all loose wiring:
`gap_of` was never called, `Stage.learns` was never read, and the data map
did not list `stages.py`. Finished and measured: **245 suites, 0 failed.**

## 2026-09-21 — afoot: the Verge at walking pace

Everything in SEEDFALL happened at the scale of a hull. The game knew a great
deal about people and places — six characteristics and a service record for
every officer, a concourse of ninety-four kinds of door, a hundred and thirty
pieces of kit with law levels — and never let anybody stand anywhere. Afoot
is a *Star Frontiers* / *Traveller* style turn-based layer on deck plans of
the places the game already has (design: `reviews/2026-09-21/afoot.md`).

- **Sites** (`sim/afoot_sites.py`): your own hull, every place alongside
  (quay, habitat, holding, settlement, a Kith gathering), a derelict seeded
  per system (six kinds of end, `data/afoot_derelicts.py`), and a struck
  prize from the battle's dialog ("Board her first").
- **Plans are derived** (`afoot_plans`, `afoot_gen`, `afoot_furnish`): a
  hull's rooms are its fittings and complement, a quay's are its open doors.
  A spine with rooms both sides, lifts between decks, furniture that never
  blocks a doorway; the same quay is the same quay every visit. A walk in
  progress is saved whole (`game.afoot`).
- **People are the people** (`afoot_people`): officers are `lifepath.of`
  with `person.of`'s kit; the captain gets a derived record for the first
  time; machines walk by class. Stamina is STR+DEX+END.
- **One grammar** (`afoot_fight`, `afoot_acts`, `afoot_talk`): every roll is
  `sim/checks`, every button shows the odds of the terms it rolls. Kit ids
  carry Traveller's weapon and armour numbers (`data/afoot_arms.py`).
- **Everybody else** (`afoot_cast`, `afoot_ai`, `data/afoot_folk.py`):
  keepers behind counters, constables by the law level, fences where it is
  low, your officers at their stations, whoever a wreck's end left aboard.
  Noticing, hunting by lift, losing track, nerve, surrender, watch fire.
- **Talk hands over to the existing doors**: `shore` for the shelf and a
  night, `crew.hire`, the harbourmaster's desk, the Kith, the Concourse's
  clinic; bribes and debts only ever take money out.
- **Incidents** (`afoot_incidents`): the stop-and-search, somebody from an
  officer's past by name, a bounty hunter, a stowaway, a fault aboard.
- **Endings bank through the doors that account for each** (`afoot_ends`):
  kit, cargo, evidence, study; crimes become charges (`dockets.allege`, two
  new offences, assault and theft); a nest burned out is fighting the Bloom;
  wounds are kept (`game.wounds`, mended daily in `core/shiptime`); a death
  is in the crew's book. `sim/prize`'s three doors now work on a hull as
  well as a battle, so a prize decided on her own deck costs what it costs
  from the bridge.
- **The screen** (`ui/afoot_*`, `o` on the rail; *Walk the decks* on the
  Ship screen, *Walk it* on the Concourse): the deck painted in the
  programme's palette with fog, reach and path previews; the column of the
  party, their acts with odds, who is in sight, conversations and counters.
  Sound through existing cues; bridge verbs in `bridge/afoot.py`.

Defects found while building it, all measured:

- a party leaving a Dry Choir probe could never gather at the hatch — four
  people in a one-square crawlway are a line of four (`LEAVE_REACH` 4);
- a raider behind a locked cabin door stayed aware for ever: people who live
  aboard carry keys, lose track after `LOST_AFTER` rounds, and only enemies
  on the party's own decks keep a walk in action;
- two of the party could end a move on one square;
- the stop's constable never arrived, pathing onto the square somebody stood
  on (`near=True`);
- the armour check was averaging misses in, and measured the wrong thing;
- boarding was a massacre in both directions until only a hit of twice a
  person's endurance kills outright, NPC armour was tuned, and a boarding
  party draws the ship's shotgun and jacket.



## 2026-09-21 — afoot, drawn to shape; yards, hotels, wheels and dens

Asked whether the deck plans correspond to what they are plans of: they did
not — every plan was the same spine of boxes. Now every one is drawn in its
own shape from a program of what it has to hold (design, and what was found:
`../reviews/2026-09-21/afoot.md`, "The rewrite").

- **Regions, not walls** (`sim/afoot_blocks.py`): a blueprint paints what
  each square is for; walls, doors, links and reachability follow the same
  way for every shape, reach measured from a deck's own locks and lifts.
- **Hulls** (`afoot_program`, `afoot_hullplan`, `afoot_latticeplan`): a
  working program read off the card and the fit — bridge forward, drives
  aft, fittings at their own mounts, berths for the complement, galley,
  heads, sickbay, air, water, tanks, stores, lifeboats, suit lockers, holds,
  the role's rooms — laid inside the hull's own silhouette; nothing dropped,
  decks added and then the hull drawn longer until it fits; all 39 classes.
- **Places** (`afoot_placeprog`, `afoot_loops`, `afoot_stationplan`,
  `afoot_worksplan`, `afoot_groundplan`): a quay's can, arm and mast; a Fleet
  Hub's spine, four berths and two rings; drum, tower, dome, ring, dug-in
  works and keel stations read off `works3d`'s traits; settlements and bases
  open to a breathable sky or sealed in tubes against an airless one.
- **Establishments** (`data/establishments.py`, `data/venues_establishments.py`,
  `sim/establishments.py`): fifteen kinds, seeded per system without luck,
  with signature doors, their own law and tech, a berth on the chart for a
  station, a yard that builds and refits, and a plan each. Three new wrecks:
  a quarantined hospital ship, a gutted yard, a ring gone quiet.
- **Lifts had never linked** — a −1 read as "linked" by the pairing and by
  every check that looked. Fixed, and the decks are now ridden in the check.
- **The play-test's rules held** (`tests/test_afoot_fair.py`): the fallen
  brought home, stun not a wound, nothing rolled twice, a bribe buys one
  witness, no looting your own, a stop with teeth, what happened this season
  stays happened, a party that rides a lift together.
- Four screenshots: a Fleet Hub's ring, a raider's hulk, a NAVIS's upper
  deck, a gaming wheel's rim (`assets/seedfall/21`–`24`).

Then, from play: the Concourse said the Fleet Hub held a million people and
listed eighty doors, and the hub walked afoot had twenty-eight of them and
four homes. The million was the *world's* population printed as the
station's; a quay now counts its own (`places.QUAY_HEADS`, a Fleet Hub
36,000) and shows what it serves beside it (`places.population`, one door
for every screen). And Afoot draws a room for **every** listed door
(`afoot_placeprog.concourse`), so a Fleet Hub's rings take levels
(`afoot_stationplan.levels`), a crowded dome digs galleries, a full keel
station takes a second deck, and residential blocks follow the place's own
headcount. `afootshapes` now walks every door of every place in a sector.
The hub's rings are drawn at radius 22 (`HUB_RING_R`), narrow enough for
the screen to letter their rooms, and the README's four Afoot shots were
retaken on them.

251 suites, 1,891 checks: one failure on the full run (no tripwire entry for
the new `afoot_ways`), fixed, and it and the twelve nearest suites re-run
green. `ruff check seedfall` clean. After the Concourse fix: 251 suites,
1,893 checks, all green.


## 2026-09-22 — afoot's open list closed, and everything weighs something

Asked to fix the open Afoot items in `IMPROVEMENTS.md`, and mid-way how
anybody moves on a deck in free fall. The user chose the unrolled strip:
every deck has a weight from what it is (`Deck.g`), and a ring's levels are
strips whose ends are the same corridor (`sim/afoot_ringplan.py`), spun to
0.8 g and stacked outermost-heaviest. Weightless, the untrained go hand over
hand, shoot unbraced and drift on a gun's kick; boots and Zero-G fix it.

- **Fire** (`sim/afoot_fire.py`): bursts, suppression, frag/stun/smoke.
- **Trouble** (`sim/afoot_trouble.py`, `sim/afoot_holdings.py`): a quarrel
  between clashing convictions, a shakedown, a brawl; your own works failing,
  striking or sabotaged, and the holding's yield moved by what was done.
- **The Kith and the vault** (`sim/afoot_kith.py`): a phrase answered, a
  song of passage; a relic in three stages.
- **The career**: counsel's two suggestions, the Academy's chapter, five
  renown rungs, the captain's lifepath; stakes in the houses, traffic bound
  for them, gossip naming them.
- **Found on the way**: a refused shot or throw spent luck (dice now drawn
  after validation); five fire buttons in a row pushed the side column off
  the window; the "reaches" gap was by design.
- New suites `afootweight`, `afootcareer`, `afootfire`; checks added to
  `establishments` and `afootui`. The four Afoot screenshots retaken on the
  strips.
- **From play: a ring had ends.** Walking round a Fleet Hub ring stopped at
  the strip's edges both ways — a step off an end was refused, and the
  camera stopped there. Every question on a ring is now asked the short way
  round (`afoot_map.apart`/`span`/`unroll`), and the canvas turns the strip
  under the party (`AfootCanvas.roll`); helpers split to `ui/afoot_marks.py`.
  A whole circuit each way is in `afootweight`, the arrow and the click
  across the seam in `afootui`; shots 21–24 retaken.

After the ring fix: 254 suites, 1,911 checks, all green; `ruff` clean.

## 2026-09-22 — made fast, or across; item 12 closed

Asked to close item 12 (a base's berth; yards that build only their own),
and mid-way, from play: the chronicle opens with the hull hundreds of
kilometres off the Fleet Hub on the flight deck while its doors are open.

- **Made fast, or across** (`sim/crossing.py`): `Game.berth` (the hull at
  a berth, 0.6 km off; a new chronicle starts made fast at its home quay;
  the harbour's pilot or a conn that ends alongside; moving casts off) and
  `Game.ashore` — by the ship's boat (crew six or more; a boat bay aboard),
  their shuttle (a fare), or suits on a line (2 km, something in orbit).
  The Concourse's money-taking doors and every walk ask it; the Concourse,
  the Afoot start page, the helm's anchorage panel and the hail offer it;
  bridge verbs `crossing` and `cross`.
- **Item 12**: a base's pad (`field` berths, a mesh of their own); the
  breakers' yard, a sixteenth kind, only where a wreck is adrift, waking a
  derelict REVENANT; a nursery refits what it grows; traffic bound for a
  house holds that house's berths only.
- Found and left open: the flight computer cannot come alongside a free
  port's arm (IMPROVEMENTS 17).
- New suite `crossing`; checks in `establishments` and `afootui`.

255 suites, 1,920 checks, all green; `ruff` clean.

## 2026-09-22 — round the station to the Grand's arm (item 17)

The flight computer's corridor leg ran straight at a hold point beside the
berth; a free port's one sideways arm put that line through the station, so
a Grand could not be flown to from its far side. `moorings_steer.around`
goes round at the hold point's distance, clear of the core by
`bays.CLEARANCE` (one constant now for bays and berths). Twelve bearings: a
Grand 8 → 12, a breakers' yard 9 → 12, a slip 10 → 11; thirteen sectors'
berths, five collisions → none. The duplicate chord arithmetic went to
`bays.chord_km`. Left open as item 18: a slip's cradle led a quarter turn
at a crawl, and a hull nursery the computer has never been able to reach.
New check in `moorings`.

## 2026-09-22 — every berth, every bearing: docking made to work

Asked to try and fix *all* the docking variations and to lean on tugs and
boats where they help. So the whole matrix was measured: 25 shapes of berth
(quay, hub, holding, a base's pad, and the 21 classes a holding is built
as) × twelve bearings plus above and below × six hulls from a 26 m SPORE to
a 990 m LEVIATHAN × boats and no boats × arriving stopped, drifting and
hot. **12,600 approaches: 957 failures → 19**, mean mass 1.57 t → 1.16 t,
and of the realistic arrivals (stopped or drifting) 7,000 of 7,019 berth.

- `autopilot.safe_rate` brakes to what can be *struck* in a bay, and noses
  in at the berthing rate once inside the stop distance rather than reading
  the room to an aim across the structure.
- `moorings_steer.around` takes the smallest turn that clears the core,
  floored near the skin and fading with range — no more quarter-turn step
  for the computer to chatter on and a hand pilot to chase.
- `moorings_steer.lead` is an intercept, fed back twice, so a hull that
  cannot keep up waits for the berth instead of chasing it.
- The boats: `tug.has_tug` belongs to the structure (a drum with a town in
  it keeps a tender in a portless system; a gate never does), they cast off
  at a bay's mouth, they let go of a hull under power, and a hull that
  simply stops is walked alongside in seven minutes for no mass at all.
- `moorings.takes`: a berth refuses a hull too long for it — a 990 m
  LEVIATHAN at a 720 m quay — and her people cross by boat (`sim/crossing`).
- New suite `berths` (250 approaches, every shape, both hulls, every
  bearing). What is left is IMPROVEMENTS 19: nineteen approaches at awkward
  angles onto small structures.

Full run: 255 suites, 1,921 checks, one failure —
`shock`'s volley check read 1.03 px of shake under `-j 8`, green on three
runs alone (8.0–11.8 px); a timing flake unrelated to this, logged in
IMPROVEMENTS' defects list.

254 suites, 1,910 checks: one failure on the full run — `pilotscreen` took
the first anchorage in view for the Hub, and it is now a spacers' rest
whose one berth a trader bound for it holds, so the hand-over was rightly
refused. The check names the quay now, and re-runs green. `ruff check
seedfall` clean.

## 2026-09-22 — single-seat craft: the cradle and the cockpit

Asked for fighters that launch off a carrier, fly from their own screen, and
scout and ferry as well. Landed whole:

- `data/craft.py` — four classes (WASP, SHRIKE, MOTE, DORY), each a few
  authored numbers: hull, armour, guns, thrust, thruster authority, slew,
  array, tank, seats, and the Pilot certificate it is flown on.
- `sim/craft.py` — the craft aboard (`Game.craft`), the cradle, the ticket
  (`pilots`, the party convention), launch and recovery, the beat, a firing
  run, an hour's scouting, and losing one. **A sortie is a `sim/conn`
  flight** with the craft's numbers in it, so every instrument, computer
  mode and berthing rule already written flies it.
- `ui/craft_window.py` — the cockpit: fore camera, instruments (hull, tank,
  speed, range home), the stick, the drive, the computer's free-flight
  modes, target list, a firing run, an hour's looking, and the cradle.
  `ui/craft_panel.py` — the Ship screen's Cradle tab, which launches.
- The hull's deck plan grows a **cradle deck** with the craft's name on it
  (`afoot_program`), so a pilot walks out to her; and the craft on the
  cradle **is** the ship's boat for a crossing (`sim/crossing.has_boat`).
- A navigator now holds a pilot's ticket (`careers.STATION_SKILLS`, which
  may name more than two skills), so every chronicle has somebody besides
  the captain who may take a craft out.

New suite `craft` (6 checks) and a cockpit check in `ui`. What is left —
craft in a battle, a yard that builds them, the seats and the hold spent on
a real lift — is IMPROVEMENTS' new "small craft" section.

## A craft in the battle, 2026-09-22

The first of that list. `sim/craft_battle.py`: *Launch the craft* is an order
on the battle screen, she comes off the cradle in the middle of an engagement
and makes a run a turn beside the consorts (`combat._run_company`), and *call
her in* is the other half. A run is her guns' dice plus the pilot's Pilot
rating, armour-soaked with the same 15% floor a shell gets and landed through
`sim/damage`; the answer is close-in fire, two dice and two more a mount, and
a dazzled hull shoots at where she was. Shot down, she is gone and the pilot
comes home with a wound. Measured over sixteen fights: 48% off a patrol
against 6% without her and never lost in eight; 35% against 3% off a warship
and lost six in eight.

Underneath it, a real one: **the engagement lived on the window**, so
`craft.can_launch`'s mid-battle refusal had never fired and `ui/gunnery_view`
read a `game.battle` that did not exist. `Game.battle` is a declared
transient field now (the save layer's "undeclared attributes would be lost"
guard caught the shortcut) and `MainWindow.battle` is a property onto it.
`core/state.py` hit 500 lines doing it, so opening a chronicle came out into
`core/state_begin.py`, the seam `core/loading.py` came off. New suite
`craftbattle` (6 checks), a second check in `craftui`.

## The hangar deck, 2026-09-22

The second of the small-craft list, and the one that had bitten: nothing put
a point of hull back into a craft. `sim/hangar.py` and the Shipyard screen's
new **Cradles** tab (`ui/craft_yard.py`, split out because `yard_view` is at
the edge of the limit, the way the machine shop was). A cradle is fitted
rather than assumed — `Ship.cradles`, capped by what a hull that size can
work — and a craft is laid down where its family's hulls are, through
`shipyard.can_build_here` rather than a second copy of it. A yard mends by
the point; a grown craft knits herself whole in her cradle off the hold, for
nothing, which is the reason to buy grown. Selling reads `data/craft.SALVAGE`
at last, scaled by condition, and is a loss at every class and every
condition. New suite `hangar` (5 checks) and a third check in `craftui`.

## The seats and the hold, 2026-09-22

The third of the small-craft list. A boat now takes only as many as she
seats (`seats - 1` besides the pilot), and — the one that had been quietly
false since the afoot layer landed — **a walk's haul comes home by the way
the party went**: `Walk.way` remembers the crossing and `crossing.lift_t`
says what it carries, so twelve tonnes no longer ride home on three
people's backs. Made fast: everything. A boat: three trips of her hold. A
shuttle: two tonnes. Suits: 0.2 t a head, and the rest is left where it lay.
Two checks in `crossing`.

## The seat somebody left, and theirs, 2026-09-22

The last of the small-craft list. An officer out in a craft is off their
station — `craft.at_stations` is the door, `recompute` reads it, and the
navigator away costs the hull its speed and its jump. A captain in a cockpit
cannot con the ship, so a launch left to itself sends an officer. And a hull
with the hands for a cradle deck launches up to three of its own at you,
every turn, wherever the range track stands; close-in fire is what answers.
Two checks in `craftbattle`, a readout panel on the battle screen. The
small-craft list is closed.

## Where you may deal from, 2026-09-22

The play-test's biggest open item. `sim/quayside.py` is the one rule for
every counter: alongside is free and unlimited, and from anywhere else in
the system the goods are lightered at a rate that rises with the distance
(692 credits on 100 t from orbit, 6,300 from seven AU), with your own boat's
lift free inside her own range. Survey data needs somebody at the counter,
which was the play-test's own example. The board, the contract card and the
till all quote it; the Port screen says where you are dealing from and its
harbourmaster button actually docks; counsel offers *Come alongside*.

Two things fell out of it. The reference captain had to learn to fly to the
quay and be brought in — it does now, and reaches its ending on day 1,415
paying 250 credits of lighterage in five years. And `tests/quay.py` is the
new door for putting a chronicle at a quay in a check: writing
`game.location_id` alone leaves the hull adrift in the system, which used to
be invisible and is now a billion kilometres of lighterage.

Two files hit the ceiling in the doing and were split at their own seams:
`sim/contract_price.py` (what a posting costs to source and what the card
quotes, out of `sim/contracts.py`) and `tests/shock_kit.py` (the frozen
clock and the deck the shock checks share). And the `shock` suite's volley
flake is fixed — it measured one instant of a decaying wobble whose phase
comes from the shock's own seed, so it now takes the peak across the first
fifth of a second, and grabs the picture on that same beat.

## Down to the ground, stage one: the lander, 2026-09-22

A player asked for landers, surface vehicles, camps and 2D planet maps.
`IMPROVEMENTS.md` has the programme in six pieces; this is the first.
`sim/landing.py` had already proved a starship cannot land on a world and
named the lander as the reason expeditions work — and nobody owned one.
Now a craft class says whether it `lands`, for how many `days` it keeps a
party alive, how many vehicle `bays` it has and how far its mast reaches;
three landers join the four craft (ISOPOD, PINNACE, CATAPHRACT); where a
craft may set down is her thrust against the world's pull with a reserve
for lifting off loaded; and the starting hull sails with two cradles full.
`fieldwork.launch_expedition` used to conjure a lander out of prose and now
needs a real one that can leave this world again, taking the party from her
seats and the supplies from her hold. New suite `descent` (5 checks).

## Down to the ground, stage two: the vehicles, 2026-09-22

`Expedition.rover` became a machine. Five classes (`data/vehicles.py`), each
with ground it is made for and ground it refuses, a mass that competes with
the supplies for the lander's hold, an opinion about air, and a build that
decides what a hazard costs it. Bought, mended and sold at the yard's new
garage beside the cradles; worn and kept between landings; left where it
stopped if the party walks out. A party with nothing still walks. The
`drive` skill, in `data/careers` since the lifepath and read by nothing, has
its first reader. New suite `vehicles` (5 checks).

## Standing facts about working here

- `python -m seedfall.tests -j 8` runs the lot (~3 min, 235 suites); one
  suite by name for a cycle, `--list` for the names.
- **Read the exit code from the interpreter, never through a pipe.**
  `... | tail -50; echo $?` reports `tail`'s status and is always 0. Send the
  run to a file: `python -m seedfall.tests > run.log 2>&1; echo "EXIT: $?"`.
  A failing check was committed once because of exactly this.
- **500 lines is the ceiling**, held by `tests/test_length.py`, and the
  `ALLOWED` debt list is empty. Split at a real seam; never record a debt.
- New `Conn` fields must be carried into `sim/preview._copy` or explicitly
  excused in `tests/test_conn.py`; the guard there will say so.
- `sim/` never imports Qt. `data → world → sim → ui`, one direction.
- **A layout check needs somebody else's fonts.** A runner has
  `fonts-dejavu-core` and nothing else, and the metrics are not this
  machine's; `tests/test_bridge._runner_fonts` loads matplotlib's copies so
  the check runs on both. The nightly ran red for its whole life over twenty
  pixels of line height.
- **Anything called from a QTimer slot needs the `painting.py` treatment**,
  not only `paintEvent`. A pop-out is `WA_DeleteOnClose`, so a widget held
  from one frame to the next can be a corpse by the next one, and the
  `RuntimeError` that raises kills the process instead of failing a check.
- A function written and never called is a defect the suite catches
  (`test_reachable`) — wire it or delete it.
