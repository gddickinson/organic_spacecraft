# What this is — the design, pass by pass (4 of 8)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

**Something worth looking at.** The conn's windows drew a flat coloured circle
with a radial gradient behind it. At twelve kilometres that reads as a distant
object; at six hundred metres it reads as a flat coloured circle, which is a
poor thing to be watching while berthing a hull against a shipyard.

`ui/render3d.py` is the substrate: a camera, perspective, back-face culling,
painter's-algorithm depth sorting and flat shading from a light. A few hundred
`QPainter` polygons a frame — no textures, no shaders, no dependency and no
build step for a game that is otherwise pure PyQt. `data/models3d.py` holds
the meshes, authored at radius 1 and scaled by whatever the object really is,
so one yard mesh serves a four-hundred-metre quay and a two-kilometre hub.

Three things it taught me while being built:

- **The light needs a source.** `sim/conn.py` records `star_dir` when an
  approach opens: the star sits at the system's centre and the target
  somewhere out from it, so light falls along the target's own position
  vector. One line, and a world gets its terminator on the correct side.
- **A sphere must be one colour.** Every other mesh alternates shade
  face-by-face so a flat-lit structure still reads as having parts. Do that
  to a sphere and you get a chessboard, and the chessboard eats the
  terminator — the one thing that makes a planet look like a planet.
- **The first pass was almost entirely black.** A handsome yard, correctly
  lit, and unreadable. Ambient went from 0.22 to 0.40.

**And the cameras were not looking where the ship points.** `conn.nose` is the
3D vector the main drive is aimed along; the camera basis was built from
`conn.heading`, a bare yaw angle **nothing in the game has ever written to**.
So swinging the hull round with the thrusters changed the flying and not the
view. `viewport.hull_frame` builds one set of axes from the nose, and the hull
keeps its belly toward whatever it is approaching — which is what makes the
ventral camera worth having in orbit, and which one inverted cross product had
backwards, putting the planet you are orbiting in the camera pointing at the
sky.

**Half the diplomatic board was still free.** `sim/allegiance.py` has charged
you for being seen working for somebody since it was written — relief to the
Concordat costs you with the Charter and the Freeholds — but `broker` and
`denounce` never got the same treatment. Measured at 70 standing with everyone:

    relief   (concordat)             charter -0.2, concordat +3.3, freeholds -1.3
    broker   (concordat, freeholds)  concordat +1.8, freeholds +1.8  <- nobody else
    denounce (concordat, freeholds)  charter +6, concordat +6, freeholds -14

Brokering is the most public thing a captain can do: it seats two powers at a
table, thanks you with **both**, moves their relation twenty-eight points and
decides the Concord ending — and the Charter, at -20 and -35 with the pair of
them, did not notice.

`allegiance.defenders_of` is the mirror of `offended_by`: who minds you
*attacking* a power rather than serving one. Deliberately symmetric — offence
starts below Cold, devotion above Correct — which means it costs **nothing at
dawn**, because the Verge opens with no friendships in it. Denouncing gets
dearer exactly as you pacify the sector, which is a better property than any
number I could have tuned: measured, nothing owed in a hostile sector and
-6.1 once the Freeholds have a friend.

And brokering is priced on what it **moves**, not on the thanks. `courtship`
has already shrunk the thanks to under two points at any standing where
brokering is permitted at all, so pricing the offence against the thanks made
the loudest act on the board cost a third power six tenths of a point.
`BROKER_WEIGHT` is to a settlement what `TREATY_WEIGHT` is to a treaty; the
Charter now pays -4.1 for a peace between the two powers it likes least.

*And a bug it surfaced in the board.* Brokering charges a third party twice
over — once as an enemy of each principal — and `preview` quoted that as two
separate lines, so the screen promised the Freeholds -3.30 and then again
-4.90 while the act moved them -8.20. Both halves were true and neither was
the number. `preview` merges to one line per power now, because the board is
read by a person.

