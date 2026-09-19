# What this is — the design, pass by pass (2 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

**Flying is done in days and AU; berthing is done in metres a second.** The
helm moves the ship body-to-body: pick a target, pick a burn, lose a week of
calendar, arrive. That is the right grain for a transfer and no grain at all
for the last ten kilometres, where the only question is whether you can match
velocity with something before you hit it. Nothing in the game modelled that.

Three modules, and two pop-out windows, do now.

`sim/track.py` makes everything in a system a `Contact` whose position is a
function of the day — bodies, quays, traffic, and a bare point in empty space
you simply want to be at. Because position is a function of the day, a track
runs *backwards* as well as forwards, and a burn can be solved for an arrival
**date** rather than only for "as soon as possible". `windows()` sweeps the
horizon, because a moving target is not equally dear on every day and waiting
is often cheaper than burning. Every cost comes back through `flight.route`
and `flight._leg`, so a plot cannot disagree with what flying charges; for a
body, `solve` *is* `flight.intercept`.

How much of that can be believed was measured rather than asserted. Over 735
predictions across ten chronicles, four systems and horizons out to 270 days,
**99.9% came true to the digit** — `traffic.in_system` is pure in the system
and the day, so asking it about a future day *is* the forecast. Every failure
was the Bloom crossing a threshold in `traffic` (0.15, where raiders can draw;
0.2, where a system loses a hull) and redrawing the errands. So `confidence`
is causal: it projects the growth forward and asks whether a crossing falls
before the arrival, rather than decaying with time for its own sake.

**A captain may take the conn whenever they like.** Every manual control hung
off an approach *to a thing*: `berthing.can_conn` wanted a contact and said so
— "a position in empty space is somewhere to steer for, not something to come
alongside" — so the six axes, the main drive, the cameras and the 3D windows
could only be used while arriving somewhere. Between structures, movement was
the plotting board, which is plotting rather than flying. Reported by a player,
and they were right.

`sim/freeflight.py` is an approach with **no target**: open space, at the
ship's own position, with the hull at the origin of its own frame. Everything
downstream keeps working because it is still a `Conn`. Two things make it real
rather than a screensaver. It **moves the ship** — `secure` writes where she
drifted to through `flight.stand_off`, the one door #103 built, so the
kilometres flown are kilometres moved on every screen that plots the system —
and it is **charged for**, through `berthing.commit` like any other approach:
the mass, the hours, and a line in the ledger that says what it was rather
than calling it a broken-off approach. Nothing ends it but the pilot, which
needed saying in `sim/outcome`: a free flight opens at zero range against a
target of radius zero, so every arrival threshold is true at once and the
first tick reported the ship as having struck open space. `hand_over` turns
one into an approach to something while keeping the way on, so flying by hand
and then giving the computer the last of it is one approach rather than two.

**Four powers, four laws, and no police force.** The governance layer's one
rule is that a law is only as long as the arm attached to it. `dockets.witness`
returns how well a power can know what happened in a system — from its quay,
its register, its hulls on station, or a friend with one of those — and
returns 0 for a power with nothing there, at which point nothing is recorded
at all. Being unobserved is not innocence and is meant to feel different.

The four forums are deliberately not comparable, and each is drawn from what
`data/factions.py` already said that power was. The Charter fields no armed
vessel and never will, so its law is paperwork and its whole armoury is
refusal — no clearance, no licence, no gate. The Concordat thinks in property
and has hulls to collect it with. The Freeholds have no forum at all: a claim
is a price on your hull, posted and sold on, and they are the only power that
ever hunts the player. The Dry Choir holds no hearing because there is nowhere
to stand, and what it imposes is anathema — the network stops answering.

