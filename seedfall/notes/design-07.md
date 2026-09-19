# What this is — the design, pass by pass (7 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

**How you look at a body decides what you find.** Surveying used to be one
button: three days, no cost, no risk, the same kind of answer for a comet as for
an ocean world — while thirteen sensor fittings and a drone technology existed
only to nudge a single `scan` float. There are now four methods, and they are
deliberately *not* a ladder:

| Method | Flies there | Sees | Blind to | Wants |
|---|---|---|---|---|
| Long-range sweep | no | resources | life, anomalies, anything buried | to be inside your sensor reach |
| Close pass | yes | resources, life, anomalies | anything buried | reaction mass for the trip |
| Probe swarm | no | resources, life, anomalies | anything buried | `dronework`, 3 t silicon + 2 t alloy |
| Deep survey | yes | everything, including buried sites | — | scan ≥ 0.55, 4 t of charges, nine days |

Each method names what it `finds`, and `world/planets.survey_body` is filtered
by that list, so a method that says it cannot see lifeforms genuinely cannot.
The panel states the whole bill before you commit — days, stores, **and the
reaction mass for getting there** — plus what the method will be blind to, which
is the part that makes choosing one a decision rather than a formality.

Sensor reach is what gates the free method, and it is the reason a **listening
post is worth planting**: three colony classes advertise sensor reach, and
`colony.effects` has tallied it per system since they were written — but nothing
ever read the tally, so a CHORUS node extended your array by exactly nothing.
`sim/survey.reach()` reads it now. It stays per-system rather than folded into
`ship_stats`, because a dish spread across one system should not help you three
jumps away.

**Two mini-games.** The **docking approach** is the control loop from the
nervous-system study — sense, compute, act, hold homeostasis — with three drifting
axes, one correction per pass, and readings blurred by how good your sensors are.
A clean approach earns standing; a botched one buys a tug. The **decoding bench**
takes a recording of something that was not speaking to you: four positions, a
hidden pattern, and feedback that tells you how many glyphs are exactly right and
how many are merely present, never which. Solving one is worth alien
understanding, and costs nothing but attempts.

**There is a game on the ground.** Landing a party opens a 7×7 zone map revealed
one tile at a time. Moving costs days of supply (known ground is cheap to
re-cross, which is what makes coming home survivable); terrain springs hazards
that officers' skills mitigate; site features offer choices resolved against a
named stat. Nothing is banked until the party is back on the lander, and running
out of supply in the field costs most of the haul. How much biomass you commit at
launch buys how long they can stay.

**Contracts are optional work with deadlines.** Six kinds, posted per port and
scaled by distance. They are checked on the clock and complete the moment their
terms are met rather than when you remember to hand them in. Nothing in the game
requires taking one — the five endings are open from turn one.

**Alien technology is a separate progression from research.** Four cultures —
the Abyssals, the Ossuary, the Weft and the Tessellate — left twelve
technologies scattered across the sector as buried sites. None can be reasoned
out. Understanding accumulates in study points from four sources: excavating a
site, taking relics apart in a laboratory, buying somebody's field notes at a
port, and seizing them off a hull you destroy. At full understanding the
technology is *incorporated* — its id is appended to `research.unlocked`, so the
shipyard and codex treat it like anything else you know, and it never appears in
the research tree because you could not have derived it.

**Thirty-five hulls and nineteen stations across five families:**

| Family | Hulls | Character |
|---|--:|---|
| Grown | 12 | Gestated from a seed. Heals; eats phosphate; takes months. |
| Fabricated | 13 | Concordat of Yards. Welded in weeks, dear, and never mends. |
| Hybrid | 4 | Freehold grafts. Both bills, both gifts. |
| Synthetic | 4 | Dry Choir. Crewless, superb instruments, no self-repair. |
| Xeno | 2 | Not ours. It mends, and nobody has explained how. |

Which parts graft to which frame is `ACCEPTS` in `data/hull_types.py`: a grown
hull refuses a fusion lance, a Yards hull refuses an intima, a hybrid takes
either, and a synthetic frame takes fabricated and Dry Choir work but nothing
alive.

### One flight deck: the armed state moved onto the flight

**The player's report, again, and it was structural:** "the pilot window,
flight control, conn and gunnery systems were not properly integrated …
contradictory displays in the different viewers … the autopilot systems were
disjointed and their actions not always correctly displayed." #147 moved the
`Conn` onto the game; the *armed state* never moved with it. Which autopilot
mode was flying was `ConnWindow.mode`; the bridge kept a different vocabulary
in `PilotView.auto`; the main-drive selection existed three times (`use_main`
on the bridge, the console and the flight panel); and each window ran its own
QTimer with its own `running` flag on the one shared `Conn`.

