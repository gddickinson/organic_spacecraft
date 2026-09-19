# Session log, part 09 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-30 to 2026-07-30; undated entries keep their original place.

## 2026-07-30 — SEEDFALL: a collision is two bodies (#105, stage 1)

Asked for real docking physics. Measured first, and the model turned out to
have one thing right and two things missing.

**Right**: the conn already works in the *target's* frame, so `conn.vel` is
the relative velocity and matching a station's motion is exactly what flying
it to zero means. That part needed nothing.

**Missing**: a collision was one-sided — `outcome.impact_damage(speed)` took a
number off the player and that was the whole event, so a quay could be used as
a backstop and was neither moved nor marked. And nothing in the game had a
mass, so nothing could be shoved by anything, and a hull moored to a station
could open its main drive without either of them going anywhere.

Both follow from one piece of physics, so there is one module. Contact is
perfectly inelastic — hulls do not bounce off quays — and two masses meeting
at a closing speed share a velocity. Everything missing falls out: how hard
the striker is stopped, how hard the struck one is shoved, and the
reduced-mass energy `½·μ·v²`, which is the only energy there is because the
rest is still in the pair's shared motion and cannot break anything. Each pays
for it per tonne of itself, so a courier is wrecked by an impact a hub shrugs
off — without either being written down as a rule.

The calibration constant is *derived*: the reference case is the hull the game
ships with meeting the hub it starts beside, which must still cost the 6
points at 4 m/s the old formula charged. So the written consequences — a
scrape at 8 m/s, half the hull at 20, the end of the chronicle at 45 — come
through unaltered, and the checks hold all four against written figures rather
than against the constant.

Measured, flown: 30 m/s into a Fleet Hub ends the chronicle at 338 off the
hull, and the hub takes 20 points and 1.70 m/s off station, both in the log.
A NAVIS into a courier at 20 m/s: 6 against 153, the courier knocked to
19.3 m/s. Twelve m/s of burn against a mooring moves the pair 0.68 on a hub,
11.6 on a courier, 0.11 on a Weave gate.

Writing `mass_of` surfaced a fallback that weighed a star the same as a pier.
The conn's own guard — "a forecast's twin carries every field that changes the
flying" — caught the two new mass fields within the minute, which is the fifth
time that check has earned its place.

Eight mutations, eight caught.

**Not done yet, and named as such**: the shove is recorded and logged but does
not displace a station or hull in the sector, because there is nowhere in the
sector's state to hold a knock — anchorages and traffic hulls are derived from
their body's orbit. That, berthing at a named berth on the structure rather
than anywhere on a bounding sphere, and a manual flight-controls window are
the remaining stages.

## 2026-07-30 — SEEDFALL: five of six cameras were lying (#79)

Flew a real approach — helm to the body, `berthing.begin`, then the flight
computer down from 12 km — and rendered the conn's six feeds as one contact
sheet at 998 m. The Fleet Hub is a proper structure by then: masts, rings,
docking arms, an amber-lit cap, filling the fore view. Good.

**And all six feeds carried a dashed bracket labelled "Fleet Hub · 998 m" in
the middle of the frame.** The hub is in one of them. On the dorsal camera the
bracket sat on top of a planet and named it as the quay.

`render3d.project` returns None for a direction behind the lens, and the
bracket fell back to the centre of the frame when it did. Every number on
every feed was correct; five of the six pictures were a lie about direction.
There is no figure that could have caught this — only the picture.

