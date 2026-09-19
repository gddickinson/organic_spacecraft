# Session log, part 10 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-30 to 2026-07-30; undated entries keep their original place.

## 2026-07-30 — SEEDFALL: one shipyard stood in for the whole catalogue (#catalogue)

Task #80 asks whether the catalogue is real variety or the same shape
recoloured. It was neither. `ui/viewport._sky` drew **everything that is not a
world** with a single mesh:

    render3d.draw(p, camera, models3d.SHIPYARD, sight.at, ...)

Across four sectors that is 67 quays, 36 Weave gates, 16 Fleet Hubs and five
errands of traffic — a courier, an ore prospector and something with no
transponder all rendered as a station with docking arms.

The information to do better was already on the objects and thrown away.
`track.Contact.berth` has carried quay / hub / holding / gate since it was
written, with a docstring saying in as many words that a screen should not have
to read an id to know a shipyard from something older than the Charter — and
`sky.build` set `look=""` for every anchorage and every hull.

So: `data/berths3d.py` (quay, hub, holding, gate) and `data/ships3d.py`
(courier, trader, prospector, patrol, and the unmarked hull a raider is drawn
as, because "no transponder" is the picture). `Contact.errand` and
`Target.errand` carry what a hull is doing, the sky keeps both, and
`models3d.present` is the one door — asked by the sky *and* by the approach
target, so what you pick out at forty kilometres is what you come alongside.

**Three things came from looking at the pictures rather than the checks.**

*Every ship was the same blob.* Hulls are authored nose along +z and the sky
drew them at a tilt of 0.42 — twenty-four degrees off dead ahead. Nine
silhouettes existed and five of them were invisible. `models3d.ATTITUDE` holds a
hull broadside; a berth keeps the shallow tilt that lets its rings read as rings.
Shipping the meshes without this would have delivered almost nothing.

*The prospector was the trader.* The silhouette check put them at 73% overlap,
and the render agreed: both a chunky can with a bell. A prospector is not a hull
with cargo in it, it is a frame with equipment hung on it, and the open space
between the parts is most of what tells it apart. Reworked spindly and lopsided
— spine, slung ore cradle, long boom, counterweight — it drops to 62%.

*Keys guessed rather than read.* The first `SHIPS` table carried invented
aliases ("trade", "prospect") beside the real ids and had no entry at all for
`raider` — the one errand that most matters to recognise. `sim/traffic.ERRANDS`
is two modules away and names them exactly; the suite now refuses an errand with
no silhouette.

Nine mutations swept, eight caught. The ninth — fattening the prospector's spine
— moves the worst pair from 66% to 67% and is recorded as a *mild* mutation
rather than a gap: the boom and cradle still carry the shape, and the bar at 72%
sits above anything blunting one hull can reach and far below the 100% that
one-mesh-for-all scores.

`test_silhouettes.py` — 5 checks. Full suite green: **1,025 checks**.

## 2026-07-30 — SEEDFALL: a world you dock over should look like a place (#3D)

First cycle on the 3D axis. I began by rendering the conn's own viewport and
looking at it, which is the whole method here: at 200 km over a 3,000 km world —
the altitude berthing happens at, so the backdrop to the entire docking
activity — the frame was **one flat colour with three banding arcs across it**.

`data/worlds3d.py` paints a world by latitude, and says so: caps for nothing,
belts for a giant. It buys a great deal cheaply and has one consequence nobody
had looked at — a world painted by latitude alone is *the same picture from
every side*, and from low orbit it is no picture at all.

`data/surfaces.py` and `ui/surface.py` add the other axis, in two sizes:

- **Named features** at a latitude *and* a longitude — maria, continents,
  storms — stable per body, so a world looks like itself every time.
- **A lattice of ground texture** fixed to the ground and sized to the frame.
  A list fine enough for low orbit would be tens of thousands of features; a
  lattice costs the cells in view, and the same patch of ground answers the
  same way every time it is looked at.

A cap on a sphere projects to an ellipse, and the honest way to get it is to
ask the camera: project the centre and one rim point per tangent, and the two
screen vectors that come back are conjugate radii of exactly that ellipse. Right
at any range, foreshortening included, no special cases. The first draft sized
it orthographically and was visibly wrong from 200 km up.

**Four things the pictures taught me, in order.**

*Soap bubbles.* Six detail cells across the frame is a handful of circles each a
sixth of the picture. Twelve is ground.