Measured, that came to: the drive armed on the bridge reading "off" on the
conn console — and a burn from the flight panel then firing the *clusters*;
"Stop clock" on one window beside "Run clock" on another, and pressing the
second arming a **second timer at double time**; the Pilot screen's autopilot
row calling the computer again for a fresh forecast one beat ahead of the
ship; and the approach plot saying *"coasting — the computer has not got it"*
while a Pilot-screen "Run for X" was burning.

**The armed state is four fields on `Conn` now** — `auto` ("" | "null" |
"close" | "orbit" | "run"), `arm_main`, `clock_on`, `mark` — and every window
reads them through properties, exactly as `conn` itself is read.
`freeflight.computer` is the one dispatcher a beat asks (it also keeps its
hands off under a tug, which used to be fought every tick), `freeflight.can_arm`
is the gate every mode button greys on (so `close`/`orbit` can no longer be
armed against open space and coast forever, lit), and `instruments.readout`
finally has a "Computer" row, because the sim can now see the mode it flies.

**One clock: `MainWindow.flight_timer`,** in `ui/flight_clock.py`, at the
bridge's 250 ms beat. Every Run/Stop button calls `set_conn_clock`; `fly_beat`
steers, flies one tick, bills through `berthing.charge_flown`, and refuses to
beat under a live battle — which the per-window clocks never did. All three
windows' manual burns bill as they fly now; before, an hour flown from the
Conn window left the stardate untouched. And the beat redraws through
`beat_refresh` (HUD + flying windows), not `MainWindow.refresh` — which
matters because of what the autosave gate turned out to be doing.

**Five defects fell out of the same measurements:**

- **The whole sector was saved to disk on every repaint.** With the default
  `autosave_days` of 0, `since >= every` read `0 >= 0` — true on a calendar
  that had not moved. Measured: five refreshes, five full saves, ~30 ms
  apiece, under every button in the game. That was most of the "sluggish".
- **The Flight-controls window was blind unless the Conn window was open.**
  It read `win.conn_window.conn` with a fallback (`win._flight_conn`) that
  nothing in the repo ever wrote. It reads `win.conn` now, like everything.
- **A hand-over from alongside opened *inside* the structure.** A moored
  hull's position is its structure's, so the offset arithmetic in
  `freeflight.hand_over` came out 0.000 km and the first press logged
  "Struck Fleet Hub coming in". Inside the radius plus the alongside margin
  it keeps `begin`'s opening range — casting off, not materialising.
- **Retargeting refunded the flight.** `_pick_target`, `_free_flight` and
  `_reopen` replaced `game.conn` after a `_settle()` that returns early for
  a live approach, so the mass already burned went back into the tank; a
  clearance refusal even wrote the `None` straight over a live flight and
  filed the reason in `self.refused`, which nothing read. `conn_moves.py`
  holds the rule now: every swap bills first, a refusal keeps the old
  flight flying and says why, and a live free flight is *handed over*.
- **Point defence bit 120× harder at a world than at a quay.** The
  approach-control ladder and `ward_bite` ran once per *substep*, and
  `_substeps` cuts a minute into up to 120 slices near a body. They run on
  the tick now, where a minute is a minute.

