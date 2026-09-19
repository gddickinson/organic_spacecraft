# What this is — the design, pass by pass (8 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

### The seventh pass: contact is allowed, and it has to be meant

**"Have the auto-pilot attempt to prevent collisions when it can."** It could
not: the only thing in the game that knew about contact was `sim/outcome`,
which decides it *after* it has happened. A captain could fly a hundred
metres a second at a Fleet Hub with every screen reading calmly and learn
about it from the wreck, and the computer — armed and flying — would help.

`sim/collision.py` is the one door for "are we going to hit that", and it
asks three questions in the order a pilot does. **What is in the way**: not
only the target — `Conn.sky` carries every world, quay and hull placed in the
approach's own frame, and a ship crossing a system passes plenty of things it
is not approaching. **How long have we got**: range to the *solid* part
(`bays.hull_km`, not the bounding sphere) over the closing rate. And the one
that matters — **can we still stop**: `v²/2a` against the room left, on the
thrust the hull actually has, because that answer goes from yes to no while
every other number still looks calm.

Measured on a hull running for a mark with something in the path: at 60 km
**clear** and nothing is said; at 30 km **watch** — a warning, though the
brakes would cope; at 20 km **imminent**, and there the armed computer burns
*away* from the hazard (−0.97 along the bearing) instead of the burn its mode
wanted. That is the whole of "calculate the braking so it does not drive you
into something", and it works under every mode because it sits in
`flightdeck.computer` above all of them.

**None of it stands in the way of a captain who means it.** `Conn.safeties`
is one flag, off by a button on the conn console and the flight panel, and
with it off the computer flies its mode into whatever it likes. The
deliberate orders speak for themselves without touching it: an ordered
descent (`landing.ditching`), a cut into a berth (`forcing`), and a hull
inside a bay's corridor are contact by invitation, and the guard is silent
through all three. Flying by hand stays as dangerous as the pilot wants —
the one thing refused, and only with the safeties on, is a burn that drives
her *harder* into something she can no longer stop for, and the refusal says
so in words and names the switch.

The warning is where a pilot is actually looking: a `Collision` row on the
instrument panel every console reads, a ringed and named box in the camera
view (`viewport_hud`), and a line in the log the first time the computer
takes over. `tests/test_collision.py` holds the five claims.

### The eighth pass: the guard was omniscient, and a cloak fixes that

The guard shipped reading `Conn.sky` directly — a perfect, noiseless list of
everything in the system. So a hull with the cheapest array got exactly the
warnings a VESPER Organ got, and a raider that `sim/traffic` has described as
an "Unmarked hull — no transponder" since the day it was written was tracked
as precisely as a lit quay. The game had a sensor rating doing real work at
sector scale and nothing at all at the scale where a collision happens.

**A signature is one number, and everything downstream is a multiplication.**
`data/countermeasures.py` states what a thing puts out as a share of a lit,
transponding hull: `LOUD` 1.00, `DARK` 0.28 (no transponder, cold hull — the
raider's trade, and it costs nothing but the squawk), `SHROUDED` 0.10 (chaff
and a plasma shroud; costs power and mass, so it is a decision about a
voyage), `CLOAKED` 0.035 (alien work — nothing in the Concordat's catalogues
does it). Which one a hull is running comes from its errand and a stable hash
of its id, so the same raider is the same raider every time you look, and two
screens asking the same question get one answer.

`sim/detection.py` turns that into kilometres against the looking ship's own
array: `SENSOR_KM = 4,000` km per light year of rating. It answers two
questions, and they are different. **Is it seen at all** — a world, a star
and a quay are not detection problems (a planet subtends degrees; a quay
squawks because being found is its job), so `always_seen` gives them infinite
range and a guard that could lose a planet is one nobody would believe about
a raider. **How well is it seen** — a contact at the edge of the envelope is
a smear, and `Track.quality` falls off as `1 − (km/reach)²`.

**Poor tracks are read pessimistically.** The guard inflates a closing rate
it cannot trust and shaves the room it thinks it has, so a bad array warns
early and loudly rather than late and precisely. Measured: the same rock at
400 km reads 200.0 m/s on a superb array and 257.9 m/s on one barely holding
it, and the board says *estimated* next to the number.

