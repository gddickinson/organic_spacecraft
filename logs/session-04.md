# Session log, part 04 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-08-01 to 2026-08-01; undated entries keep their original place.

## 2026-08-01 — SEEDFALL: the guns get a button, and the click stops stuttering

#136. `sim/engage` had decided who may be fired on and at what band since it
landed, and nothing in `ui/` could reach it. `ui/fire_panel.py` is the button —
one door, taking `(win, game, conn)` rather than a window, because the Pilot
screen holds its own free flight while the conn window keeps one on the game.

**The two-door risk was real and is closed.** `ui/battle_view.begin` builds its
own `Battle` from an encounter dict with no band, so routing a conn engagement
through it would have thrown away the range the pilot flew for. Measured, the
same hull from two distances:

    at rest,  5,091 km  ->  Medium
    150 burns, 3,405 km ->  Close

and the window's battle carries that band, because `engage.open_fire`'s battle
is handed over rather than rebuilt.

**The picture found a defect nothing else would have.** Rendered, the fire
control offered to open fire on a hull **1,293,058,866 km** away and called it
extreme range — `band_for` clamps to the last band, so everything past
`reach_km` (10,000 km) reads as merely far rather than as out of the question.
Four of the five hulls on seed "fire" were like that, the worst 129,306 times
past reach. `may_engage` had no range gate at all; it has one now, and the
board offers one gun instead of four and counts the rest.

**A mutation caught a tautology of mine.** The check asserted `not view.running`
after firing — and the clock had never been started, so it read False either
way. Started properly, it went red, and it was right to: the clock only stopped
because the *button* passed an `after` hook. Two attempts to fix that:
`hideEvent` looked like the door and is not — Qt posts no hide event for a
widget that was never really shown, so it held in a played window and not in a
built one. `ui/window.go` calls `leaving()` on every route out now, so walking
to the Shipyard stops the beat too.

### And the pilot could feel the lag, so I measured it

    one press of Ahead        48.7 ms
    world.galaxy.distance     151,728 calls per press
    traffic.in_system          27 rebuilds per press

`weave.sites` is a farthest-point sample over the whole sector, **pure in the
galaxy and nothing else**, and it sat on the path of every question about where
a hull is: `track.at` -> `traffic.in_system` -> `_busyness` -> `gate_at` ->
`gates` -> `sites`. A `Galaxy` is generated deterministically from its seed and
never added to afterwards — the one `systems.append` runs while it is being
built — so it is answered once per seed now.

The other half was mine: `build()` measured every range on demand and the
demand was thirty-two times a click, because `in_view`, the rows, the fly-at
buttons, the board and the triggers each asked again, and `may_engage`,
`band_for` and `note` each measured a third time inside one row. Measured once
and handed down.

    one press of Ahead        48.7 ms  ->  12.3 ms
    galaxy.distance           151,728  ->  0
    traffic.in_system              27  ->  6

**Counting calls to `sites` proved nothing** — the memo makes it return early,
so it is called exactly as often and costs nothing. The check counts
`galaxy.distance`, which is the work that used to happen. A stopwatch would
have measured the machine; this measures the program.

Eleven mutations red across the two suites. The memo mutation that ignores the
seed breaks two *pre-existing* weave checks as well as the new one, which is
the evidence that caching a sector is correctness-critical and not merely fast.

## 2026-08-01 — SEEDFALL: the sweep that guards the constants had nothing guarding it

#134, first half. The task said the fast paths were blind and named
`bloom.HEART_HP` as the proof. Measured, one suite at a time, the constant
halved and doubled:

    HEART_HP = 1300.0 / 5200.0
      bloom   green      <- the fast path
      tuning  green      <- the only suite that imports the module
      play    RED        <- the only suite that guards it

So the sweep had been reporting a pinned constant as a survivor, and "SURVIVES"
has meant *"not caught by the suites I chose to run"* rather than
*"unprotected"*.

**The wrong turn: I tried to fix the table by reading.** I parsed every check
file's imports to find which suites touch each constant-holding module — 46
modules, 105 (module, slow suite) pairs, 53 distinct slow suites — and the
answer was worse than useless. `test_play` imports **nothing** from `bloom`; it
plays the game and the heart is on the far end of that. Static analysis pointed
at `tuning`, the one suite that does import it and does not guard it. An
imports-derived fast path would have been confidently wrong in both directions.

