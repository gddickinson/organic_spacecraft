# What this is — the design, pass by pass (5 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

**The declared-field guard went past `data/`, and found seven traits that did
nothing.** Task #88 pointed `test_declared.py` at `sim/`, `world/` and `core/` as
well — 1,167 fields — and the richest find was in the crew.

`crew.TRAITS` has declared seven officer traits since it was written, each with
an effect key and a magnitude: Charter-raised +0.04 diplomacy, Yards-trained
+0.05 repair, Freehold-born +0.05 trade, Bloom veteran +0.05 tactical, Wet-wired
+0.03 accuracy, Quiet +0.04 scan, Reckless +0.04 evade. **Not one was ever
applied.** `Officer.trait_id` was written when a candidate was generated and read
by nobody: `trait_name` and `trait_note` went to the crew screen, so a Bloom
veteran said "Was at Kessel's Reach and came back" and fought exactly like
anybody else. It was not free either — `make_officer` charges 25 a month for a
trait, so a captain had been paying for seven effects that did not exist.

`crew.trait_effects` sums them by key and `ship.stats` adds each into the stat it
names. Six of the keys name a stat computed there; the seventh, `tactical`, names
the *skill* the combat numbers derive from, and a first draft converted it into
levels — which measuring showed to be nonsense, moving accuracy by 0.0026 where
every other trait moved its stat by 0.03 to 0.05. A magnitude declared in stat
units is a stat, so it adds to accuracy and evade directly.

Two more of the findings landed on the gunner's board, which is the one screen
whose job they were:

- **`firing.Shot.band_shift`** — "bands to close (negative) or open (positive) to
  reach its envelope" — read by nobody, so a mount out of range said "range" and
  left the captain to work out which way. It says **"open 3"** now, which is an
  order for the helm rather than a complaint.
- **`gunfire.Shot.frm`, `.to` and `.weapon`** recorded who fired, at whom, with
  what, and nothing read any of them: which gun did what existed only as prose in
  the log, while a gunner pulling the trigger saw a heat number change and
  nothing else. The board carries a **Last exchange** list now, both directions.

Two were deleted rather than wired. `anchorage.Anchorage.extras` was a dict built
in three places carrying a redundant copy of the port's level, a gate's lit flag
and a colony id, all reachable from the objects themselves; and
`territory.Demand.holdings` was a count of what was at stake beside a live
`holdings_in()` — a stored copy that can disagree with the truth the moment a
colony is lost, which is the two-doors fault this project has hit more than any
other. The six that remain are allowlisted against tasks #92, #93 and #94.

**And two lessons about the guard itself.** A regex for `.name` counted
`self.x = 1` as *reading* `x`; it walks the AST for a `Load` now, because a field
only ever assigned is exactly as dead as one nobody mentions, and three findings
were of that shape. The other is that a field only the *suite* reads is still
dead: `extras` was read by `test_anchorage` and by nothing in the game, which is
why the sweep excludes the tests. Constructor keywords stay invisible to it —
`Demand(holdings=…)` and `Anchorage(extras=…)` were both real writes it did not
see — which is right for the verdict, since a write is not a read, but it means
the count of writes it could report would be wrong.

**The gunner had no middle.** `combat` offered one named mount or `_salvo` —
"everything that can bear, fired together" — and `_salvo`'s own docstring says
the cost is heat and ammunition, "which is why a single aimed shot stays a real
option". That reads like a trade until it is measured.

**A HAMMERFALL with five mounts puts 69 points of heat into itself in one salvo,
against a fault line of 40 and a vent of 6 a turn.** It faults on turn one and
never comes back: across ten turns its resolve bled from 92.9 to −34 on its own
radiators, in a fight it was winning on damage. The alternative on offer was one
mount out of five. So **buying armament made the salvo button worse**, which is
the question this project asks of every good thing, and here the answer was yes.

`sim/gunnery.py` is the missing control: fire *some* of them. `quote` says what a
chosen set does to the hull before the trigger — heat in, clamp, vent, then the
fault test, in that order, because a volley that lands a point over and vents six
is not a fault and quoting it as one would be crying wolf. `advise` picks the
most damage of any set that will not fault, found exhaustively, since no chassis
carries more than five mounts and 32 subsets is nothing.