The number that decides whether any of this matters is not the range but the
**stopping distance**. On the opening hull's 4.2 ly array a transponding hull
shows at 16,800 km, running dark at 4,704, shrouded at 1,680 and cloaked at
588 — and at 300 m/s she needs 1,019 km to stop. So *a cloak beats your
brakes before it beats your eyes*: everything else is seen with room to
spare, and the cloaked contact is the one that is on you. That is the whole
point of a cloak, and it is now a fact of the flight model rather than
flavour text. `tests/test_detection.py` holds the seven claims.

One of them exists because *playing* the game found what the suite could not.
The roll that decides which raider carries which countermeasure was keyed off
the builtin `hash`, and Python salts that per process: the same hull came up
cloaked in one session and dark in the next, so a reloaded chronicle was a
different sky. Nothing inside a single run can see that, which is why the
check spawns three interpreters and compares. It rolls off `core/rng.hash_seed`
now — the generator that exists precisely so "a saved seed always grows the
same sky" — and the roll itself moved out of `data/countermeasures.py` and
into `sim/detection.py`, because a table states odds and a rule applies them.

### The ninth pass: every orbit was the same orbit

A player looked at the plotting board and said *every object in the system is
orbiting the sun in the same way*. That was exactly true, and it was not a
drawing fault. `flight.position` read one element — the radius — and returned
`r·cos θ, r·sin θ` for it, so every body in every system ran a **circle**, in
one **shared plane**, all the **same way round**. There was nothing else to
draw.

`sim/elements.py` gives an orbit the other five elements. **e** makes it a
shape, so distance from the star varies over the year and a transfer's cost
depends on *when* you fly it. **i** tilts the plane, and past a right angle
the body runs the other way — so "different directions" is that one number
rather than a flag beside it, and a retrograde orbit cannot get out of step
with its own inclination. **Ω** and **ω** place the tilted ellipse. **M₀** is
what `flight._phase` already was.

**Nothing is stored.** `data/orbit_shapes.py` states the range each kind of
body keeps and the elements are drawn off `rng.hash_seed` of the body's own
identity — the idiom `_phase` was already using — so a chronicle saved last
week grows real orbits the moment it is loaded, with no migration, and two
screens cannot roll differently. Every bound in that table is a real body:
Mercury (e=0.206, i=7.0°) tops the rocky range, Jupiter (e=0.049, i=1.3°) the
giants, Pluto (e=0.249, i=17.2°) the icy ones, Pallas (e=0.231, i=34.8°) the
rubble, and Halley (e=0.967, i=162°, retrograde) makes the comet range look
timid. Measured across 787 bodies in five galaxies: eccentricity median 0.103,
inclination median 4.8°, 3.8% of everything retrograde — about half the comets.

**The degenerate case is exact.** At `e=0, i=0, Ω=0, ω=0` the solver returns
precisely the circle the old function did, to 5×10⁻¹⁵ AU. A flat orbit is a
*value* in the new model rather than a second path through the code, which is
what made it safe to change every caller at once.

`position` returns three numbers now, and the change reaches everywhere a
position goes: `separation` and `distance_to` are `math.dist`; `path.route`
still bends a course around the star, and the geometry generalised untouched
because the closest point on a segment to the origin does not care how many
axes there are — only the degenerate "dead through the star" case needed
thought, since a plane has one perpendicular to a line and space has a circle
of them. The conn's sky is no longer flat: `sky.offset` used to end `, 0.0`
for everything, and a world on a steep orbit was drawn level with the hull
however far above the plane it stood.

Two docstrings that described limitations got to retire. `freeflight.where`
dropped `z` "because the sector is a plane and always has been", so a captain
who spent a whole flight climbing ended up where they would have without the
climb; and `freeflight.toward` returned a zero third component for the same
reason. Climbing is now how you reach half the system.

