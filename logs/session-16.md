# Session log, part 16 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: gravity that knows which star, and an orbit you choose

Two player reports, one system: *"the player should be able to orbit planets at
different distances — at the moment it seems like there is only one option"*
and *"please ensure the gravity is working correctly for all bodies"*.

Both were right, and the second turned out to be the bigger fault.

**Every star weighed one Sun.** `flight.period_days` was `YEAR_AT_1AU · a^1.5`
— Kepler's third law with the `sqrt(M)` left out. Eight spectral classes have
existed since the game was written and a world at one AU took the same year
round a 0.32-solar M dwarf as round an A-type nearly six times heavier.
Measured after the fix: **645 days round an M dwarf against 272 round an
A-type and 129 round a black hole**, and 539 bodies in four sectors now sit
somewhere a one-solar-mass sector would not have put them. `StarClass` gained
`mass_solar`, `starclasses.mu_of` is the single door, and `period_days` takes
the star's `mu` as a **required** argument — a default is how half the call
sites end up quietly assuming the Sun.

Black holes joined the catalogue while I was there: eight solar masses in a
23.6 km event horizon, weight 1. Safe to add because a galaxy is *stored* in
the save, so existing chronicles keep the sector they grew with.

**And there was one orbit**, wherever the transfer happened to drop you. There
is now a ladder — low, standard, high — with the standard rung defined to be
`targets.approach_range` exactly, so a transfer arrives at the standard orbit
and the other two are a real piece of flying. It is a trade in both
directions, from the same geometry: escape speed is `sqrt(2mu/r)`, so **low
costs 1.3–3.6× what high does to leave** and resolves correspondingly more.

The control law took four attempts and the failures are worth recording,
because three of them looked perfectly reasonable written down:

1. **A radial rate, capped against circular speed at the destination.** 877
   m/s of climb where a thruster pulse is half a metre a second. Ballistic,
   then aground. You do not raise an orbit by thrusting outward.
2. **Excess tangential speed with a zero radial demand.** A contradiction: it
   spent every tick cancelling the rise it spent the previous tick creating.
3. **Vis-viva, re-solved every tick.** Elegant, needs no constants — and only
   ever burns prograde at the ship's current position, which raises the
   *opposite* apse. It lifted apoapsis toward the target for ever and never
   once raised periapsis: e pinned at 0.52 for sixty thousand ticks.
4. **Round it off, then move it.** Circular speed at the current radius while
   the orbit is out of round (which drives e→0 with no second branch), and the
   vis-viva transfer once it is round. 31 of 32 offered heights reached.

Underneath those were two real bugs, both fixed rather than tuned around:

- **A hull could not reverse.** `attitude.turned` sweeps along the shortest
  great circle, and to a point *exactly* astern there is no shortest one —
  every great circle is the same length, the perpendicular component is zero,
  and the function returned the nose unchanged. So `conn.apply` spent every
  tick slewing, the slew moved nothing, and no thrust was ever delivered.
  Nothing had asked for a reversal until the orbit computer did.
- **The computer ordered the main drive for work the thrusters should do.**
  The swing estimate predicted 2.4 ticks for a 180° turn the ship measurably
  could not finish, so a five-metre-a-second trim got the main drive, and the
  hull turned instead of burning.

Three screens disagreed with the sim once `in_orbit` learned to judge the
ellipse rather than the instant, and all three are the same fault: a readout
asking an instantaneous question about a thing that is only true at an apse.
`orbit_note` called a completed orbit "a departure, not an orbit" in the panel
beside the conn reporting it made; `instruments.readout` marked 9,123 m/s in
amber on five of twelve approaches — the speed the ship had just got right;
and `adrift` was measured against the range the approach opened at, so
climbing to the high orbit the screen had just offered was reported as losing
the target astern.

`sim/conn.py` went past five hundred lines, so **how an approach ends** came
out into `sim/outcome.py` — a real seam rather than a line count: `conn`
answers what the ship does when you fire a thruster, and `outcome` answers
whether the approach is over. The thresholds stay in `conn` and are passed in,
because a constant written twice is this project's most frequent fault.

**Adding one star class re-rolled every sector, and five checks fell over that
had been passing on seed luck.** That is the most useful thing this cycle
found: not one of the four was measuring what its own name claimed, and each is
now a real measurement rather than a coincidence.