Played over twelve engagements at two difficulties with the guns supplied, on the
hot hull the advised volley won **6/12 and 4/12 against 1/12 and 2/12** for firing
everything, and never faulted once against 53% and 57% of turns. On a cooler
LONGSHOT the three options are level inside a twelve-seed sample, and firing
everything still overheats on nearly half its turns.

**`advise` was wrong twice and playing it is what showed both.** It first ordered
by damage *per point of heat* — heat is the constraint, so economise heat — which
favours the small guns: a PDC is four damage a point, a Fusion Lance barely two.
It picked the pea-shooters, left the main armament cold and won 3 of 12, while
firing one Fusion Lance every turn won 6 despite faulting a fifth of the time.
Economising heat is not the job. Then it could advise firing *nothing*: on a warm
hull no mount fitted under the line, so the answer was to sit still, and played
out it said fire, hold, fire, hold — shooting half as often as the enemy.
`ship.py` records the same lesson beside `HEAT_CEILING` from the last time it
happened, that they "lost to their own radiators, in a fight they never shot in".
The floor is now the heaviest gun that bears: faulting is a cost, being harmless
is a loss.

Three more things the work turned up:

- **The fault line is `heat_cap`, not `heat_cap * HEAT_CEILING`.** The ceiling is
  the physical clamp on how much heat a hull can hold; the line `_end_of_turn`
  tests is half that. I read them the wrong way round and built a board on it,
  which would have called every faulting volley safe. `gunnery.fault_line` is one
  function and `_end_of_turn` now asks it too.
- **`Shot.mount_id` is a part id, so it is not unique.** Five mounts came back
  under three names, because three Fusion Lances are all `fusion_lance`. They are
  genuinely interchangeable — one hold rather than per-mount magazines, identical
  parts in identical arcs — so a selection is a **multiset** and the count has to
  be capped at what the hull carries. The window keys its holds by slot for the
  same reason.
- **Five of the eighteen weapons draw `alloy` and a new captain carries none.**
  Not a bug — you supply your own guns — but it wrecked two rounds of my own
  measurements, which compared gunnery modes on a ship where nothing could fire.

`ui/gunner_window.py` is the seat: a boresight per mount, the tactical plot, a
board of every mount with what stops it and what it costs, and the trigger with
the heat quoted before it is pulled. `ui/mount_sight.py` draws the sights — and
**`firing.arc_span` returns half-angles**, which its docstring says and my first
draft ignored, putting a fore arc entirely to starboard. `ui/tactical_plot.py`
had already been fixed for exactly that and left the reason behind it: "drawing
only one of them is a lie about the ship." It looked plausible on screen because
the target happened to be near dead ahead when I looked.

`MainWindow.battle_act` is now the one door for resolving a turn, because there
are two seats on the same engagement and the second copy is where the
`b.player.st = ship_stats` line gets left out.

**The pilot could not throttle.** `sim/conn.apply` has taken a `throttle` since
the drive learned to throttle and a `ticks` since it was written, and the conn
could reach neither: it fired `apply(conn, axis, main=use_main)` and nothing
else, so the human's main drive was a switch — full power, one minute — while
the flight computer beside it throttled freely. `apply` still carries the note
saying why the *computer* needed it: "one tick of a fusion torch on a SPORE is
124 m/s, so the computer lit it to trim ten, overshot, corrected the overshoot,
and never converged."

Flown by hand, that is not a rough edge, it is a hull that cannot be berthed. A
SPORE under a Fusion Torch moves **41.9 m/s a press**, so a pilot with ten metres
a second of way on has no move that improves matters: every press overshoots
further than the error. Measured, a full-power-only pilot stays **stuck at 10.00
m/s**, outside the 1.5 m/s berthing limit, for ever.

