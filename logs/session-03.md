# Session log, part 03 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-08-01 to 2026-08-02; undated entries keep their original place.

## 2026-08-02 — SEEDFALL: the sweep's ten hours were mostly one suite

#134. With the tool alive again, I set out to run a slice of the 439 and
measure the real rate. The rate turned out to be the finding.

    piracy      10 constants, 0 survivors        20 seconds
    exchequer   13 constants                     still going after 30 minutes

**The task's "seven constants per ten minutes" was measured before the fast
paths were fixed and is meaningless now.** The cost is not per constant at all.
Timed individually:

    exchequer alone       3.6 s
    politics alone      145.4 s     <- the most expensive suite in the project
    both in one run     148.0 s

`exchequer`'s fast path is `("exchequer", "politics")` and the stage handed
*both* to a single run, so all thirteen of its constants paid 148 s a variant
to ask a question `exchequer` answers in under four. The cost of sweeping a
module is the cost of the most expensive suite its entry names, times three
variants, whether or not the cheap one would have answered.

**Two changes, both measured, neither altering a verdict.**

*Stage one asks one suite at a time and stops at the first objection.* The set
consulted is unchanged, so no constant's answer moves; only the order and the
early exit are new. Entries are written module-suite-first, which is both the
cheapest and the likeliest to object. `piracy` went 19.9 s to **9.2 s**, and
the report now names the suite that actually objected — "— fence" instead of
"— piracy, traffic, fence".

*`--fast` skips stage two.* Two stages that differ by two orders of magnitude
should not be one command. The fast sweep of everything is a shortlist; the
broad stage confirms the shortlist. And the wording changes with it, because
**"unprotected" is a verdict the fast stage cannot reach** — all it knows is
that the suite naming the module did not object. Saying more is exactly how
`bloom.HEART_HP` came to sit on a survivor list with `test_play` holding it.

**The wrong turn: I expected the short-circuit to rescue `exchequer`.** It does
not — its own suite does not catch its constants, so they fall through to
`politics` anyway and the module still costs an hour and a half. The saving is
real where a module's own suite answers and nil where it does not, which is
worth stating rather than implying.

Both kills of a running sweep left the tree clean — `git status` empty after
SIGTERM — which is the restore handler doing the job it was written for.

Four mutations red. The ten-hour re-run is still not done; it is now a
fifteen-minute shortlist followed by a targeted confirmation, which is a job
that fits somewhere.

## 2026-08-02 — SEEDFALL: the seam was easy; the sweep behind it was dead

#138. `tests/tripwire.py` sat at 500 exactly — the next line anybody added to
it would have failed the ratchet — and the seam was measured before anything
moved: `SKIP`, `ROOT`, `constants`, `variants`, `rewrite` are lines 105..175,
**contiguous, containing nothing else, and reading nothing from the rest of
the file**. They are now `tests/sweepkit.py`: how to find a tuning constant and
how to change one on disk, knowing nothing about suites. `tripwire.py` is 428.

The alternative seam — the suite table, `SLOW`/`SUITES`/`KIN`/`LIMIT`, 153
lines — is the bigger cut and also needs nothing from the rest, but it is *not*
contiguous: five blocks with the mutation machinery interleaved. Contiguity
won.

### Then I ran the tool I had just split, and it died

    TypeError: 'bool' object is not callable

`main` assigns `noticed = False`, which shadows the module-level `noticed()`
for the whole function **including its closure**, so the first constant it
tried called `False(suites)`. Checked against HEAD by stashing: **pre-existing,
and dead at HEAD.** #134 — re-sweep all 436 constants — has been waiting on a
tool that could not start. `main` had no check of any kind, which is exactly
how it stayed broken. Renamed the local to `caught`; the sweep runs:

    python3 -m seedfall.tests.tripwire tug
    5 constants, 0 unprotected — control, clearance

which is also the first independent confirmation that last cycle's `tug` fast
path does its job.

### And proving a check bites left real damage on disk