*What it does to the game.* Over twenty determined chronicles, a captain who
only brokers reaches the Concord **6 times in 20**; one who brokers and keeps
everyone sweet, **19 in 20**. The ending is not harder — it asks to be paid
for. `test_politics`'s determined-broker bot was updated to court as well as
broker, because brokering alone was a complete strategy only while it was
free, and it clears the same bar far better than before.

**The Weave.** A hull's jump range is ten light years. The sector is
sixty-eight across with a median pair distance of twenty-nine, so a fresh
captain reaches **three systems of forty-one** and the rest of the Verge is
scenery. The interstellar model was never the problem — `data/crossings.py`
has four profiles with real time dilation and a documented three-cornered
trade between reaction mass, the crew's remaining years and all the work they
would otherwise have done. The problem was *reach*.

`sim/weave.py` derives nine ancient anchors from the galaxy's own seed by
farthest-point sampling — take the system nearest the middle, then repeatedly
take whichever is furthest from everything chosen so far — so they are
landmarks, identical in every process, and need no save migration. They are
paired in a ring with chords across it: the ring makes the network legible and
the chords are what make holding one system worth anything. Three burn at
dawn, lit as a connected *chain*, because a link burns only when both ends do
and three scattered singletons would have been a Weave with one working link
in it.

`sim/gates.py` is what a captain can do about it:

- **Transit is instant** — the only act in the game that does not spend the
  calendar — and pays a toll to whoever holds the far end, priced on the light
  years saved. Standing halves it or closes the ring entirely, which makes the
  Weave a political object rather than a convenience.
- **Waking a dark anchor** needs `weavecraft`, which requires Xenolith
  Metallurgy *and* the Foldrunner Coil. Learn only one and you have a very
  expensive ring you cannot switch on — the ancient-and-modern mixture the
  whole system is built on.
- **Laying your own** costs more again, and only ever onto a ring already lit.

Measured, across five sectors: a drive alone reaches 2–35 systems of 42; a
fully-lit Weave adds **8 destinations, never fewer than 2 of them beyond any
amount of hopping**.

And the price. **The Bloom travels the Weave.** A lit ring hands a share of an
infested system's growth to the far end regardless of the light years, scaled
by the same stage and provocation as everything else it does. Differenced
against the same chronicle with the carry disabled, the far end of one ring
went from clean to **0.70 infested in 180 days against 0.00**. One link is
survivable; a fully-woken Weave with something bad on it is how a sector dies.
That is the decision the system exists to pose, and it is why waking an anchor
is not simply an upgrade.

**Only rings the captain lit carry.** The three anchors burning at dawn have
been burning for four centuries; whatever they were going to spread, they
spread long ago, and the sector's present state is the equilibrium that
already includes them. This is not a dodge — it is where the decision belongs,
and it fell out of a real regression.

The first draft's carry was flat, which made it a growth channel that did not
care what the Bloom had been through, and it swamped the check that provoking
the Bloom makes it grow faster (31.8 against 33.4, when the provoked run
should be larger). Scaling it by `stage` and `provoked` fixed that and made it
a firehose instead: the sector's burden crossed several stage thresholds
inside a single tick, so the escalation check saw three stages where it wanted
four — it was *jumping* them. Three long-chronicle suites went with it, all
for the same reason: `clock.advance_days` returns early once `victory` is set,
so a sector that drowns freezes the calendar and nothing ages, escalates or
flies again.

Tuning the constant against four checks at once is fitting to tests, not
designing. Charging the world afresh every tick for rings the powers have run
for centuries was the actual mistake. With the carry restricted to what the
captain wakes, the baseline is untouched, every long-running check is valid
again, and the consequence lands exactly where the choice is made.

**Engines with places, a hull that has to point them.** A player asked three
questions the game could not answer: is there a braking burn as well as an
accelerating one, does the ship turn to aim its engines, and where are the
engines on the hull. The honest answers were no, no, and nowhere — drive slots
were a *count*, `Conn.heading` was written by nothing at all, and `flight._leg`
handed back one lump with the braking burn living only in a comment.