**Hulls go round too, and about half of them the other way.** A ship holding
station sat at one fixed point beside its world for the life of the chronicle.
Now each walks its own circuit at its own tilt. The first draft gave them a
real Keplerian period off the body's `mu`, which is honest physics and
unplayable — six thousand kilometres off a rocky world is about five
*kilometres* a second, and a conn closes at tens of metres a second, so
rendezvous broke outright and the computer arrived alongside still doing
16.5 m/s. A hull holding station is *under power*; it walks a slow circuit at
a speed a visitor can match, and `traffic.STATION_DRIFT_LO` says so. A hull
genuinely falling round a world at orbital speed would be a different errand
and would need matching orbits to reach.

### One order, from open space to lines across

**A run stopped fifty kilometres short of the thing it was sent to.**
`freeflight.alongside` is open-space alongside — no berth to touch and no
structure to stop against — so the computer said *"Alongside Fleet Hub, 50 km
off"*, handed the conn back and held there. A player found the other half of
it: having arrived, the autopilot would not move anywhere, because as far as
it was concerned the order was finished.

Everything needed to finish already existed and nothing joined it up.
`freeflight.hand_over` turns a run into an approach keeping the way on;
`clearance` asks the structure which berth it has assigned, where to hold and
what rate it may be crossed at; `moorings` flies the hull to that fitting; and
`tug` sends boats out to walk her the last stretch for nothing at any port of
level 2 or better. `flightdeck.berth_from_here` is the join, and it only fires
where the structure will actually have her — a refusal leaves the run ending
exactly where it used to, with the words to say why.

**Then the boats turned out to be the danger.** A tow drew the hull along a
straight line to the berth from wherever it caught her, and the boats come out
as far as `TUG_REACH` of the opening range. From the twelve kilometres an
approach normally opens at that line is harmless; from a run handed over fifty
kilometres out on whatever bearing the ship arrived on, it goes *through the
structure*. Measured: cleared, under tow, granted mast 4, walked onto the
plating 579 m short of it at nought metres a second, the log reading "the
frames took it" — a collision at zero speed, performed by the harbour.

`tug._walk` puts the tow on the same two-phase discipline the flight computer
is held to: while the straight line would cut inside the keep-out sphere the
hull is swung *round* it at the radius she has, and only run in once the line
is clear. Two things had to be got right and each was found by a check rather
than by reasoning. The guard may never exclude the destination — at a hub
whose hold point is 444 m out against a 448 m sphere it forbade every route
and froze the tow for 2,100 beats while the station turned 136° underneath
it. And a hull on the *far side* is exactly anti-parallel to its berth, which
is the case the guard exists for, so falling back to a straight line there
towed her through the middle: 12 m from the centre of a 400 m hull. There is
a whole circle of ways round; it takes the one square to the axis she is
least parallel to, the way `sim/path` picks a way round a star.

Measured across eighteen chronicles: **eighteen berthed, none lost**, from
490–2,800 km out, arriving at a named fitting with 8.1–14.2 t of a 20 t tank
still aboard — the tug's own drive doing the last stretch, which is the whole
of why being cleared is worth having.

**A quay was at the centre of its own planet.** A player reported two things
as one: *"I tried running to Fleet Hub and the auto-pilot wouldn't move
anywhere, and Fleet Hub could be seen in every view at the same distance in
every direction."* Both halves were the same fault. An anchorage's position
*was* its body's — the class docstring said so — so from that world the range
to it was **0.000 km**: the flight computer read zero, correctly concluded it
had arrived, and did nothing; and a target at zero range subtends 180°, which
is exactly the picture of being inside something. Three places had already
worked around it — `orbit_chart` seats quays apart on screen, `sim/sky` lifts
a co-located sight 400 km clear so it does not stack, and the docstring
admitted it — while the sim itself had no answer, which is the two-doors
fault this project has paid for more than any other.

`anchorage.berth_orbit` gives a quay a real place in orbit of its world,
derived from its own id and never stored, the discipline `traffic` uses for a
hull's station and `elements` for a body's orbit. Fleet Hub now stands 2,067
km off its world, and running for it is a manoeuvre: 606 beats and 8.7 t of
reaction mass to come alongside.