`sim/pilot.py` is the console's side of it: `THROTTLE_STEPS` of a tenth, a
quarter, a half and everything, and `COAST_MINUTES` of 1, 5 and 15. With the
ladder that same pilot gets to **0.48 m/s** and berths. Two controls rather than
one, because `apply` does two things — it fires *once* and then steps time
`ticks` times, so the second is a **coast** and not a burn length; calling it a
burn length would be a lie about the button, and the button's name is all a pilot
has to go on.

`pilot.quote` is the only door the console speaks through, so a tooltip cannot
promise what the burn will not do; the old tooltip was computed at full power for
one minute whatever the console said. `pilot.burn_cost` is the only door the
*cost* comes through, and that fixed a real fault: **`can_burn` demanded a whole
`MAIN_COST` whatever the throttle**, so a hull holding 0.119 t was told "No
reaction mass for the drive" for a burn costing 0.012. That is the gate refusing
an act it could well afford — the fault this project has swept every other gate
for, and it existed here only because the throttle was unreachable, so nobody had
thought to ask. `apply` has its own gate call, and a sweep caught *that* one
separately: asking it at full power left `can_burn` correct and the burn still
refused, with nothing to show it.

`ui/pilot_view.py` is the **Pilot screen**, and the one thing that makes it
different from every other screen in the game is that **time passes while you
look at it**. The Conn is for a situation — an approach to a berth, an orbit to
make. This is the general case: the ship, open space, a live camera and the
console, always reachable from the rail (`data/screens.py`, key `p`).

That is only safe because the clock is honest. `core/clock.MAX_STEP` is 1, so a
jump of N days is N jumps of one, and billing in pieces is *exactly* billing
once. Measured: 1,440 beats of `conn.TICK` moved the chronicle from day 0 to
day 1 and the purse from ₡18,000 to ₡17,982 in wages, with `conn.elapsed` and
`conn.charged` equal to the second — and securing afterwards added nothing,
because `sim/berthing.charge_flown` is the one door either way and bills only
the minutes nobody has billed yet.

**Two wrong turns, both found by looking rather than reasoning.** The first
draft had six cameras and no hand on the stick at all: the pilot could look
anywhere and fly nowhere. It surfaced as `KeyError('fore')` — `conn.VIEWS` ids
are `fore/aft/port/starboard/dorsal/ventral` and `conn.AXES` ids are
`forward/back/left/right/up/down`, and a check that burned along a camera id
found the missing console rather than the typo it was looking for.

The second was a **second door for the throttle**, and only the rendered
picture caught it: the button read "THROTTLE: 50%" and the ship panel one row
below it read "Throttle 100%". The view had kept its own `self.throttle` and
passed it to `apply` as a keyword, while `instruments.readout` read
`conn.throttle`, which nothing had written. The throttle lives on the conn and
`pilot.set_throttle` is its only writer; the console reads it back. No value
comparison would have found this — both numbers were internally consistent.
The check that holds it now walks all four rungs of `pilot.THROTTLE_STEPS` and
asserts the button and the panel say the same thing at each.

**And the panel stopped answering a question nobody asked.**
`sim/instruments.readout` had two branches, orbiting and not, and "not" meant
*berthing*. `conn.range_km` is the distance from the origin of the conn's frame
— the target in an approach, and **where she let go** in a free flight — so it
was printed as "Range" and judged against the 40 km at which a berthing is
going badly. Measured on a flight out to a hull: "Range 8,590.0 km" in amber
with the contact she was flying at 2,968 km off, and "Relative 583.2 m/s" in
amber, because 583 m/s is a great deal for coming alongside a quay and nothing
at all for crossing a system. The panel sat in amber for the whole flight, and
a screen that cries wolf teaches the pilot to ignore it.

A free flight gets **Flown** and **Speed**, both plain, and no "Closing" — out
there nothing is being closed on. No range-to-mark row was added: the mark
lives on the screen that holds it, and `ui/pilot_view` already prints its name,
range and bearing. A second copy in the panel is how two ranges start
disagreeing.

**The computer will come alongside, and says what it cannot do.** `sim/autopilot`
already had `close`, and measured on a free flight it — and `orbit` — returned
`[0, 0, 0]`, *the same answer as `null`*: `close` aims at a mooring mast through
`sim/moorings` and measures its room against a structure's radius and a hold
point, and open space has neither. A console offering "Close and berth" out
there would have stopped the ship and called it an approach. Both refuse now,
through `targets.is_open`.