Mutating `rewrite` so it does not restore made my new round-trip check go red,
correctly — and left `data/gates.py` holding `TOLL_REFUSED_BELOW = 0` and
`sim/tug.py` holding zeroed constants, because **both my check's cleanup and
the sweep's own restore took their undo from `rewrite`'s return value**. Break
the rewriter and you break the undo with it. A check that cleans up through
the thing it is testing has no cleanup.

Both now snapshot the text themselves and restore from that. Re-run, the same
mutation goes red and the tree stays clean — which is the difference.

One mutation **survives and should**: swapping the restore back to `rewrite`'s
word is invisible while `rewrite` works, because the two are then equal. It is
defence against a broken rewriter, and no check can prove defence-in-depth
without first breaking the thing it defends against. Said here rather than
dressed up in a contrived assertion.

Five mutations red: the shadowing local, no restore at all, negatives made
invisible again, `rewrite` not restoring, `rewrite` not changing anything.

Twelve debts still; this split was of a file that was never on the list.

## 2026-08-02 — SEEDFALL: I had built two of everything, and measuring said so

#138. I opened this cycle to split `tests/tripwire.py`, which sits at 500
exactly and would fail the ratchet on the next line anybody added to it. While
mapping its readers I found `tests/test_harness_guard.py` — a file that
predates all of this work — and it already held **both** of the guards I had
been so pleased with:

    @check("the tripwire's fast paths point at suites that exist and run")
    @check("no file in the package is past five hundred lines")

So `tests/test_length.py`, which I wrote three cycles ago, was a **second debt
list**, and `tests/test_tripwire.py`, written four cycles ago, duplicated the
weaker half of a stronger check. Its docstring opened with "Nothing has ever
checked the tool itself", which was simply false.

**The two lists had already drifted, inside two cycles.** Measured:

    harness_guard still carried   sim/conn.py    612   (split; actually 489)
                                  sim/control.py 602   (split; actually 487)
    the two disagreed about       ui/viewport.py 535 against 533

That is the exact fault this project keeps recording — one fact, two doors —
committed by me, in the checks whose whole job is to catch it. And it hid
in plain sight because both lists pass: a ceiling of 612 over a 489-line file
is green, so a stale row is silent unless something refuses stale rows, which
only *one* of the two lists did.

**Closed to one door each, keeping the better of each pair.**
`test_length` holds the ceilings, because it also refuses a paid debt and a
row for a file that no longer exists — the thing that would have caught the
drift. `test_harness_guard` keeps the fast-path check, because it is strictly
stronger than mine: it catches a module named *twice*, and a dict literal
keeps the last value for a repeated key silently — that had once swept
`stations` against one suite of five.

**And one of the checks I deleted was not a duplicate, which measuring caught
and reading would not have.** A ghost `KIN` entry — a row for a module that
does not exist — survived after the deletion. My first mutation *appeared* to
catch it, and did not: adding the row pushed `tripwire.py` from 500 to 501 and
the **length** check fired. Re-run as a replacement rather than an insertion,
same line count, it went straight through. The assertion is folded into
harness_guard's fast-path check now, where the table's well-formedness already
lives, and bites there.

`test_tripwire.py` is 92 lines from 120 and holds exactly one check — the
measured guards, which is the half that was genuinely missing.
`test_harness_guard.py` is 241 from 279.

**No file was split this cycle, and the task is no further forward.** Deleting
a hundred and thirty lines of duplicated checking was the better use of the
cycle, and `tests/tripwire.py` is still at 500 waiting for its seam.

## 2026-08-02 — SEEDFALL: two rules nothing was holding, and a comment that said otherwise

#142. Both constants confirmed genuinely unpinned before anything was written —
**sixteen candidate suites between them, halved and doubled, all green.**

**The measurement caught a lie in a comment.** `tests/test_tuning` says, in as
many words, "`ODDS_PER_DAY` zeroed retires the whole approach system in
silence. `QUIET_DAYS` zeroed turns it into a nagging inbox. Both are pinned by
counting arrivals over a decade." It pins the first and it does **not** pin the
second: its bounds are three to sixty envoys a decade, which is a wide enough
door to walk a spacing rule through sideways. `tuning` was not in my earlier
candidate list, so I tried it first this cycle precisely because the comment
claimed it — and it ran green at half and at double.