**And the ledger is exact (#148, #149 closed).** Reaction mass is billed as
it burns — `charge_flown` keeps `conn.charged_rcs`, the mass twin of
`charged` — and `commit` takes only the remainder, exactly: securing used to
charge `round(spent, 2)` and refund up to 0.005 t, and a flight nobody ended
was never charged its tonnes at all. Transfers close the last door:
`berthing.secure_underway` is called by both `transit.begin` and
`flight.travel_to`, so a leg flown mid-flight secures and bills the conn
instead of teleporting the hull out from under it.

**Naming (#153 closed):** the camera rows say "Look fore" … "Look to port"
was the shape of the fault — "Port" was both *look to port* and *thrust to
port*, pixels apart, which is why every probe that found a button by its text
had been lying. Cameras say "Look …" now, one autopilot mode wears one name
in all three windows ("Hold station"), the main drive is "armed"/"off"
everywhere, and every flight control carries an `objectName`
(`cam_*`/`thr_*`/`auto_*`) so a check can address exactly one control.

Paying for the room: `sim/flight.py`'s recorded debt is off the ledger —
`sim/path.py` took the arc, the star's heat on it and the risk (`route`,
`hot_risk`, `_heat_risk`, `burn_heat` and their constants; `flight` imports
them for its own quoting, so the names stay reachable where their readers
are) — and the conn window's flight-swapping acts moved to `ui/conn_moves.py`
under the same rule as `ui/flight_clock.py`: methods in module clothing,
bound in the class body. `tests/test_flightdeck.py` pins the lot: nine
checks, from "one beat is one minute however many windows watch" to "a
structure's patience runs on the tick".

### The second pass: what the deck's own backlog measured out to

**The forecast is true through both doors now.** `flight.travel_to` has
applied arrival heat and rolled the quoted risk since the burn board was
built; `transit.finish` applied **neither**, so the same leg on the same
profile arrived at 42/50 heat flown instantly and stone cold flown watch by
watch. The transit stores the risk the helm quoted when it was committed —
recomputing at arrival would price a leg of zero length — and rolls it
through the same `_incident` door. And the orrery walks the hull along the
leg by watches stood, dashing what is still to fly: the recorded position is
the departure body until arrival, so the one thing guaranteed to be moving
was the one thing that never moved on the chart.

**The computer can fly into a bay.** Measured before: six of six `close`
approaches to a gestation shell ended in a **collision**, and a drum managed
three of six — `moorings.aim`'s hold point sits on the *berth's* line, and a
bay's berth is deliberately deep inside, so the corridor ran through the
shell. `bays.approach_aim` is the corridor law now: the hold point is on the
**mouth's axis** (the same hole `in_corridor` protects and the window
draws), the phase test is the corridor itself rather than a distance race —
the first draft handed over on nearing the hold point, and since point and
berth sit on different lines, closing on one opened the other and a 40 t
tank went dry shuttling between them — and a run that would chord the core
stands out to the bisector first. Measured after: **16 of 16 alongside from
every bearing on 1.0–2.1 t**, against 15–40 t and a mixed bag before.
`close` on another *hull* is refused with the reason (there is no fitting to
fly to); coming alongside a hull is hand-flying.

**The ground is an order a captain can give.** `sim/landing.py` has told
down, ditched and aground apart since it was written, and the order that
makes "ditched" possible was reachable only from a check. The conn console
carries **Put her down / Belay the descent** on body approaches, greyed with
`why_not` where there is no surface, quoted through `landing.quote` — which
is honest to the point of cruelty about arriving at orbital speed.

**The conn window stopped churning.** Its side panel was torn down and
rebuilt — every row, every label — on each beat; `ui/conn_panel.py` gives it
the Pilot screen's medicine (#150): `content` is the one door for the words,
`apply` updates labels in place on a beat and rebuilds only when the *set*
of things said changes. Measured: 18–21 ms a refresh down to **2.8 ms**.

**Two numbers that merely looked like one bug.** `engage.reach_km` was
literally defined as `freeflight.far_km()` — flying *advice* and gunnery
*reach*, coupled so a pacing retune silently rebanded every weapon; it owns
its number now, equal today, moved deliberately or not at all. And the two
ship masses are a **documented split, not a defect**: `thrusters.mass_tonnes`
is the handling mass the drives push, `impulse.ship_mass` the registry mass
a collision weighs, and across the fleet they differ by up to six orders of
magnitude (a LEVIATHAN is twelve billion tonnes in the registry and 8,500
in the hand) — fly the registry mass and the big hulls never move; collide
the handling mass and ramming means nothing. The same shape as `radius_km`
against `bays.hull_km`, made on purpose where it used to be an accident.

### The third pass: the engines are held, the clock is everywhere

**"The engines seem to work in steps, with instantaneous responses."** They
did: a press was one impulse — `apply` adds the whole burn's Δv between two
frames, then coasts. The pads are **press-and-hold** now, through one pair of
doors (`flight_clock.start_burn` / `end_burn`, `hold_wire` on every pad): a
held button or key (W/A/S/D, R/F — `ui/flying_keys.py`) is a standing order
the beat consumes minute after minute, so velocity *builds* and the plume
stays lit on the flight-control diagram for the burn's true duration. A quick
click is still one precise tick; with the clock held it keeps the old
coast-and-quote exactly, which is why every promise-is-the-act check passes
unchanged. The order outranks the armed computer for the beats it stands —
a hand on the stick is a hand on the stick.

