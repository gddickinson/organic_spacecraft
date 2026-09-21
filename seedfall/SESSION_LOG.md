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