`sim/freeflight.run_for(game, conn, contact)` is the mode that belongs there,
and it decides nothing new. The braking arithmetic lives in
`autopilot.rate_for(room_km, dv)` — pulled out of `safe_rate`, so an approach
and a free flight cannot disagree about what is stoppable — and the burn comes
from `autopilot.hold(conn, want)`, which is the whole flight computer in one
place: every mode is a statement about what the velocity ought to be, and the
act is always cancelling the difference.

Flown to alongside from a standing start: 5,137 km in 18.3 hours arriving at
0.35 m/s on 18.26 t; 5,952 km in 17.6 h at 0.05 m/s. Through the screen with
the clock beating, 962 beats and 16.0 hours, after which the computer hands the
conn back to station-keeping and writes a line — a computer that stops without
a word leaves the pilot wondering. `freeflight.ALONGSIDE_KM` is 50, well inside
`engage.reach_km` of 10,000, so running something down arrives with the guns
able to speak.

**Where the ship is, in either frame.** `conn.pos` is an offset from the
frame's origin — where she let go in a free flight, the *target* in an
approach — and `freeflight.where` used `flight.ship_position` for both, which
is not rewritten until `berthing.commit`. Measured with the ship stood off
10,164 km from a quay and then given the conn on it: `where` said 10,152.4 km
and `conn.range_km` said 12.0. It read right on a fresh game only because the
ship is moored *at* the quay's body. `sim/track.at` is the one door for where
anything is, and it locates a `Target` now as well as a `Contact` — a target
carries `at_xy` and `hull_id`, which `target_from_contact` used to drop for
hulls entirely.

**One name to a spot, and only inside the frame.** Measured: four hulls
projected to `dx=0, dy=0` in one camera — hundreds of millions of kilometres
off in nearly the same bearing — so four labels printed on a single pixel.
Nearest wins and the rest are dropped, which loses nothing because the "In
view" board lists them all with ranges. And `project` returns a point for
anything merely *ahead*, so a contact eighty degrees off the nose came back at
x=2,000 in a 464-pixel window and was counted as drawn; `viewport_mark._screen`
bounds it to the frame.

**The window names what is out there.** A player reported that the Conn shows
the Fleet Hub and the Pilot screen does not, and they were right: `_target`
gives `conn.target` its true angular size, a free flight has no target, so the
same Hub was a 1.6-pixel speck in `_sky`. The data was never missing —
measured, a free flight's sky holds ten entries against an approach's nine,
*including* the anchorages the approach leaves out. `viewport_mark.draw_sights`
names quays and hulls, brighter inside `engage.reach_km`; worlds are left to
`_sky`, which draws them as lit discs. Moored, a quay is at exactly the ship's
position and the bearing is `(0, 0, 0)` — nothing to draw, and correct.

**The computer says what it is doing.** Measured on one run to a contact
5,137 km off, `run_for` went forward on the torch, then astern on the
thrusters to brake, then coasted — and the screen read "running for Held
Breath" at every one of them. The autopilot row now names the axis, the drive
and the throttle it is actually asking for, from `run_for`'s own answer.

Beside it, `freeflight.closing_on`: the component of the velocity along the
bearing to the mark, because `Conn.closing` is measured against the conn's
origin — *where she was let go* — so a ship braking onto a contact read as
opening on the place she came from. At rest 0, burning at it +95 m/s, burning
away −207.

**The screen says what a press did**, because three of the six thrust buttons
could look dead. The main drive only pushes along the nose, so with the torch
lit a press whose axis is not under it spends the whole tick swinging the hull
and burns nothing — right, and documented in `sim/attitude`, and previously
silent. Flown through the buttons: Ahead moved her, Port and Starboard and
Astern moved her nothing at all with no word said. The ship panel now reads
"swinging the hull round to bear — the torch did not fire" or "fired", taken
from `conn.apply`'s own answer rather than guessed at a second time. On the
attitude clusters every axis fires.