Two traps, both sprung during the build and both worth knowing about. **The
law must never re-enter itself**: a patrol that charged the captain two days
with `advance_days` ran the clock, which ran the law, which stopped the
captain — surfacing as a `RecursionError` three modules away in
`settlement.maturity`. And **the process must not generate its own work**: a
default charge decided in absence produced another, whose debt produced
arrears, which was also decided in absence, reaching 61,820 charges and ₡498
million from one contraband bust inside eight years. `Offence.procedural` and
`dockets.PROCEDURAL_DAYS` bound it; what escalates is the instrument, through
`tribunal.severity`'s count of priors, not the paperwork.

**Where the ship is, and which frame the answer is in.** This is the fact the
project has got wrong in the most ways, so it is worth stating plainly. There
are two questions and they have different answers:

- `flight.base_position(game)` — the **recorded** place. A body id, or
  `game.ship_xy`. Written by exactly two functions, `flight.hold_at` and
  `flight.stand_off`, and by nothing else.
- `flight.ship_position(game)` — where she is **now**: the recorded place plus
  `Conn.flown_km`, the flight in hand. This is the one door every screen
  reads, and it is the one to ask unless you specifically want the other.

Two traps live here, both of which have been sprung. The first: the recorded
place is not written again until `berthing.commit`, so for the whole of a
flight it is *stale by however far the ship has been flown* — which is why the
helm's map, the plotting board and the tactical list once held a hull at the
quay it left while the conn beside them counted the range down. The second is
subtler and cost a rewrite. **`conn.pos` is not an offset from the ship.** An
approach's frame is anchored on its *target*, and `conn_open.start` opens it
at a canned arrival range, so `conn.pos` is already twelve kilometres the
instant the conn is taken and says nothing about where the hull is. The
quantity that is honest in an approach frame and a free one alike is the
difference from where the frame started — `Conn.start_pos`, and the
`flown_km` built on it.

The invariant that keeps the two consistent: **whoever writes the recorded
place spends the flight into it** (`flight._flight_spent`, called by both
writers). Without it a hull moored by `berthing.commit` read 473 km from its
own quay, because the place accounted for the flight and `ship_position`
added it again on top.

`sim/conn.py` is the close-quarters frame — kilometres, metres a second, and
a minute a tick. Reaction control for fine work, the main drive for closing
distance, `mu` taken from the body's own `radius_km` and `gravity` so a heavy
world genuinely demands a faster orbit. `sim/autopilot.py` is the computer
that flies it, split off along a real seam: `conn` says what the ship does
when you fire a thruster, `autopilot` says which thruster a competent pilot
would fire.

Four faults, all found by flying rather than reading:

- **The closing rate was wrong by a factor of a thousand.** `pos` is in km and
  `vel` in m/s, so `pos·vel / r` is already a velocity; the first draft
  divided by another thousand "to convert". The panel read **+0.01 m/s while
  the ship flew in at twelve**, the autopilot believed it, and every approach
  ended in the hull. A unit test on `closing` would have seen a plausible
  number and passed.
- **The computer managed the closing rate and ignored the rest of the
  velocity.** Motion across the line of sight does not change the range at
  all, so it reported itself perfectly on profile while sailing past — it hung
  at 1.7 km circling a hull, or went into a quay sideways at 12 m/s.
- **A body approach opened twelve kilometres from the planet's centre**, which
  is several thousand underground; `mu / r²` there threw the ship out of the
  system at eleven thousand kilometres a second.
- **The orbit band was a percentage.** A tenth of circular is 500 m/s at a
  middling world — forty burns — and wider than the whole orbit at a rock.

`ui/viewport.py` paints what a camera sees: six of them, and the target's
angular size *is* the range instrument, read the way a pilot reads a window.
The starfield is fixed at import, because a field drawn from `game.rng()`
would both shimmer between repaints and quietly advance the save's seed — the
docking instrument was bitten by exactly that. `ui/conn_window.py` is the conn
itself; `ui/plot_canvas.py` and `ui/plot3d_window.py` are the plotting board,
with zoom, pan, tilt, selection, tracking, and an arrival-date slider.