- **A one-in-twenty tail.** `test_politics` asserted the Concord is not *always*
  reachable, read off the tail of twenty samples at a true rate near 0.95 —
  which fails better than a third of the time on nothing at all. The property
  it wanted is already measured directly two checks above. It is now a
  differenced claim with real power: the same captain, same billion credits,
  same standing, who *never brokers* must not arrive at the Concord by
  waiting. Measured 20/20 determined against 0/20 idle.
- **One sector standing in for the sector.** `test_bloom_arc` measured
  provoked-versus-calm growth in a single galaxy. The effect is real —
  `growth_multiplier` is 2.589 — but three years of growth in a forty-two
  system sector runs near saturation, which compresses the gap, and provoked
  wins in *seven of eight* sectors rather than eight. Which one is the
  exception depends on the sector. Now aggregated over eight, with the tally
  reported so a real change in the mechanism shows rather than averaging away.
- **A check that asked one official for five favours.** `test_officials`
  looped over all five, asked the first, and asserted it had checked two —
  but asking *spends regard*, 28 of the 48 a well-liked captain has, so only
  one favour is ever reachable per chronicle. It passed while the seed's desk
  happened to offer a cheap one first. One official per favour now, and all
  five get asked.
- **A price compared across a state change.** `test_counter` checked that a
  one-shot office rate expires by comparing the board against the price posted
  *before* the deal — but buying moves the board, two tonnes of ore taking it
  from 36 to 37. It passed only while the drift on whichever commodity the seed
  picked stayed under a rounding boundary. Now measured against a control
  chronicle that made the same purchase and never asked for anything.
- **A conn that preferred a stranger.** Covered above.

Two of the project's own guards earned their keep on the new code. The harness
guard noticed that `sim/outcome.py` arrived with a tuning constant and **no
tripwire fast path**, which is how a constant stops being measured. And the
reachability check caught `orbits.nearest_height`
— a function I wrote this cycle and never wired in. It is wired in now, and
better for it: the panel names the rung as well as the altitude, so it reads
"Circular at 3,353 km — a standard orbit" rather than a bare number, which is
what the departure cost and the survey resolution actually follow from.

And the conn's own preference order turned out to rest on a premise this
cycle removed. It ranked `anchorage, hull, body`, on the reasoning that
"approaching what you are already orbiting is not a manoeuvre" — true when an
orbit had no height, false now. Once bodies moved onto their real orbits a
passing freighter was often the nearest thing in the system, so the conn opened
on `Patient Ledger` while the hull sat in orbit around a world it was not being
shown. `default_target` now puts **where the ship actually is** first, and only
then looks at the rest of the system.

Two more were latent and exposed by bodies being somewhere new: `route` reported a course **bent around the star whose
detour was exactly zero** — the innermost orbit slot sits at exactly the
clearance radius, so `near` and `clear` are the same number computed two ways
and differ by 1e-16, which sent the course down the bend path to a waypoint
already at the radius it was being pushed to. And a check that spawns a fresh
interpreter to prove orbits are process-independent needed the new import
inside its own snippet, which is the sort of thing that only fails honestly.

Mutation sweep **17/17**, and it took two passes to get there — the first ran
13/17, and every one of the four misses was a hole in a *check* rather than in
the code. Two are worth writing down:

- **A check that could not fail.** The ladder's trade was asserted with
  `look == sorted(look, reverse=True)`, and a mutation that made `look_factor`
  return a flat 1.0 sailed through it, because a constant list is trivially
  sorted either way. Strictly decreasing now, and measured where the game
  actually reads it — `survey.look_bonus`, 1.03 from a low orbit against 0.80
  from a high one. The departure lift had the same shape of hole: computed and
  never applied passed the forecast-matches-act check, because the quote and
  the act agreed perfectly while both were wrong.
- **Two of the seven bug fixes had nothing holding them.** The hull-reversal
  fix and the adrift-limit fix were both real, both found by flying, and both
  invisible to every check in the suite — because the control law that finally
  worked happens not to need a 180° turn, and happens to resolve before the
  old adrift limit bites. Fixing a bug does not protect it. Both have direct
  checks now: four hulls turned through 180°, and a ship constructed 227,056
  km out reading "still flying" when that height was asked for and "adrift"
  when it was not.