*Bokeh.* Every mark was a perfect circle and the overlaps were perfect lenses.
Two harmonics of the polar angle turn a disc into a blotch and cost nothing —
the outline was already a polygon. Fixed weights then gave every blotch the same
three-lobed notch, so the weights vary per feature too.

*A splash.* A gas giant's storms were sheared along an *arbitrary* tangent, so
the giant read as a fingerprint. Weather on a banded world runs along the band,
and east is a thing with a definition. Even so, blotch texture fought the belts:
a giant now gets a few great storms and no ground lattice, because a giant has
no ground.

*A smooth marble.* Detail only ran when a world nearly filled the frame, so the
ordinary view — a world seen whole — was untouched by the whole cycle. Lowering
the threshold to a quarter of the frame is what turned the globe from a marble
into a place.

**And the checks found a real defect in my own lattice.** It hashed each cell by
its global index and *positioned* it relative to the camera, so the ground slid
as the hull moved and each blotch changed identity at a cell boundary — the
boiling the lattice exists to prevent, shipped under a comment claiming it could
not happen. Snapping the cell to the globe fixed it; the check that caught it
moves the camera and asks the cells the two views share to agree.

Measured after: local contrast from low orbit 0.36 → 1.17, over 37% of the
world; half a turn changes 42% of it; two rocky worlds differ over 36%.

Twelve mutations swept, all caught. One caught nothing and is a near-no-op — the
axis a *round* blotch is stretched along cannot show — so the claim it guards is
pinned geometrically instead: east is square to the pole, exactly.

`test_surfaces.py` — 8 checks. Full suite green: **1,020 checks**.

## 2026-07-30 — SEEDFALL: the orders panel forecast the order, not the turn (#combat)

Combat this cycle, on the crew-stations axis. I started by playing engagements
headlessly and accounting for where the damage goes, which turned up the usual
sort of thing and then something better.

`stations.order_preview` costs each order before it is given — and it costed the
order *in isolation*. The captain does not give an order in isolation. They give
it inside a turn, and the two seats they have just walked away from run
themselves. Measured on a Bastion at 45 of a 50 heat cap, sitting down at
engineering and ordering **vent**:

    the panel said    heat 45 → 20 of 50
    the turn ended at 74

The gunner left at the guns fires everything that bears, always, whatever the
heat. That behaviour is deliberate — `combat._run_stations` says so in as many
words, and it is what a battle computer is bought to fix. Quoting it at nobody
was not. **The one order in the game whose entire purpose is cooling was
advertised with the wrong sign**, and *hold fire* — which really does cool this
hull, by 10 — read as the order that does nothing.

`test_orderplan` had checked this since it was written, and passed throughout,
because it compared the forecast with `run_engineering` called directly. Both
agreed. Both were answering a question nobody asks.

The forecast now steps the turn the way `combat.take_turn` steps it —
engineering, then the helm, then the guns, then the radiators — and every part
of it goes through the door the act uses: `bearing_set` is the list `_salvo`
fires and the log counts, `will_burn` drops the dry mounts (announced aloud and
then charged no heat, because `_fire` returns before `add_heat`), and
`idle_gunnery` is asked by the panel *and* by the turn, so the two cannot drift.

**Two things I got wrong on the way, both caught by measuring rather than
reasoning.**

*The geometry moves under a forecast.* Folding in the other seats left a
residual: eight turns in a thousand still promised cooling and delivered
heating, every one of them at *present the broadside* — the order whose own
blurb says everything on the flanks bears. Our guns fire after our own helm has
moved us and before the enemy moves at all, so flying the order on a copy of the
body is not an approximation, it is the answer. Two dataclass copies, and the
whole error class went.

*The ceiling belongs to `add_heat`.* Shedding heat is a plain `max(0, heat - x)`
that never consults the ceiling. I clamped on every step and on a step of zero,
which cooled a hull sitting above a ceiling lowered by radiator damage by five
points a turn that it never lost. `delta >= 0` and `delta > 0` are different
programs when the hull is already over.

Result: **2,095 played turns, two hulls, twelve orders, hot and cold, full and
empty magazines — every one ending exactly where the panel said, to the
hundredth.** The stated exception is the turn that ends the engagement, when
`_finish` returns before `_end_of_turn` and there is no end of turn to have; the
suite counts those rather than hiding them.

Twelve mutations swept, all caught. One of them — swapping the salvo's
arc-and-band test for arc alone — caught nothing, and the honest reading is that
it is a *no-op*: the two sets never differ at any range these hulls fight at,
0 turns in 89. The real gap was next door, in my own check, which ran only with
full magazines where "what trains" and "what burns" are the same list. With an
empty one, both mutations bit.