`tests/test_approach` had the other apparent guard, and it is the classic
shape: it built its fixture with `game.day += QUIET_DAYS - 5`, so halving or
doubling the constant moved the fixture with it. Two guards standing over a
constant, neither able to fail.

**Both are pinned now on what they govern, measured and never read.**

`QUIET_DAYS` — two chronicles played a day at a time for eleven years each,
recording the days between consecutive approaches *from the same power*:

    78 repeat approaches; shortest gap 120 days, longest 608

Asserted at 110..140. Halved (60), doubled (240) and zeroed all go red.

`RESIST_DECAY` — what the Bloom forgets about a weapon family you have stopped
using, from a full 0.55:

    100 days   -> 0.515
    1,000 days -> 0.200
    1,600 days -> gone      (4.4 years)
    1,400 days -> still resisting

Asserted against those figures, plus the invariant that a thousand days told
one at a time equals a thousand told at once — the clock steps daily in play
and jumps in a transfer, and those must agree. Halved, doubled and zeroed all
go red.

**And the fast paths were earned, not guessed.** `tuning` is in `SLOW`, so the
broad stage would not have caught either constant — which makes these two
legitimate `test_tripwire.MEASURED` rows, unlike the tug row the same check
threw out last cycle for naming a guard the broad stage runs anyway. Added to
`KIN` by editing the two existing lines rather than adding any, because
`tests/tripwire.py` sits at 500 exactly and the ratchet does not care why.

Six mutations, six red. Two of 436 constants down; #134's full re-sweep will
find more of these, and now there is a worked pattern for each.

## 2026-08-02 — SEEDFALL: the tug gets its own file, and a row I was not allowed to write

#138, second debt paid. `sim/control.py` was 602 and had drawn its own seam
years ago: a banner reading "── the tug ──" at line 490, and — measured through
`ast` before a line moved — **nothing above the banner calls anything below
it**. Four functions, five constants, 113 lines. `sim/control.py` is 487.

**The constants came with it, which is the opposite of last time and for the
same reason.** Splitting `sim/conn` they had to stay put: `ALONGSIDE_RATE`
alone had five other readers. Searched untruncated this time — the lesson from
that cycle — `TUG_FROM`, `TUG_RATE`, `TUG_REACH`, `TUG_CATCH` and `TUG_SECONDS`
are read by nothing outside the tug, so they belong with it. Nine external
references in all, every one repointed: `sim/clearance`, `sim/conn_step`,
`ui/conn_window`, `tests/test_control` and a docstring in `sim/conn`.

**The tripwire refused a row I tried to give it, and was right.** Having moved
constants into a new module I added a `MEASURED` entry recording that `control`
catches `TUG_FROM` at half — which it does. The check threw it out:

    FAIL 'control' is not in SLOW, so the broad stage would have caught
         tug.TUG_FROM anyway and this row proves nothing

That assertion went in last week on the grounds that such a row *would* look
like evidence without being any, and here it was stopping its own author from
writing exactly that. The `KIN` entry stays, because a fast path is worth
having; the comment beside it now says plainly that it is speed and not safety.

**And the length ratchet caught me twice in one cycle.** The comment explaining
all this pushed `tests/tripwire.py` from 496 to 505:

    FAIL over five hundred lines and not a recorded debt: tests/tripwire.py (505)

Trimmed to three lines; the file is 500 exactly, which is passing and one line
from not being. It is a candidate for the next split rather than the next
exemption.

Reverting the split is red, as it must be — `sim/control.py (598)` — and five
mutations through the new module's constants all bite, so the tug's behaviour
is held where it now lives rather than merely parsing there.

Thirteen debts to twelve; 656 lines of debt left, from 758.

## 2026-08-02 — SEEDFALL: the panel stops answering a question nobody asked

#141, found in a rendered picture two cycles ago and made starker by the
autopilot: with the computer closing on a mark 1,926 km away, the ship panel
read **"Range 3,210.4 km"** in red.

