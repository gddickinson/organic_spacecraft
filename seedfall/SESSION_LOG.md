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

## Standing facts about working here

- `python -m seedfall.tests` runs the lot (~25 min, 192 suites); one suite by
  name for a cycle. A suite that reports must `return True` from `run()`.
- **Read the exit code from the interpreter, never through a pipe.**
  `... | tail -50; echo $?` reports `tail`'s status and is always 0. Send the
  run to a file: `python -m seedfall.tests > run.log 2>&1; echo "EXIT: $?"`.
  A failing check was committed once because of exactly this.
- **500 lines is the ceiling**, held by `tests/test_length.py`. The `ALLOWED`
  debt list may shrink and never grow — pay it by finding the seam, not by
  recording a new debt.
- New `Conn` fields must be carried into `sim/preview._copy` or explicitly
  excused in `tests/test_conn.py`; the guard there will say so.
- `sim/` never imports Qt. `data → world → sim → ui`, one direction.
- A function written and never called is a defect the suite catches
  (`test_reachable`) — wire it or delete it.