Looking at the rendered panel also changed it twice: the first wording invited
the captain to halve a figure that was already halved, and the first gunner
clause repeated a forty-character warning under all five helm orders — one the
panel above already carries in red — which pushed the only figure that varies
off the end of the row.

`test_turnplan.py` — 8 checks. `test_orderplan`'s "helm orders are silent on
purpose" is retired: they speak now, because a turn spent flying still leaves a
gunner firing. Full suite green: **1,012 checks**.

## 2026-07-30 — SEEDFALL: a treaty that promised berthing and charts, and gave neither (#diplomacy)

The cycle opened on diplomacy, testing INTERFACE.md's claim that the Concord
ending is "a diplomatic achievement rather than four grinds". It is: driving
every available overture at all four powers with unlimited stores reaches 4/4 Kin
and 6/6 pairs at peace in **year 2**, and `diplomacy.drift` — which pulls every
pair back toward its hostile baseline by about 13% of the remaining gap a year —
is live and measurable (+25 → +17.3 → +10.7 → +4.8 → −0.3 over five years). The
eleven-year freeze in the first run was my harness hitting `game.victory`, which
stops the clock. So the ending is sound, and I went looking on the same axis.

**A treaty has been sold since treaties were written as "a signed instrument:
mutual berthing, shared charts, and a clause about the Bloom that nobody expects
to be honoured", at 30,000 credits and a 180-day cooldown.** The third clause is
a joke on purpose. The other two were as well.

Signing appended a faction id to `DiplomaticState.treaties`. Two things read that
list: `treaty_bonus` (+3% on the trade stat, named on no screen) and the matrix's
"treaty" pill. Measured at Vesper Bight: wharfage **1.714% before signing and
1.552% after** — and the whole of that fall was the *standing* the treaty granted,
which a tribute at a third of the price buys as well. Charts known: **0 before,
0 after**. Both named benefits were fiction, and the one real benefit was
invisible.

`sim/accord.py` is the two clauses, and it is the only place either is worked out:

- **Berthing.** `wharfage.rate` — already the single door for the charge — asks
  `berth_relief` and takes 50% off at the signatory's quays, multiplied through
  rather than added, so standing keeps the widest spread on the page (a factor of
  four Kin-to-Hunted) and the instrument is a second factor of two on top. Because
  it lives in `rate`, it reaches the market board, the freight forecast, a cargo
  contract's sourcing figure and the holder's purse in one move.
- **Charts.** They hand over what they hold of their own space that you cannot
  see, priced at what a broker would want for the same paper. This turns out to
  be **geography**: at the opening the Charter — whose space you are sitting in —
  can give 3 systems worth 4,060, and the Freeholds 11 worth 50,597. So *which*
  treaty first is a decision about where you intend to fly, and only one of the
  four is worth its price on the charts alone.

The desk now quotes both before you sign — "Berthing · 50% off wharfage at their
3 quays" and "Their charts · 9 system(s) of theirs you cannot see — about ₡25,851
of broker's paper" — and both figures are a *dry run* of the act rather than a
formula resembling it: `preview` and `perform` ask the same `accord.worth`. The
market board says why its number fell.

**Three things worth keeping from how this was checked.**

*Isolate the lever.* The first version of the berthing check let `perform` grant
its standing — and standing is also an input to `wharfage.rate`. It would have
passed on a treaty that did nothing but flatter you. Both checks now restore
`game.rep` after signing, on the envoy path too, where `accept_rep` lands instead.

*Both doors.* There are two ways to sign — propose one, or accept the one an
envoy brings — and `data/diplomacy.py` already records what happened when they
disagreed about `TREATY_WEIGHT`: waiting to be asked was the way to sign for
free. I had wired the charts to the proposing door alone, which is that bug in
reverse. `accord.hand_over` is the one delivery both call, with a check that
signs through each and compares.

*Read the screen you built.* The board's first wording was "takes 0.6% … — and
50% off that", and the 0.6% already has the relief in it. Looking at the rendered
page settled it: the sentence invited the captain to halve the figure twice.

Twelve deliberate mutations, all caught by the check that names their subject —
including one that only bites at the Freeholds, whose independent outposts fly
the faction's flag and take no due, so a quay count read off the flag rather than
off `wharfage.holder` over-promises at exactly one power in four. My first
version of that check tested only the Charter, which has no such ports. The
project's own reachability guard then caught a dead public function in the new
module and it was deleted.

