# What this is — the design, pass by pass (3 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

**A tactical station that is open before anybody shoots.** Measured on a
fresh chronicle: the battle screen outside an engagement was two labels — *No
engagement / Nothing is shooting at you* — and a Back button; the gunner's
window was one label; and there were five hulls in the system. Combat existed
only once it had started, so the decision the whole tactical model is built to
serve — whether to be here at all — was made blind and reviewed afterwards in
the log.

`sim/readiness.py` answers it by **rehearsing the fight**: `sparring` builds
the same `Battle` `combat.start` would build if that hull opened fire, off
`encounters.make_enemy` at the middle of the range `roll_encounter` actually
draws, and throws it away. Every figure is then read off it with the
engagement's own functions — `assessment.weight`, `firing.solution`,
`gunnery.quote`, `stations.seat_value`. There is no arithmetic in the module
that a fight would not do. It rehearses on a deep copy of the hull, because a
board a captain opens on a whim may not spend ammunition.

`ui/tactical_window.py` and `ui/tactical_board.py` are the window: the traffic
here and how far off, the boresights, the readiness board, and the plot. Two
states — standing by it shows the rehearsal, captioned as one; engaged it
shows the live plot and enables the way through to gunnery. Reachable from the
helm, from the battle screen, and from its own row alongside the conn and the
plotting board, and refreshed with everything else so the ranges follow the
ship.

Two faults found by looking at the pictures rather than at the figures:

- **The window titled itself with the ship actually firing and printed a
  rehearsal against a different one** — *Freeholds GRAFT «Margin Call», turn
  1* over *against Charter CORAL «Long Consent»*. Every number on it was
  correct; it was answering another question. `readiness.of` splits report
  assembly from battle construction so the board reads the live engagement
  when there is one. The check that catches it had to be narrowed to the
  board's own labels: reading the whole window included the title it was
  comparing against, and the mutation sailed through.
- **The boresight captions sat on top of the arc**, and half the window was
  dead space. The sight row has a measured height now and the rehearsal's
  plot fills the third column.

**Where the ship is: one door, and a captain who starts somewhere.**
`sim/flight.ship_position` is the only place anything asks. Behind it are two
states and only one of them is stored:

- **alongside a body** — the position *is* the body's, worked out from the
  calendar on every read. A hull in orbit is not parked in space: the world
  takes it round the star, so a captain who moors and waits four months is
  still at the quay when they look up. A copy in a field would be a second
  answer that goes stale the first time the clock moves.
- **free space** — `Game.ship_xy`, written by `flight.stand_off`, which is
  what a jump's arrival is. That used to be *the only* meaning of "not
  alongside anything", and it was a single fixed point at 4.05 AU.

Two writers, `flight.hold_at` and `flight.stand_off`, and nothing else in
`sim/`, `ui/` or `world/` assigns `orbit_body` any more — `transit.begin`,
`flight.travel_to`, `flight.transit_to` and `berthing.commit` all go through
the door.

What that fixed, measured at the opening of six seeds: every one puts a Fleet
Hub in orbit of body 0, and every one left `orbit_body` unset. So the log said
"under way from Fleet Hub" and the game placed the hull 645,000,000 km from
it. `berthing.can_conn` refused every contact in the system — *"Fleet Hub is
4.31 AU off. The conn is for the last few kilometres"* — which is why the conn
opened on empty space and its controls appeared dead. They were not dead: the
clock and the autopilot are timer-driven and work, and were correctly refusing
to fly an approach to nothing. `core/state._moor_at_home` puts a new captain
alongside the body their home port orbits, and the conn now opens on the quay
at 12 km with the station drawn and the world above it.

Seven checks elsewhere had encoded the old model and had to be told what the
game does now — and four of them turned out to be measuring something else
entirely, which is the real yield of the change:

- `test_play`'s landing check rolled its own party leader that turned for home
  when `supply <= manhattan + 3`, pricing every step at a day when
  `expedition.step_cost` charges up to four. Thirty parties: **17 stranded**
  with that walker, **none at all** with `tests/ground_ai.py`, which costs the
  walk through `sim/wayhome` the way `move` charges for it. It measured the
  terrain roll, not the supply budget.
- `test_burns` drew a fresh galaxy per burn profile — harmless only while every
  chronicle began at the same point on the edge. Four different legs cannot
  say anything about four profiles: economy came out hotter than standard.
- `test_watches` opened the transit panel on whatever chronicle it found, and
  `MainWindow.go` refuses to leave a waiting envoy. The panel was never built
  and the empty string read as a missing risk line. It asks the window now.
- `test_transit` read `started["transit"]` off a refusal: 5 of its 90 seeds are
  one-body systems, and the ship now starts at that body.

**A station you could see and could not use.** Two reports from a player, and
one cause. The Fleet Hub was drawn on the helm chart, labelled, and inert:

- **"Set course" did nothing.** The button reads "Set course — 4 d, 2 t" and
  its tooltip says "Fly to Fleet Hub"; it called `course_to`, which only
  *aims* the helm — and a quay's body is very often the body already
  targeted, so it set what was already set. Clicked and measured: target 0 →
  0, orbit_body None → None, day 0 → 0, fuel 20 → 20. It flies now.
- **The Hub could not be clicked.** The painter drew its mark 11 px off the
  planet; the hit test only walked `system.bodies` with an 18 px radius, so a
  click on the station landed on the world underneath — usually already
  selected, so nothing appeared to happen. `QUAY_OFFSET` is one number now,
  read by the painter and the hit test alike, and quays are tested first.

**A conn that teleported, and one that did not notice being flown.** Two more
player reports, both about the window losing touch with the ship.

*Close and berth* ran four hundred ticks **inside the click**: the hull
arrived and the result was reported, which is exactly what a conn exists not
to do. The mode is held now and one tick is flown per beat of the same clock
the coast button already used, so a berthing takes the forty minutes it takes
— measured, 39 ticks and 39 minutes — and can be watched, corrected, or called
off half-way by pressing the button again.

And a course set at the helm moves the hull, while the conn was built around
wherever the ship stood when it opened — so it went on showing an approach on
somewhere the ship had left. It compares where the ship is against where it
was on every refresh, and reopens on whatever is alongside now.

**The broadside you ordered, and the sky you were flying in.** Two halves of
the same complaint: the game resolved things and then did not show them.

`combat._fire` resolved a shot and wrote a sentence. By the end of a turn all
that survived of a salvo of seven was seven lines of prose — no record of what
fired, from where, at what, or whether it connected, so nothing could draw it.
`sim/gunfire.py` keeps the shots: one per attempt, **including the ones that
never left the tube**, because "the lance will not train that far" is exactly
the thing worth seeing rather than reading and it is the whole argument for
coming about. `ui/battle3d.py` draws them — beams, tracers, seeking rounds on
a curve, impact flashes sized by what they did — from a camera behind and
above your own hull. The general check ties the record to the resolver:
**2,138.9 of damage recorded against 2,138.9 taken** over six chronicles.

Refusals had to be *constructed* to test. `_salvo` pre-filters to the mounts
that bear, so eight full engagements produced 285 shots and not one refusal;
the check finds the geometry by asking the sim's own predicates rather than by
placing hulls at angles guessed at.

And a player reported that taking the conn with nothing in reach showed
nothing at all. It did: the windows drew the approach target and a fixed field
of stars, so with no target there was only the field. Measured, standing off a
body at 0.40 AU, **the system's own star subtends 1.34°** — two and a half
Suns — and was not being drawn. `sim/sky.py` gives an approach the rest of its
system, placed in the approach's own frame at the size it really has, and
`conn.observe` opens the conn with nothing to approach at all, because a
captain can always look out of a window.

