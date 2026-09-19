# Session log, part 02 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-08-02 to 2026-08-02; undated entries keep their original place.

## 2026-08-02 — SEEDFALL: the computer was flying her and not saying how

#145 continued. Measured before writing: one run to a contact 5,137 km off,
printing what the computer intended against what the screen showed.

    beats     range      the computer intends        the screen said
        0   5,137 km   forward, torch, 100%    "running for Held Breath"
      200   3,493 km   back, thrusters         "running for Held Breath"
      600     208 km   None (coasting)         "running for Held Breath"

Accelerating, braking and arriving, and six identical words for all three. A
pilot watching the window could not tell which was happening.

**And the one number that would have told them did not exist.** `Conn.closing`
is measured against the conn's origin, which in a free flight is *where she
was let go* — so a ship braking hard onto a contact reads as opening on the
place she came from. True, and useless. `freeflight.closing_on` is the
component of the velocity along the bearing to the mark:

    at rest              0 m/s
    burning at it      +95 m/s
    burning away      -207 m/s

The board now says what the computer is doing — "ahead on the torch at 100%",
then "astern on thrusters", then "coasting", then it hands back — and a
Closing row with the range's own clock on it: "146 m/s — about 6.3 h to go".

**The layout check caught me widening the bridge.** The first phrasing
repeated the target's name in the autopilot row and cost **29 px** of width
the screen did not have — overflow 0 became 29, which is the check written
last cycle doing exactly its job on its own author. The name is on the Course
row a line below; the autopilot row says "running her in — astern on
thrusters at 100%" and the overflow is 0 again.

Four mutations red: one fixed phrase again, the wrong axis named, closing
measured on the release point, and the closing sign flipped.

**One item on #145 was wrongly premised and is struck.** I had listed
"berthing and orbiting still need the Conn" as a gap. Re-reading the original
request: *"This will leave the Conn for specific situations (docking,
orbiting) and this will be a general purpose way of directly driving the ship
in any situation."* The Conn keeping docking and orbiting is what was asked
for, not a shortfall.

## 2026-08-02 — SEEDFALL: you could not see the thing you were flying at

#145 continued. Measured first, and the measurement was blunt: laying a course
on a contact rendered the viewport **byte-identical**. `Viewport._target`
draws `conn.target`, a free flight has none, and the method says so in its own
comment — "station keeping: there is no target, only sky". So the screen's
whole promise, *what you can see you can go to*, came down to a row of text to
cross-reference against a starfield of identical dots.

`ui/viewport_mark` rings the marked bearing and names it. The screen hands
down a **direction and a name**, from `freeflight.toward`, so the window looks
nothing up: it knows how to draw a ring, not what a contact is.

**Adding it to `ui/viewport.py` was not allowed, and that was the useful
constraint.** That file is a recorded debt at 533 lines, and the ratchet does
not care what the extra lines are for. So the drawing went in its own module
and the projection maths — `project` and `_unit`, pure geometry with no Qt in
it — came out into `ui/viewport_math.py`. `viewport.py` is **518**: a feature
added and fifteen lines of debt paid at the same time.

**Then the picture caught the next fault.** Rendered, the label read "H" — it
was drawn always to the right of the ring, and a mark near the edge of the
window lost its name to the frame. It goes on whichever side has room now, and
"Held Breath" reads in full.

**And a mutation caught me writing a test that proved nothing.** To check the
zero-bearing guard I mutated `length` to 1.0, which sent a zero vector through
`project` — which rejects it anyway — so the mutation survived and told me
nothing about the guard. Deleting the guard outright is the real question, and
that goes red: without it the division raises.

Four mutations red: the ring never drawn, the window never told, a mark behind
the camera drawn in front of it, and no guard on a zero bearing.

## 2026-08-02 — SEEDFALL: the bridge did not fit in the window

Asked to keep working on the Pilot window until it works correctly, so I
measured it rather than glanced at it. **An offscreen widget that has never
been shown reports a scroll range of zero and answers every layout question
"fine"** — the first probe said so and was worthless. Shown at 1360x880:

    the bridge is 1,444 px tall in a 782 px view — 662 px below the fold