`test_accord.py` — 10 checks. Full suite green: **1,004 checks**.

## 2026-07-30 — SEEDFALL: a commission promising a technology nobody had written (#missions)

Missions was the last breadth area untouched this session. The commissions read
well — four chains, twelve stages, pay multipliers escalating 1.2 → 1.5 → 2.2, and
the desk already says the premise, the stage count, the credits, the standing and
which rival commission taking it shuts. So I went looking at what it *doesn't* say,
and found something worse than a missing line.

`Chain.reward_tech` has been on the table since commissions were written. The
Reliquary sets it to **`xenolinguistics`**, and there is no such technology — not
in the research tree, not anywhere. `chains._finish` does this:

    if chain.reward_tech and chain.reward_tech not in game.research.unlocked:
        game.research.unlocked.append(chain.reward_tech)

...so finishing three escalating stages for the Dry Choir appended a phantom
string to the bench's list. Measured: it changes the bonuses **not at all**. And
`reward_tech` appeared on **no screen anywhere**, so the one commission in four
that hands over a whole node of a fifty-eight-node tree advertised itself as
credits and standing, exactly like the three that hand over neither — and nobody,
player or check, was in a position to notice the node did not exist.

This is task #38's shape again: *annex* was gated behind a technology nobody had
written; here a reward *is* one.

It grants `firstcontact` now — First Contact Protocol, tier 4 of the xenology
branch, 1,100 points, +0.25 diplomacy and +0.25 research — which is precisely what
the Reliquary is about: the Choir reading what a relic site says. `reward_tech_of`
is the door, and the desk reads **"And the work itself — First Contact Protocol —
1,100 points of research you do not have to do."**

**The guard I wrote to catch it was wrong first, and the way it was wrong is the
interesting part.** Sweeping every tech id named anywhere in `data/` against the
research tree reported **thirty-seven phantoms**. Thirty-six of them were real:
twelve xeno parts, listed in three tables, naming ids that live in
`data/xenotech.py` — a *second namespace*, gated behind studied alien work rather
than the bench. A check that cried wolf about twelve pieces of working content
would have been deleted inside a month, and rightly. So the guard knows about both
tables, and only the Reliquary's id was ever in neither.

It also refuses a xenotech id used *as a commission reward*, which is a real id in
the wrong place: `_finish` grants by appending to `research.unlocked`, and only a
tree node can go there — incorporating alien work is `xeno.incorporate` and would
need its own field. I found that out by mutation: pointing the Reliquary at
`vent_symbiosis`, which exists, still fails.

Six deliberate breakages, six caught: the phantom restored, a reward naming a real
id in the wrong namespace, the desk not naming the technology, the door refusing to
resolve it, a stage posting a kind the contract book has not got, and a commission
shutting a rival that does not exist.

Two new checks, 994 across the suite, all green.

## 2026-07-30 — SEEDFALL: the chart's price told you what the chart was for (#exploration)

`sim/intel.py` ranks a system 0 to 3 and writes down, in as many words, what each
rank knows. Rank 0 is "a name, a position and **a body count the registry will not
stand behind**". Rank 1 — which is exactly what buying a chart gets you — is "read
at range or bought as a chart. **The bodies are real**; what is on them is
guesswork."

The screen honoured neither sentence. It printed `len(sys.bodies)` at every rank,
sized the star's marker by it, and — the part that made the whole thing circular —
priced the chart at `900 + 260 per body`. **Measured across a sector: forty-one
unknown systems, thirteen distinct prices, and the count inverting exactly.** 1,160
meant one body. 1,420 meant two. 1,680 meant three. The single fact a chart exists
to sell was written on its price tag, and a captain who could do a subtraction
never had to buy one.

So the bottom two rungs of a four-rung fog differed by a faction name and the shade
of a dot, on a screen whose own suite says **"how bad is public; where is earned"**.

Now: `intel.body_count` returns the count or None, the panel says *"how many
bodies, nobody has said"* until somebody has looked, the marker is drawn at a fixed
size for anything uncatalogued, and the price is `CHART_BASE + CHART_PER_LY ×
distance` — the trip somebody else made, which is the part of a chart a broker can
honestly charge for. Its correlation with the body count is **0.02, 0.00 and 0.05
across three sectors, against 1.00 for the old formula**. And the offer says what
it buys, in the #39 idiom: *"A chart of this system buys you how many bodies are
down there, whose space it is, a chart marker you can trust."*