**The clock is universal.** Walking to the Helm no longer stops it (the old
`PilotView.leaving` stop is gone); the HUD wears a "CLOCK RUNNING ×N" chip
readable from every screen; the helm carries Run/Stop and the time scale
(`SCALES` ×1/×4/×16 — one multiplier, in the one beat, so the burn, the
computer and the bill scale together); and an engagement stops it the moment
it begins, whichever door the fight came through (`begin_combat` and the
`go("battle")` route both).

**And the window finally shows the flying** (`ui/viewport_hud.py`, drawn in
every camera): the predicted path under the current control state — the same
`preview.track` dry run the approach window plots, as dots shrinking with
time; **prograde and retrograde** marks, because the nose is not the
velocity; the **aim point** the approach is actually flying next
(`moorings.aim`); and a bay's **mouth as the ring it is**, on the axis
`in_corridor` protects — missing the ring is hitting the rim. The mark on
the bridge carries the engagement band when the guns could speak, off the
same `engage` doors the trigger uses. `points`/`draw` are split so checks
ask where everything landed without reading pixels.

The rest of the pass: brake-to-zero (a `"brake"` mode in
`freeflight.computer` that hands the conn back when she is still), one-button
computer docking from the helm (`Dock at <quay> — computer`), and a ninth
tutorial lesson, "Take the ship's wheel", watched through `game.conn_seconds`
— billed conn time, bumped in `berthing.charge_flown`, so a screen merely
opened counts nothing.

### The fourth pass: one computer, wearing the same bar everywhere

**"It isn't easy to turn the auto-pilot on from every flight-related
screen."** Measured, the player was being kind: the bridge offered two of
the five modes, the helm only a docking shortcut, and the approach window
none at all — each screen with its own private arming logic. And behind
that, the deeper split they named next: docking, berthing, moving away,
destination flying and orbiting spread across different controllers.

**`sim/flightdeck.py` is the one front door now.** `can_arm` is the gate
every autopilot button in the game greys on and `computer` the dispatcher
every beat asks; the *law* stays in `sim/autopilot`, the free-flight
mechanics in `sim/freeflight`, and no screen owns a private computer.
`flight_clock.arm_mode` is the one arming door in the UI — toggle, gate,
clock-start, refusal toasted with the reason — and `ui/autopilot_bar.py`
is the one bar: **Hold station · Brake to zero · Close and berth · Make
orbit · Move away · Run for <mark> · Manual**, the same labels, the same
`▶`, the same objectNames, on the Pilot screen, the Helm, the Conn window,
the Flight controls and the Approach window. Manual is always lit when
nothing is armed, so "is the computer flying" has one obvious answer and
one obvious exit — and a held thruster outranks the computer anyway.

**"Depart" closes the verb the system never had**: moving away was manual
or it was a transfer. The same computer flies her out past the corridor and
the arrival range, stops, says "Standing clear", and hands the conn back.
Docking wears three doors on the system screen — fly the approach yourself
(the mini-game, for standing), hand it to the flight computer (the same
`close` the bar arms, via `autopilot_bar.dock`), or let the harbourmaster
skip it — and the computer path is the same one the helm's "Dock at
<quay>" button uses.

**And destination flying has one executor.** The plotting board's *Engage*
called `flight.travel_to` — the instant transfer — while the helm flew
`transit`: two interplanetary autopilots, chosen by which window you
pressed. The board hands its course to the same watched crossing now;
`travel_to` remains the programmatic door (`ensure_at`, local work), with
the same quote, heat and risk since the second pass.

### The fifth pass: flown rigorously, and three things fell out

The brief was to *play* it — every goal, from every window, by hand and by
computer, and to find what breaks. Three real defects came out, none of
which any suite could have caught, because no suite had ever pressed a
control in a pop-out window: `tests/test_verbs` sweeps the thirteen
standing screens and had never touched the conn, the flight panel, the
approach view, the plotting board, the tactical station or the gunner's
seat. `test_flightops` sweeps all six now, on a flight of every kind.

**Taking the conn on a world you were orbiting was not a flight at all.**
Measured across seeds, **8 of 11 body approaches opened already finished**:
`outcome.resolve` saw a hull in a sound orbit on the first tick and wrote
"orbit", so the pad was dead, every mode was dead, and there was no way to
change height, descend or depart. An outcome is what a flight *achieves*,
not the state it began in — `Conn.opened_orbiting` records the orbit she
arrived in and `resolve` clears it the moment she is out of one, so a real
manoeuvre re-arms the ending. Flying *into* orbit resolves exactly as it
always did, and `autopilot.fly` now writes the mode it is flying onto
`Conn.auto`, because a computer nothing can see is how this drifted.