That exposed the one place the flight model's simplification shows. An
anchorage's position in AU *is* its body's — which is why no screen needs a
special case for flying to a quay — and asked what the sky looks like *from* a
berth it answered that the planet was at zero range and therefore 180° wide,
which is a picture of being inside it. Co-located sights are placed where they
physically are: the world below a berth reads 98° across.

**Screening that actually screens.** `ConsortOrder.shield` was one of the eight
dead fields below, and the allowlist entry I wrote for it claimed it had already
been wired. It had not — a false reason inside the field meant to prevent false
claims, and nothing checks the reasons.

The order promised "draws fire that would otherwise land on you, and takes it on
a smaller hull" and delivered only the first half: measured, the flag took 228.5
with two escorts screening against 223.6 flanking, while the screens lost 36 more
hull. A pure cost.

`consorts.interception` is the fix: a hull genuinely between wears
`shield × SHIELD_SHARE` of each blow *before* the flag's armour, landing it on
its own layers, saturating at `SHIELD_FLOOR` so six screens still leave the flag
wearing 45 of every 100. At forty seeds screening saves the flag 26% (95 against
flanking's 128) for 19 more hull off the escorts.

Two things were tried and taken back, both worth recording. The screen's station
was moved off the **midpoint** on the reasoning that a midpoint cannot be held —
measured under one method the midpoint is better (95% of alive turns against
85%), because it is *on* the line by construction, so the change was reverted and
a claimed 21%→82% improvement withdrawn as a comparison of two different
measurements. And the armour floor turned out to erase interception: flooring
against the weapon's *nominal* output means the part a screen absorbed never
reaches the comparison (at 34 armour, 26.5→21.6 flat against 26.5→15.1 scaled).

The first mutation sweep ran 7/12 and every miss was the same fault — testing a
mechanism with an aggregate something else dominates. Discarding interception's
answer entirely passed a forty-seed engagement comparison. The checks are single
blows with constructed geometry now, where 72 unscreened − 50 screened = 22 worn
balances to the tonne.

**Eight things declared and read by nobody.** `test_reachable.py` asks this of
functions; asking it of **data** is the richer seam. Every field on every
dataclass in `data/` against whether anything reads it: **eight that nothing
does**, several with docstrings asserting they mattered — `luminosity` "drives
how hard the light falls on everything else" and drove nothing; `halo` was the
corona colour and the corona was drawn in the disc's; `boredom` was "what that
costs in morale" and `morale_tick` had no lineage term at all; `time_sense` was
a written line nobody had seen. Two of the eight were mine, from the
star-catalogue cycle.

A dead field is worse than a missing one: it reads as a feature, gets quoted in
the prose beside it, and promises behaviour the game does not have.

`tests/test_declared.py` is the guard. It fails on any unread field in `data/`,
with an allowlist carrying a **reason per entry** — an allowlist used to dodge
work is the anti-pattern; one with a written reason is how "known and
deliberate" gets said. It also fails when an entry names a field that has gone,
or one that *is* now read, so excuses cannot go stale. The scan counts
`getattr(x, "name")` as a read: without that it cried wolf on `System.star` and
`Target.berth`, and a guard that cries wolf is worse than none.

Four wired, each differenced: `conn.star_lum` carries the star's brightness as
a *fact* (the way `star_dir` carries the light's direction) and `viewport.glare`
decides how many stops to show — a fourth root, since the raw range is five
hundred to one and a screen has four. Measured M 293 → A 324 on the brightest
tenth, 1.48x per lit face. Coronae now use `halo`. `crew.tedium` puts a
lineage's boredom into morale over a crossing: same voyage, wet 0.770 against
dry 0.920. And `crew.how_it_feels` says the line, above a threshold set from
354 measured crossings rather than picked (a first draft's 30 days meant it
almost never appeared).

**The bench after the tree.** The tech tree is sixty-two nodes and 28,790
points end to end, and the game carries on past every one of its ten endings. So
`research.banked` grew for ever once `researchable` came back empty — **146,040
points over the ten years after the tree closed**, on a screen that displayed
the figure and no code that could spend it. Found by asking whether every
declared thing is consumed.

`sim/programmes.py` gives it somewhere to go. A programme opens when its
*branch* is exhausted, never finishes, and completes rounds each
`ROUND_GROWTH` = 1.4 dearer than the last, so a finished tree cannot become a
fountain (eight rounds: 1,100 points to 11,595). Each round yields a **finding**
that buys standing or credits and never a better hull — an endgame bench that
improved the ship would only inflate it. Three doors, each consuming it: file
with one power, publish to all four, or sell. `PUBLISH_SHARE` = 0.45 keeps the
choice real: filing wins with the power you file with (+24.2 against
publishing's +10.9) and publishing wins on the sector total (+25.1 against
+22.2).

Two bugs, both the same fault the feature exists to fix wearing a new coat.
`research.take_spare` zeroes what it hands over — so a day's work cannot be
spent twice — and `clock` called it unconditionally, meaning a bench standing
down **destroyed** every point the tree could not use; there is a `can_take`
gate before the taking now, and 1,833 points are correctly held where the first
draft held none. And `programmes.state` attached the bench to the game as a
plain attribute, so a reload came back empty: the save codec encodes *declared
fields and nothing else*. It is a declared field on `Game` now.

**Gravity that knows which star it is, and an orbit you choose the height of.**
Two player reports, one system, and the second was the bigger fault.

`flight.period_days` was `YEAR_AT_1AU · a^1.5` — Kepler's third law with the
`sqrt(M)` left out, so **every star in the sector weighed exactly one Sun** as
far as its planets were concerned and a world at one AU took the same year
round a 0.32-solar M dwarf as round an A-type nearly six times heavier. It now
takes the star's `mu` as a *required* argument (a default is how half the call
sites end up quietly assuming the Sun), `StarClass` carries `mass_solar`, and
`starclasses.mu_of` is the single door. Measured: **645 days at one AU round an
M dwarf, 272 round an A-type, 129 round a black hole**. Black holes are new —
eight solar masses in a 23.6 km event horizon — and safe to add because a
galaxy is *stored* in the save, so an existing chronicle keeps its sector.

And there was one orbit, wherever the transfer dropped you. `sim/orbits.py`
now holds a ladder whose middle rung is `targets.approach_range` **exactly**,
so a transfer arrives at the standard orbit and low and high are each a real
piece of flying. The trade is geometry rather than invention: escape speed is
`sqrt(2mu/r)`, so `departure_factor` makes low **1.3–3.6× dearer to leave**
than high, and `look_factor` gives it correspondingly better resolution on a
survey. `heights_for` withholds rungs the hull cannot hold — a four-kilometre
comet has a 2 m/s orbit and a thruster pulse is half a metre.

**And it asks a second question now: can the tank pay for the climb.** It could
not, and nothing else did either. `climb_dv` prices a rung at
`|v_circ(from) − v_circ(to)|`, the cost of a thrust-limited spiral, and the conn
compares it against the metres a second in the tank. Flown before the gate
existed: **every high rung at every body was offered and not one was reachable**
— 25 to 264 tonnes of reaction mass against the 20 t a captain opens with — so a
captain found out by spending the whole tank to arrive at 63–76% of the height
with nothing left to leave on. The tank is volatiles in the hold, so the refused
rung is shown with its price rather than hidden: **a high orbit is a fuel
decision**, and a captain who wants one goes and buys the mass.

The control law took four attempts, and three of the failures looked perfectly
reasonable written down: a radial rate (you do not raise an orbit by thrusting
outward — 877 m/s of climb, ballistic, then aground); excess tangential speed
with a *zero* radial demand (a contradiction that cancelled the rise it had
just made); and vis-viva re-solved every tick, which is elegant and needs no
constants but only ever burns prograde at the ship's current position, so it
raised apoapsis for ever and never periapsis. What works is **round it off,
then move it**: circular speed at the current radius drives eccentricity to
nothing with no second branch, and the vis-viva transfer runs once it is round.

Two real bugs sat underneath, both fixed rather than tuned around:

- **A hull could not reverse.** `attitude.turned` sweeps the shortest great
  circle, and to a point *exactly* astern there is no shortest one — the
  perpendicular component is zero and it returned the nose unchanged. So
  `conn.apply` spent every tick slewing, the slew moved nothing, and no thrust
  was delivered. Nothing asked for a reversal until the orbit computer did.
- **`worth_turning` ordered the main drive for thruster work**, predicting 2.4
  ticks for a turn the hull measurably could not finish.

And three screens disagreed with the sim the moment `in_orbit` learned to judge
the **ellipse** rather than the instant — all the same fault, an instantaneous
question about something only true at an apse. `orbit_note` called a completed
orbit "a departure, not an orbit"; `instruments.readout` marked 9,123 m/s amber
on five of twelve approaches, the speed the ship had just got right; and
`adrift` was measured against the range the approach opened at, so climbing to
the high orbit the screen had offered read as losing the target astern.

**Adding one star class re-rolled every sector, and five checks fell over that
had been passing on seed luck** — the most useful thing this cycle turned up.
None was measuring what its name claimed: `test_politics` read "the Concord is
not always reachable" off a one-in-twenty tail (now a differenced claim,
determined 20/20 against idle 0/20); `test_bloom_arc` measured provoked growth
in a single galaxy where the effect wins in seven sectors of eight (now
aggregated over eight, tally reported); `test_officials` looped five favours at
one desk, asked the first, and claimed two — asking *spends* regard, so only one
is ever reachable per chronicle (one official per favour now, all five asked);
`test_counter` checked that a one-shot office rate expires by
comparing the board against the price posted *before* the deal, when buying
moves the board (36 to 37 on two tonnes of ore) — now measured against a
control chronicle that bought the same and never asked; and the conn preferred
a stranger's hull to the world it was orbiting.