46% of the screen was out of sight. Everything after the instrument table —
what is in view, the fly-at buttons, the fire control, the guns, the marks,
the autopilot, the clock — needed a scroll past the readouts to reach. A
`View` gives one column and the screen used it for everything, stacking a
260-px window onto a nine-row table onto four rows of buttons, while the
window was 1360 wide and nobody was using the room sideways.

**Two columns: the view and the hands on the left, the boards on the right.**
662 px below the fold became 170.

**And that broke the width, which the picture showed and the numbers named.**
Rendered, every reading in the right-hand column was cut off mid-number —
"0" for "0 m", "0.0 m" for "0.0 m/s". Measured: the content was **1,348 px
wide inside an 891 px viewport**. Two culprits, each found by asking which
widget demanded the most:

    the fire-control rows, each carrying the whole of `engage.note`   802 px
    four "Fly at <name>" buttons in a row that cannot wrap            660 px

A `Panel` row does not wrap and a `QHBoxLayout` of buttons does not either.
The fire rows are short now — "close range · 3,405 km" — with the refusal
sentence underneath as a `note`, which does wrap; the button rows are a grid
two wide; the six cameras are three wide, because six across wanted 486 px and
that was the last 56.

    1,348 px wide -> 891 in a 891 px viewport, overflow 0
    662 px below the fold -> 199
    23 of 27 controls reachable without scrolling

**The check is measured on a shown window**, and bites on all four faults: one
column again, the fly-at row unwrapped, the cameras six across, and the whole
sentence back in a fire row.

Re-flown through its own buttons afterwards, everything still works. The
flight harness still reports three "dead" thrust buttons, and it is wrong
rather than the screen: with the torch lit an off-axis press spends its tick
turning, which the ship panel now says out loud. The harness reads positions
and not `view.last`.

## 2026-08-02 — SEEDFALL: the law of telepresence gets its own file

#138, third debt paid. `sim/robots.py` was 616 with four banners of its own,
and the first one — "── the law ──", lines 145..276 — is a single idea: how far
away a machine is and how much of it survives the delay. 132 lines,
contiguous, nothing else inside. `sim/robots.py` is 435.

**It was not the clean leaf it looked like.** Measured through `ast` before
moving anything: the law needs `owned` from the roster (in `ward_from`) *and*
the roster needs `effective` from the law (in `standing`, `aboard_effects`,
`working`). A two-way dependency, so a plain move is a cycle.

The resolution is the one `sim/conn_step` already uses in reverse: the new
module is the leaf and takes its two roster references *inside* the functions
that need them — `ABOARD`/`STOWED` in `gap_au`, `owned` in `ward_from` — so
`sim/robots` can import it at module level and the seam runs one way.

**Five constants moved and two stayed, decided by counting readers.**
`HALF_LIFE_S`, `STANDING`, `LIGHT_S_PER_AU`, `AU_PER_LY` and `ALONGSIDE_AU`
are read only by the law. `ABOARD` and `STOWED` are read by eight functions in
the roster, so they stayed — the same rule that kept `ALONGSIDE_RATE` in
`sim/conn` and let `TUG_*` travel with the tug.

**And I very nearly left a re-export behind.** The first wiring had
`sim/robots` importing all five law functions so its old callers kept working
— which is a second door, the thing this project keeps closing. `robots`
imports only `effective`, which it actually uses; `ui/machineshop`,
`ui/robots_panel`, `sim/colony`, `test_robots` and `test_swarm` were repointed
at `sim/telepresence` on their existing import lines, so `test_robots` stayed
at exactly its recorded 624.

**The wrong turn, and it is the recorded one wearing another hat.** I checked
who *called* the moved functions and not who *imported the moved constants*.
Four checks went red — the autonomy ladder, the light-year holding, light-lag
at gunfight range, and which machines count as guards — because `test_robots`
and `test_swarm` read `HALF_LIFE_S`, `LIGHT_S_PER_AU` and `GUARD_DUTY` through
`robots`. A split is not done when it parses, and it is not done when the
function callers are found either.

Five mutations red, including putting the paid debt back on the length list.
Twelve debts to eleven; 540 lines of debt left.

## 2026-08-02 — SEEDFALL: flew the Pilot screen through its own buttons