**"Move away" flew the ship into the planet.** The mode demanded a radial
velocity, which in a gravity well asks the drive to cancel the entire
orbital velocity — measured at a world, **2,779 m/s of it** — so the hull
decayed and went `aground`. In a gravity well, moving away is *climbing*:
`depart` picks the lowest rung the ladder will sell above where she is and
flies the orbit law that `test_climbs` holds, and where the ladder sells
nothing it refuses with the reason and points at the height picker and the
helm. Measured after: no departure grounds, and a climb under way is not
re-asked of the ladder every tick (that abandoned the climb halfway up).

**A held thruster could outlive the hand holding it.** Qt sends no
`released` to a widget that no longer exists, so a rebuild mid-hold — or
walking off the bridge with a key down, or closing the window — left a
standing burn order and *the ship burned with nobody holding it*. Every
door that can take the control away now closes the order through
`flight_clock.end_burn(quiet=True)`, which still honours the press if no
beat has taken it.

What the sweep found *sound*, and now checks: berthing at a quay under the
computer from all five surfaces and by hand from all three pads; orbit
mode and the height rungs; running alongside another hull (and `close`
refusing one, with the reason); departing a structure; a crossing flown
watch by watch from the helm and from the plotting board, arriving with
its heat; berthing then disembarking to the port; landing a party once a
body is surveyed; opening fire from the bridge, the clock stopping the
instant the fight begins, and the gunner's and tactical stations painting
through it.

### The sixth pass: a curriculum, not a nag bar

The tutorial was nine lessons in a flat list — enough to stop a new captain
drowning, not enough to teach the game. It is **twenty-nine lessons in ten
courses** now, and the courses are scenarios: *First light* (the screens and
the ship), *The wheel* (flying by hand and by computer, and getting
alongside), *Bread and salt* (prices, selling, fuel), *Looking closely* (the
four ways of surveying, and the bench), *The long crossing* (burns, watches,
a jump), *Rock and ice* (a seam, a trench, a landing party), *Iron* (marking
a hull, and opening a fight at a band you chose), *Roots* (a colony, and
reading what it costs), *Powers* (the two axes of opinion), and *The long
game* (a yard, a refit, work, and the record).

**The rule that shaped the first nine still holds: it must not take your word
for it.** Every lesson names a watcher in `sim/tutorial_watch.py` that reads
the *world* against a mark taken when the lesson opened. Where a deed leaves
state behind, the watcher reads the state — a body newly surveyed, a quay
stood at, a colony planted, a technology unlocked, a power warmer than it
was. Where it leaves none — flying under the computer, standing a watch,
working a seam or a trench, putting a party down, opening fire — the *sim
function that performs the act* records one flag through `tutorial_watch.deed`,
never a screen, so a button that refuses records nothing.

**`ui/academy_panel.py` makes it a menu.** A curriculum you can only take
from the beginning is one most players abandon at lesson three, so the
Academy tab under Help lists every course, what it teaches, how much of it
you have done, and a *Teach me this* button — `tutorial.jump_to`, which also
steps over anything you can demonstrably already fly. And the manual gained
four pages about playing *well* rather than about what things are: your
first hour in order, making money, flying her well, and fighting (or not).

Three checks changed shape with the curriculum and none lost its teeth: the
veteran check now asserts the orientation course is stepped over on a
demonstrable career (`have_played` wants prices, a survey *and* a second
star, together); the settling-in bracket and the mark check jump to the
course they are about; and `tests/test_tutorial` performs all twenty-nine
lessons in order, which is what stops a lesson being added that nothing can
actually do.

### And the crash that only a full run could find

The suite came back **exit 134 with zero failures** — 171 suites green and
the process dead. `ui/painting.py` was written for exactly this ("a paint
that cannot begin, or dies mid-frame, is recorded in `MISSES` rather than
killing the process from inside `paintEvent`") and **only the widgets that
inherit `Painted` were ever protected**: thirteen others build their own
`QPainter` and draw. Late in a long run the approach view's painter was live
at the top of a frame and invalid by the time it drew a label, and the
`TypeError` PyQt raises for a dead receiver escaped `paintEvent` and took Qt
down — reported a hundred lines from the cause, as an argument-overload
error listing seven `drawText` signatures.

Both halves of the guard are general now: `painting.alive(widget, painter)`
for the painter that never began, and `@painting.safe_paint` for the frame
that dies part-way. All thirteen raw painters carry them. A picture that did
not happen belongs in `MISSES`, where the checks that care can read it, and
nowhere near the process exit.