**Aiming, and why there was none.** For as long as the conn had existed,
"Ahead" meant +y — `Conn.heading` was declared and **never written**, so
`conn.apply`, which derives the drive's direction from the axis button rotated
by the heading, rotated by zero every time. Measured: a hull 5,952 km off, main
drive, full throttle, 500 burns on Ahead took the range to 22,695 km.

`sim/attitude` was the other half of the same silence — `slew`, `plan_turn`,
`turned`, `heading_note` and `pointed_at` had no caller outside their own
module, so nothing in the game had ever turned a hull, and the module's own
"turn, burn, and turn again" was a description of nothing.

`freeflight.steer` is the door that closes both. `conn.rotate` takes the
forward axis to `(-sin h, cos h)`, so laying the course on a contact is
`atan2(-dx, dy)` — after which `apply`'s existing machinery swings the hull
onto it, spending whole ticks and reaction mass to do it. Flown: 5,952 km to a
**14 km** closest approach, six ticks spent coming about; 3,146 km to 13 km on
another seed. She flies past — nothing brakes, which is #140's.

A first attempt slewed `conn.nose` at the contact directly and moved the range
**not one metre** over four hundred burns while the tank drained, because
`apply` slews the nose back onto the heading every tick. The heading is what
the flight computer reads; the nose is what it writes.

**What a kill costs, and who else minds.** `sim/aftermath` has always dropped
the victim's own standing by `KILL_COST` and pleased its rivals through
`allegiance.offended_by`; nothing walked `defenders_of`, so a captain could
work through one power's shipping hull by hull and stay welcome with its
friends. `allegiance.charge_attack` — the door `sim/diplomacy` already spends
to denounce a power — is charged at the same weight now. Measured: on day one,
with relations starting negative and `defenders_of` empty for all four powers,
a kill costs `charter -14.0` and nothing more; with the Sanhedrin warmed to 60
it costs `charter -14.0, sanhedrin -8.6`.

None of it fired before, because **`sim/track` was dropping the flag**:
`Contact.faction` is set for a quay and was never set for a hull, so
`engage.open_fire` fought an *unaligned* enemy whoever the ship belonged to.
Measured through `traffic` rather than `track`, 55 of 55 hulls across twelve
systems carry one. `engage.price` quotes the whole bill before the trigger,
from the same two doors at the same weight.

**The guns, and how fast the screen answers.** `ui/fire_panel.py` is the button
`sim/engage` waited for. It refuses out loud — `may_engage` returns a sentence
so the board can print "The guns answer to the conn, and the conn is flying an
approach" instead of going grey — and it hands over the `Battle` that
`engage.open_fire` built rather than letting `ui/battle_view.begin` construct a
second one with no band. Measured, the same hull at two distances: 5,091 km
opens at Medium, 3,405 km at Close, and the window carries that band.

Rendering it found the gap nothing else would have: the first draft offered to
open fire on a hull **1,293,058,866 km** away and called it extreme range,
because `band_for` clamps to the last band so everything past `reach_km`
(10,000 km) reads as far rather than as impossible. `may_engage` gates on range
now.

**And the Pilot screen used to stutter.** One press of Ahead took 48.7 ms and
ran `world.galaxy.distance` **151,728 times**, because `weave.sites` — a
farthest-point sample over the whole sector, pure in the galaxy alone — sits on
the path of every question about where a hull is, and the screen asked for
every range thirty-two times a click. The sector shape is memoised per galaxy
seed (a `Galaxy` never grows after it is built) and the ranges are measured
once per rebuild and handed down: **12.3 ms, 0 distances, 6 traffic rebuilds**.
The check counts `galaxy.distance` rather than timing anything, because
counting calls to `sites` proves nothing once it returns from a memo.

### One conn: two views of one situation

**The Pilot screen and the Conn window used to fly two different ships.** The
player said so: "the conn and the pilot view and controls still appear to be
completely separate instead of two views of the same situation." Measured, and
it was worse than it sounded — fly 290.9 km on the Pilot screen over 60 minutes,
burning 20.00 t of reaction mass down to 14.57, then open the Conn window: it
read **12.0 km off, 0 minutes elapsed, 20.00 t aboard**. Not a stale display. A
second `Conn` object, built from the ship's saved position, flying in parallel.

