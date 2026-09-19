# Session log, part 13 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-30; undated entries keep their original place.

## 2026-07-30 — SEEDFALL: the checks were flying a ship the game does not fly

Went after #83 — "the last few per cent of a high orbit at a small body", a
limitation `test_orbits` records in its own failure message rather than hiding.
Found something bigger on the way in.

**`conn.apply(conn, axis, main, throttle)` — the signature is
`(conn, axis_id, main, ticks, throttle)`.** Four check call sites passed the
throttle positionally, into `ticks`, where `max(1, ticks)` quietly rounded it to
one tick and left the throttle at its default of fully open. So **every flight
those checks flew had the main drive wide open** — which is the one thing
`pilot.usable_throttle` exists to prevent, and this module's own comment records
why: an unthrottled drive made a bigger engine *worse*, because one tick of a
fusion torch is 124 m/s and the computer would light it to trim ten, overshoot,
correct the overshoot, and never converge.

`ticks` and `throttle` are keyword-only now. A positional throttle is a
`TypeError` rather than a silent misfire.

**And one check was passing because of it.** "A lopsided hull still makes orbit,
slower and dearer" flew body 0 of each system — small bodies, where an orbit climb
is thruster work and the throttle cap has nothing to bite on. With the throttle
actually reaching the drive, one engine took **0.79× the time and 1.03× the
mass**: losing half the drive cost nothing at all. Re-measured at the largest body
in each system, where circular speed runs from three to twenty-five kilometres a
second and the drive does the lifting: **2.32× the time and 1.91× the mass**. Both
figures are now in the check, because the reversal is a fact about the game and
not a nuisance.

**Then the thing #83 was really about.** Every orbit check flies with
`conn.rcs = 99999` — "the fuel is checked elsewhere" — and `orbits.heights_for`
offers a rung on `holdable` alone, which asks whether the thrusters are *fine*
enough and has never asked whether the tank is *big* enough. Flown with the twenty
tonnes a hull actually carries, the high rung of a 153 km asteroid:

    spent all 20 t in ~2,000 ticks reaching 95% of the height
    then ordered a burn every tick for another 18,000 ticks
    refused each time by can_burn — nothing moved, nothing said
    the approach never resolved

A captain watching the conn would see the computer working and the numbers not
changing, for ever. `outcome.resolve` ends it now: as **orbit** if the hull is in a
sound one — reporting the height it actually reached, *"550 km against the 1,753
asked for, and the tanks are dry — this is the orbit you have"* — and as **dry** if
it is not in orbit and no longer closing. Still closing is left alone, because a
dry hull can arrive on momentum and taking the approach off it would be wrong.
Measured after: 716 ticks instead of never, and every one of 32 offered heights
across three sectors resolves inside 6,000 ticks on a real tank.

**Two things I tried and took out again**, both recorded in the code because they
are the obvious next ideas:

- **Modulating the thrusters** down to a minimum impulse bit, since a full pulse
  is twice the deadband and a ship therefore cannot settle. It changed the
  flights not at all — because of the argument bug above, which is how I found
  that.
- **A thrust-limited spiral** in place of the vis-viva transfer demand: circular
  speed nudged one pulse toward the aim. It settles beautifully at a small body
  and **descends into the ground at a large one**. `_across` returns the tangent
  *in the xy plane*, so an inclined arrival is asked to flatten itself, and that
  plane change is worth thousands of metres a second at a 57,000 km world — the
  axis fell 62,133 → 56,737 km over 1,288 ticks with the drive at full throttle
  the whole way. The shipped law survives it only by out-muscling its own plane
  change. That is filed as #101, and the spiral cannot be used until it is fixed;
  the limit cycle it would fix is #102, with the measurement that names it: **1,046
  tonnes against an ideal of 4**.

I also wrote three functions and deleted all three. `orbits.trim_dv` and
`orbits.settled` were to let the computer stop when it could do no better; measured,
they changed the outcome of **0 of 32 flights**, so they were decoration.
`orbits.transfer_dv` — an exact Hohmann — I argued should stay as the thing a fuel
quote would be built on, and `test_reachable` disagreed: *"1 public function
nothing ever calls. Either wire it into the game or delete it."* Kept-for-later is
exactly what that guard exists to refuse, and the arithmetic is four lines whenever
it is actually wanted.

Two new checks, 904 across the suite, all green.

## 2026-07-30 — SEEDFALL: whose word it is (#93, two fields nobody read)