`data/mounts.py` gives thrust somewhere to come from: main drives mount aft on
the transom and push along the nose, without exception, because that is what a
main drive *is*; a hull with two slots and one engine pushes 0.34 off the
centreline. Attitude clusters are not fitted — every hull is built with six of
them, because a ship that could not rotate could not be flown and there is no
loadout in which that is an interesting choice.

`sim/thrusters.py` asks what that means for a particular ship. Mass comes from
the chassis `hull` rating plus every part and every tonne in the hold, so the
loadout stops being a stat line: the same Fusion Torch pulls **2.06 m/s² on a
SPORE and 0.108 on a LEVIATHAN**, and the LEVIATHAN takes 493 seconds to swing
end for end against the SPORE's 50.

`sim/attitude.py` is the consequence. The main drive pushes along the nose, so
a burn in a new direction is a *turn* first — three ticks to swing a NAVIS 90°
— and the turn spends reaction mass out of the same tank.

**Worlds are painted now, not built** — `ui/spheres.py`, and it is the fix the
previous cycle filed rather than started.

A sphere does not need geometry. It projects to a circle, and a Lambertian
sphere's brightness across that circle *is* a radial gradient whose centre is the
sub-stellar point: so the light is one gradient, exact rather than interpolated,
with no faces to show at any size. The latitude structure goes on as nested
ellipse caps, because a circle of latitude projects to an ellipse — which is what
makes the bands curve round the limb and read as a ball instead of a striped coin
— and a thin bright limb carries the atmosphere seen edge-on. The mesh path stays
for hulls, stations and gates, which are not spheres, and for ring systems, which
want geometry because they interpenetrate the world they circle.

Measured: **11 ms against 88.8 ms** for the same world close up, the worst
brightness step across the surface down to 10 levels — which is quantisation, not
a facet — and the phase ordering right all the way round, from the star behind the
camera through half-lit to eclipsed.

The level-of-detail from the previous cycle went with the meshes it served: there
is one mesh resolution again, kept only for the catalogue checks that compare one
kind of world against another under a fixed light.

**Four things had to be got wrong first, and each one is a lesson about where the
bugs live in a renderer.**

- **Ninety degrees out.** A first draft built each latitude cap by rotating a box
  with `QTransform`, and put the pole on the local *x* axis while the ellipse and
  the skirt both ran along *y*. Every world came out as a vertical split with the
  polar colour flooding the rest. Rebuilt from explicit vectors, which cannot be
  ninety degrees out because there is no frame to confuse.
- **Sign-guessing the light.** The first lighting worked the star's screen
  direction out from the light vector and came out evenly lit, because two
  conventions — "the direction light travels *from*" and "which way is up on the
  picture" — both had to be right at once. Now the *sub-stellar point itself* is
  projected: `render3d.draw` lights a face by `dot(normal, -light)`, so the
  brightest point on the sphere is the one whose normal is `-light`, and asking
  the camera where that lands asks exactly the question the mesh asks.
- **An eclipsed world lit like noon.** Using the projected distance to place the
  gradient failed when the sub-stellar point was on the *far* hemisphere, where it
  still projects inside the disc. The offset comes from the phase now — the disc
  centre's own brightness — which puts the bright pole at the centre at full day,
  on the limb at half, and clear of the disc when the star is behind the world.
  And when the star is exactly behind either the camera or the world there is no
  direction at all and the disc is *uniform*, which needed saying separately: a
  gradient centred on the disc drew an eclipse with a bright middle.
- **Two lighting laws.** The first version invented its own brightness constants
  and drew every world darker than the mesh it replaced. It reads
  `render3d.AMBIENT` and `DIFFUSE` now and samples the same law at known angles —
  `AMBIENT + DIFFUSE·cos θ` at `sin θ` of the radius — so there is one lighting
  law with two ways of evaluating it rather than two laws.