`sim/instruments.readout` had two branches, orbiting and not, and "not" meant
*berthing*. `conn.range_km` is the distance from the origin of the conn's
frame — the target in an approach, and **where she let go** in a free flight —
so it was printed as "Range" and judged against the 40 km at which a berthing
is going badly. Measured, flying out to a hull:

    after 300 burns      true range to the mark   2,968 km
      Range     8,590.0 km   [warn]     <- distance flown, called a range
      Closing    -583.2 m/s  [ok]       <- closing on the place she left
      Relative    583.2 m/s  [warn]     <- judged against a berthing rate

583 m/s is a great deal for coming alongside a quay and nothing at all for
crossing a system, so the panel sat in amber for the whole flight. A screen
that cries wolf teaches the pilot to ignore it — which `readout`'s own
docstring already says, about the orbit rows, from the last time this happened.

Free flight has its own three rows now: **Flown** and **Speed**, both plain,
and no "Closing" at all, because out there nothing is being closed on. Same
flight, after the fix:

      Flown     6,490.6 km   [ok]
      Speed       583.2 m/s  [ok]

**No range-to-mark row was added, deliberately.** The mark lives on the screen
that holds it and `ui/pilot_view` already prints its name, range and bearing;
a second copy in the panel is how two ranges start disagreeing. That was the
choice #141 offered and it is the one that keeps the door single.

**The near-miss.** `ui/flight_window` builds its *own* Range and Closing rows
rather than going through `readout`, so the same defect could have been sitting
there untouched. Measured rather than assumed: opened against a live free
flight it refuses outright — "Flight controls — nothing in reach. Take the conn
on something first." — so its rows only ever paint for an approach, where
"Range" is exactly right. Nothing to fix, and worth the two minutes to know it
rather than guess.

Four mutations red, including one that puts the new branch *above* the orbiting
one incorrectly — the free-flight test alone would not have caught an orbit
losing its Altitude row, so a second check holds the two branches that were
already there.

## 2026-08-02 — SEEDFALL: the computer will come alongside, and refuses what it cannot fly

#140, the half that was left after the guns landed. The request said it
plainly: fly to the asteroid, "or also engage the auto-pilot to come alongside"
it.

**`sim/autopilot` already had a `close` mode, and it does not fit.** Measured on
a free flight, `close` and `orbit` both returned `[0, 0, 0]` — *the same answer
as `null`* — because `close` aims at a mooring mast through `sim/moorings` and
measures its room against a structure's radius and a hold point, and out in
open space there is neither. A console offering "Close and berth" there would
have quietly stopped the ship and called it an approach. Both refuse now.

**Two doors closed rather than a third opened.** The braking arithmetic came
out of `safe_rate` into `autopilot.rate_for(room_km, dv)`, so an approach
(which works out its room from the structure, the hold point and the corridor)
and a free flight (which has only the range to what it is running at) cannot
end up with different ideas of what is stoppable. And "cancel the difference
between the velocity you want and the one you have" — the whole flight computer
— came out into `autopilot.hold(conn, want)`. `freeflight.run_for` decides
nothing: it works out the velocity it wants and hands it to `hold`.

Flown, three seeds, from a standing start to alongside:

    auto        Held Breath      5,137 km -> 50 km  1,098 ticks (18.3 h)  0.35 m/s  18.26 t
    fire        Held Breath      5,091 km -> 50 km  1,036 ticks (17.3 h)  0.43 m/s  17.80 t
    flighttest  Patient Ledger   5,952 km -> 50 km  1,059 ticks (17.6 h)  0.05 m/s  17.67 t

Through the screen, with the clock beating: 5,137 km to 50 km in 962 beats,
16.0 hours, arriving at 0.17 m/s. It hands the conn back at that point — sets
itself to holding station and writes "Alongside Held Breath, 50 km off." A
computer that stops without a word leaves the pilot watching a still picture
wondering whether it is still working.