The cause was ownership. `ConnWindow.__init__` did `self.conn, self.refused =
berthing.begin(...)` and kept it on the window; `PilotView.ensure_conn` did
`self.conn, why = freeflight.begin(...)` and kept it on the view; `MainWindow`
had no `conn` at all. Two objects, no door between them.

`ui/window.py`'s own comment already stated the rule this broke: *"An approach,
an exchange and a crossing all belong to the game rather than to the window: a
save taken in the middle of one used to lose it."* A flight is one of those.

So **`core/state.Game.conn` is the flight**, `MainWindow.conn` is
`_on_game("conn")` beside `transit`, `dig` and `docking`, and both screens are
properties onto it:

    conn = property(lambda self: self.win.conn,
                    lambda self, value: setattr(self.win, "conn", value))

Three things fell out of that, each of which had to be fixed before the join
would hold.

**1. Opening the Conn on a contact hands the flight over — it does not start
one.** `freeflight.hand_over` has always existed for exactly this and the window
never called it. Now: fly free, open the Conn on the Fleet Hub, and it is the
same object, with the velocity (159.0 m/s), the nose, the reaction mass (14.57 t)
and the 60 minutes carried across.

**And `hand_over` did not do what its docstring promised.** It said the fresh
approach is placed where the ship really is; it set `vel`, `nose`, `rcs` and
`elapsed` and never set `pos`. A conn's `pos` is an offset from its frame's
origin, and the frame changes under a hand-over — a free flight is measured from
where she was let go, an approach from the target. So the new conn inherited
`berthing.begin`'s arrival range and the hull **teleported 302.9 km**: 290.9 km
off the Hub became 12.0. Fixed by taking the offset from `track.at`:

    tx, ty = track_sim.at(game, contact, game.day)
    fresh.pos = [(here[0] - tx) * KM_PER_AU, (here[1] - ty) * KM_PER_AU, 0.0]

Measured after: before 290.9 km, after 290.9 km, **the hull moved 0.0 km in the
world**, and the frame it is measured in is the only thing that changed.

**2. Securing had to actually secure.** `PilotView.secure` ends the flight and
asks the window to redraw — and the redraw comes back through `ensure_conn`,
which took a fresh conn on the same breath. Measured: 30 minutes flown became a
different `Conn` at 0 minutes, still live on the game, and the button read as
doing nothing. Standing down is a decision, so it is remembered:
`self.stood_down` gates `ensure_conn`, and the bridge offers **"Take the conn"**
to undo it. It is not a second answer to "are we flying" — `game.conn` is that —
but to "should the bridge hand her back".

**3. Closing the Conn window is leaving the room, not stopping the ship.**
`closeEvent` used to write `outcome = "broken off"` and settle on the way out,
which was right when the window owned the flight and is wrong now the game does:
it ended an approach under a pilot who was still flying it from the bridge.
Giving up is what `_break_off` is for, and two doors onto one act is one too
many.

**The flight is deliberately not saved, and that is not a shrug.** The first
attempt put a plain `conn` field on `Game` and broke saving outright: a `Conn`
holds a `sim/targets.Target`, a clearance and a sky, none of which
`core/save.register` knows. The save was written and would not read back at all
— *"save refers to unknown type 'Target'"* — and `load_game()` returned `None`.
The field is `metadata={"transient": True}`, so saving behaves exactly as it did
before the conn moved here: measured `saved: True | loaded: True | conn after
load: None, day 0 credits 18,000`.

**Two defects fell out of the measurements and were filed rather than folded
in** (tasks #148 and #149). `berthing.commit` charges `round(spent(conn), 2)`
while `conn.apply` tracks `conn.rcs` to four places, so securing refunds up to
0.005 t — measured 2.715 t burned, 2.71 t billed, 17.285 t left coming back as
17.29 t aboard. And reaction mass comes off the hull only in `commit`, unlike
the hours, which `charge_flown` bills as they pass — so a flight nobody ever
ends is never charged for its mass.