Two fields had been written since the day their features shipped and read by
nobody at all.

**`Rumour.heard_at`** — the port you were told something at. Truth was
`not rng.chance(kind.unreliable)`, a per-kind coin flip, so a story about the far
side of the sector told at a lonely outpost by people who have never been within
forty light-years of it was exactly as good as one about the next star over told
at a Fleet Hub where a dozen hulls a week put in.

**`Mind.met` and `Mind.first_met`** — how many times somebody has dealt with you,
and since when. Every decision in the game came from *standing*, which is what you
have done, and nothing from *acquaintance*, which is who you are to them. A
captain who had traded at the same quay for six years and one who arrived last
week were the same stranger.

**Word travels by ship**, so `rumours.provenance` grades a story by how far it has
come and how busy the quay telling it is. It is one figure with three readings:
the truth roll at creation, the trust the desk prints, and the price. Measured
over 2,214 stories from six sectors:

    local source     30% of stories   true 77%   desk says 75%
    a few jumps out  27%              true 62%   desk says 62%
    the far side     44%              true 45%   desk says 47%

The desk's number *is* the rate, within two per cent, because it is the same
number the roll used. And the price follows it — within a kind: a salvage lead is
dearer than a nobody-goes-there whatever its source, because it is worth more if
it holds up, and the panel says so rather than leaving the comparison to be
misread.

**Acquaintance is not regard.** `memory.acquaintance` reads both halves — the
business done and how long since the first of it — and `charts.value_to` pays for
it: a survey is a claim about places the buyer cannot check without flying there
themselves, so who the surveyor is to them is part of the price. **38,845 from a
stranger, 50,499 once they know you.** Twenty-four dealings crammed into a month
is worth less than the same business spread over four years, which is the point of
keeping `first_met`.

**A constant I chose instead of measured.** The provenance scale ran from 12 to 55
light-years, which sounded right and was not: across 4,264 port-to-system
distances in five sectors the median is 27, the 80th percentile 40 and the longest
69 — so 55 sat at the 96th percentile and **three per cent of stories ever reached
the far end of the scale**. The whole top of the range was decoration. At 11 and
42 the bands come out 30/27/44% with 17% saturating. The check that caught it was
one I had written to assert the geography was big enough for the term to bite,
which is the only reason I looked.

Also cleaned up two things in my own checks: a "best source against worst source"
price comparison that read backwards, because the dearest lead in the sector is a
dear *kind* rather than a good source; and a shadowed name in the panel where the
acquaintance readout reused `known` from the sector-charted count above it.

Nine new checks, 902 across the suite, all green.

Both fields were on `test_declared`'s `ALLOWED` list — the guard had found them
and they were excused with an entry naming this task and what it would take. The
guard then failed the moment they *started* being read: "ALLOWED still excuses
fields that are now read — delete the entry". A stale excuse is a lie of the same
kind as an unread field, and the check that catches one catches the other.

## 2026-07-30 — SEEDFALL: technology that changes somebody else's market (#96)

The tech tree had **sixty-two nodes and one economic effect**. Thirty-three carry
a bonus and the only one of them that touched money was `trade` — a haggling
bonus, which moves the price *the captain* is quoted at a counter and nothing
else. Nothing anybody could ever learn changed what a market held, what a port
could make, or what anything cost anybody but the player. The tree was a shopping
list of ship parts.

A **process** is the other kind of technology: one that makes a thing. Twelve of
them (`data/industry.py`), each naming a technology the tree already describes and
the commodity its own blurb already claims — a Separation Gut separates, a
Magnetosome biomineralises magnetite, Xenopharmacology makes xenopharma.

Licence one to a power and it becomes an industry at every berth they hold. They
pay out of the treasury the last cycle gave them, so a licence is bounded by
whether they can find the money; their berths' baseline supply of that good rises;
and the price comes down and *stays* down. Played, one year, Separation Guts sold
to the Concordat: **alloy 134 → 118 across their berths, against 187 everywhere
else**. A berth they found afterwards comes up with the industry already running.

**It cuts both ways, and that is the design.** A port that starts making alloy is
a port that stops paying well for alloy, so licensing your separation gut to the
power whose quays you have been selling alloy at is a way to put yourself out of
business. The panel quotes it in credits a tonne before you sign: 168 quoted
against 157 it actually cost.