**Two lessons from writing the checks, both about where a rule lives.**

Six of my seven mutations were caught at once; the seventh — putting the old
`r = 2.6 + len(sys.bodies) * 0.3` back — sailed through, because no check read the
ink. So I wrote a pixel-counting check in the idiom of the halo check that sits ten
lines above it in the same file. **It was no good**: eleven pixels against six on
*unmutated* code, and it went red in the full suite while passing on its own. A
marker is nine pixels across on a chart full of links, hatching and labels, and
there is not enough ink in it to difference. The halo works that way because a halo
is forty pixels of one colour; a dot is not.

The answer was to stop measuring the drawing and give the rule a name:
`map_view.marker_radius` is a function now, the paint reads it, and the check reads
it — equal for two uncatalogued stars four bodies apart, and 3.2 against 4.7 once
both are charted. That catches the mutation exactly and cannot flake.

Seven deliberate breakages, seven caught: the count handed over again, the price
back on the body count, the panel counting regardless, the marker measuring it out,
the offer saying nothing, a chart that reveals nothing, and the marker rule
inlined again.

Four new checks, 992 across the suite, all green.

## 2026-07-30 — SEEDFALL: five numbers whose own suite could not speak for them

I went looking for a defect in research and did not find one — `inquiry.draw` is
live (the zero in my tally was an artifact of how I wrapped it), evidence really is
spent, and starvation is properly graduated: fully supplied 1.00, missing one kind
of three 0.78, missing two 0.57, nothing at all 0.35. Recorded and moved on.

So I used the project's own sharpest tool instead. `tests/tripwire.py` changes
every tuning constant — zero, double, half — and reports the ones no check
notices. It was swept clean at task #60; **seven cycles have added constants since
and nobody had swept them.** Module by module: wharfage, parley, abilities,
territory, orbits, consorts, autopilot, wayhome.

Nothing came back *unprotected*. But five came back with the sweep's other and
more interesting verdict — **"protected only by a suite that does not name their
subject"**, which means the wide run catches them incidentally and the module's own
suite has nothing to say. And two of those five were **tautologies I wrote myself,
in the last three cycles, having quoted the docstring about this exact mistake
while doing it**:

- `parley.WAVERING_AT` — my check set the enemy's resolve to `WAVERING_AT ± 5`, so
  both probes moved with the number under test and the check passed with it set
  anywhere at all. It is 40 and 50 now, written down, and the step across the line
  is asserted to be worth about a quarter of the chance.
- `abilities.SHED_SHARE` — the only assertion was "the hull moved", which catches
  the share zeroed and not the share doubled. Shedding puts back half a skin: 0 →
  20 of 40, and a skin at three quarters goes to full rather than past it.

Three had no check anywhere:

- `territory.SEIZURE_PER_YEAR` — the price of refusing a claim, and nothing said
  what refusing risks. Played out instead of read: **9 of 60 defiant holdings taken
  inside a year**, and one defied for a single year before they came for it.
- `orbits.HEIGHT_TOLERANCE` — where the flying stops *and* where the pricing stops,
  and it moved into `orbits` two cycles ago precisely so one number would do both.
  1% off the rung costs nothing; 5% off costs 32.2 m/s, exactly the difference of
  the two circular speeds.
- `autopilot.ACROSS_FLOOR` — the floor under the tangent's *sense*, with a
  documented history: below it the sign of a dot product flipped between ticks and
  drove a comet's 6.8 m/s orbit from 335 km out to 1,340 and adrift.

**And the last one taught me something about writing these pins.** My first
attempt probed at 0.4 and 6 m/s — comfortably either side of 1.0 — and the sweep
*still* reported the constant unpinned. The floor is `max(ACROSS_FLOOR, one
thruster pulse)`, and a pulse is 0.45 on that hull: zeroing or halving the constant
leaves the line at 0.45 or 0.5, and 0.4 is still below both while 6 is still above.
A probe has to fall **between the values a mutation would put the line at**, not
merely on the right sides of the true one. 0.7 and 1.5 catch it, and the sweep now
names `conn` for it.

Five constants, five suites that can speak for them, and the sweep re-run on each
to prove it: parley → `parley, combat` · abilities → `abilities, combat` ·
territory → `territory, levy` · orbits → `orbits, conn, berthing, climbs` ·
autopilot → `conn`. None reads the constant it tests.

Five new checks, 988 across the suite, all green.