The conn's default target rested on a premise this work removed. It ranked
`anchorage, hull, body` because "approaching what you are already orbiting is
not a manoeuvre" — which stopped being true the moment an orbit had a height
you could choose. With bodies on real orbits a passing freighter was often the
nearest thing in the system, and the conn opened on it while the hull sat in
orbit round a world it was not being shown. `default_target` now prefers
whatever is **co-located with the ship** before anything else in the system.

`sim/conn.py` went past five hundred lines and **how an approach ends** came
out into `sim/outcome.py`. The seam is real: `conn` answers what the ship does
when a thruster fires, `outcome` answers whether the approach is over. Three
of the four outcomes are about a distance; the fourth is not, and asking about
an orbit at an instant is the mistake that took four control laws and three
contradicting screens to find. The thresholds stay in `conn` and are passed
in — a constant written twice is the fault this project has hit most often.

**It went past five hundred again**, and the forecast came out into
`sim/preview.py` for the same reason and along the same seam: `conn` is the act,
`preview`, `instruments` and `outcome` are what is said *about* the act. It is
one idea — fly a throwaway twin and report what it ends up with — and it is the
part that had just been caught lying, so it earns its own file. `_rotate` became
`conn.rotate` on the way out: `autopilot` had already been importing the private
name, which is usually the tree telling you something belongs to more than one
caller.