So every entry has to be earned by mutation. Two were, this cycle:

    bloom.HEART_HP            caught by `play`   (half)   kin was ("bloom",)
    approaches.ODDS_PER_DAY   caught by `ticks`  (double) kin was ("envoy","approach")

`approaches` was not in the task at all — `envoy`, `approach`, `politics`,
`play`, `sim`, `courting` and `overtures` all ran green on `ODDS_PER_DAY` and
`ticks` caught it.

**And two constants are genuinely unpinned**, not blind-spot artefacts — halved
*and* doubled against ten and eight candidate suites respectively, all green:
`bloom.RESIST_DECAY = 0.00035` (how fast a bloom forgets a weapon you have
shelved) and `approaches.QUIET_DAYS = 120` (how long a power leaves you alone).
Filed as #142.

**The structural finding: nothing had ever checked the tool.** A dozen suites
cite its verdicts in their comments and several checks exist *because* it
reported something unpinned, and `KIN` — 133 hand-kept entries, 226 suite names
— had no check of any kind. `tests/test_tripwire.py` is the first. It found two
faults immediately that are statically decidable: an entry for `declared`, a
module that does not exist anywhere in the package, and it now holds the
measured guards so a fast path cannot quietly stop naming the only suite
protecting a constant. Five mutations, all red — including one that names a
guard which is *not* in `SLOW`, because such a row would prove nothing.

The 10-hour re-sweep is the remaining half of #134 and is untouched.

## 2026-08-01 — SEEDFALL: the ship could not be aimed, and nothing had ever turned her

#139. Measured before writing anything: a hull 5,952 km off, main drive, full
throttle, 500 burns on *Ahead* — and the range went to 22,695 km. You could
see a thing and you could not go to it.

**Two wrong turns, both corrected by measuring.**

*The task's own premise was wrong.* It said to use `freeflight.hand_over`.
Measured: `hand_over` **teleports**. With the hull 3,146 km away it produced an
approach whose `conn.pos` was 12 km — the arrival range — while
`flight.ship_position` had not moved at all. It hands the *last few kilometres*
to the computer, which is what `berthing.can_conn` says in as many words when
it refuses a star: "The conn is for the last few kilometres." It is not a way
to cross 3,146 km, and using it would have been a teleport wearing a flight.

*My own first fix was wrong too.* I slewed `conn.nose` straight at the contact
through `sim/attitude.slew`. The nose came about correctly — 84.4° off to 0.00°
in 180 s — and then four hundred burns moved the range **not one metre** while
the tank drained from 20 t to 16 t. `conn.apply` re-derives where the drive
should point on every tick, from the axis button *rotated by `Conn.heading`*,
and slews the nose back onto that. Pointing the nose by hand was arguing with
the flight computer and losing.

**`Conn.heading` was the door, and nothing had ever written it.** So "Ahead"
meant +y for every hull in every flight since the conn was written. All the
machinery for turning was already there and correct: `apply` spends a whole
tick swinging the hull when the nose is off, which is `sim/attitude`'s "turn,
burn, and turn again". `sim/attitude` itself was declared and unconsumed —
`slew`, `plan_turn`, `turned`, `heading_note` and `pointed_at` had no caller
outside their own module. The one missing fact was *which way is ahead*.

`freeflight.steer` is that fact: `rotate` takes the forward axis to
`(-sin h, cos h)`, so laying it on the bearing is `atan2(-dx, dy)`.

Flown through the screen afterwards, seed "flighttest":

    Patient Ledger      5,952 km  ->  closest approach     14 km
    (seed "aim")        3,146 km  ->  closest approach     13 km
    ticks spent coming about: 6 and 9

She flies *past* it — nothing brakes, which is the autopilot's job and #140's.

The course is re-laid every beat, because a hull holding station rides its body
round the star: measured, ninety days on, the contact had moved to 2,958 km and
a course laid once was pointing at where it used to be.

Eight mutations, all red: heading never written, wrong sign on the bearing,
bearing taken from the origin instead of the ship, the course laid once and
never held, no fly-at buttons, `fly_at` not laying the mark, and both exits
failing to clear it.