**And then it had to actually happen.** The conn shipped as a sandbox. Asked
this project's most productive question — *is everything it declares
consumed?* — the answer was nothing at all. Measured on a fresh chronicle:

    flew into Fleet Hub at 20 m/s  ->  collision, damage 50.0
    berthed alongside              ->  0.54 t of reaction mass, 0.8 h elapsed
    day 0 -> 0 · fuel 20 -> 20 · hull 336 -> 336 · where None -> None

You could wreck the ship against a station and walk away, berth alongside a
quay and not be docked, and burn a tank the hull never had — the conn invented
36.8 t of reaction mass for a ship carrying 20.

`sim/berthing.py` is where it lands. The tank is the ship's `volatiles`;
`commit` charges what was spent, advances the clock, applies the damage, and
writes `orbit_body` — which is what every other screen reads to know where the
hull is standing. It is idempotent and is called when the approach resolves,
when the captain breaks off, and when the window closes, so nothing is ever
flown for free. `can_conn` is the gate: measured, the distance from the ship
to a contact is bimodal — **0.000 AU at your body, 2.2 AU or more otherwise** —
so the threshold sits in empty space and the check holds the rule rather than
the number.

Wiring it up surfaced two more, both from playing:

- **Impact damage was linear and capped at 80**, so lithobraking into a world
  at five kilometres a second cost sixty points of three hundred and
  thirty-six. Energy goes as the square of the speed and so does the damage
  now, uncapped — 8 m/s is a scrape, 20 m/s takes half the hull, 45 m/s ends
  the chronicle.
- **A fast approach passed straight through its target.** At 45 m/s the ship
  crossed 2.7 km in one 60 s tick and went clean through a station 400 m wide
  between two contact tests — reported *adrift*, no damage. Since the curve is
  quadratic, the most dangerous approaches were precisely the ones escaping.
  `_sweep_min` tests the whole path now, not its endpoints.

**Docking is granted, not taken.** Berthing was something the *ship* worked
out: `sim/moorings.py` read a table of fittings, picked the nearest and flew
at it. Nobody ever asked the quay whether it would have you, so a hostile
patrol and a Charter Fleet Hub offered the same welcome — none, because
neither was asked.

`sim/clearance.py` moves the authority to the structure. A quay, a shipyard or
a hull that will take you **issues a clearance**: which berth it has assigned,
where that berth is and how fast it is travelling, how long the structure
takes to come round, where to hold before the run in, and the rate it may be
crossed at. `berthing.begin` asks for one and a refusal stops the approach, so
there are two gates asking different sides — `can_conn` asks the ship (near
enough, any reaction mass, nothing already running) and the clearance asks the
structure.

Four refusals, each in its own words: a world is orbited rather than docked
with; a Weave gate is a relic with nothing to tie up to; a hostile hull "does
not answer, and is closing"; and a port whose power has turned against you
shuts the quay at `WELCOME_AT`. Writing that last one surfaced a gap —
`track.Contact` carried no faction, though `Anchorage` has had one since it
was written, so a port a power had turned against still waved every hull in.

A ship clears you for **the collar**: one hard point amidships, no masts and
no arms, and it does not turn. That is hull-to-hull docking through the same
door.

`moorings` stays the geometry and the clearance is the authority over which
fitting you get — and `test_clearance` holds them to the metre, because a
clearance that named one place while the flying went to another would be the
worst of both.