**A sky with eight kinds of star and seven of world.** The sky then had *one*
star and *one* world, painted different colours. Eight spectral classes have
existed since the game was written — M dwarf, K, G, F, A, binary, white dwarf,
neutron star, each with its own name and tint on the chart — and every one was
drawn as the same 695,700 km ball, because `sim/sky.py` held one number for a
star's size and never asked which star. `data/starclasses.py` gives each its
real radius and luminosity: **104,355 to one**, a 12 km neutron star against
an A-type at 1.8 solar. The data already said which was which.

`data/worlds3d.py` does the same for bodies, on one idea — **latitude**.
`by_latitude(paint)` colours a sphere's bands by how far up them they sit, and
that one hook is the whole vocabulary: `capped()` gets polar caps for nothing,
`banded()` varies the bands into a gas giant, and `ring_disc()` is a flat
annulus of concentric bands. Rings are drawn in two halves — the far arc
before the world and the near arc after it — because a flat annulus
interpenetrates the sphere it circles and painter's algorithm has no answer to
that. Which giants carry rings is derived from the body's **name** in
`sky.has_rings`, so a ringed world is ringed in every chronicle from that seed
and there is nothing to save.

`tests/test_worlds.py`, `test_sky_kit.py` and `test_lighting.py` (10 checks
between them) measure all of it in pixels rather than asserting it from the
table that made it. Three lessons:

- **The first "do these look alike?" measure was measuring the background.**
  A 6×6 grid of mean colours over the whole plate, three quarters identical
  black sky — it reported seventeen pairs rendering alike. Over lit pixels
  only, plus a vertical profile (a bare mean cannot see *banding*, which is
  the whole of what makes a giant a giant), nothing collides.
- **A share test cannot catch a low-entropy key.** Ring assignment was once
  keyed on `body.id`, and there are only **seven distinct ids across 192
  giants** — so the ringed share is seven coin flips and lands on 47% by luck.
  The check that bites asks whether all thirty-one giants in the *same
  orbital slot* agree. Groups of eight or more only: the outermost slot holds
  one giant in the whole sector, and one body agreeing with itself proves
  nothing.
- **Every sphere in the game wore a faint wireframe.** Two adjacent
  antialiased polygons each cover half the pixel on their shared edge and each
  blends its half with the background, so `NoPen` ruled every solid hull with
  hairlines of empty space. `ui/render3d.py` strokes each face in its *own*
  colour: **1,194 seam pixels → 54**, on every 3D object in the game.

And then flying at one found the bug the plates could not. The **sky** drew
rings on a ringed giant; the thing being *approached* did not, because
`Target` had a `look` and no `ringed` and `viewport._model_for` returned a
bare world mesh. So a giant's rings vanished at exactly the point you got
close enough for them to be worth looking at — two doors into the same
question disagreeing, which is this project's most reliable bug shape. The
check is the general one: every body in the sector must give the same answer
to `sky.has_rings` and to `targets.target_from_body(...).ringed`, and the
picture is differenced against the identical approach with the rings taken
off (10,440 lit samples against 3,443).

**An anchor with nowhere to be.** A player reported it plainly: the gate is on
the sector chart, invisible on the helm, impossible to fly to, and nothing is
happening around it. All true. A Weave anchor was a *sector* abstraction — a
system id and a list of links — with no place inside the system it stood in.

It is an `Anchorage` now, of kind `gate`, and almost everything else fell out
of that: the helm chart already draws anchorages, `track.contacts` already
turns them into things the conn and the plotting board can aim at, and the
"where you can put in" panel already offers a course to one. `gate_body` puts
it at the **outermost** body and deliberately not the one the quay is built
over — an anchor predates every port in the Verge, it was put where there was
room and no gravity to fight, and arriving through the Weave should drop you
at the edge of a system rather than in the middle of its traffic.

The other half of the report — *shouldn't there be a lot of activity around
any gates?* — is `traffic._busyness`, which now adds two hulls for a lit
anchor. Measured: lit anchors work 3.7 hulls against a dark one's 2.1, and
waking one takes its system from 2 to 4.

*A latent bug it exposed.* `HelmView._pick` read the quay that was clicked off
`self.chart` — but `refresh()` builds a new chart every time, so it was asking
a widget that had not been clicked. It could only ever show up in a system
holding **two** berths, which no system did until anchors got a place of their
own. It reads the signal's sender now.