`tests/test_orbits.py`, 9 checks. One measured limitation is recorded rather
than hidden: the high rung at a 153 km asteroid settles into a sound, round
orbit (e = 0.049) at 94% of the height asked, because circular speed there is
44 m/s and the hull moves 0.45 m/s at a time. Short of the mark and safe,
which is the right way to miss — task #83, and the check asserts `missed <= 1`
so a second one is a regression rather than a quiet slide.

## 2026-07-29 — SEEDFALL: a sky with eight kinds of star and seven of world

The standing objective is a catalogue worth looking at. The sky had one star
and one world, painted different colours.

**Stars.** Eight spectral classes existed since the game was written — an M
dwarf, a K, a G, an F, an A, a binary, a white dwarf, a neutron star — each
with its own name and tint on the chart, and every one drawn as the same
695,700 km yellow ball, because `sim/sky.py` held one number for a star's
size and never asked which star. `data/starclasses.py` gives each its real
radius and luminosity: **104,355 to one**, from a 12 km neutron star to an
A-type at 1.8 solar. It was free — the data already said which was which.

**Worlds.** Same story: a 12 km comet, a 7,000 km ocean and a 71,000 km giant
all came out as one ball with a tint. The cheapest fix is **latitude** —
colour a sphere's bands by how far up them you are and polar caps come for
nothing, vary the bands and you have a gas giant, and a flat annulus round it
is a ring system. `data/worlds3d.py`, seven meshes, and rings on 39% of
giants.

Three things worth keeping from building it:

- **The first measure of "do these look alike?" was measuring the
  background.** A 6×6 grid of mean colours over the whole plate, three
  quarters of which is identical black sky — it duly reported seventeen pairs
  of world rendering alike. Over lit pixels only, plus a vertical profile
  (because a bare mean cannot see *banding*, which is the whole of what makes
  a giant a giant), the closest pair is ice/comet and nothing collides.
- **A share test cannot catch a low-entropy key.** Which giants carry rings
  was once keyed on `body.id` — and there are only **seven distinct ids
  across 192 giants**, so the ringed share is seven coin flips and lands on
  47% by luck. The check that catches it asks a different question: do all
  thirty-one giants sitting in the same orbital slot agree? Only groups of
  eight or more count; the outermost slot holds one giant in the sector, and
  one body agreeing with itself is not evidence.
- **Every sphere in the game wore a faint wireframe**, and it took a contact
  sheet to see it. Two adjacent antialiased polygons each cover half the
  pixel on their shared edge and each blends its half with the background, so
  `NoPen` ruled every solid hull with hairlines of empty space. Stroking each
  face in its own colour: **1,194 seam pixels → 54**. That one is in
  `ui/render3d.py` and improves every 3D object in the game.

Then flying at one found the bug the test plates could not. The **sky** drew
rings on a ringed giant; the thing being *approached* did not — `Target` had
a `look` and no `ringed` — so a giant's rings vanished at exactly the point
you got near enough for them to matter. Two doors into the same question
disagreeing, again. The check asks the general form: every body in the sector
must give the same answer to `sky.has_rings` and to `target_from_body().ringed`,
and the picture is differenced against the same approach with the rings taken
off — 10,440 lit samples against 3,443.

Mutation sweep 15/16. The one miss is honest and stayed a miss: removing the
surface mottling changes nothing any check should care about — measured, the
closest pair of worlds is still 41 apart without it. The mottle is there
because it looks better, and the docstring that claimed it was load-bearing
for separation was corrected rather than defended with a check invented to
score against it.

`tests/test_worlds.py`, 7 checks. Full suite green.