- **A multiply of white is a no-op, so half the lighting law was missing.** The
  light went on as one `CompositionMode_Multiply` gradient — and a multiply can
  only darken. `AMBIENT + DIFFUSE` is **1.45** at the sub-stellar point, every
  level above 1.0 clipped to the same white, and so a grey-154 world that should
  have run **223 → 62** across its face ran **154 → 62**: the entire lit half
  flat, and the terminator a cliff **6% of the face** wide. It survived a cycle
  because the check compared the two *ends* of the profile, which were right. The
  multiply carries everything at or below unity now and a `Plus` pass carries the
  excess above it (`OVER_BRIGHT`), which brightens toward white rather than toward
  the surface's own colour — an approximation, said out loud in the code, because
  `Plus` cannot know what is underneath it. Measured after: **223 → 62 over 18%
  of the face**.

And two about the checks. Measuring "no facets" by walking a scanline reported 121
levels, which was the *silhouette* — the atmosphere ring against empty space,
which is meant to be an edge. It samples inside the limb now. And **the defect
above was found by a mutation that survived**: flattening the falloff to no
terminator at all changed nothing on the picture, because every stop was already
clipped to the same white. A surviving mutant is not always a missing check — this
one was pointing at the code.

**Worlds were faceted, and four attempts to smooth the shading failed.** Graphics
picked because it was asked for. At 22 rings by 30 segments — 660 faces, already a
fine mesh — a world filling the window read as the polyhedron it is: flat shading
gives each face one colour, so you could count the quads across the terminator.

The obvious answer is Gouraud, and `QPainter` has no per-vertex colour, so I tried
to reach it with a `QLinearGradient` per face. **It cannot be done, and it took
four goes to see why.** A linear gradient is constant perpendicular to its own
axis, where real Gouraud varies — and that error alternates with a quad's
orientation, so every version put a *checkerboard* on the sphere:

1. Corner to corner, from the darkest-lit vertex to the brightest. Two vertices of
   a quad often sit at nearly the same brightness, so which counted as darkest
   flipped face to face.
2. The same, with the gradient's *axis* taken from the projected light instead.
   No change: the colour ends were still chosen by brightness.
3. Ends chosen geometrically along that axis. A quad whose per-vertex colours run
   (low, high, high, low) still had them swapped whenever the extreme pair changed
   edge.
4. Ends ordered by *latitude*, so the colour can never reverse. Still checkered,
   for the structural reason above.

It was not the rim term either — forcing that to zero left the pattern exactly as
it was, which is how the colour pairing was identified as the cause. All of it was
reverted.

**Geometry is what worked.** Rendered side by side, 22x30 is plainly faceted and a
mesh four times finer is smooth, and the cost is in *faces* rather than pixels —
6.7 ms against 20 ms for the same world at any size on screen. So worlds are built
at two resolutions and `ui/viewport.py` spends the fine one only above
`FINE_ABOVE` pixels of radius: a body nine pixels across in a camera thumbnail
looks identical either way and must not cost four times as much. Measured, the
whole conn window repaints in 102 ms against a 700 ms timer — 15% of a frame — and
a distant world still costs 8 ms.

**Where the faces go matters as much as how many.** At about 2,550 faces either
way, 44x58 still bands horizontally, because the colour runs with latitude and
rings are what sample it; 70x36 and 96x26 kill that banding and stripe the limb
instead, because segments are what round the silhouette. 60x44 is the pair that
reads smooth in both, and that is what `FINE` is.

**It is better rather than beautiful, and worth saying so.** The residual banding
is inherent to flat-shaded polygons with one colour a face, and the real fix is to
stop treating a sphere as geometry at all: project it to a disc and shade it
analytically with an offset radial gradient, which is exact for a Lambertian
sphere and cheaper than either mesh. That is its own piece of work — task #97.

**The price register sorted on the sticker price and never said what the flight
cost.** Trading picked for breadth. The market itself turned out sound — measured
across all thirteen goods there is a 20% spread and no same-counter money pump,
and the depth is real: buying 280 t of ore drove the price 36 → 43 and drained the
stock to nothing, which then relaxed back over a year. The fault was in the
*information*.