**"Ahead" could not point up, and that is what a flat sector had been
hiding.** `Conn.heading` is one angle about the vertical, so the direction a
pilot calls ahead was confined to the orbital plane; `freeflight.steer`
computed `atan2(-dx, dy)` and threw the third number away. Free while every
orbit lay in that plane, and wrong the moment they did not. Measured on the
flight deck: a course laid on a hull **15.4° above the plane** left the nose
15.4° off it, and five hundred burns on the torch closed 5,952 km to 1,514
and sailed past. `Conn.pitch` is the second angle, `rotate` takes both, and
the same run now closes to **14 km**. At `pitch=0` the arithmetic is the
yaw-only formula it replaced to the last bit, which is what let every caller
gain the angle at once.

**It took the process down again, the same way.** A route leg is three
numbers now and one chart still unpacked two, which raised `ValueError` inside
`paintEvent`. `ui/painting.safe_paint` — written after the *first* time a
paint error killed the run — caught `RuntimeError` and `TypeError`, being the
two that had been seen, so this one escaped: exit 134, 151 of 186 suites
green, nothing failing. A guard whose job is "a bad picture must not be fatal"
cannot be a list of the exceptions met so far, and it is not one now.

**Six cameras do not cover a sphere, and now it shows.** They sit on the six
axes with a sixty-degree field, which leaves a blind cone between each pair —
invisible while every orbit lay in one plane, because anything you laid a
course on was near the ring of the four side views. Measured after the tilt
arrived: a mark 35.7° out of the plane landed 51°, 54° and 59° off the three
nearest axes and was ringed in **none** of the six windows. A course laid on
something no camera will admit exists is worse than no course, so
`viewport_mark.draw` now puts a chevron on the frame pointing the way to turn
when the mark is in front of the lens but outside the picture.

The same tilt shows in what the flight computer says it is doing. One run,
narrated: *coming about to burn → ahead on the torch at 62% → **up on the
torch at 62%** → ahead on thrusters → down on thrusters → astern on thrusters
→ coasting → holding station*. The third of those is the third dimension.

`tests/test_elements.py` holds the seven claims.

### The tenth pass: the systems layers answer for themselves

A four-agent review (combat, economy, strategic layer, player experience)
measured everywhere the nine flight-deck passes had not, and the worst of
what it found was fixed the same day. The full findings and what remains
are in `IMPROVEMENTS.md` ("the 2026-08-04 review"); the shape of the fixes:

- **A dialog's None is a refusal, never a choice** (`ui/window_dialogs.py`)
  — Escape at the ending used to run `clear_save()`. And `go()` refuses an
  unknown screen before hiding anything: two manual topics naming
  non-screens could brick the window for the session.
- **The same counter never pays more than it asks** — an invariant clamped
  at both price layers (`world/economy.sell_price`,
  `sim/market.quote_sell`) rather than a repaired coefficient, because the
  exploit was two independent modifiers crossing (trade skill, the grudge
  bias) and the next modifier would have crossed it again. 18,000 → 2.6M
  credits on day 0, closed.
- **A posting is fed by bringing material in** (`Contract.bought_here`),
  a delivery completes from the hold, and the board turns over on the
  harbour's clock through `contracts.board_for` — the board was built in a
  UI module, which is *why* nothing in `sim/` could ever have aged it.
- **The Bloom's stage rides what it has answered**
  (`data/bloom.STAGE_BY_ANSWERS`) as well as the burden, so the antagonist
  — adaptation, roaming instars, the hunt — is met by the captain who
  fights it rather than only by the one who ignores it for three years.
- **Sensory interference saturates** (`combat.DAZZLE_CAP`), and the enemy
  plays a real seat a turn through the same arc test as the player
  (`sim/enemy_ai.py`), so fights are decided on the plot rather than by
  whether a 3,400-credit flash organ is fitted.
- **Diplomatic cooldowns key on the work** — the pair brokered, the power
  denounced — not the seat the order came from.

`tests/test_ui.py`, `test_counter.py`, `test_cargo.py`, `test_postings.py`,
`test_bloom_arc.py` and `test_overtures.py` hold the claims, all of them
played rather than quoted.