Answered a question about gravity along the way, and it exposed a real gap
(now task #81): every **body** has mass — `mu = g·R²`, integrated as `mu/r²`
each tick, spanning a million-fold from an asteroid's 12.6 to a giant's 14.2
million — but a **star** has none. The largest object in every system pulls
on nothing, which is newly conspicuous now that stars differ by five orders
of magnitude in size. Nor does anything but the conn's current target pull:
no slingshots, no third-body perturbation.

## 2026-07-29 — SEEDFALL: a conn that teleported

Two more reports, both about the window losing touch with the ship.

**"Close and berth" teleported.** It did — `_auto` ran four hundred ticks
inside the click, so the hull simply arrived and the outcome was reported.
That is precisely what a conn exists not to do: the whole point of modelling
the last twelve kilometres is that you fly them. The mode is *held* now, and
one tick is flown per beat of the same clock the coast button already used.
Measured: 39 ticks and 39 minutes to come alongside, none of it inside the
click, and pressing the button again gives the conn back rather than doing it
twice.

**And the window did not notice the ship being flown.** A course set at the
helm moves the hull; the conn was built around wherever the ship stood when it
opened and went on showing an approach on somewhere it had left. It compares
where the ship is against where it was on every refresh, and reopens on
whatever is alongside now.

Both were straightforward once found, and both are the same shape as the
staleness bugs from two cycles ago — a window holding a copy of the world
instead of reading it. That is now three times, so it is worth naming as a
pattern rather than a coincidence.

`tests/test_connwindow.py` (4 checks), split out of `test_cameras.py`, which
had crossed five hundred lines. Full suite 795 green.

## 2026-07-29 — SEEDFALL: the broadside you ordered, and the sky you were in

Two halves of one complaint: the game resolved things and then did not show
them.

**Weapons.** `combat._fire` resolved a shot and wrote a sentence. By the end of
a turn all that survived of a salvo of seven was seven lines of prose — no
record of what fired, from where, at what, or whether it connected, so nothing
could draw it. `sim/gunfire.py` keeps the shots now, one per attempt,
**including the ones that never left the tube**: a mount that will not train
that far is exactly the thing a captain should see rather than read, and it is
the whole argument for having come about.

`ui/battle3d.py` draws the exchange from behind and above your own hull —
beams, tracers, seeking rounds on a curve, impact flashes sized by what they
did, and a dashed stub at the muzzle for a mount that would not bear. It sits
above the tactical plot rather than replacing it: the plot is what you
*decide* on and this is what the decision produced.

The general check ties the record to the resolver rather than to a second
model that could drift: **2,138.9 of damage recorded against 2,138.9 taken**
across six chronicles. If `_fire` ever grows a path that deals damage without
noting it, the totals part company.

Refusals had to be constructed. `_salvo` pre-filters to the mounts that bear,
so eight full engagements gave 285 shots and not one refusal — the check finds
the geometry by asking the sim's own predicates instead of placing hulls at
angles I had guessed at, which is just as well, because my first three guesses
about the arc conventions were all wrong.

**The sky.** A player reported that taking the conn with nothing in reach
showed nothing on any screen, and that large bright bodies ought to be
visible. Both true. The windows drew the approach target and a fixed field of
stars; with no target there was only the field. Measured: standing off a body
at 0.40 AU the system's own star subtends **1.34°**, two and a half Suns, and
was not drawn at all. From the system edge it is still 0.13° and by orders of
magnitude the brightest thing there is.

`sim/sky.py` gives an approach the rest of its system, in the approach's own
frame at its real size, and `conn.observe` opens the conn with nothing to
approach — because you can always look out of a window. The title reads
"station keeping at Orrin's Mouth" and the log line is "the watch is kept".

**And it exposed the one place the flight model's simplification shows.** An
anchorage's position in AU *is* its body's — the reason no screen needs a
special case for flying to a quay — and asked what the sky looks like *from* a
berth it answered that the planet was at zero range and therefore 180° wide,
which is a picture of being inside the planet. Co-located sights are placed
where they physically are now: the world below a berth reads 98° across.

**Two checks had to stop measuring the wrong thing.** "A camera shows what is
in front of it" counted total brightness — fine until the sky started drawing
the world a berth orbits into the ventral view, at which point it was
measuring the sky rather than the target; it empties the sky first now. And
the new star check counted bright pixels and was really counting the
starfield, 111 against 90. A field star is a point and a corona is an area, so
it counts lit *area*: 41 against 6.

Full suite green.

## 2026-07-29 — SEEDFALL: an anchor with nowhere to be

A player's report, and a fair one: the Weave anchor is drawn on the sector
chart, invisible on the helm, impossible to fly to, and nothing is happening
around it. Where is it? How do I get there? Shouldn't a gate be busy?

All true. An anchor was a *sector* abstraction — a system id and a list of
links — with no position inside the system it stood in. The sector chart drew
it because the sector chart knew about the Weave; nothing else did.

The fix was to stop treating it as special. It is an `Anchorage` of kind
`gate`, and almost everything else fell out for free: the helm chart already
draws anchorages, `track.contacts` already turns them into things the conn and
the plotting board can aim at, and the "where you can put in" panel already
offers a course. One new derivation — `gate_body`, which parks it at the
**outermost** body and deliberately not the one the quay is built over. An
anchor predates every port in the Verge; it went where there was room and no
gravity to fight, and coming through the Weave ought to drop you at the edge
of a system rather than in the middle of its traffic.

Busyness was the other half. `traffic._busyness` adds two hulls for a lit
anchor, which is the whole reason the powers built their capitals on the ones
they found first. Measured: lit anchors work 3.7 hulls against a dark one's
2.1, and waking one takes its system from 2 to 4.

The conn draws it as the torus `data/models3d.py` already had, at 1.1 km
rather than a quay's 0.4 — an anchor is a far bigger thing than a berth and
should read that way on the way in.

**And it exposed a latent bug that had been sitting there for two cycles.**
`HelmView._pick` read which quay had been clicked off `self.chart` — but
`refresh()` builds a *new* chart every time, so it was asking a widget that
had not been clicked. It could only ever go wrong in a system holding **two**
berths, and no system held two until anchors got a place of their own. It
reads the signal's sender now. The check that caught it was the one written
two cycles ago for the original clickable-quay report, which is a pleasing
argument for writing the check even when the fix looks obvious.

Sweep 6/6 against a green baseline. Full suite green.

## 2026-07-29 — SEEDFALL: something worth looking at

The captain asked for the piloting to be worth watching — docking at a
well-rendered shipyard, other craft, weapons fire, crashes, planets and
satellites on orbital insertion, asteroid belts. That is several cycles of
work. This one builds the substrate everything else needs, and gets one thing
right end to end: a shipyard you can watch yourself come alongside.

`ui/render3d.py` — a camera, perspective, back-face culling, painter's
algorithm and flat shading from a light. A few hundred `QPainter` polygons a
frame. No textures, no shaders, no dependency and no build step for a game
that is otherwise pure PyQt. `data/models3d.py` — a shipyard with a spine,
two habitation rings and four docking arms with lit berths; a hull with a nose
you can tell from its tail; a Weave anchor; a lumpy asteroid; and a UV sphere
for worlds. Authored at radius 1 and scaled by what the thing really is.

**Three things it taught me.**

The light needs a source. `conn.start` records `star_dir` now: the star is at
the system's centre and the target somewhere out from it, so light falls along
the target's own position vector. One line, and a world has its terminator on
the correct side.

A sphere has to be one colour. Every other mesh alternates shade face by face
so a flat-lit structure still reads as having parts — do that to a sphere and
you get a chessboard, and the chessboard eats the terminator, which is the one
thing that makes a planet look like a planet.

And the first pass was almost entirely black: a handsome yard, correctly lit,
unreadable. Ambient 0.22 to 0.40.

**And a fault the models exposed.** `conn.nose` is the 3D vector the main
drive is aimed along. The camera basis was built from `conn.heading` — a bare
yaw angle **nothing in the game has ever written to**. So swinging the hull
round with the thrusters changed the flying and not the view; the nose camera
did not look where the ship pointed. They are one frame now, and the hull
keeps its belly toward whatever it is approaching, which is what makes the
ventral camera worth having in orbit. One inverted cross product had that
backwards and put the planet you are orbiting in the camera pointing at the
sky.

**Two checks were measuring the paint rather than the camera.** The
"what is in front of it" check counted *green-cast* pixels, which was true of
the flat tinted disc the window used to draw and false of a plate-grey
shipyard the moment it had a real model. My first fix counted any bright pixel
and duly counted the **starfield** — four hundred samples of empty space in
every camera. A star is a point and a hull is a surface, so a sample only
counts now when its neighbours are lit too: model-agnostic and
starfield-proof.

And the control sweep earned its place again, catching a crash I had just
written: the conn can be opened with no approach running at all, and
`hull_frame` did not answer for `None`.

Still to do, and recorded as such: asteroid belts to fly through, weapons fire
and impacts, crashes, moons in orbit with their worlds, and the Weave anchors
still have no position *inside* their system — they show on the sector chart
and are invisible on the helm.