`best_markets` returned a price, an age and a confidence, and the panel drew a
straight-line light-year count beside it. No hops, no days, no notion of whether
the ship could get there. Measured over six sectors and six commodities:

- **32% of the recommendations were to systems the ship cannot reach at all** —
  not far, not dear, unreachable, and nothing said so.
- **44% of the lists put a worse port first.** The worst case ranked a port worth
  0.5 a day above one on the same list worth 3.9 — seven times better, listed
  below it.

`reach.route_to` has existed since the contract board needed it, and its docstring
names this very lesson: the board "named a reward and a deadline and never once
said where the work *was*". The rows carry `hops` and `days` now and selling ranks
on **revenue a day**; buying ranks on price with the days breaking ties, because
there what you want is the low number. The unreachable are kept and marked rather
than dropped — a jump drive is a thing a captain can go and buy — but they rank
last. On one board that means Lumen Mouth, paying the *highest* price for ore at
₡31, sits at the bottom reading "beyond your jump · nothing you can reach", while
the port that can actually be flown to shows "1 hop, 7 days · 4 a day".

`reach.routes_from` is the walk, once, for the whole list: `route_to` used to run
its own breadth-first search per call, and the register asks about four ports for
each of thirteen commodities on every repaint.

**Two more faults fell out of the reordering, both latent:**

- **`freight.runs` said "a price you wrote down beats a price somebody described
  to you" and did not do it.** It kept whichever run had the higher `worth`, and
  the register happened to win often enough that the check on it passed. Measured,
  **18 of 44 runs known both ways have the desk quoting the better number**, so a
  rumour was replacing your own notes four times in ten. It implements the rule
  now.
- **`from_register` inherited a display limit.** It generates candidate runs and
  called `best_markets` with its default `limit=4`, so what work existed at a desk
  depended on how many rows a panel draws. 549 register-known runs are offered
  where the top four used to be, and 54 commodity-and-port sets are larger than
  four.

**One asteroid gave up 8,427 tonnes instead of 140.** Mining picked for breadth,
and found the largest arithmetic hole in the game so far.

`raise_rate` lifts material with four rigs — `mine` for ore, `phos` for
phosphate, `drink` for volatiles, `graze` for biomass. `actions.extract` wore the
body down with **two of them**: `st.mine + st.drink`. So a phosphate rig and a
harvest tendril raised material and depleted nothing. Fit a token mining root
beside them, and one body gave up **8,427 t over 283 spells against an ordinary
hull's 140 t over 8** — sixty times its worth. Not infinite, because `extract`
refuses a hull with no mining root and no harvest tendril at all, which is what a
first draft of the check claimed and had to withdraw. Sixty times is enough.

`mining.RIGS` is the one table now — the pairs `raise_rate` walks — and
`mining.rig_of` sums it, so a rig that lifts material is a rig that wears the body
down by construction rather than by two lists agreeing. Measured after: 159 t
against 128 t, which is a hull's fittings mattering rather than a fountain.

**And the forecast was biased by the option it was comparing.** `prospect`
estimated the average rate at the midpoint of what was left and multiplied by days
and a `WORKING_LOSS` fudge. Against actually working the body out it was 2% low on
a bioleach and **45% low on a bore** — the error tracking how fast the method
depletes, because the faster it goes the fewer steps the average is taken over.
The days figure was separately a fifth too long, because `prospect` used
`max(mine, drink)` where `extract` used the sum.

It is a **dry run** now: it walks the body down in five-day steps through
`raise_rate` and the same depletion arithmetic, and adds up what comes off. It
cannot disagree with the act because it *is* the act with the ship left at home —
the same reason `sim/preview.py` flies a throwaway twin instead of predicting a
burn. Checked with events silenced, the error across all four methods is −0.0%,
+0.0%, +0.2% and +0.1%; with events live it varies ±6% either way, which is a
windfall and an accident behaving like noise rather than bias.