**And one tautology I wrote and caught myself**: `assert off_course(...) < 1e-6
or True`. That is the exact fault this log keeps recording, written again, in a
check about not writing it. Removed before the suite ever saw it green.

Filed #141 from the picture: with a course laid on something 4,909 km away, the
ship panel prints "Range 1,042.5 km" in red — `conn.range_km` in a free flight
is the distance flown from the release point, because the conn's origin is the
release point when there is no target. Both numbers are true; the label answers
a question nobody asked.

## 2026-08-01 — SEEDFALL: a Pilot screen, and two doors I only found by looking

The Conn is for a *situation* — an approach to a berth, an orbit to make. There
was no screen for the general case: the ship, open space, and time passing. The
**Pilot** screen is that (`ui/pilot_view.py`, 230 lines, rail key `p`), and the
one thing that makes it different from every other screen in the game is that
**the clock runs while you look at it**.

Measured, one ship day at the bridge:

    1,440 beats of conn.TICK   day 0 -> 1        purse ₡18,000 -> ₡17,982
    conn.elapsed 86,400 s      conn.charged 86,400 s   (equal to the second)
    secure() afterwards        day stayed 1      (commit re-billed nothing)

That last line is the whole safety argument. `core/clock.MAX_STEP` is 1 (#116),
so a jump of N days is N jumps of one, and `sim/berthing.charge_flown` bills
only the minutes nobody has billed yet — so billing in pieces is *exactly*
billing once. Before #116 landed, a live screen would have quietly drifted away
from a played one.

**Wrong turn one: six cameras and no hand on the stick.** The first draft could
look anywhere and fly nowhere. It surfaced as `KeyError('fore')` — `conn.VIEWS`
ids are fore/aft/port/starboard/dorsal/ventral, `conn.AXES` ids are
forward/back/left/right/up/down — so a check written to burn along a camera id
found the missing console instead of the typo it was hunting. The screen has
all six axes, a coast, the main drive and the throttle now, and flying it
spends: **196 km on 2.400 t**, and `flight.ship_position` follows.

**Wrong turn two: a second door for the throttle, caught only by the picture.**
Rendered offscreen and looked at, the button read `THROTTLE: 50%` and the ship
panel one row below it read `Throttle 100%`. The view had kept its own
`self.throttle` and passed it to `apply` as a keyword, while
`instruments.readout` read `conn.throttle`, which nothing had ever written. No
value comparison would have found this — both numbers were internally
consistent, and only side by side were they a contradiction. The throttle lives
on the conn; `pilot.set_throttle` is its only writer.

**And two of my own checks did not bite.** Eleven mutations run with `-B`; nine
went red immediately, two walked straight through:

- `set(seen) <= THROTTLE_STEPS` was **tautological** — `set_throttle` snaps to
  the nearest rung, so cycling over `[0.37, 0.62]` still lands on the ladder.
  It asserts every rung is *reachable* now (`==`, not `<=`).
- Pinning `apply(throttle=1.0)` left the button, the panel and the ladder all
  correct while every burn went out at full power — a console showing a tenth
  and firing the lot. **Nothing checked the setting reached the burn.** It does
  now, in reaction mass: ten burns cost **0.1450 t at 10% against 0.9050 t at
  100%**.

Both survivors are the same fault this log keeps recording: a check that reads
the thing it claims to test. Finding them cost one mutation run.

One more lesson, from Qt rather than the game: the test's `app` was a local, so
when the builder returned, the last Python reference to the `QApplication` died
and Qt tore down every widget it owned — "wrapped C/C++ object of type
PilotView has been deleted", on a view built two lines earlier. The app and its
windows are held for the life of the module.

### And the full run kept dying, in a place I had not touched

Three full runs, three deaths, three different suites — gunnery once, verbs
twice — always the same traceback, always in `ui/gauges.py`:

    p.drawText(10, 16, self.reading.get("title", "").upper())
    TypeError: first argument of unbound method must have type 'QPainter'

That is PyQt's wording for a painter with no C++ instance behind it. Qt says it
plainly one line earlier: `QPainter::begin: Paint device returned engine == 0`.
Raised inside `paintEvent`, where Qt cannot propagate an exception, it did not
fail the run — it **ended** it, silently, at whichever window was painting.
Every suite after that point simply never ran, and the pipeline exit code was
`grep`'s, so it read as 0.

Pristine HEAD in a worktree ran all 174 suites with no traceback; my tree died
twice out of two. So it was mine to fix, even though `ui/gauges.py` is nothing
to do with a Pilot screen — one more view in every window's stack is enough to
change when a backing store is refused.

**Two fixes were not enough, and the measurement said so both times.** Asking
`p.isActive()` before painting caught the zero-size case and nothing else: the
next full run died *inside* `_face`, three calls after the painter had just
said it was active. The painter can go away *during* a paint, and no question
asked beforehand covers that. So `paintEvent` took ownership of the whole span
— begin, check, draw, catch, end.

Then the run after **that** died in `ui/viewport.py` instead, on the same line
of the same fault. Guarding one file had only moved it. That is what made it a
class rather than a site: `ui/painting.py` is one door now (`Painted`, and
`MISSES`), and `Instrument` and `Viewport` both go through it. Neither owns a
painter's lifetime any more; they implement `draw` and nothing else.

Four full runs to find that, at roughly 25 minutes each. Every one of them was
needed — the fault does not reproduce in 28 suites, only in the whole 174.

A guard that catches everything is the shape of thing that turns a real
regression green, so two checks hold it from both sides: a healthy instrument
given room to draw must record **no** miss, and an instrument whose `draw`
raises must be recorded and must not propagate.

**And my mutation harness scored the most important mutation backwards.** With
the try/except removed, the run *crashed* rather than failing, so there was no
`FAIL` line to grep and the script reported "SURVIVED" — the guard called
worthless by the exact failure it prevents. A run that never reports is not a
run that passed; the harness treats an unfinished run as red now.

Suite: `test_pilot_screen`, 5 checks, registered as `pilotscreen` — **not**
`pilot`, which was already taken by `test_pilot` and would have been silently
dropped from `SUITES_BY_KEY`. Three `tripwire.KIN` entries gained it by
*merging*, not by adding rows: `freeflight`, `berthing` and `engage` already
existed as keys, and a duplicate literal key in a dict overwrites in silence.

## 2026-08-01 — SEEDFALL: the last two were never broken, and one of my guards was

#116's list was two. It is nought, and not because I fixed them.

**I set out to fix `approach` and `ventures` and could not make either budge.**
Both roll a probability scaled by the span, so the obvious repair is to
compound rather than multiply — `1 - (1 - p)**days` instead of `p * days`,
which is distributionally identical to rolling `p` on each day. It changed
nothing, and the arithmetic says why: at exactly thirty days the two forms
give the same number. The measurement had to be wrong, not the code.

It was. Under a **real** generator, 200 trials a side, one call of thirty days
against thirty of one:

    ventures   0.505 ± 0.045 live   against   0.540 ± 0.047   (0.5 s.e.)
    approach   0.905 ± 0.021 sent   against   0.895 ± 0.022   (0.3 s.e.)

Neither is a difference. Both were **false positives of my own sweep**, which
drives every tick with a stateless generator so that only structure shows —
and that turns `chance(p)` into a threshold clearing in both runs or neither,
depending on nothing but whether `p` lands above a half.

**Worse: last cycle I asserted the opposite off sixty trials.** `ventures`
measured 0.400 against 0.500 and I wrote a check pinning that gap. At 200
trials it is half a standard error. An under-powered measurement encoded as a
guard is worse than no guard, because it reads as evidence — and I had already
written the note about validating instruments twice over.

So `test_ticks` now judges by structure only the five ticks that draw no
randomness, and sends the nine that do to a trials check under a real
generator, which asserts they **agree** within three standard errors. The
per-call list is empty.

    judged by structure   5 ticks, 0 per call
    judged by trials      9 ticks, all agreeing
    fixed this cycle      none — two were never broken

The clock's remaining blocker is #121 alone.

Full suite green at 1,230 checks.

## 2026-08-01 — SEEDFALL: the exchequer keeps a cadence, and the sweep had two blind spots

#116's list was three; it is one. But the interesting part is that the guard
itself was wrong in two different ways, and both were flattering it.

**The fix.** `exchequer.settle` accrued money in proportion to the span and
made its decision — found a berth, raise one, give one up — once per *call*.
`_books` now works a `SETTLE_DAYS` cadence at a time, and `settled` advances
*by* the cadence rather than snapping to today. Measured on seed "exq" over
900 days:

    before   one call 0 settlements, margins 214/274/394/214
    after    one call 25 settlements, margins 202/260/374/200
    walked   29 settlements,          margins 282/342/471/303

Over ninety days the two agree exactly, which is why this survived: the gap
only opens once a span covers more than one cadence.

**Blind spot one: lazy state, and it cost a whole cycle.** The sweep jumped
one game to day 30 before its first call and stepped the other. Several
subsystems build state on first use and stamp it with the day they were asked
— `exchequer.purse` is born carrying `settled = game.day` — so the two runs
started from different stored state and the tick was flagged for *when it was
created*, not how it scales. It cost me an hour of this cycle too: my first
probe created the purse after advancing the day, so no decision could ever
fire and I read "the fix does nothing" three times before tracing it. Both
games now share an identical first day before they diverge.

**Blind spot two: the fixed generator cannot see a probability.** The sweep
drives every tick with a stateless generator so only structure shows, and that
makes `chance(p)` a threshold which either clears in both runs or neither.
`ventures` rolls `ONSET_PER_MONTH * (days / 30)` once per call and is
genuinely per-call — under a *real* generator, 60 trials a side, one call of
thirty leaves 0.400 ventures live against 0.500 walked. It would have dropped
silently off the list. It now sits in `PROBABILISTIC` with its own
trials-based check.

**And the guard could not see its own fix.** `test_ticks` runs 30 days, where
exchequer agrees either way, so both mutations of the repair came back green.
A focused check at 900 days pins it — the same lesson as `loyalty` last cycle,
which needed a finer check than the coarse diff could give.

    structural per-call   approach
    probabilistic         ventures
    rate                  the other twelve

**And a downstream check went red, which is the fix working.** `test_politics`
asks that background politics never foreclose the Concord ending. Its window
compared 10 years against 25 and allowed a 12-point slide; the reading is now
12.4, because powers that actually expand generate more territorial friction.
Measured further out, the property holds and the curve simply bends later:

    0y −45.00   10y −62.67   25y −75.10   50y −74.69   80y −75.36

Flat from 25 onward. So the check reads the plateau where it is rather than
widening the old window, which makes it a stronger claim than before — it now
demands relations actually *stop*, and separately that they never reach the
floor, instead of merely sliding slowly.

Full suite green at 1,230 checks.

## 2026-08-01 — SEEDFALL: loyalty comes off the list, and two of my three fixes were tidying

Working #116's list from last cycle. Four per-call ticks named; this cycle took
`loyalty`, and it is now three.

**What was wrong.** `tick` recorded a payday at
`scale=min(3.0, max(0.25, days / 30))`. The floor is the defect: a day at a
time credits a *full month* thirty times over. Measured over thirty days,
officers ended at

    one call of 30   57.97 / 67.01 / 63.40
    thirty of one    67.42 / 99.92 / 72.87

One officer 33 points high. Removing the floor brings the two within 0.25 of a
point, and the guard now calls `loyalty` a rate.

**Two of my three changes turned out to be tidying, and the mutations said
so.** I also removed a 0.005 dead-band in `record` and made `drift` compound
rather than add. Both are more correct. Neither is load-bearing:

- the dead-band never fires — `feels` is large enough that a thirtieth of a
  month still clears 0.005, so putting it back changes nothing. It *looked*
  like the reason the 0.25 floor existed, and it is not.
- linear against compounding drift is 6.40% versus 6.60% over a month, about
  0.13 of a point on an officer.

Both mutations came back green. I have written that into the code rather than
leaving comments implying I fixed three things.

**And the guard needed correcting too.** Exact equality was the wrong test: a
tick applying two per-day rates in sequence can never match itself across
chopping, because they do not commute — `loyalty` records a payday and then
drifts toward the ship's mood, and interleaving those lands 0.23 of a point
from doing each once. That is convergence, not a defect, and the clock's step
is one day anyway. `test_ticks` now diffs with a 2% tolerance, and a separate
finer check watches the loyalty numbers directly, because the coarse diff
cannot see the things the tolerance was widened past.

The third check earned itself immediately: the moment `loyalty` was fixed it
went red saying "take it off the list, the guard is loose by that much".

    decide per call   approach  exchequer  ventures
    rate              the other eleven

Full suite green at 1,228 checks.