The buyer's side had to make sense too, or nobody would ever sign — so an industry
lifts what its holder's berths yield (`INDUSTRY_YIELD`, six per cent each). A
licence pays for itself in a season to a year, which is a deal a power takes for a
permanent industry. And selling one is a public act: the licensee gains standing,
every rival loses it, the two of them fall out a little, and the one illicit
process — unlicensed seed — costs you with everybody including the buyer.

**A real bug, found by checking that the illicit process had somewhere to work.**
`make_market` stocks unlicensed seed at nine ports in twenty-one and leaves the
rest with nothing. `tick_market` then adopted a baseline of 1.0 for any stock that
had none, and its supply floor lifted a zero supply to 0.02 so the shim adopted
*that*. Between them, **all twenty-one ports were selling contraband one day into
every chronicle** — most of the point of smuggling, gone, since 2026-07-2x when
the baseline shim landed. A stock with no baseline *and* no supply is skipped now:
9 of 21 at day zero, 9 after a day, and the tenth two years later is a berth the
Freeholds founded, which is correct. It is the only way a market can say "not
here", and the seed licence is the one thing allowed to open one.

**Three of my own errors, all in the checks rather than the code.**

- The industry check read a **6% fall where four of five berths had fallen 11%**.
  The fifth had a *strike* on and its price had gone up fifteen per cent. An
  industry is a permanent change in what a place makes and a shock is a temporary
  change in what it costs; the two are deliberately separate fields, and a
  measurement that averages across both is measuring neither.
- The forecast check said every berth was **40–50% out, all in the same
  direction** — the signature of a scale factor, not a bad forecast. The forecast
  quotes what the captain would be charged, standing and haggling included, and I
  was comparing it against a raw price at rep zero. A captain holding every
  process in the tree carries a trade bonus of 0.48 and pays a quarter under the
  sticker. Priced the same way on both sides: **worst forecast 8% out across 21
  berths, a year later**.
- A payback-period band of 60–900 days that the cheapest process failed at 59.
  The constant was fine; the band was arbitrary. `INDUSTRY_YIELD` is pinned by
  what one industry does to a power's income (3.5–9.5%) rather than by a number
  the check reads off the constant it is testing.

Ten new checks, 893 across the suite, all green.

## 2026-07-30 — SEEDFALL: somebody pays for it now (#95, the public purse)

The four powers of the Verge were penniless in the literal sense. They held
ports, annexed systems, blockaded each other and censured each other, and no
credit ever changed hands over any of it. A `Port` carried a level and a list of
services fixed at galaxy generation, and **nothing in the game could raise it,
lower it, build a new one or close an old one** — the only berth that could come
into existence was the player's own Free Port, and the only one that could vanish
was that same one. The map you flew in year one was the map you flew in year
twelve.

Now every power keeps a treasury. `data/exchequer.py` holds the numbers,
`sim/exchequer.py` the purse, and the shape is chosen so the sector has an
**equilibrium rather than a direction**:

- A berth pays its holder `level × 90` a day and costs `30 × level²`. So an
  outpost clears 60, a station clears 60, and a **Fleet Hub clears nothing at
  all**. Prestige is expensive.
- A surplus founds an outpost on ground the power holds, or promotes one up
  `world.galaxy.PORT_KINDS` — the same ladder that made every port in the sector,
  rather than a second copy of it in `data/`.
- A deficit takes the cheapest berth down a step, and an outpost that goes down a
  step **closes, taking its market with it**.