What that buys is a legible decision. On one ice body the screen now reads: a cut
and a bore both recover about 98 t, but the bore does it in 64 days against 135;
a bioleach recovers **254 t** and takes 386. Speed against total, and both figures
true.

**A hang, and the lesson from it.** The dry run's `while` loop exited only when
the depletion arithmetic advanced, so a mutation that removed the advance spun for
ever and took the whole sweep with it — I had to kill it, and killing it left the
mutation in the tree, which is its own hazard. There is a hard step bound beside
the depletion test now: a loop whose termination depends on arithmetic is a hang
waiting for someone to break the arithmetic, and a check that hangs is worse than
one that fails because it costs everything and tells you nothing.

**"Grievances are counted" was true in three places and false in the code.**
`approach.preview` tells a captain refusing a levy that "they will file it as a
grievance, and grievances are counted"; the levy's own `costs` line in
`data/approaches.py` says "they collect grievances". What actually happened was

    dip.ensure(game).grievances = getattr(dip.ensure(game), "grievances", 0) + 1

— a counter on a field `DiplomaticState` **does not declare.** Nothing read it,
and because it was undeclared the save's decoder dropped it: set it to seven,
save, reload, and it comes back as nothing at all.

**An existing check covered it and passed anyway.** `test_envoy` asserted the
counter went up, reading it through `getattr(state, "grievances", 0)` — which is
how an undeclared attribute passes for a field — and never saved. The number
moved, the check was satisfied, the feature was missing.

The deeper fault was an asymmetry. An overture is remembered
(`diplomacy._remember`), and so is an answer to a demand for ground —
`territory.answer` notes all three of pay, cede and refuse, and
`grudge.because` puts them on the diplomacy screen. **An envoy's answer was the
one dealing with a power that left no trace**, so a captain who had refused four
levies faced a power that priced him badly and a screen that could not say why.

`data/approaches.AS_ANSWERED` is the table and `approach._remember` is the door,
mirroring the one diplomacy already had. A grievance is a *memory* now, which is
the machinery that already turns dated things into a price bias and into whether
a power will deal with you — and which persists. Measured: refusing levies takes
the Charter from **0.0 to −28.6** feeling and its prices from x1.000 to
**x1.051**, and the screen reads "Their feeling −34 · Their prices to you +6% on
what you buy · Y1 D001 · you left our levy unpaid (−14)". Accepting a
requisition is deliberately *not* remembered: a power that recorded every barrel
of ore would have a ledger nobody could read.

Three fields went with it, all read by nobody: `Envoy.choice`,
`territory.Demand.choice` — both redundant now the memory carries the answer —
and `DiplomaticState.favours`, whose story is the guard's.

**The guard's accessor hatch was cut too wide.** It credited any dict subscript
or `.get("literal")` as reading a field, and that hid
`DiplomaticState.favours` for a whole cycle: the field is read nowhere, and
`sim/officials.py` keeps a *different* per-official favours dict which it reaches
as `store["favours"]`. A field excused by an unrelated dict that happens to share
its name is a guard doing nothing. What counts now is a **named accessor reaching
a field by string** — `getattr`/`hasattr`/`setattr`, and a two-argument
`get`/`set_to` with the subject first and the key second, which is the shape of
`options.get(game, "hints")` whose body is a `getattr`. The credited-name set
fell from **538 to 153**, and the swept total from 8 unread to 6.

**And a mirage worth recording.** I came to this by measuring whether the four
powers ever move among themselves, saw the relations matrix freeze after year six
and the venture count stop dead at 36, and spent a good while building the case
that the powers stall. They do not. `advance_days` returns early on
`game.victory`, the unattended chronicle had reached the **"ruin" ending**, and
the clock was correctly waiting for the player to take it or carry on into the
epoch. There is no venture bug. The lesson is about the measurement: a headless
probe that advances years without driving the ending is measuring a stopped
clock, and `tests/chronicle.py` already knew that — it guards its loop on
`game.dead and not game.victory` and asserts it got twenty rounds in.