**A standoff berth is the second sort, and a different manoeuvre.** At a
fitting you arrive; at a standoff you hold still and the structure comes and
gets you. A holding's four gantry stubs are standoff berths: `berths3d.
STANDOFF` puts the berth 429 m out of a 400 m hull and `hinge_points` gives
the other end of the arm, so what the ship aims at is off the structure
entirely. `moorings.boom_step` runs the arm out over `BOOM_SECONDS` while the
hull is inside reach and steadier than `hold_rate` — `BOOM_STEADY` of
`ALONGSIDE_RATE`, 0.51 m/s — and back in the moment it is not, so the whole
content of the manoeuvre is station-keeping rather than a threshold to cross.
`outcome.alongside` also asks `moorings.captured`, so near and slow is not
moored until the arm has you, and `clearance.line` gives the standoff its own
instruction and its own rate rather than a fitting's. `viewport._boom` draws
it reaching from hinge to tip, amber while it travels and lumen once it has
you.

**Still to build, and named in `Clearance.sort` so the field means something
now rather than being widened later**: bays inside structures big enough to
fly into, with an aperture to pass through and a berth within.

**One hard sun.** The renderer lit everything with `AMBIENT = 0.40` — a
studio fill, not a star. Every shadowed face came up to the same grey, and a
Fleet Hub at 943 m read as a flat cutout: measured, the whole structure sat
between 20 and 215 with a median of 47, and nothing in the frame said where
the light was coming from.

Three things, and only together do any of them work:

- **`AMBIENT` 0.40 → 0.06.** Not zero: a hull is lit by the world under it and
  by its own running lights, and a face at pure black is a hole rather than a
  shadow.
- **`DIFFUSE` 1.05 → 1.40, so the sum stays where it was.** `ui/spheres.py`
  paints a world by this same law and a surface of 154 at `AMBIENT + DIFFUSE`
  must land under 255 — above about 1.65 the sub-stellar point clips and the
  whole lit half goes flat, which is the exact defect `test_lighting` exists
  for. So the change is not *more* light, it is light in **one place**.
- **Built things are painted bone white.** Dropping the fill alone did
  nothing — median 47 → 42 — because `_shade` multiplies a base colour and a
  dark base can never reach white however hard the sun is. The paint was the
  limit, not the light. It also draws a line the fiction has always claimed
  and never shown: a quay is *built* and a hull is *grown*, and they no longer
  look like the same material.

**And the smoothness check was measuring the wrong thing.** It bounded the
biggest jump between neighbouring pixels at 18 levels — but `AMBIENT +
DIFFUSE·cos θ` changes by **19.6 levels across one pixel under the constants
that bar was written for**, and 26.1 under a harder sun. The law was always
steeper than the bar; the renderer passed because seven gradient stops let Qt
interpolate linearly between them and flatten the curve. Chasing it turned up
the tell: the measured "step" grew monotonically with the number of stops,
8.9 at seven and 24 at sixty. The picture was smooth because it was wrong.
A facet is a *departure from the law*, so the check compares with the law —
span, and no flat run across the curve — and the gradient is sampled 48 times,
uniformly in screen radius, which is what a radial gradient is parameterised
by.

`test_cameras` had the same disease in a milder form: it counted pixels above
a brightness threshold, which was a fine proxy for "the target is in frame"
only while the fill light lifted everything. It renders each feed twice now,
with the target and without, and counts what changes — the nose loses 1,246
samples and every other camera loses **zero**, which is a far stronger claim
than the brightness ratio it replaced and does not care how the scene is lit.

**Showing the autopilot fly.** The computer has flown the ship since it was
written and nothing on any screen said so: a captain watching the conn saw six
identical buttons, no sign of which thruster was firing, and no indication the
autopilot was even on.

`Conn.fired_axis/fired_main/fired_share/fired_turning` are written by
`conn.apply` — **the burn that happened**, not a fresh ask of the computer,
which would be a forecast and would disagree the moment anything moved. Both
the conn's console and the flight panel light the control that fired off that
record, and the autopilot's modes light too. Arming it from either window arms
the one computer; pressing the running mode again turns it off, and so does an
explicit *Autopilot off*, so there is no way to be uncertain whether it is on.

`sim/thrusters.firing` says which mounts are alight, and **a thruster fires
opposite to the way the ship goes** — pressing *Ahead* lights the **aft**
cluster. `data/mounts.RCS_CLUSTERS` has carried each cluster's shove direction
since it was written and no screen had ever used it, so the game could say
"the forward cluster" and mean the one that slows you down.
`ui/shipdiagram.py` draws the hull with a mark at every mount and a plume on
the lit ones. `render3d.place` was split out of `draw` for it: a mark rotated
by a second copy of that arithmetic sits *near* the hull rather than on it.

`ui/approach_window.py` is the third view — ship and target together from
outside, with zoom, pan and tilt, because which way to look at a docking is a
question only the pilot can answer. The camera orbits **the midpoint of the
pair**, not the target: orbiting the target puts a ship twelve kilometres out
in a corner and leaves most of the window empty.

`sim/preview.track` draws the predicted course, and it is a **dry run of the
act**: a throwaway twin flown with the real `apply` under the real flight
computer. Checked by flying the real approach the same distance — 1,746 m
predicted, 1,746 m flown, exact rather than close, because it is the same
code.

**A berth is a place on the structure, and you can fly to it by hand.**
Coming alongside was a distance from a *point*: `range_km <= ALONGSIDE_KM +
radius_km` and slow enough, where `radius_km` is a bounding sphere. So a hull
that crept up on the far side of a Fleet Hub, nowhere near a mast, and
stopped, was moored — and the structure the window spends the whole approach
drawing had nothing to do with it.

`data/berths3d.BERTH_POINTS` says where the berths are, in the model space the
meshes are authored in and off **the same numbers the builders use**: a quay's
one arm ends in a warn-lit box and that box is the berth; a hub's four lit
masts are four berths; a holding has four gantry stubs; a gate has three
blocks on its rim. So a berth is a thing you can see. `sim/moorings.py` is the
sim side — the conversion into the approach's frame, which berth this approach
is for, and whether the ship is at it. The reach is a *share* of the
structure's own size (0.35), because a fixed tolerance in km would be generous
on a quay and meaningless on a gate; measured, it separates "alongside the
fitting" from "the far side" by 5× to 13× at every scale.

`moorings.aim` is the one door for where an approach is going, and both the
computer and the manual panel read it. Two phases: out to a hold point on the
berth's own line and clear of the hull, then in along it — and the handover is
on *reaching* that point rather than on crossing a radius. Both refinements
were forced by measurement: aiming straight at a fitting ran two of eight
off-axis approaches dry shuffling round a hub, and switching on radius alone
left a ship inside the corridor on the wrong side trying to crab round the
hull where `safe_rate` allows almost nothing. The berth itself is chosen
freely while there is room to change your mind and held once inside the
corridor — re-picking every tick chases a moving aim; committing at twelve
kilometres picks a mast before the drift has played out.

`ui/flight_window.py` is the panel: range, **closing against the rate that is
allowed**, **lateral rate**, which berth and how far off, the gate in the
units the readouts are in, and every pad button labelled with the burn it will
give and an arrow saying whether it takes you toward the berth. Both of the
emphasised ones were found by trying to fly it — three chronicles hit the
structure at 9.2 m/s with nineteen of twenty tonnes unspent, because nothing
said when to brake, and `autopilot.safe_rate` had known all along.

Flying by hand also found the real gap in the berth gate: **there are two
roads to "alongside"** — the station-keeping branch and the contact branch —
and only the first had been gated, so a hull that bumped the structure
anywhere at walking pace was moored 477 m from the mast. A gentle touch away
from a fitting is a scrape now, priced by `sim/impulse.py`.

**And the thing you hit is off station afterwards.** Stage one could only
*say* what a collision did to the other body: the sector had nowhere to put
it. An anchorage's position is its body's, worked out from the calendar every
time it is asked, and a traffic hull's is interpolated between two bodies —
neither has a place to hold "and then somebody hit it".

`sim/knock.py` is that place, and `track.at` — the one door for where anything
is — adds it, so a shoved station is off station on the plot, in an approach,
in the readiness board's ranges and in every forecast, because all of them
read the same function. A knock is a velocity offset with a date on it, and
there are two ways of carrying one, the difference being whether anybody is
aboard:

- **a manned berth or a hull under way** arrests it and works back:
  `x(t) = v·t·e^(−t/τ)`, leaving at exactly the speed it was shoved, peaking
  at `v·τ/e` and home again after a few time constants. `KEEPING_DAYS = 12`
  puts a hard ram's 1.7 m/s **649 km off station** a fortnight later — far
  enough that a conn notices, near enough that a chart in AU does not;
- **a derelict holding or a Weave gate** has nobody aboard, so `x(t) = v·t`
  and it simply goes.

The bearing is *drawn* from the seed, the contact and the day rather than
derived from the approach, and the module says why: the conn's frame carries
no system orientation, because an anchorage and its body share a position in
the flight model, so at the moment of contact there is no bearing in the
sector to take. Computing something that looked derived and was not would be
worse than admitting it.

**A collision is two bodies.** `outcome.impact_damage(speed)` took a number
off the player's hull and that was the entire event: the quay a captain hit at
forty metres a second was neither moved nor marked, and could be used as a
backstop. Nothing in the game had a mass, so nothing could be shoved by
anything, and a hull moored to a station could open its main drive without
either of them going anywhere.

`sim/impulse.py` is the physics, and knows nothing about ships or stations —
it takes masses and speeds. Contact is **perfectly inelastic**, because hulls
do not bounce off quays, so two masses meeting at a closing speed share a
velocity and the rest falls out of it: `Δv₁ = −v·m₂/(m₁+m₂)`,
`Δv₂ = +v·m₁/(m₁+m₂)`, and `E = ½·μ·v²` with `μ` the reduced mass — the only
energy there is, since the rest is still in the pair's shared motion and
cannot break anything. Each structure pays for `E` per tonne of itself, which
is why a courier is destroyed by an impact a hub shrugs off without either of
those being written down as a rule.

`HARM_PER_MJ_PER_T = 795.0` is **derived, not chosen**: the reference case is
the hull the game ships with meeting the hub it starts beside, and it must
still cost the 6 points at 4 m/s that `impact_damage` charged — so the written
consequences (a scrape at 8, half the hull at 20, the end of the chronicle at
45) survive the change unaltered, and `tests/test_impulse.py` holds all four
against written figures rather than against the constant.

`impulse.mass_of` is the one door for what a thing weighs: worlds and stars an
effectively infinite mass (which makes lithobraking fall out of the same
arithmetic rather than needing a special case), berths by kind — a quay is
60,000 t against a NAVIS's 24,000, a capital hub 400,000, a Weave gate
2,500,000 — and hulls off their chassis. Writing it surfaced a fallback that
weighed a star the same as a pier.

`Conn` records both masses when the approach opens, the way it records
`star_dir` and `star_lum`, so `sim/outcome.py` can resolve a contact without a
`game` to ask; `berthing.commit` carries what the struck body took out to the
chronicle. **What is not done yet**: the shove is recorded and logged but does
not yet displace a station or hull in the sector — there is nowhere in the
sector's state to hold a knock, since anchorages and traffic hulls are derived
from their body's orbit. That, berthing at a named berth on the structure
rather than anywhere on a bounding sphere, and a manual flight-controls window
are the remaining stages of #105.

**A reticle may only be drawn where it lands.** Found by rendering the conn's
six camera feeds as one contact sheet, a kilometre off a Fleet Hub, and
looking at it: the quay was in the fore view and in no other, and **all six
feeds carried a dashed bracket labelled "Fleet Hub · 998 m" in the middle of
the frame**. On the dorsal camera the bracket sat on top of a planet and named
it as the quay. `render3d.project` returns None for a direction behind the
lens, and `Viewport._target` fell back to the centre of the frame when it did.

No figure could have found this. Every number on every feed was right — the
range was 998 m and the target was Fleet Hub — and five of the six *pictures*
were a lie about where it was.

`tests/test_reticle.py` holds it, entirely off rendered pixels, and its own
third check needed two goes: the first draft measured the bracket against the
centroid of every lit pixel *including the bracket's own*, and did it on a
bow-on approach where the target projects 10 px from the middle of the frame —
so "nailed to the centre" and "on the target" were the same picture. Measured
with the nose 30° off, where they part company at 79 px, and with the
bracket's own pixels excluded, all three mutations are caught.