- A venture costs its sponsor a 9,000 stake, and a power that cannot find it
  starts nothing. One with a war chest and nothing left to build gets restless
  instead — which is the sink that stops a treasury growing for ever with nothing
  to spend it on. (The bench's banked research points were exactly that bug.)

Played, eight years, one sector: **17 berths and 32 levels became 30 and 75**, 49
works paid for, 6 steps given up, and the four purses holding steady between
118k and 215k rather than running away. The ship's log fills up with it — *Dry
Choir: Station at Pale Crossing is now a Fleet Hub*, *Charter: a new Outpost is
open at Thule's Mouth*, *Outpost at Iron Rise is now a Station*.

**A blockade now costs the blockaded something.** A venture puts a shortage on a
rival's market, a pinched berth yields 35%, and the purse feels it: measured end
to end, a landed blockade took the Sanhedrin's income from 814 to 578 a day and
its margin from +334 to +98. In an ordinary chronicle a power is pinched about
**28% of the time**, so this is a standing pressure rather than a curiosity.

The player is on the ledger for one thing: a Free Port of their own pays a
harbour due. `player_built` was read by exactly one function before this — the
one that tears the harbour down again.

**Three things playing found that reading would not have.**

- **`tick_market` was throwing the port's size away.** `make_market` scales the
  opening stock by the berth's level, and the daily drift then pulled every
  commodity at every port toward the same `supply × 60` regardless — so within
  about a month a Fleet Hub held exactly as much cargo as an outpost. The level
  was decorating the opening inventory and nothing else. It takes the level now:
  a year in, outpost 1,300 t, station 1,779 t, hub 2,832 t, and holding.
- **The register offered a berth that no longer existed.** With ports able to
  close, a two-year-old note about a good price drew exactly like a live one —
  hops, days, revenue a day and all. Rows carry `open` now, closed berths are
  marked and ranked below open ones, and the note is kept because it is still a
  true record of a price that was paid there.
- **`test_geography` crashed on the None** — it listed the ports, ran eight
  years, and read `system.market.stock` on one that had since been given up. Its
  spread is measured over the berths still open at the end now, on both sides of
  the comparison.

**And two checks that were passing on luck.**

- *"A long enough chronicle ends a career"* put an officer two years short of
  their span and ran forty years. It never ran forty years: `advance_days`
  returns on `game.victory`, the chronicle reached its Ruin ending at day 3,650,
  and the clock stopped. It got away with that only because the officer usually
  retired first — the odds of still standing a watch eight years past ninety-six
  are about **one in four**, and this time the dice went the other way. It plays
  on through the ending the way a player does now (`legacy.begin`), and since
  `END_SLOPE` is named in `sim/lifespan.py` and nowhere else, it also measures
  the *rate* over a cohort of sixty: half of them gone five years past span.
- *"Being provoked genuinely makes it grow faster"* wanted the provoked Bloom
  ahead in at least six of eight sectors and got five. The mechanism is fine —
  over twenty sectors it is **+8.5% aggregate and ahead in 15** — but three years
  of growth runs close to saturation, which compresses the gap, so per-sector it
  loses about a quarter of the time. Twenty sectors and a *share* rather than a
  count, so widening the sample now makes it more stable instead of inviting the
  same edit next time. That is the third widening of this one check, and the two
  earlier ones were also for changes that never touched the Bloom.

Ten new checks, 883 across the suite, all green. The other half of #95 — NPC
settlements on habitable worlds, of which there are still exactly none — is filed
as #99, and a harbour due on the player's own trade as #100, deliberately left
until it can be done with the balance suites in view.

## 2026-07-29 — SEEDFALL: a multiply of white is a no-op, and it cost half the light

#98 was three mutations of the painted-world renderer that the last cycle's sweep
could not kill. Its own task note said: *establish why before writing the check,
because it may mean the terminator check is measuring something other than what it
claims.* It did. One of the three was pointing at a defect in the code.

**The falloff could be flattened to no terminator at all and the picture did not
change.** The reason: the light went on as a single `CompositionMode_Multiply`
gradient, and **a multiply can only darken**. `AMBIENT + DIFFUSE` is 1.45 at the
sub-stellar point, so every level above 1.0 clipped to the same pure white. A
grey-154 world that should have run **223 → 62** across its face ran **154 → 62** —
the whole lit half flat, at exactly the surface's own colour, with day meeting
night in a cliff **6% of the face** wide. Flattening the falloff moved stops that
were all already clipped to the same value, so of course nothing moved.

It survived a whole cycle because the check compared the two *ends* of the profile,
and the ends were right: 154 against 62 is still a ratio, still mirrors when the
star swings round, still monotone into the shadow. Endpoints cannot tell a gradient
from a step.

The fix is two passes. The multiply carries everything at or below unity; a `Plus`
pass carries the excess above it (`OVER_BRIGHT = 0.66`). The additive part
brightens toward white rather than toward the surface's own colour, because `Plus`
cannot know what is underneath it — an approximation, and one the code says out
loud rather than dressing up as a law. Measured after: **223 → 62 over 18% of the
face**, against the 223 the lighting law predicts.

Then two assertions the renderer had been getting away without:

- **Full day is brighter than the surface's own colour** — the missing claim,
  checked against `AMBIENT + DIFFUSE` so it cannot drift from the law it tests.
- **The falloff has width**, measured as the span of the face at middling
  brightness. 6% before, 18% now.

**The third mutant was a lesson in what a mutation actually does.** Cutting the
latitude bands from 96 to 6 did not make worlds coarser, it made them *smaller*:
each band paints an ellipse plus a skirt covering everything south of it, so with
only a few bands the southernmost swallows the disc and the northern cap is never
reached — **7.5% of the face left as bare sky at the pole**. Every existing check
looks *across* the disc through its middle, where the hole is not, and by their
measure a coarse world is if anything smoother. So the new check asks the one thing
they cannot: is any of the sky still showing through the world? Five tilts,
pole-on to edge-on. The shipped renderer is solid at all of them.

The three checks were one file until it passed 500 lines; the lighting ones now
live in `tests/test_lighting.py`, on a shared plate helper, and produce the same
numbers they did before the split. `test_worlds.py` keeps the catalogue and
`test_sky_kit.py` the stars and rings.

All three mutants die now, and a second sweep confirmed the new `OVER_BRIGHT` is
not an unchecked constant. Full suite green.

## 2026-07-29 — SEEDFALL: a world is a disc with a gradient on it

Took #97, the fix the last cycle filed rather than started, and it worked.

A sphere does not need geometry. It projects to a circle, and a Lambertian
sphere's brightness across that circle *is* a radial gradient centred on the
sub-stellar point — exact, not interpolated, and with no faces to show at any
size. The latitude structure goes on as nested ellipse caps, because a circle of
latitude projects to an ellipse, and that is what makes the bands curve round the
limb instead of reading as a striped coin. A thin bright limb carries the
atmosphere seen edge-on. `ui/spheres.py`.

Measured: **11 ms against 88.8** for the same world close up; the worst brightness
step across the surface down to **10 levels**, which is quantisation rather than a
facet; and the phase right all the way round, from the star behind the camera
through half-lit to eclipsed. The level-of-detail machinery from last cycle went
with the meshes it served.

**Four things had to be got wrong first, and every one was in a convention rather
than in the idea:**

- **Ninety degrees out.** The caps were built by rotating a box with
  `QTransform`, which put the pole on the local *x* axis while the ellipse and the
  skirt ran along *y*. Every world drew as a vertical split with the polar colour
  flooding the rest. Rebuilt from explicit vectors — no frame, nothing to confuse.
- **Sign-guessing the light**, which came out evenly lit: "the direction light
  travels from" and "which way is up on the picture" both had to be right at once.
  Now the sub-stellar point is *projected*, which asks the camera the same
  question the mesh asks.
- **An eclipsed world lit like noon**, because the sub-stellar point can be on the
  far hemisphere and still project inside the disc. The offset comes from the
  phase now. And the two degenerate cases — star exactly behind the camera, or
  exactly behind the world — have no direction at all and needed handling as
  *uniform*, since a gradient centred on the disc gave an eclipse a bright middle.
- **Two lighting laws.** I invented brightness constants and drew every world
  darker than the mesh it replaced. It reads `render3d.AMBIENT` and `DIFFUSE` now
  and samples the same law at known angles, so there is one law evaluated two
  ways rather than two laws.

**And three about the checks, which is where this cycle's real weakness was.**
A sweep of the painted renderer caught **1 mutation of 7** at first, for a reason
worth writing down: every catalogue check in `test_worlds.py` still rendered
through `mesh_for`, so they were all testing a path the game had stopped taking.
Pointed at `spheres.draw` they bite, and the seam count fell to 0.

Then two of my own assertions about the *middle* of the disc were simply wrong,
and both times the renderer was right: with the star square to one side the
terminator **is** the middle and the far half is correctly flat at ambient; with it
swung two-thirds behind the camera the terminator is two-thirds across and the
middle is still full day. Monotone-into-shadow is the claim that holds in every
phase, so that is the claim.

Ending at **4 of 7**. Three mutations still survive — a flattened falloff, latitude
circles that stop being squashed, and the surface painted in six bands instead of
ninety-six — and I have spent well past a cycle on this already, so they are
recorded as unpinned rather than papered over. The first is the one that puzzles
me: with every gradient stop set to the same level the profile inside the limb
ought to be flat and the terminator check ought to fail. It does not, and I have
not established why.

And one about my own check: measuring "no facets" along a scanline reported 121
levels, which was the silhouette — the limb ring against space, which is supposed
to be an edge. It samples inside the limb now.

Full suite green.