Asked to fly it from the GUI and find problems, so I pressed what a player
presses — every camera, every axis, the throttle, the drive, the clock, the
course, the autopilot, the guns, the mark, walking away and coming back, and
securing — and checked what the screen said afterwards.

**Most of it holds.** Six cameras each draw a different picture. The throttle
walks 10/25/50/100 and the panel agrees at every rung. The clock runs at 250 ms
a beat and stops when you leave the bridge. A course laid on a contact
survives walking away and coming back. The guns and the mark appear for what
is in reach. Securing clears the course and the computer.

**One real defect, and it is the one a player would hit first.** With the main
drive lit, *three of the six thrust buttons moved the ship nowhere*:

    Ahead      d-pos [0.0, 0.0, 0.0]     <- nothing
    Astern     d-pos [0.0, 0.025, 0.0]
    Port       d-pos [0.0, 0.0, 0.0]     <- nothing
    Starboard  d-pos [0.0, 0.0, 0.0]     <- nothing

Measured through `conn.apply`'s own return, the cause is not a bug at all:
`burned=False, turning=True`. The torch only pushes along the nose, so a press
whose axis is not under it spends the whole tick swinging the hull — which
`sim/attitude` documents as the point ("a hard burn to port on a loaded
freighter is a decision rather than a button"). **The screen said nothing.**
A correct rule with no feedback is a dead button as far as the pilot can tell.

The panel now says which it was — "swinging the hull round to bear — the torch
did not fire", or "fired" — from `apply`'s own answer rather than a second
guess at it. On the attitude clusters every axis fires, as it always did.

**And my own check was wrong before the code was.** I asserted a turning tick
left `conn.pos` unchanged; it does not, because the minute still passes and a
ship already moving keeps coasting through it. The claim worth making is that
the swing bought no *speed*, so it asserts `conn.vel`.

Three mutations red. The mutation harness itself needed rewriting first — I
built its table with nested quoting and produced a `SyntaxError`, which is the
same string-concatenation trap this log has recorded twice before; it is
written with `repr()` now.

## 2026-08-02 — SEEDFALL: the flag was being dropped, so nobody could be charged

#144 said opening fire on a power's hull costs nothing with its friends. True,
and the reason was one line deeper than the task described.

**`sim/track.contacts` never copied `hull.faction`.** `Contact` has the field
and sets it for a quay; for a hull it was left `None`. So `engage.open_fire`,
which reads `contact.faction or "unaligned"`, fought an **unaligned** enemy
whoever the ship belonged to — taking with it the enemy's fit from
`encounters.make_enemy`, the standing a kill costs, and everyone who cared.

The first probe made it look rarer than it is: seed "price" showed every hull
with `faction=None` and I nearly wrote that most traffic is unaligned. Asked
through `traffic` instead of through `track`, across twelve systems: **55 of 55
hulls carry a flag**, 85.5% Charter. The field was wrong for all of them.

**Then the gap the task named.** `aftermath._standing` drops the victim's own
standing by `KILL_COST` and walks `allegiance.offended_by` so its *rivals* are
pleased — and nothing walked `defenders_of`, so the people fond of it did not
mind. `allegiance.charge_attack` is the one door for that and only
`sim/diplomacy` had ever spent it, for denouncing. Measured:

    day one, nobody fond of anybody:  charter -14.0
    Sanhedrin warmed to 60:           charter -14.0, sanhedrin -8.6

Costing nothing extra on day one is the point rather than a gap: relations
start negative, `defenders_of` is empty for all four powers, and friendship has
to be built before it can be spent.

**And the bill is quoted before the trigger.** `engage.price` asks the same two
doors at the same weight `aftermath` spends through, so the board says
"Destroying her costs charter -14.0, sanhedrin -8.6" *before* the pilot
commits. A cost discovered afterwards is the same defect as a greyed-out
button.

**The full suite went red once, and the check it broke was right to break.**
`test_aftermath`'s "nobody gloats in a sector at peace" sets every relation to
+30 and then asserted that *only the victim* moved. At +30 all round every
power is a **friend** of the victim, so the new rule charges them all — three
of them, 2.9 apiece. The title's claim still holds and the second assertion
had quietly encoded "gloating is the only way anyone can move", which was true
when it was written and is not now. It asserts nobody comes out of a kill
*better off*, which is what the title always meant.

I saw that check fire during the mutation runs and put it down to sensitivity
rather than looking. It cost a full 25-minute suite run to be told properly.

Six mutations red. The sharpest is swapping `charge_attack` for
`price_attack` — the report is identical and no standing moves — which the
check catches because it compares `game.rep` before and after rather than
reading the dictionary the sim handed back. Dropping the flag again also kills
a *pre-existing* aftermath check, which is how a one-line omission had gone
unnoticed for so long: nothing downstream had ever seen a flagged conn fight.

## 2026-08-02 — SEEDFALL: the captain gets his own enemies, and my harness lied

#143, and the last unbuilt piece of the original Pilot request — "set targets
as enemies to be targeted".

**Hostility was derived and only derived.** `sim/traffic` builds every hull
with `hostile=ERRANDS[errand][2]` — a raider is hostile, a freighter is not —
and `sim/track` copies that onto the `Contact` a screen draws. The game had an
opinion about who your enemies were and the captain had none.

**Measured before building: a mark is worth something.** `hostile` is read by
`traffic.hostiles`, `present_factions` (a hostile hull's flag stops counting as
present for encounter rolls), the readiness board (hostiles sort to the top),
`ui/orbit_chart` (a warn-tinted cross with no label), `traffic_panel` and
`mesh_panel`. So one stored fact lights up six readers.

**It could not live on the contact.** `Contact` and `Hull` are both rebuilt from
nothing on every call — that is what makes the Kestrel you hailed yesterday the
same Kestrel today — so `hostile = True` would last until the next redraw.
`sim/hostiles.Grudges` is on the chronicle and registered with `core/save`.

**The two answers meet in exactly one place**, `traffic.in_system`, where
`hostile` is computed: `ERRANDS[errand][2] or hostiles.is_marked(...)`. Flown,
one mark and every reader follows — `tint` goes to warn, `traffic.hostiles`
names her, the readiness board puts her top — without any of them knowing the
module exists. Saved and reloaded, she is still marked; a chronicle with no
such state opens clean.

**Marking costs nothing and tells nobody**, and that is checked: no standing
moves, no credits, no time, and `sim/hostiles` writes nothing to the log —
the screen that pressed the button says so, because a sim door that also
narrates is two doors. `allegiance.price_attack` is what a *denunciation*
spends.

### And the mutation harness reported seven survivors that were not

Every one of the seven mutations came back `*** SURVIVED ***`. They had all
applied; the harness was running **only the `tripwire` suite**, because the
suite name sat inside a multi-line call and my edit to it had silently matched
nothing. A check that passes without checking — the exact fault I keep finding
in the game — in the tool I use to prove checks bite.

The suite list is a named constant at the top now, and the runner raises if the
child prints nothing at all. Re-run properly: seven mutations, seven red, and
one of them — dropping the errand from the expression — also killed a
*pre-existing* traffic check, which is the evidence that the derived answer
still carries its own weight.

**Left undone deliberately**: opening fire on a faction's hull costs nothing
with its friends. `allegiance.price_attack` exists and only `diplomacy` spends
it. Filed rather than folded in.

## 2026-08-02 — SEEDFALL: measuring the guards one constant at a time

#134, its own named next step: `exchequer` and `ventures` name `politics` —
145.4 s a run, the dearest suite in the project — with nothing cheaper in front,
so every constant those modules hold pays it. Timed the alternatives first:

    armada 0.1 · accord 2.0 · fleets 2.7 · exchequer 3.5 · ticks 3.6
    industry 7.5 · geography 11.4 · levy 11.9 · territory 14.7 · orders 29.9
    politics 145.4

Every one of them is cheaper, `orders` at 30 s by a factor of five.

**Measured constant by constant**, mutating each and asking the cheap suites in
turn, ten of `exchequer`'s thirteen resolved:

    YIELD_PER_LEVEL  UPKEEP_COEFF  CAPITAL_BONUS  SHORTAGE_YIELD
    FOUND_COST  RESERVE  RICH_APPETITE          -> exchequer   (3.5 s)
    INDUSTRY_YIELD  WAR_CHEST                   -> industry    (7.5 s)
    VENTURE_STAKE                               -> none of the cheap ones

So `exchequer` names `("exchequer", "industry", "politics")` now — cheapest
first — and two constants that used to cost 145 s a variant cost 7.5.

**The run did not finish.** `SETTLE_DAYS`, the eleventh, sat for half an hour:
set to 0 it sends some suite into a very slow path, which is exactly what
`tripwire`'s own `LIMIT = 60` exists to bound and what my scratchpad probe,
with a 400-second timeout and no signal handler, did not. `ventures` was never
reached.

**And the probe left `SETTLE_DAYS = 0` on disk** when I killed it, because
unlike `tripwire.main` it registers no SIGTERM restore. Restored from git —
and worth noting what did *not* happen: the file was intact but for that one
line. Last cycle's atomic `put` held, where the week before the same situation
truncated `data/diplomacy.py` by 168 lines.

Two mutations red, one of them a surprise: putting `politics` *first* in the
entry fails the ordering check as well as costing time, so cheapest-first is
held rather than merely intended.

Eleven measured guards recorded now. Two constants are still open —
`exchequer.VENTURE_STAKE` and `exchequer.SETTLE_DAYS` — and `ventures`'s six
are unmeasured.

## 2026-08-02 — SEEDFALL: the shortlist was all false, and a hard kill ate a file

#134. Ran the fast sweep over everything. It is **not** the fifteen minutes I
estimated last cycle: 19 constants in fourteen minutes, so 439 is an overnight
job, not a cycle. The reason is the same one as before, unfixed — 27 constants
sit behind `politics` at 145.4 s a run, and `diplomacy`'s fast path named
*only* `politics`.

**Four candidates came off those 19, and all four were false.** Every one was
already guarded, by a suite its fast path did not name:

    charts.KNOWN_WORTH          provenance   0.3 s     kin was (charting, charts)
    diplomacy.COURTSHIP_KNEE    courtship    1.4 s     kin was (politics,)
    diplomacy.COURTSHIP_FLOOR   courtship
    diplomacy.COURTSHIP_FALLOFF courtship

A hundred per cent false-positive rate on the sample. Both entries now name
their real guard, cheapest first: `charts` re-swept reports **0 of 4** with
`KNOWN_WORTH — provenance`.

**And the measurement overturned a rule I wrote a week ago.** `MEASURED` rows
had to name a guard in `SLOW`, on the reasoning that otherwise the broad stage
would catch the constant anyway and the row proved nothing. Neither
`provenance` nor `courtship` is slow — and the rule would have barred exactly
the four rows that stop a false shortlist. What a fast path that misses its
guard produces is not a slow answer but a **wrong** one. The rule is gone, the
tug row it rejected last cycle is back, and `MEASURED` holds nine.

### A hard kill ate 168 lines of a source file

A ten-minute foreground timeout sent SIGKILL to a running sweep. The tool's
SIGTERM restore handler never ran, `write_text` had truncated
`data/diplomacy.py` and not yet finished writing it, and the file came out
**168 lines shorter than it started** — the whole courtship curve gone. Its
own module docstring had warned of this exact thing happening once to
`data/industry.py`, and the fix had never been applied to the tool itself.

`sweepkit.put` writes a sibling temp file and `os.replace`s it, which is
atomic: the path names the old contents or the new one and never a half.
`rewrite` and both of the sweep's restore paths go through it. Restored from
git; nothing lost.

**And the check I wrote for it failed its own second run.** It counted every
`.swp` beside the probe file, so litter left by the *previous* mutation — the
one that proved the check bit — failed every run after. It measures the delta
now. A check that inherits the last run's mess reports the mess.

And the mess is not small: the mutation that stops `put` renaming leaves one
temp file per write, so proving that check bit scattered **212 `.swp` files**
through `data/` and `sim/`. Untracked, so nothing was lost and `git status`
told the whole story — but a mutation that disables a cleanup leaves mess in
proportion to how much work it was cleaning up, and the harness should be run
knowing that.

Five mutations red. The sweep still has not been run to completion; what this
cycle bought is that its shortlist can be believed.