`ALONGSIDE_KM` is 50 out here, well inside `engage.reach_km` of 10,000, so a
pilot who runs something down arrives with the guns able to speak — measured,
`may_engage` answers True on arrival.

Nine mutations, all red, including a flat 20 m/s closing rate (the exact bug
`safe_rate` records driving a hull into a quay at 70 m/s) and `rate_for` made
linear in the room rather than a square root.

**No wrong turn worth the name this cycle** — the measurement was taken before
anything was written and it changed the plan once, which is the process
working rather than a mistake: the task said to use the autopilot modes
`ui/conn_controls` already drives, and two of the three turned out to be
meaningless where this screen flies.

The picture did find something, and it is #141 again, now much starker: with
the computer closing on a mark 1,926 km away, the ship panel reads **"Range
3,210.4 km"** in red. Both true, different questions, and the red one is the
distance flown from where she let go.

## 2026-08-01 — SEEDFALL: one seam cut, and a ratchet so the rest cannot grow back

#138 said fifteen files were over five hundred lines. Counted: **nine outside
`tests/`, fourteen in all**, 758 lines of debt between them. The task was stale
in its number and right in its substance.

**The seam.** `sim/conn.py` was 612. Its own structure names the cut: the
console, the axes, the throttle and what a burn costs are the pilot's side;
`_substeps`, `_sweep_min`, `_step`, `_touch` and `_resolve` are the other —
given a hull with a velocity, how far does a minute carry her and does she
touch anything on the way. Measured before moving a line:

    the block is contiguous, 472..599, and holds nothing else
    120 lines, needing math, outcome_sim, Conn, and five constants
    exactly one caller: apply -> _step
    no caller anywhere outside the module

`sim/conn_step.py` is those 120 lines; `sim/conn.py` is 489.

**The constants stayed put, deliberately.** `ALONGSIDE_RATE` alone is read by
`autopilot`, `moorings`, `clearance`, `instruments` and the flight window;
`SAFE_CLOSING` by `preview`, `impulse`, `landing` and `instruments`. Moving
them to keep the new file self-contained would have forced `sim/conn` to
re-export them, and a re-export is a second door. So `conn_step` imports them
from `conn`, and `apply` imports `conn_step` lazily — the way it already
imports `sim/attitude` — which keeps the seam one-way instead of a cycle.

### The real finding: nothing had ever enforced the rule

The five-hundred-line rule has been standing instruction from the start and
**no check anywhere counted a line**. That is the whole reason #138 exists as a
task rather than as a non-event: files drift over one commit at a time, nobody
notices until somebody counts, and then it is fifteen at once — each needing a
real seam found, which is a cycle apiece.

`tests/test_length.py` is the ratchet. A file not on the debt list must be
under 500. A file on it must not grow. A debt that has been paid must be struck
off, because a row for a file that no longer needs one makes the remaining work
look bigger than it is and sends the next person to split something already
split.

**The wrong turn, and it is one I have made before in a different costume.**
I checked for external callers of the five private functions with a grep that
ended in `| head` — and trusted it. The tenth line of output was not the last:
`tests/test_orbits.py:380` called `conn_sim._resolve`, and the full suite found
it at suite 167 of 178 after twenty-odd minutes. The recorded lesson from the
last split was "a split is not done when it parses"; the same lesson wearing a
new hat is **a split is not done when the grep was truncated**. Searched
properly afterwards: exactly one caller, and it is now pointed at the new home.

Then the ratchet caught its own author. Fixing that test added three lines to
`tests/test_orbits.py`, which is itself a recorded debt at 567:

    FAIL already too long and grown since: tests/test_orbits.py 567 → 569

The right answer to that is not a bigger number in the list. The note went onto
the call line as a trailing comment and the file is back at 567 exactly.

Five mutations, all red — including the one that matters, putting the
integrator back into `conn.py`:

    FAIL nothing new is over five hundred lines
         over five hundred lines and not a recorded debt: sim/conn.py (618)

Raising `LIMIT` to 700 instead of splitting anything does not get past it
either: every debt then reads as paid and the stale-row check refuses the lot.