Checked the two things that looked wrong and were not, before touching them:
the hub is dim because it orbits an M dwarf and `Viewport.glare` reads
`star_lum` (0.04 → a glare of 0.55, against an A-type's 22); and the target is
excluded from `sky.build` on purpose, because it is drawn at the origin of the
approach's own frame by `_target`.

`tests/test_reticle.py`, all three claims read off pixels. The third one took
two goes: the first draft compared the bracket against the centroid of every
lit pixel — the bracket's own included, which drags the target toward it — and
did it on a bow-on approach where the target projects 10 px from the middle of
the frame. "Nailed to the centre" and "on the target" are the same picture
there. Measured 30° off the bore, where they differ by 69 px, with the
bracket's pixels excluded: three of three mutations caught.

## 2026-07-30 — SEEDFALL: a tactical station open before anybody shoots (#104)

Measured on a fresh chronicle with nothing shooting:

    the battle screen      2 labels — "No engagement / Nothing is shooting
                           at you", and a Back button
    the gunner's window    1 label
    hulls in the system    5

Combat existed only once it had started. Five hulls on the chart and nowhere
to ask the one question they raise: *what happens if one of those turns on
me?* The decision the whole tactical model is built to serve — whether to be
here at all — was made blind and reviewed afterwards in the log.

`sim/readiness.py` answers it by **rehearsing the fight**. `sparring` builds
the same `Battle` `combat.start` would build, off `encounters.make_enemy` at
the middle of the range `roll_encounter` actually draws, and throws it away;
every figure is then read off it with the engagement's own functions. No
arithmetic in the module that a fight would not do. It rehearses on a deep
copy of the hull, because a board a captain opens on a whim may not spend
ammunition. `THREAT_FLOOR` and `THREAT_SPREAD` were inline literals written
twice in `roll_encounter` — named now, so the board and the ambush describe
one sector.

`ui/tactical_window.py` + `ui/tactical_board.py`: traffic and ranges, the
boresights, the readiness board, and a plot. Standing by it shows the
rehearsal, captioned as one; engaged it shows the live plot and opens the way
to gunnery. From the helm, from the battle screen, and refreshed with
everything else so the ranges follow the ship.

**Both real faults came from looking at the pictures, not the figures.**

- Mid-engagement the window titled itself with the ship actually firing and
  printed a rehearsal against a different one — *Freeholds GRAFT «Margin
  Call», turn 1* over *against Charter CORAL «Long Consent»*. Every number was
  correct. It was answering another question. `readiness.of` splits the report
  from the battle so the board reads the live one.
- The boresight captions sat on the arc and half the window was empty.

**And the check for the first fault did not bite.** It read every label in the
window — including the title it was comparing against — so "the enemy's name
appears" was satisfied by the title itself, and the mutation that puts the
fault back sailed through. Narrowed to the board's own labels, it catches it.
Seven mutations, seven caught, after two rounds of that.

Two were no-ops worth recording rather than gaps: `combat.start` writes
nothing to the ship it is handed, so "the hull is unscathed" cannot see the
deep copy (asked structurally instead); and handing `initial_layout` an rng
moves the *picture* — the pair's orientation and the enemy's heading — while
every figure in the report stays identical, because the enemy is always dead
ahead and `weight` has no aspect term. That one is asked of the pixels.

**And then I wrote the tautology the tripwire exists to catch, again.** The
new constants were pinned with `typical_threat() == FLOOR + SPREAD / 2` —
the definition rearranged, moving with both and holding neither. All four
mutations (floor doubled, floor zeroed, spread doubled, spread zeroed) passed.
Replaced with what the range actually produces, measured over 120 opponents
per difficulty: median hull 149 at the softest the sector sends, 208 at what a
report quotes, 359 at the worst. Four of four caught now.

A second habit worth naming: the tripwire *edits source files while it
sweeps*, so nothing else may run against the tree at the same time — and
killing it mid-sweep leaves a mutated constant behind. It left
`THREAT_SPREAD = 0.0` in the working tree here, caught by `git status`.

Full suite green.

## 2026-07-30 — SEEDFALL: one position for the ship (#103)

The report was that the conn is disconnected from the game and its controls do
nothing. Measured at the opening of six seeds, that is exactly true, and the
cause is one line:

    the opening log         "The Ladon is under way from Fleet Hub."
    Fleet Hub               in orbit of body 0
    game.orbit_body         None
    distance to Fleet Hub   645,000,000 km
    berthing.can_conn       "Fleet Hub is 4.31 AU off. The conn is for the
                             last few kilometres — plot a transfer first."

The sector has always been positioned — `track.at` gives every contact a place
that moves with the calendar — and the ship never was. It had a body id or
nothing, and "nothing" was a fixed point at 4.05 AU. So a captain who had not
moved was hours of light from the quay they were tied to, and the conn opened
on empty space. **The controls were not broken.** The clock and the autopilot
are timer-driven and work: 12.00 → 11.88 km on the clock, closing at 8.3 m/s
under the computer. They were correctly refusing to fly an approach to nothing.

`sim/flight.ship_position` is the one door now, with two states behind it and
only one of them stored: alongside a body the position *is* the body's, worked
out from the calendar on every read; otherwise it is `Game.ship_xy`, written by
`flight.stand_off`. Deriving rather than storing is the whole point — a copy
goes stale the first time the clock moves, and a hull in orbit is not parked in
space. Two writers, `hold_at` and `stand_off`, and nothing anywhere else in
`sim/`, `ui/` or `world/` assigns `orbit_body` any more.

A new captain is moored where their log says they are. The conn opens on Fleet
Hub at 12 km, station drawn, world above it, six live feeds and live controls.

**The yield was in the checks.** Seven encoded the old model; four of them
turned out to be measuring something other than what they claimed:

- `test_play`'s landing check rolled its own party leader that turned for home
  at `supply <= manhattan + 3` — one day a step, when `expedition.step_cost`
  charges up to four on fresh scarp in weather. Thirty parties: **17 stranded**
  with that walker and **none** with `tests/ground_ai.py`, which costs the walk
  through `sim/wayhome` the way `move` charges for it. It was measuring the
  terrain roll. It sat at 3-5 strandings against a bar of 4, and moving where a
  captain starts — which changes nothing about the ground — pushed it over.
- `test_burns` drew a fresh galaxy per burn profile. Four different legs cannot
  say anything about four profiles: economy came out hotter than standard.
- `test_watches` opened the transit panel on whatever chronicle it found, and
  `MainWindow.go` will not leave a waiting envoy. The panel was never built and
  an empty string read as a missing risk line. It asks the window now.
- `test_transit` read `started["transit"]` off a refusal — 5 of its 90 seeds
  are one-body systems, and the ship starts at that body.

Full suite green. `tests/test_position.py` is new: five checks holding the door
shut, including a save written before `ship_xy` existed opening where it always
thought it was.

## 2026-07-30 — SEEDFALL: a 170x92 feed cost more than a 782x455 view (#3D)

Measured the conn window during an approach — the live 3D view the whole
docking activity happens inside:

    conn window        47.0 ms   ->  21 frames a second
    six camera feeds   31.2 ms   of that
    the 782x455 main   12.0 ms

The six feeds are **170x92 pixels each** and together cost more than the main
view at twenty times the area. The renderer's work was never pixel-bound: each
feed drew all ninety-six latitude bands of a world whose disc was 301 px across
and of which the frame showed a corner, and asked for an outline for every
blotch of the ground lattice whether or not it could land on the picture.

Two culls — a band that paints nothing, a blotch whose box misses the frame —
plus a cap count that follows the disc's size. **21 to 32 frames a second.**

**Both first attempts were optimistic, which is the one thing a cull may not
be.** The band test compared the frame's *centre* against the cap's, which is
the real test with the boundary ellipse shrunk to a point. The feature test
bounded a blotch by the longer of its two conjugate radii instead of by
`hypot(ax, bx)`, and forgot that the wobble stretches every radius by up to
1.6. Sixteen pixels of a 782x455 approach moved — and I only knew because the
first thing I did after the speedup was render both versions and diff every
pixel.

**And I misread my own instrument for an hour.** Counting bands drawn, seed
after seed, I read zero and took it for a broken monkeypatch. It was the cull
correctly rejecting all ninety-six of a world the frame happened to miss. How
much this saves depends entirely on geometry — 81 of 97 kept with the disc
centre in frame, all 97 with it off frame and nothing to save at all, 42 with
the world larger than the picture. A bar set on the best case would have called
the honest middle case a failure, so the check states all three.

Seven mutations swept. Four passed the first version of the suite — two
weakenings of the feature bound, and two that make the renderer slower without
making it wrong — and closing them meant flying the seed that had exposed the
original bug and counting bands at the act rather than at the rule.

`test_drawbudget.py` — 3 checks. Full suite green: **1,050 checks**.

## 2026-07-30 — SEEDFALL: the catalogue screen had no catalogue in it (#catalogue)

Task #80 names "the catalogue/codex screens that display them", so I went and
looked at the Codex. Its "Fleet classes" tab lists **thirty-five hull classes** —
name, binomial, tier, blurb, role, crew, mass, hull, hold, jump, build time —
and not one picture. Nor do the nineteen colony and station classes. Five hull
silhouettes, four berths, nine classes of star and seven kinds of world have
been in the sky for cycles, and none of it reached the one page whose whole job
is to show a captain what is out there.

`ui/thumb3d.py` is a portrait: one subject, on the same renderers everything
else uses — `render3d` for meshes, `spheres` for worlds, `stars3d` for stars —
so a hull in the codex and the same hull on the tactical plot are the same ship.
Every fleet-class card carries one, and a new **"The sky"** tab holds the seven
worlds, the nine stars and the four berths, each with a line about what it is.

**Five pictures across thirty-five classes would not have been a catalogue
either.** A class's proportions now come from its own entry: hold against mass
gives beam, jump range gives length. Both are printed in words on the same card,
so the portrait and the specification are the same facts twice — and thirty-five
classes give thirty-five distinct builds, a SPORE fat and stubby against a
LEVIATHAN long and lean.

Both anchors were measured rather than guessed. The first pair — 0.011 t of hold
per tonne and a 3 ly jump — put nearly every class hard against the beam cap,
because the median hull actually carries twice that and jumps nearly twice as
far, so the whole spread was spent before it started.

Two things came from looking at the page. The hull portraits were framed at 3.4
and cut the docking ridge off the top of every card. And a star's corona runs to
eleven disc radii, so on a card it was still tinted at the corner — nine classes
appearing to sit on nine differently-coloured backgrounds, which reads as a
layout fault rather than as light. `stars3d.draw` takes a `max_glow` now: the
sky wants no cap, a catalogue card does.

**Nine mutations, eight caught, and the ninth was my own tautology.** The check
claiming the class spread was bounded asserted `1 - CLASS_SPREAD <= beam <=
1 + CLASS_SPREAD` — a bound that moves with the constant it guards, and it
passed happily with the spread set to nine. Written figures now: nothing may
pass 1.5 either way, and the widest hull in the game sits at 1.42.

`test_catalogue.py` — 5 checks. Full suite green: **1,047 checks**.

## 2026-07-30 — SEEDFALL: the tactical plot showed one ship twice (#3D)

`data/hullforms.py` opens with "Five families, five silhouettes" and gives each
a length, a beam, a taper, a facet count and its own furniture — a grown hull's
docking ridge and radiator bloom, a Yards hull's welded spine and slab bow, a
hybrid's cradle, a Dry Choir lattice, a xeno hull's shards. `sim/plans.py` built
the captain's own ship from those numbers for the cutaway panel. Nothing else
read them. `ui/battle3d.py` drew:

    pairs = [(b.enemy, models3d.HULL, "warn"),
             (b.player, models3d.HULL, "lumen")]

One mesh, one size, both combatants. Thirty-five chassis across five families,
masses from 60 t to twelve billion, and the plot showed one ship twice.

It also drew them **standing on their tails**. Every model in this package is
authored nose along +z; the plot's hulls sit in the z=0 plane with the camera
looking across it; and `render3d.draw` could spin a model about its own pole and
tilt it over but not then point it anywhere — the tilt decides which way it
falls. A heading could not be read off the picture at all. `draw` takes a `yaw`
now, applied after the tilt about the world's vertical, and `data/hulls3d.py`
builds the five silhouettes from `hullforms`' own numbers. Size follows mass,
off the median of the thirty-five and a sixth root, because anchoring on one
hull and taking a cube root put everything above a NAVIS against the ceiling.

**Two shapes were too alike, and both times the fix was the mesh.** A xeno hull
"is not symmetrical and does not explain itself" — and was a body of revolution
like the other four, sharing 83% of its outline with a grown hull; shards on a
symmetric spindle are still a symmetric spindle, so its spine bends now. Then a
hybrid, which *is* a grown body in a cradle, sat at 79%: standing the cradle off
from 1.14 beams to 1.62 took it to 63%, and made the cradle the silhouette
rather than a stripe on one.

**The mutation sweep put four holes in the new suite at once**, and they were
all the same hole: every check asked `hulls3d.mesh_for`, `_family` or
`_hull_scale` directly, so rewriting the *call* in `paintEvent` changed nothing
any of them looked at. The answer was a check that renders the widget and reads
the picture — which then took two more rounds, because comparing a NAVIS with an
ANTIPHON varies their mass too, and a mutation fixing only the family still
moved the frame. A CORAL and a CARAVEL are both exactly 9,000 t in different
families; that pair leaves the shape as the only variable.

And one hour lost to a hard abort with no output: `_app()` hands back the
QApplication, the check discarded it, Python collected it, and the next QWidget
killed the process with "Must construct a QApplication before a QWidget". A
reference count, wearing a setup error's clothes.

`test_hullshapes.py` — 7 checks. Nine mutations swept, all caught. Full suite
green: **1,042 checks**.

## 2026-07-30 — SEEDFALL: nine star classes, one white dot (#catalogue)

`data/starclasses.py` has carried a `core` colour per class since it was
written — an M dwarf's salmon, a K-type's amber, a G-type's cream, an A-type's
blue-white, a black hole's violet. `ui/viewport._star` worked that colour out
into a local called `tint` and then drew:

    p.setBrush(QColor(255, 253, 244))
    p.drawEllipse(point, radius, radius)

The same off-white, nine times. So **the black hole — whose own entry says there
is nothing to see, and that the accretion disc is the only reason you know where
it is — was drawn as the brightest object in the picture**, identical to an
A-type at twenty-two solar luminosities.

Two lines above that fill is a comment congratulating an earlier cycle for
noticing the *corona* colour was going unused. It fixed the halo and left the
core. Worth keeping: a guard against unconsumed *fields* cannot catch this,
because `core` is read — into a variable that is then dropped.

`ui/stars3d.py` gives each class its own picture, and all three levers come from
the data already there:

- **Colour**, with a hot centre whose whiteness follows luminosity, so an
  A-type reads as violent and an M dwarf as an ember.
- **Corona**, spreading and brightening on a log scale — the range is 0.0002 to
  22, and a linear law gives eight of the nine classes no glow at all.
- **Kind.** A black hole is an absence with a ring round it. A white dwarf and a
  neutron star get a hard rim, because degenerate matter has an edge.

And **a binary pair is drawn as a pair**. Its entry says "two stars about a
common centre" and it was one disc, in a cream within eight points of the
G-type's — so the two classes rendered as the same star. That came out of the
checks, not the eye: the closest pair scored 8 apart, and the fix was the
picture rather than the threshold.

**The mutation sweep earned its keep twice.** Six mutations, five caught at
once. The sixth pinned the disc's *innermost* gradient stop to white and walked
past two versions of the check: the first sampled off-centre, where the class
colour rules; the second compared two classes at three pixels — the size most
stars are actually seen at — and still passed, because the mutation moves a warm
class toward white without moving a hot one. What caught it was a property with
a measured margin: an M dwarf's centre carries 98 points of red over blue, and
the mutation leaves 46.

`test_starlight.py` — 5 checks. Full suite green: **1,035 checks**.

## 2026-07-30 — SEEDFALL: the world was being drawn thirty metres from the lens (#3D)

Two cycles ago I gave worlds a surface and could not make it show in the conn.
Last cycle I noticed the docking view was still a flat wash and let it go. This
cycle I chased it, and the answer was underneath all of it.

`ui/spheres.py` sizes a world from `camera.project`'s second return value. That
value is the offset's component **along the view axis** — how far *ahead* the
world is — not how far away. On the axis the two agree, which is why every
synthetic render this project has ever judged a world by looked correct. Off the
axis `ahead` falls toward zero however distant the world is, and `screen_radius`
is `tan(asin(r/d))·focal`, which runs away as `d` drops under `r`.

Measured in the conn on an ordinary approach to a station:

    a 2,419 km world, 2,981 km off, 73° from the view axis
    screen radius drawn      5,611 px       on a 360x290 frame
    screen radius true         335 px
    frame covered in ground       99%   ->   15%

So a berthing approach — the activity the whole conn exists for — looked out at
a featureless wall of planet, and the surface work of two cycles went into
ground that was being drawn thirty metres from the lens. The picture now shows
space, stars, the lit station, the sun, and the world's limb curving across a
corner of the frame with its ground texture on it.

**The same mistake was in my own code from the previous cycle**, in the same
shape: `surface.visible_span` took the horizon from the world's *forward*
distance, which collapsed to nothing for anything off the axis. It also
estimated the ground in frame with an orthographic ratio of radii, which
understates it eightfold at close range and cut the detail lattice's cells to
about a pixel each. Both are gone: the span is measured by casting the axis ray
and a corner ray at the globe and taking the angle between where they land — no
projection model, no small-angle assumption.

And a sphere's outline is a circle only head-on. Off-axis it is an ellipse, and
the projected centre can be off the frame while the world still fills a corner.
`surface.limb` projects the tangent circle itself, which is exact at any angle;
its first version returned nothing the moment one of those points fell behind
the lens — precisely the close approach it exists for — and clips against the
lens plane now.

Retuned on the back of it: with the span finally measured correctly the lattice
was cutting cells to fit a frame it thought was eight times smaller, so
`CELLS_ACROSS` goes 12 → 9. Same picture, more of it: 35% of a low-orbit world
carries ground texture against 23%, at the same local contrast.

Seven mutations swept, all caught — the seventh only after the coverage check
was tightened from "under 55%" to a measured 6–26%, because a silhouette drawn
**71% oversized** had been passing at 38%.

`test_projection.py` — 5 checks. Full suite green: **1,030 checks**.
