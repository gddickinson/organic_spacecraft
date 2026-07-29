# SESSION_LOG.md — GESTALT project

Running progress log. Newest first.

## 2026-07-29 — SEEDFALL: the Weave, and the road the Bloom walks

The captain asked for faster-than-light travel: gates, a network of them, more
being built, ancient alien technology mixed with modern.

**What I did not rebuild.** The relativistic side is already there and good —
four crossing profiles with real dilation, two clocks (`Game.day` for the
Verge, `Game.ship_day` for the people aboard) and a documented trade between
reaction mass, the crew's remaining years and everything they would otherwise
have got done. Rewriting that would have been busywork. What is missing is
**reach**: jump range is 10 ly, the sector is 68 across with a median pair
distance of 28.6, so a fresh captain reaches three systems of forty-one.

**The Weave.** Nine ancient anchors, derived from the galaxy seed by
farthest-point sampling so they are landmarks in every chronicle and need no
save migration — the same trick anchorages and traffic use. Paired in a ring
with chords across it. Three burn at dawn.

A link burns only when **both** ends do, which is the whole shape of the
progression: the first anchor you wake buys nothing at all, and the log says
so — "Nothing answers yet." My first draft lit the three best-connected
anchors independently and produced a sector with one working link and two
rings standing alone in the dark. They are lit as a chain now.

Transit is instant — the only act in the game that does not spend the calendar
— and pays a toll to whoever holds the far end, priced on the light years
saved and scaled by standing. A power that loathes you will not open at all.
Waking a dark anchor needs `weavecraft`, which requires Xenolith Metallurgy
*and* the Foldrunner Coil: learn one half and you have a very expensive ring
you cannot switch on. That is the ancient-and-modern mixture the request asked
for, made mechanical.

Measured across five sectors: a drive alone reaches 2 to 35 systems of 42, and
a fully-lit Weave adds **eight destinations, never fewer than two of them
beyond any amount of hopping**.

**And the price, which is the part I like.** The Bloom travels the Weave. A lit
ring hands a share of an infested system's growth to the far end regardless of
the light years between them. Differenced against the same chronicle with the
carry disabled: **0.70 infested against 0.00** after 180 days. The network you
built to move fast is the network the enemy uses.

That broke things, honestly and instructively — twice.

The carry was flat, so it was a growth channel that did not care what the
Bloom had been through, and it swamped the existing check that provoking the
Bloom makes it grow faster (31.8 against 33.4, when the provoked run should be
larger). Scaling it by `stage` and `provoked` fixed that and made it a
firehose: three long-chronicle suites fell over, and the cause was the same
for all of them — `clock.advance_days` returns early once `victory` is set, so
a sector that drowns **freezes the calendar** and nothing ages, escalates or
flies again. The Bloom's own escalation check saw three stages where it wanted
four because the burden was *jumping* thresholds rather than climbing them.

I caught myself tuning one constant against four checks at once, which is
fitting to tests rather than designing, and stopped. The real mistake was
charging the world afresh every tick for rings the powers have run for four
hundred years. Only what the **captain** lights carries growth now: the
anchors burning at dawn are part of the sector as it already is, the baseline
is untouched, every long-running check is valid again — and the consequence
lands exactly where the decision is made, which is where it always belonged.

**What the mutation sweep taught me this time.** 8/11 first, and all three
misses were defects in my *checks* rather than in the code. The standing block
sat behind `if far.faction:` and silently ran nothing where the far end had no
owner, so a toll that ignored standing entirely and a ring that opened for a
power that loathed you both went unnoticed. And the helper that builds a rich
captain always granted Weavecraft, so removing the requirement broke nothing
anywhere. Fixed by giving the far end an owner and adding a check that asks a
captain who has not done the reading. 11/11 after.

Also this cycle, before the request arrived: I went looking in diplomacy and
found that **brokering a settlement costs nothing with anyone else** — every
ordinary overture charges `allegiance` for being seen, but `broker` and
`denounce` never got the same treatment, though brokering is the most public
act in the game and the only lever on the Concord ending. Parked as a task
rather than half-done.

Shipped: `data/gates.py`, `sim/weave.py`, `sim/gates.py`, the `weavecraft`
technology, the Weave drawn on the sector chart, `ui/weave_panel.py`, the
Bloom's road through `sim/threat.py`, and `tests/test_weave.py` (8 checks).
Full suite green.

## 2026-07-29 — SEEDFALL: engines with places, and a hull that has to point them

The captain picked the three gaps I had reported at the end of last cycle: no
accelerate/decelerate split, no attitude, no engine geometry. They interlock —
without geometry there is no thrust axis, without a thrust axis attitude means
nothing, and without either a transfer cannot be broken into burns.

`data/mounts.py` gives thrust somewhere to come from. Main drives mount aft
and push along the nose, without exception, because that is what a main drive
is; a two-slot hull running one engine pushes 0.34 off the centreline.
Attitude clusters are built into every hull rather than fitted — a ship that
cannot rotate cannot be flown, and there is no loadout where that is an
interesting choice.

`sim/thrusters.py` turns that into numbers for a particular ship: mass from the
chassis rating plus every part and every tonne aboard. The same Fusion Torch
now pulls **2.06 m/s² on a SPORE and 0.108 on a LEVIATHAN**, which flips end
for end in 493 seconds against the SPORE's 50. `sim/attitude.py` makes it
bite: the drive pushes along the nose, so a burn to port is a turn first.

**Three faults, all found by flying, each caught by the same general check —
more thrust is never worse.**

A bigger engine made every hull *worse*. One tick of a fusion torch on a SPORE
is 124 m/s, so the computer lit it to trim ten, overshot, corrected the
overshoot, and never converged: the recoverable drift ran 60, then 2, then 140
m/s across three drives of increasing thrust. Engines throttle now.

Then the control law itself. It was a ladder of branches — fix the drift, else
the closing rate, else coast — and it held together only at the flat delta-v
the conn used to assume. Across a 160-fold range of real acceleration the
branches fought each other. It is one law now: `target_velocity` says what the
velocity ought to be and the burn cancels the difference. Simpler, and stable
by construction rather than by tuning.

Then the last one, and my favourite: thrust comes in **six** directions, so
the nearest axis to a correction is up to 45° off it. Burning the whole error
along it overshoots and creates error somewhere else — a NAVIS hunting between
left, back, down, right and up at 650 m, never berthing. Only the component
that axis can actually cancel is burned. After that the envelope is monotonic
in thrust for every hull.

**Where I had to correct myself.** The burn plan's first draft derived a cruise
speed from the quote and reported the burns needed to reach it: 4,500 km/s, and
every hull in the game declared hopelessly inadequate. The arithmetic was
right — a NAVIS crossing 6.5 AU in five days *is* doing 0.75% of light speed —
and the conclusion was wrong. The game does not fly interplanetary legs on
Newton: it has a jump rating, a Foldrunner Coil, a relativistic profile, and a
`dilation` argument on the clock precisely because a hard crossing runs the
crew's clock slower than the sector's. I had invented a physics the game does
not use in order to fail it. The plan now describes the crossing in the game's
own terms — half the mass is the braking burn, the turns take the time this
hull needs, the coast is the rest — and `flight` stays the authority on days
and mass.

Also this cycle, before the captain answered: I went looking in diplomacy and
found that **brokering a settlement costs nothing with anyone else**. Every
ordinary overture charges `allegiance` for being seen — relief to the
Concordat costs you with the Charter and the Freeholds — but `broker` and
`denounce` never got the same treatment, though brokering is the most public
act in the game, gives standing with *two* powers at once, and is the only
lever on the Concord ending. Parked as a task rather than half-done.

Shipped: `data/mounts.py`, `sim/thrusters.py`, `sim/attitude.py`,
`sim/burnplan.py`, a rewritten control law, the engine board and heading on
the conn, the crossing broken into phases on the helm, and
`tests/test_thrusters.py` (8 checks). Mutation sweep 12/12 against a green
baseline. Full suite green.

## 2026-07-29 — SEEDFALL: a conn that changed nothing, and a station you could not click

Asked of last cycle's work: *is everything it declares consumed?* — the
question that has found more in this project than any other. For the conn the
answer was **nothing**. Measured, not guessed:

    flew into Fleet Hub at 20 m/s  ->  collision, damage 50.0
    berthed alongside              ->  0.54 t reaction mass, 0.8 h elapsed
    day 0 -> 0 · fuel 20 -> 20 · hull 336 -> 336 · where None -> None

So I had shipped a well-tested sandbox that did not pilot the ship. You could
wreck the hull against a station and walk off, berth alongside a quay and not
be docked, and spend reaction mass from a tank the ship never had — the conn
invented 36.8 t for a hull carrying 20.

`sim/berthing.py` lands it: the tank is the ship's volatiles, `commit`
charges what was spent, advances the clock, applies the damage and writes
`orbit_body`. Idempotent, and called on resolve, on break-off and on close, so
closing the window is not a way to un-burn the fuel. The gate is derived
rather than tuned — measured, contact distances are bimodal (0.000 AU at your
body, ≥2.2 AU otherwise), so the threshold sits in an empty gap.

**Two more faults, both from playing the consequences.**

Impact damage was linear and capped at 80, so putting the hull down on a world
at five kilometres a second cost sixty points of three hundred and thirty-six
— a captain could aim at a planet as a shortcut. Energy goes as v²; so does
the damage now, uncapped.

And making it quadratic exposed a worse one: **at 45 m/s the ship passed
straight through the station**. It covered 2.7 km in a 60 s tick and crossed a
400 m target between two contact tests, reported *adrift*, undamaged. The
fastest and most dangerous approaches were exactly the ones getting away with
it. Contact is swept along the whole path now.

**Two player reports, one cause.** The Fleet Hub was drawn on the helm chart
and was inert. "Set course — 4 d, 2 t", tooltip "Fly to Fleet Hub", called
`course_to`, which only *aims* — and a quay's body is usually the body already
targeted, so it set what was already set: target 0 → 0, orbit_body None →
None, day 0 → 0, fuel 20 → 20. Nothing. And clicking the Hub selected the
planet, because the painter drew its mark 11 px offset while the hit test only
knew about bodies, with an 18 px radius that swallowed it. `QUAY_OFFSET` is
one number now, read by both, and quays are hit-tested first.

**What the mutation sweep taught me this time.** 13/13 — but one of them only
after I stopped trying to catch the wrong thing. Changing `QUAY_OFFSET` is
*not* caught, and should not be: the painter and the hit test both read it, so
they move together and agree all the way down. That is the shared-gate lesson
again. The rule worth holding is that a world and its quay each select
themselves — which an offset of zero breaks, and which is now checked.

**Three more reports, and they were all one bug: a window that captured the
game instead of reading it.** Moored to the Fleet Hub, the conn opened on the
*planet* — bodies are listed before anchorages and it took the first row in
reach, though you are already in orbit of the body and approaching it is not a
manoeuvre. `ConnWindow.contacts` and `PlotCanvas.system` were both built in
`__init__`, so after a jump the board drew the system you had left while its
own contact list showed the one you had arrived in.

The same report asked whether positions are linked across the game. They are —
and I checked it rather than saying so: the helm chart and the plotting board,
two different projections, place the same body within **9e-16 AU** of each
other. What the report was seeing is physics. The periods are properly
Keplerian (0.40 AU → 92 days, 9 AU → 27 years), so over a four-day crossing
the outer worlds move half a pixel and the inner one two, on a chart where an
AU is twenty pixels. The traffic moves 11–18 px in the same time. Planets look
frozen because in four days they very nearly are.

Shipped: `sim/berthing.py`, swept contact detection and a quadratic impact
curve in `sim/conn.py`, the conn window wired to charge the ship, a clickable
quay and a working "Set course" on the helm, and live system/contact tracking
in both pop-out windows. `tests/test_berthing.py` (6) and
two new checks in `tests/test_helm.py`. Full suite 759 green, 0 failures.

## 2026-07-29 — SEEDFALL: the last ten kilometres

The captain asked for something the game did not have at any grain: a window
you actually fly the ship from. Cameras out of the hull in six directions,
thrusters fine enough to come alongside a station, orbits you insert into —
and separately, a plotting board where every object in the system can be
selected, tracked, and intercepted **at a chosen future date**, against where
it will be then rather than where it is now.

Nothing existed to build on at the near end. `flight.travel_to` moves the ship
body-to-body over days; `sim/tactical.py` is a separate combat-local plane.
Between "a week to cross the system" and "guns at knife range" there was
nothing at all.

**What was already there, and turned out to be exactly enough.** `traffic.py`
says of its hulls: *"Position is a function of the day and nothing else"*, and
identity is *"stable for the life of the chronicle"*. If that is true, hull
positions are not merely estimable — they are **exactly computable for any
future day**, by asking `traffic.in_system` about that day. I checked it by
playing rather than by trusting the comment: 735 predictions across ten
chronicles, four systems, horizons to 270 days, each compared against really
advancing the sector with `advance_days`. **99.9% came true to the digit.**

The failures were not noise. Every one was the Bloom crossing a threshold
inside `traffic` — 0.15, where raiders may draw; 0.2, where a system loses a
hull — and redrawing the errands. So I threw away the decay curve I had
written first (`0.35` at the horizon, a number I had invented) and made
confidence *causal*: project the growth forward, ask whether a crossing falls
before the arrival day. A captain can act on that. A number that merely falls
with time is decoration.

**Four faults, all found by flying.**

The worst was a unit error. `pos` is in kilometres and `vel` in metres a
second, so `pos·vel / r` is already a velocity — and I divided by another
thousand "to convert". The panel read **+0.01 m/s while the ship flew in at
twelve**. The autopilot believed the panel, so it went on accelerating, and
every approach in the game ended in the hull. No unit test on `closing` would
have caught it: the number looked entirely plausible. Only flying showed it.

Then: the computer managed the closing rate and ignored the rest of the
velocity. Motion *across* the line of sight does not change the range at all,
so it reported itself perfectly on profile while sailing past — hanging at
1.7 km circling a hull, or going into a quay sideways at 12 m/s. Then: a body
approach opened twelve kilometres from the planet's *centre*, several thousand
underground, where `mu / r²` threw the ship out of the system at eleven
thousand kilometres a second. Then: the orbit tolerance was a percentage — a
tenth of circular is 500 m/s at a middling world, forty burns, and wider than
the whole orbit at a rock.

**What the mutation sweep taught me, twice.**

First run: 11 of 13 caught. One miss was a *bad mutation* — I broke the
starfield by calling `_starfield()` per paint, but it is seeded, so it drew
the identical field and nothing changed. Not a weak check; a mutation that
mutated nothing. I rebuilt it to reseed per paint and it was caught.

The other miss was real and better. Disabling the branch that kills lateral
drift passed everything, because `start` always puts the ship dead ahead with
its velocity along the line of sight — the branch never fired. So I added a
check that arrives off-axis on purpose, and **it failed**: at 15 m/s of drift
the computer collided. The tolerance was a share of the closing profile, 2.4
m/s at twelve kilometres — harmless there, fatal at three hundred metres — and
it never tightened on the way in. Tying it to what the *arrival* can absorb
fixed it: 144 of 144 off-axis approaches now berth, including 30 m/s.

**And a discipline failure of my own, worth writing down.** That second sweep
reported 14/14 — from a suite whose new check was failing at baseline, because
`lateral` had moved modules in a file split and I had not re-run the suite
after adding it. Every mutation "failed" for a reason that had nothing to do
with the mutation. The harness now refuses to run unless the baseline is
green, and says so. A sweep without that guard is not evidence in either
direction.

Shipped: `sim/track.py`, `sim/conn.py`, `sim/autopilot.py`, `ui/viewport.py`,
`ui/conn_window.py`, `ui/plot_canvas.py`, `ui/plot3d_window.py`, and
`tests/test_conn.py` (14 checks). Both windows open from the helm.

## 2026-07-29 — SEEDFALL: the one thing the fog did not cover

The docking bug last cycle was an instance of a third pattern worth sweeping:
a screen reading a truth the player should not have. So I asked it of the
sector chart.

The chart has a careful knowledge system. `intel.level` ranks a system 0 to 3
— catalogued, named, visited, charted — the marker is an outline, a disc or a
ring accordingly, and the port ring is drawn only `if sys.port and known`.

**The Bloom was exempt from all of it.** A red halo sized by `system.bloom`
was painted on every star in the sector however unknown, and the side panel
printed

    Bloom mass: 77% of this system converted.
    Knowledge: name only

one line above the other. The one thing the whole game is about was the one
thing the fog did not cover — and it quietly undid last cycle's picket work,
where `watch` was made to gate the reports of new growth while the chart went
on showing the growth itself for free.

`intel.sees_bloom` is the single door: you have been there, you can see it
from where you stand, something of yours watches it, or you hold a colony in
it. A registry entry is not eyes.

The captain is not blinded, only made to scout — Holdings still reports the
sector total, how many systems carry growth and what share of the mass. **How
bad is public; where is earned.** At the opening that means 2 systems of 42
read rather than all of them, and a picket bought at 6,000 credits lights one
up.

Seven mutations, all caught — but the halo one only after a second pass. The
panel is words and the halo is pixels, so a suite that reads labels cannot see
it: the check grabs the chart widget, counts red pixels around the star, and
differences against the same star with nothing growing on it, because the
hatching the chart draws over anything beyond reach is red too and the first
draft counted that instead.

730 → 736 green.

## 2026-07-29 — SEEDFALL: an instrument that changed when you looked at it

Task #72, which I raised last cycle: the docking mini-game's forecast had
never been checked against its act. The premise was half wrong — there *is* a
suite for it, `test_approach_game`, which my grep for "minigames.forecast"
missed. Asking the question properly anyway turned up three faults in one
panel.

**The readout re-rolled on every look.** `reading()` blurred the true error
with a fresh die each call, and the screen called it from `game.rng("readout")`
— which advances the save's seed. Five consecutive paints of an axis nobody
had touched:

    -44   -49   -42   -47   -49

**The panel took its colour from the truth while printing the blur.** A
reading of +9 could sit in a green panel; measured at noise 5, 3% of readouts
contradicted their own colour.

**And every button's forecast quoted `d.error` outright** — so whatever the
instruments said, the tooltip knew exactly where the axis would end up. That
is the whole of what `noise`, and the sensor rating behind it, was for.

`Docking.shown` is the instrument now: read once when a pass begins, held
until the next correction, and used by the panel, the colours and the forecast
alike. The truth stays behind it.

**That left the rating still inert, which I only found by playing it.** `noise`
topped out at 5 against a `TOLERANCE` of 6 — null the reading and you were
inside tolerance whatever your hull carried. Flying on the instrument alone,
400 approaches at each level, noise 0 through 5 all docked **100%** in 3.2–3.5
passes; only past the tolerance does it cost anything. `NOISE_CEILING` is 9:
a bare hull (sensor 2) reads ±7, docks 92% and spends 5.2 passes; a well-found
one (sensor 7) reads ±3, docks 100% and spends 4.3. A fresh captain sits at
3.8, so the opening is barely touched.

Two existing checks in `test_approach_game` went red, and deserved to: both
compared the forecast against `d.error`, which passed only because the
forecast was reading the truth as well. They are stated against `d.reading`
now — the same claims, in the terms the pilot actually has.

Five mutations, all caught. Two needed a second pass: my forecast check only
asserted exactness where the instruments were clear (so the leak survived it),
and my screen check read the printed number but not its colour. Both are
asserted directly now — the forecast in instrument space, and the colour by
reading the label's own stylesheet against a state where truth and instrument
straddle the tolerance.

725 → 730 green.

## 2026-07-29 — SEEDFALL: the card said two officers and the game gave three

Last cycle's systematic sweep worked, so this one asked the same question of a
second family: the sim has nineteen functions that promise what an act will do
— `preview`, `forecast`, `quote`, `odds_for`. Most have a forecast-versus-act
check somewhere. **Three had none at all**: the docking mini-game's, and both
of the opening screen's.

The opening is the first thing a player sees, so I compared its card against
the chronicle it builds, across every stock, origin and posting. Credits,
cargo, standing and hull all matched. The bridge did not:

> **For 30 of 90 openings the card promises two officers and the game seats
> three.**

`CREW_SLOTS` says a Dry Choir stack sails with two — "a wet crew needs people;
a dry one is the ship, and takes fewer" — and it was read by `preview` and by
absolutely nothing else. `apply` only touched the officers when the player had
picked some, and no screen let them.

**I nearly shipped the wrong fix.** My first move was to make it a hiring cap
too, so a dry lineage could never hold more than two. Then I read the constant's
own comment — "Officers you may sign *at the start*" — and the berths board,
which says plainly that in play "you may keep as many as you can pay". It is an
opening complement, not a ceiling. I reverted that half; `can_hire` deliberately
does not consult it.

So `Choices.crew` has been honoured by `apply` since the day it was written and
no screen ever set it. The opening has a bridge picker now: six stations, take
as many as your lineage seats, and the card's number becomes a real decision —
which two, for a dry stack.

**Building the picker exposed a third vocabulary.** `CREW_CHOICES` lists the
stations the opening may seat, and two of its six were *stat* names —
"engineering" and "medicine" against the roles "engineer" and "medic". And
`make_officer` answered an id it did not recognise by picking a role **at
random**. Measured: asking for "engineering" seated a science officer, a
navigator, a medic or anybody else, thirty times out of thirty. Nothing had
ever exercised it because nothing had ever set `Choices.crew` — the picker
would have been the first thing to, and choosing the engineer would have
seated somebody else. One vocabulary now, and an unknown station is a
`ValueError` rather than a shrug.

Four mutations, all caught.

723 → 725 green.

## 2026-07-29 — SEEDFALL: asking every gate whether it agrees with its own act

Two of the last few cycles found the same shape by accident: a function whose
job is to answer "may I?" disagreeing with the thing it guards. `is_stranded`
read a body's richness where `extract` reads its depletion. `quote` priced two
contract kinds where `check` completed three. So this cycle asked it on
purpose, across all seventeen `can_*`/`is_*` functions in the sim.

It found a third immediately. **`crew.hire` refuses a station that is already
crewed, and nothing on the berths board knew.** A fresh bridge holds science,
engineering and nav; the recruit pool draws evenly from all six roles. Measured
over sixty ports:

- **49% of candidates could not be signed** — 107 of 219
- 55 boards in 60 had at least one, and four had four
- every one of them drew a live "Sign on" that answered with a toast

The panel had the ingredients: a *different* button on the same screen already
gates itself on `lifespan.can_sign_on`. The officer cards simply had no
`enabled=` at all. `crew.can_hire` is the one door now — `hire` calls it, the
board calls it — and a closed berth says which officer holds the chair, so the
alternative (Pay off, already on the bridge panel) is legible.

**The check taught me its own limit, which is worth more than the bug.** Once
`hire` calls `can_hire`, mutating `can_hire` moves *both* answers and they
agree all the way down. Deleting the signing-fee rule entirely passed the
agreement sweep. So did making `can_build_here` return yes everywhere — and
that one passed **every check in the project**, which is a real hole the sweep
exposed rather than caused. Agreement guards the architecture; the rule needs
a check measured by outcome. There is one now: the fee is charged and refused
on its own terms, and 39 systems in a fresh sector will not take a keel.

I also recorded what came back clean, because most of it did: `can_found`
against `found` over 1,805 states, `can_afford` against `extract` over 360,
`can_build_here` against `start_build` over 144 — no disagreements anywhere.
And before settling on gates I swept the whole suite for last cycle's pattern
(a check selecting its subjects with the code's own vocabulary) and found the
rest were content tables, where iterating every entry is the right thing.

Five mutations, all caught — two of them only after adding the outcome checks,
which is the point.

719 → 723 green.

## 2026-07-29 — SEEDFALL: the whitelist that was written three times

Breadth cycle into missions, the last area these cycles had not touched. Two
sweeps came back clean and are worth recording as such: the contract board
offers all six kinds every year for nine years running, and every kind has a
completion path that `check` can actually reach.

The finding was in what the board *says*. `quote()` — the function that tells
a captain what a contract's cargo will cost and what they would clear — opens
with `if contract.kind not in ("deliver", "prospect")`. But `check()`
completes a **relic in the same branch as a prospect**: both want the
commodity in the hold at the issuing port. One of two identical contracts was
priced and the other was not.

Worse, `shape()` had the same pair written out again. `deliver` and `prospect`
derive their fee from `cargo_cost(...)` — that is task #34's floor, which is
why neither can lose money. `relic` used a flat `rate × amount` that takes no
notice of what a xenolith costs, and a xenolith is dear and moves about.
Measured over 271 relic contracts against the market:

| kind | median net | worst | % losing | priced? |
|---|---|---|---|---|
| deliver | +15,797 | +2,020 | 0% | yes |
| prospect | +7,346 | +846 | 0% | yes |
| **relic** | **−402** | **−4,694** | **62%** | **no** |

**And the check that exists to prevent exactly this had the list a third
time.** `test_cargo` opens `CARGO_KINDS = ("deliver", "prospect")` — its own
copy of the code's whitelist, so "no cargo contract pays less than its own
cargo costs" could only ever confirm what `shape` already assumed. Xenolith is
stocked at all 20 ports, so buying really is the route it was pricing.

One list in the sim now, imported by the test. Relic's fee is derived from the
goods like the other two, with its rate on top because a relic is a find and
not merely freight: median net +7,267 against prospect's +7,005, and 0%
losing. The board card prints "clears ₡8,266" where it printed nothing.

The general check is the point though: **a check that shares the code's
whitelist proves nothing.** `test_cargo` derives the set by playing now — hand
each of the six kinds its completion state with an empty hold, then a full
one, and see which needs the cargo. It answers `deliver, prospect, relic`.

One existing check had to be re-aimed rather than re-thresholded: "distance
pays haulage on cargo" started sampling relics once the list grew, and a relic
has no destination — it goes back to the desk that asked — so it never takes
the haulage premium, and "per tonne" means nothing for 1–3 xenoliths worth
thousands each. It selects contracts that have somewhere to fly to now, which
is what the claim was always about.

Four mutations, all caught.

717 → 719 green.

## 2026-07-29 — SEEDFALL: skill moved the odds on screen and the prize in secret

Breadth cycle into surface expeditions, which these cycles had not touched.
Two hypotheses died first, and I want them recorded because discarding them
was most of the work:

- **The ground options are not dominated.** `monolith` offers the same reward
  at difficulty 4 and 5, and `wreck` offers a field note at 3 and at 4 — which
  looks like a dead option until you notice the *stat* differs. A fresh crew
  is always science, engineering and nav, never comms, medicine or tactical,
  in 40 of 40 games — so half the ground's options roll at skill zero. That
  looked damning too, until I checked the recruit pool: all six roles turn up
  evenly, ~16% each. It is progression, not dead content.

What was real is what the card says an option pays. `attempt` multiplies a
success by `1 + margin * 0.12` — a bare literal — while `odds_for` quoted the
`REWARD_SCALE` band the roll is drawn from *before* that multiplication.
Measured on "Cut a sample", 800 attempts a level:

    level 0   quoted 8–26 ore   paid up to 32.2
    level 3   quoted 8–26 ore   paid up to 41.6
    level 5   quoted 8–26 ore   paid up to 47.8   (mean up 38%)

**28 of 42 option-and-level pairs paid over their quoted ceiling.** The card
read identically for a green hand and a veteran. Skill moved the odds on the
screen and moved the prize in secret — half of what an officer is worth, and
the half nobody was told, which is exactly the decision "send them or keep
them aboard" turns on.

The quote is conditioned on the officer now: the smallest and largest margin
they can roll on a *success*, carried through. A seam reads 8–32 for a green
hand and 9–45 at level four. Swept over every priced option at three levels,
400 attempts each — every payout now inside its quote, and 17 options quote a
wider band for a veteran. The success chance was already accurate (worst 5%
over 500 rolls) and still is.

**An existing check was holding the card to the wrong number.**
`test_attempts` asserted `(low, high) == REWARD_SCALE[reward]` — the table the
roll is drawn from, not what the ground pays. It asserts the relationship now
(the quote is the table carried through the officer, never narrower) and
`test_prospect` plays out the exact figures.

`MARGIN_BONUS` is named, and it and the other three ground constants moved to
`data/expedition.py` — which also took `sim/expedition.py` back under five
hundred lines, where my change had pushed it to 501.

Five mutations, all caught. One needed a second pass: leaving the *floor* of
the band at the bare scale went unnoticed, because a check that only asks
"nothing paid below the quote" is satisfied by a quote that is too low. It
asserts the floor rises with skill now — skipping `sample` and `xenolith`,
which are counted in ones, where a pip of margin rounds straight back.

712 → 717 green.

## 2026-07-29 — SEEDFALL: two colony effects that a check said were alive

Breadth cycle into empire-building. I went looking with the question that paid
last time — does this system still work years in? — and had to discard three
leads honestly before finding anything:

- **Research** is clean. All 61 technologies have a reachable prerequisite
  chain, and all eight bonus keys are consumed. A "domination" sweep looked
  damning until I saw it was comparing empty dicts: most technologies gate a
  part rather than grant a bonus. No finding.
- **`victory=ruin` at day ~1500** in every long harness run is the Bloom
  drowning the sector while the captain does nothing. By design, and it also
  corrects what I said two cycles ago about it being starvation.

Then the colony effect vocabulary. `data/colonies.py` states the rule itself:
"Every key any class declares must appear here, and **must be read by the
sim**. `tests/test_grants.py` holds both halves." That suite exists because
`megastructure` was once declared and read by nothing.

Two more were in exactly that state, and the check said otherwise:

- **`watch`** — VESPER Picket, Monitor Station, Relay Choir. "Keeps an eye on
  this system whether or not you are in it."
- **`fabricate`** — Fabricator Yard (46,000 credits), Refinery Platform.
  "Fabricated parts can be made rather than bought."

`colony.effects()` copied them into a `watch_systems` set and a
`has_fabricator` flag that **no other line in the game ever opened**, and the
check counted those copies as consumers. *A mention inside a function whose
own output nobody reads is not a consumer; it is a place for a dead effect to
hide.* The aggregator gets no vote now — and because `vault` legitimately
reaches `state.py` through `has_vault`, the check follows one hop through the
aggregate rather than banning it outright.

Holding the aggregate to the same standard found four more dead keys, one of
them worse than the others: **`colony_fx["research"]` was always 0.0**, even
with five research-yielding colonies online, while `clock.py` and `tech_view`
both added it to the bench rate. Colony research goes through `banked`
instead. Six keys gone; the aggregate publishes four now, and something opens
all four.

Both effects do something now:

- A picket **gates the report**. The sector used to announce every new
  infestation anywhere, which is precisely why an eye on a system bought
  nothing — you already knew. Measured: 329 reports with pickets out against
  6 without.
- A yard takes 70% off the *credits* of fabricated fittings built or refitted
  in its system — 35,980 off an 89,400 hull. The metal is charged either way,
  grown fittings are untouched, and a yard one system over does nothing. The
  bill on screen goes through the same call, and says why it is smaller.

One test was proving the bookkeeping rather than the game: `test_empire`
probed `colony_fx["build_systems"]`, an aggregate the game never opened. It
asks the colony's own effect now, which is the granularity
`shipyard.can_build_here` consults.

Six mutations. Five caught outright; the sixth — removing the new guard —
catches nothing on its own now that both effects have real consumers, so I
reproduced the original bug (a `decoy` effect mentioned only by the
aggregator) and showed the guarded check catches it while the unguarded one
passes.

709 → 712 green.

## 2026-07-29 — SEEDFALL: after year one there was no trade in the game

Task #66, which I raised last cycle: surveying is break-even and tips on seed
luck. Chasing it reframed the question entirely and found something worse.

First I had to stop trusting my own instruments. Bots for surveying, mining,
trading and hauling all lost money — but so did the same bots in wide-open
sectors, so the bots were the problem, not the game. I threw out the "every
profession loses money" conclusion.

Then the real chain. A destitute run (run-a) turned out to have a jump range of
8.0 ly and **three reachable systems**; by year one it had zero unsurveyed
bodies within reach and 159 in a sector it could not get to. Surveying is a
*finite* resource — a body is surveyed once — so the profession that funds the
early game runs out. That is by design: the pocket is deliberate, and
`test_reach` has a check that a pocket "is a long project and not a trap".

That check proves the pocket can *supply* the way out — a yard, the materials.
It never asks whether a captain inside can **afford** the 78,000 credits. The
tightest pockets hold four to eleven bodies: 1,600 to 4,400 credits of survey
work, in total, forever. So I went looking for renewable income, expecting to
declare it a trap.

It is not a trap: **freight inside a two-system pocket pays 6,800 to 47,940
credits a round trip**, and every pocket I measured offered work in most years.
I was wrong, and said so rather than building on it.

But measuring that turned up the thing that matters. Watching prices year by
year across eighteen ports:

    year 0   ore 4   alloy 34   biomass 10   phosphate 52   silicon 533
    year 1   ore 0   alloy 21   biomass 17   phosphate -20  silicon -7
    year 2   ore -3  alloy -9   biomass 2    phosphate -8   silicon -10

**After year one the best arbitrage in the whole sector is zero or negative on
every commodity.** Buying at the cheapest port and selling at the dearest loses
money. The spread in ore supply across ports collapses from 0.431 to 0.117
inside a year.

`make_market` builds careful economic geography — a system rich in ore gives
its port up to 1.75x supply, a faction's exports 1.55x, the things it is short
of 0.62x. `tick_market` then dragged every commodity at every port toward
`1 + volatility * trend * 12`, which has nothing to do with the port. The
module's own opening line has always said each port drifts "toward **its own**
equilibrium". The arithmetic said 1.0.

`Stock.base` is what `make_market` decided; the drift reverts to that. Trends
still move a port around its own level, shocks still hit it, trade still pushes
it — but a mining world stays cheap in ore. Six years in, four of five staple
goods are still worth carrying, best margin 510 a tonne; the silicon run
between Quill Bight and Marrow's Deep is still worth 1,174.

**The suite then taught me something about itself.** The Concord broker check
went red. It runs four seeds and demands three — and measured over seventy-two
games the true rate is 56–68%, so that assertion had roughly an even chance of
failing on any given day and had been passing on luck. A fixed-length control
showed my change had no political effect whatever (same 322 ventures, standing
and relations within noise), and the apparent 53%-against-75% gap **vanished on
a fresh range of seeds**: 21/36 against 22/36. Twenty games and a floor at 35%
now, with the measurement recorded beside it.

Four mutations, all caught. Two of my first five were not defects at all — one
mutation did not actually freeze anything, and reverting the seed count is not
a bug the suite should catch — so I fixed the mutation rather than contorting
the check.

704 → 709 green.

## 2026-07-29 — SEEDFALL: told "you can still move" with nowhere to go

Breadth cycle — away from combat, into the economy. I set out to ask whether a
captain can make a living at each profession, and built bots for surveying,
mining, trading and hauling. All four lost money, which told me more about my
bots than about the game, so I switched to the project's own `captain_bot`:
the one whose docstring says it "catches deadlocks — when it cannot make
progress, the game has a hole a player would fall into".

Six five-year runs. **Two of them stopped short.** One at day 1406 of 1825,
moored at Amber Anchorage — a system with exactly one body — holding
**0 credits and 2.3 tonnes of reaction mass**. The body had 0.271 volatiles
and was worked out. `extract` refused it: *"there are other bodies."* There
were none. The captain called for a tow and the game answered:

> **You are not stranded — you can still move.**

`is_stranded` is the gate on `distress_call`, which is the only way back from
exactly that position, and it was answering a different question from the ones
that actually grant a way out. Two guesses in one function:

- **The ice test read abundance where mining reads depletion.**
  `resources["volatiles"] > 0.05` is how *rich* a body is; `worked_out` reads
  how much has been *taken*. Different quantities entirely, so a rich body
  worked to exhaustion counted as a fuel supply for ever.
- **The port test priced an empty shelf at 40.** `buy_price` returns None when
  the market holds none, and `or 40` turned that into "you can buy your way
  out". I checked and no port in a fresh sector is dry — 0 of 417 — which is
  why nothing had caught it. A *played* sector gets there: run-a found Nine's
  Crossing with no reaction mass on the board.

Both now ask the thing that owns the answer. And `nearest_port` no longer
answers a distress call with the berth you are already moored at.

Two of the six stalls turned out to be the bot, not the game, and I checked
rather than assumed: at Nine's Crossing it took the first body over a
threshold, got a worked-out one, and gave up beside four bodies that would
have answered. It picks the richest workable seam now, and calls for a tow
before giving up.

**And the check beside it was hiding this.** `test_play` asserts the naive
strategy "stays solvent for five years" on the *mean* treasury of six runs —
which was 12,159 while three individual runs ended at 0, 254 and 546 credits.
A mean cannot see ruin. There is a check now that every run reaches the end of
its five years with moves left.

Worth recording separately, measured and not fixed: surveying earns 41,579
credits over 4.6 years and spends 44,503 on fuel and rig time. The naive
strategy is *exactly* break-even and tips either way on seed luck. That is a
balance question rather than a bug, and it wants its own cycle.

Six mutations, all caught. One needed a second pass: disabling the jump escape
entirely went unnoticed, because every state in my sweep had a second way out
— I had never constructed one where jumping was the only answer.

698 → 704 green.

## 2026-07-29 — SEEDFALL: the other side could not fight

Last cycle I noticed in passing that the enemy AI runs its helm but never its
engineering section, and said so without acting. Chasing it this cycle turned
up something much worse underneath.

**Enemy heat never rose above 0.14× its own cap, and usually sat at zero.**
Not because heat was exempt — `add_heat` is symmetric — but because NPCs were
barely firing. 684 "the gun is dry" messages across twenty fights.

`make_enemy` gave every hull a flat 4–20 tonnes of ore, alloy and biomass.
Those are *salvage*, meant to be worth pulling off a wreck, and they had been
quietly doing a second job as ammunition that nobody had ever sized against a
fight. Measured over forty engagements:

- mean **12 rounds** carried, against a **31-turn** fight
- dry in **35 of 40** fights, on **turn 11**
- **unarmed for 63% of every engagement**
- and so: *the player took no damage at all in 13 of 20 fights*

Every ammunition *type* was stocked — alloy, biomass and ore cover all
eighteen armed mounts — so the usual "is every declared thing consumed"
question came back clean. It was the quantity that had never been measured
against anything.

Fixing that left 7 of 24 fights still bloodless, so I looked at those rather
than loosening the threshold. **Every one was against a hull armed with
nothing but point-defence cannons** — a flak mount doing 8 damage against a
median of 30. `_weapon_pool` raises the tier until *some* weapon exists, and
for a fabricated hull the first to appear is the flak gun. **40% of NPC hulls
in the game were armed entirely with anti-missile guns**, Concordat warships
at difficulty two included.

`test_balance` had a check for exactly this and it passed happily, because it
asked whether the throw was above zero. A single flak gun clears that. Being
armed was never the claim worth making; being able to hurt somebody is. That
check asks the right question now.

And requiring a main gun exposed a third thing. The old difficulty curve was
a **cliff**, not a curve — scales 0.5, 1 and 2 all sat at 8–16 points of
throw because every one of them was carrying flak, then scale 3 jumped to 85.
My fix gave the bottom a floor and immediately created a new fault: a
fabricated hull's first main gun is tier three, and tier three holds the
breach torpedo, so a light patrol was drawing from a battleship's rack. The
balance suite caught it — an armed hull's win rate against a scale-0.5 patrol
fell from 99% to 75%. `_rack` widens the gun pool with difficulty. The curve
is 27 · 28 · 45 · 88 now, and the win rates 88% / 31% / 16%.

What this cost, honestly: combat is a different game. Mean damage to the
player went from **21 to 150–196**, and the player now loses 4 to 10
engagements in 40 where it had never happened once. Wrecks are worth more
too — unspent rounds are legitimate salvage — 31 tonnes recovered per kill
against 60 now.

Seven mutations, all caught. Two of my own checks needed a second pass: the
magazine check read its bar off `ROUNDS_MIN`, the constant it was guarding,
and passed without blinking on a three-round magazine; and the dry-share
threshold was loose enough that the salvage stores alone satisfied it. Both
measure against absolute numbers now.

692 → 698 green.

## 2026-07-29 — SEEDFALL: the order you give the drive arrives a turn late

Priority #3, positional combat with crew stations. I measured the system
before touching it, asking whether the captain's choice of seat matters at
all — if officers hold the other two competently, the whole idea is
decoration.

It matters, and it *reverses by hull*, which is the healthiest answer I could
have got. Over 40 engagements apiece:

| hull | captain at the helm | captain at the guns |
|---|---|---|
| navis, beam-armed | enemy at **46%** hull | enemy at 92% |
| bastion, heavy | enemy at 66% | enemy at **30%** |

Taking the gunnery seat costs you the helm, which repeats its last order at
seven-tenths turn rate. For a ship that must keep its beam on the target that
costs far more than the accuracy is worth; for a turret boat it costs nothing.
No dominant seat. That is now written into `INTERFACE.md` as something not to
"fix".

What I did find was in the turn order. `_run_seats` ran the helm first and
engineering second — but **engineering is what sets `side.route`**, and its
two consumers sit on opposite sides of that:

- the guns read it when they fire, which is *after* both seats, so
  `route_guns` landed on the turn it was given;
- the helm reads it while steering, which is *before* engineering set it, so
  `route_engines` landed a turn late.

Measured by playing, ordering "power to the drive" on turn three:

    turn 3   route_engines   route=engines   speed  0.00
    turn 4   hold            route=None      speed 74.90

**The captain who ordered it saw nothing happen, and the ship leapt forward on
the turn they ordered *hold station*.** Engineering runs first now — whatever
allocates a resource has to run before whatever spends it.

The panel was the other half of it, and it was already wrong before the fix:
it said "takes effect next turn" for *both* routing orders, which was untrue
of the mounts even then. `ROUTE_ACCURACY`, `ROUTE_SPEED` and `ROUTE_ACCEL`
are named constants now, read by the act and by the forecast, and the panel
quotes them: "+12% to hit, this turn" and "+25% top speed and +60%
acceleration, this turn".

Combat outcomes are unchanged within noise across four hull/strength
combinations — the fix corrects the timing without moving the balance, which
is what I wanted to be able to say before committing it.

Seven mutations, every one caught. One needed a second attempt: I had asserted
the routed speed against `top * ROUTE_SPEED`, which is the tautology trap
again — both sides of that comparison come from the constant under test. It
measures the ratio of two played-out speeds now, and separately states the
design bound (routing is a lever on the ship you have, not a different ship).

687 → 692 green.

## 2026-07-29 — SEEDFALL: goodwill had no price curve, so the Concord was a shopping list

Priority #2, diplomacy. I measured before touching anything: ten years of
doing nothing, to see whether the powers move on their own account. They do —
164 improvements against 142 worsenings across twelve sectors and thirty
years, net mildly downward. Healthy. Every faction field is consumed too;
`buys` reaches the economy as a 0.62 supply multiplier, not just the codex.

Then I played the diplomacy screen as a captain with money and no scruples:
press the four buttons, never leave port, never take a risk.

**The Concord arrived on day 855.** Two and a third years for the sector's
whole political condition, at 460,000 credits and 1,270 tonnes of biomass.
Across three sectors it landed on day 855, 930 and 840 — a shopping list on a
cooldown timer, not a challenge. All four powers finished pinned at 100.

The cause: **nothing in diplomacy had a diminishing return.** `gain` was a
flat number on the action. Forty tonnes of biomass moved a power sitting at
95 exactly as far as one sitting at 0, so standing was a commodity bought at
a fixed price.

`courtship()` is the curve — squared, knee at 25, floor at 0.30. Chosen by
measuring candidate shapes against the climb, not by taste:

- 3 relief parcels still carry a stranger to Correct. The opening is untouched.
- Kin costs 11 parcels where a flat rate charged 7.
- 95 costs 8 more on top of that.

The same captain now takes **3.2 years**, spends 576,000–628,000 credits and
about 1,700 tonnes, and finishes with the powers sitting *at* Kin — 70 to 73
— rather than pinned at 100.

**The floor was nearly set too low, and the suite caught it.** I first chose
0.08 on the strength of the climb numbers alone. Two suites I had not been
running failed: a determined broker reached the Concord in two games of four,
and committing to one side of a feud topped out at 75. The cause is that
standing erodes on its own — the churn takes a power at 90 down to 83 inside
two years — so throttling gains to 8% at the top makes high standing
unholdable and the ending unreachable. That is a worse fault than the one I
set out to fix. Swept 0.08 / 0.15 / 0.22 / 0.30 against the climb, the
Concord playthrough and both suites; 0.30 is the first value that satisfies
all of them.

**Two doors, one rule.** `preview` and `perform` each carried their own copy
of `action.gain * (1 + diplomacy)`. That is the arrangement that has already
produced a free treaty, an ungranted favour and a phantom haggle payment in
this same file. `offer_gain()` decides it once; the suite greps the source so
a third copy cannot appear.

**And the curve exposed a trap that had been sitting under it.**
`allegiance.price` computes what serving a power costs with its enemies, and
`BITE` calls itself "a share of what you gained with the issuer" — but there
was a flat `max(1.0, ...)` under it. Invisible while every act was worth five
or more. Once a gift to an old friend was worth 0.88, the floored penalty of
1.0 with each of two rivals meant **relief at 85 standing cost forty tonnes
of biomass to leave you 1.12 worse off overall.** The button was a trap.

The floor was also flattening the severity ramp that module exists to create
— its own docstring argues against "a flat penalty for anyone under some
line" — so removing it made a mildly-offended power (rift 0.09) charge 0.3
where it had charged a full point. One allegiance check failed on that, and it
deserved to: it asserted two flat thresholds, which a flat floor satisfies by
construction. It now asserts the ramp — a deeper rift costs strictly more —
which is the claim actually worth defending.

Eight mutations, every one caught. Two needed a second attempt: my floor check
read its expectation off `COURTSHIP_FLOOR` itself and passed happily with the
floor set to zero — the tautology trap again. It asks the panel's question
now: does any overture cost real resources and render nothing you can see?

Two smaller things fell out of the same work. The panel began printing
"−0 standing" once penalties got small enough to round to nothing — a figure
that reads as neither zero nor a quantity. And my first guard against it
tested `abs(delta) < 0.5`, which misses exactly −0.5: Python rounds a half to
even, so that formats as "−0" as well. `standing_figure` asks what the number
rounds to instead.

679 → 687 green: seven new courtship checks and one new allegiance check.

## 2026-07-29 — SEEDFALL: two of seven watches had no decision in them

Priority #4, the crossing. The panel prices every option's days, mass, hull,
heat, salvage and research — and then renders the risk as a bare "Might go
wrong: 30%". `risk_text` and `risk_damage` were in the data, read by
`sim/transit.py` when the risk fired, and referenced by no screen at all. So
holding through debris (30% of thirty off the hull) and running a bad slug
(35% of twenty-four) looked like the same gamble.

Fixing the display meant reading every risk, and one of them was empty:

- **`contact/hold` declared 45% — the largest risk in the table — and cost
  nothing.** It printed "They were not nobody." and that was the whole of it.

Which raised the general question, and the general question is the one that
paid. `data/watches.py` states its own design rule in its docstring: *"there
is no option that is simply best."* **Does any option dominate another** —
cost no more on every axis, and pay at least as much?

Four did, across two watches:

- `hulk/beacon` was free and paid 12 research + 3 components; `hulk/log` was
  free and paid 4. Logging it was never worth picking.
- On `contact`, all three collapsed. `hail` was free, riskless, and the only
  one that paid, so running dark (two days) and holding course (nothing) were
  both pointless.

**Two of seven watches contained no choice at all.** Every option now trades
something different: hailing tells a stranger who you are (25% of 48 off the
hull) and learns who they are; running dark costs two certain days; holding
course is free until they come alongside and take three days over you.
Stripping a hulk's beacon costs the day the blurb always said it did.

`risk_days` is new. A risk could only ever cost hull, which is precisely why
the contact could not be priced — being stopped and searched costs *time*.

**The hull regrows and the calendar does not**, and that nearly cost me the
fix. My first retune of `contact/hold` was ten off the hull plus two days —
and the two days healed the ten exactly, so the option's own cost cancelled
itself out. Measured: about 2.3 hull a day when badly hurt, faster near full.
The lesson generalises past this watch: **hull damage is a cheap currency and
days are an expensive one.**

So the domination check does not read declared damage. It plays each option
from one shared state per watch, both branches of the risk, and compares what
is *still missing* once that option's own days have elapsed. A check that
reasoned from the numbers blessed a trade worth three hull as though it were
worth eighteen.

Five checks in `test_watches.py`, every one proven to bite by reintroducing
the bug it exists for. The domination check catches four of the five on its
own, which is the shape a good general question has.

Suite green.

## 2026-07-29 — SEEDFALL: all one hundred and fifty-three

Task #60 has been open since long before this run and I have twice said it
needed a cycle of its own. This is that cycle, and it is closed.

- **Every tuning constant in the game is pinned.** 53 modules, 153
  module-level numeric constants across `data/`, `sim/` and `core/`, each
  doubled, halved and zeroed. Every single one is noticed by at least one
  check. Nothing is unprotected.
- **The original "52" was an artefact.** It was counted when `tripwire.py`
  kept its own copy of the suite list, which went stale the moment a suite was
  added — constants protected by the newer suite read as unprotected. The
  tool's own docstring records that failure; `SUITES` derives from the
  canonical list now, and the count predates the fix.

**A pass/fail sweep that reports nothing but "all clear" is a poor use of
seventy minutes.** So the tool now says *where* each constant's protection
comes from: its own neighbourhood, or only the wide set. The second is worth
knowing — it means the constant is held up by a suite that happened to walk
past rather than by a check written for its subject.

One constant was in that state: **`consorts.WITHDRAW_AT`**, the hull fraction
below which an escort breaks off and falls out of the line. Something
somewhere noticed it moving; nothing in the combat suite did, which is where a
rule about consorts belongs. `test_combat` has a check for it now — in the
line at 60% and 35%, out of it at 10% and 5%, measured against fractions
written in the check rather than against the constant — and the sweep now
reports it caught by `combat` directly.

Three mutations bite it: never breaking off, breaking off at the first
scratch, and skipping the check entirely. A fourth mutation I tried aimed at
the tool's new reporting line and missed; that is a diagnostic rather than a
rule, and I am not going to pretend a print statement is load-bearing by
writing a check for it.

674 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: what the order will cost you, before you give it

Priority three. The seats already say what taking one personally is worth —
`seat_value` has done that since task #40. The orders *inside* the seats were
bare buttons with a sentence of prose and no number anywhere.

That mattered most at gunnery, and more since the thermal work. A Bastion at
30 of a 50 cap presses **fire everything that bears**, makes seventy-four
more, and ends the turn pinned at the ceiling — where every penalty for
running hot is charged against it. Nothing said so until the turn resolved.

`stations.order_preview` says it now, and the panel prints a line under each
button:

- *Fire everything that bears* — 5 of 5 mounts bear · heat 30 → 100 of 50 —
  pinned at the ceiling  (in warn)
- *Aimed shot* — Standing Wave Projector, 52 damage · heat 30 → 48 of 50
- *Vent heat* — sheds up to 25 · heat 30 → 5 of 50
- *Damage control* — patches about 16 of Whipple Bumper

Helm orders are left deliberately silent: the firing picture already reports
what coming about would bring on, in degrees, and saying it twice is noise. A
check holds that both ways — no gunnery or engineering order may be a bare
button, and no helm order may start speaking here.

**I made the same mistake I was fixing, one layer up.** The first draft quoted
the raw sum: "heat 30 → 104 of 50" for a salvo that actually stops at 100,
because the ceiling clamps it. A forecast that does not clamp what the hull
clamps is exactly the defect this function exists to end. It now reports the
clamped figure and distinguishes *over the cap* from *pinned at the ceiling* —
which are different places to be — and the check measures the forecast against
`_salvo` itself from three starting heats: 0 → +74, 30 → +70, 95 → +5, every
one exact.

Six checks in a new `test_orderplan` suite, every one proven to bite.
673 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: two buttons, one of them priced

Back to diplomacy. The piece I had not measured is ventures — the powers
acting on their own account, which you may back, work against, or let happen.

The system itself is healthy: all six kinds fire, hundreds of them over twenty
chronicles. The screen was the problem.

- **Neither button said what it does to the odds.** The panel showed "Odds as
  things stand: 51%" and two buttons. Backing takes that to **81%** and
  opposing to **21%** — a thirty-point swing either way, which is the entire
  reason to intervene, and it was stated nowhere.
- **Only one of the two buttons was priced.** "Backing it costs ₡5,000" and
  "Backing buys +12 standing" were both there. "Work against it" had nothing
  beside it at all — not the −14 standing with the power, not the +8 with
  whoever they are against.
- **And being right pays again, silently.** Backing something that comes off
  is worth +8 more with the power; opposing something that fails is worth +5
  with every power that already disliked them. Both were bare numbers inside
  `_resolve`, mentioned on no screen.

`RIGHT_BACKED` and `RIGHT_OPPOSED` are in `data/ventures.py` now, and
`ventures.preview` reads the same constants `_resolve` does — the arrangement
`TREATY_WEIGHT` was extracted to get. The panel prints both stances in full:
odds before and after, credits, every power whose standing moves, and what it
pays if you turn out to be right.

Six checks in a new `test_ventures` suite, every one proven to bite —
including one that restores the old panel, pricing backing only, and one that
makes the forecast and the outcome read different numbers.

667 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: the fifty-two that were not there

Task #60 — "pin the remaining 52 unprotected tuning constants" — has sat on
the list for many cycles. This cycle measured it instead of assuming it.

- **59 constants across 14 modules, and 0 of them unprotected.** ship, flight,
  expedition, colony, convictions, officials, diplomacy, plans, mining,
  stations, minigames, aftermath, assessment, ventures — every one pinned,
  including every constant the last ten cycles introduced: `HEAT_CEILING`,
  `QUIET_SHARE`, `TREATY_WEIGHT`, `STRANDED_SHARE`, `MEGASTRUCTURE_GUARD`,
  `PROMOTION_OWN`, `PER_AU`, `LONG_LEG_CAP`, `WORTH_SAYING`, `PATCH`.
- **The "52" is stale, and the tool records why it would be.** `tripwire.py`
  used to keep its own copy of the suite list; it went out of date the moment
  a suite was added, and constants protected by the new suite read as
  unprotected. `SUITES` is derived from the canonical list now. The count was
  taken before that fix.

**Two real defects in the tool itself, found by asking it the question it asks
of the game.** `KIN` maps a module to the cheap suites to try first, and it is
hand-written:

- **`memory` pointed at `voices`, which is in `SLOW`** — a suite the sweep
  deliberately excludes. A constant protected only by a slow suite therefore
  read as protected when its module had an entry and unprotected when it did
  not. The two stages have to agree on what counts.
- **21 modules with tuning constants had no fast path at all**, including
  `ship`, which holds the thermal rule the whole game reads. Every one of
  their constants paid the full wide run: measured, `ship`'s four took 240
  seconds without a fast path and 17 with. Fourteen times.
- And the entries that existed had gone stale against this run's newer, more
  specific suites — `charts` still pointed at `charts` rather than `charting`,
  `expedition` at `ground` rather than `landing`, `officials` at `officials`
  rather than `counter`.

All fixed, and `test_harness_guard` now holds the map: no entry may name a
suite that does not exist, none may point at a `SLOW` one, and every module
with constants must either have a fast path or be named as having no suite
that covers it. Four mutations, all biting.

Task #60 is rewritten with the measured figure and instructions for finishing
the sweep. The remaining ~92 constants are unswept; a full pass is about
eighty minutes even with the fast paths, because the fast stage only saves
time on constants it *catches* — anything genuinely unprotected still pays the
wide run, which is the right way round.

661 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: four more doors into the same hull

Priority four: richer helm and flight. Two cycles went into bounding heat, and
this is the one that found out how incomplete that was.

- **`INTERFACE.md` said there were exactly two places heat is added.** There
  were six. A crossing watch in `transit`, a flight incident in `flight`, an
  action's own effects in `actions` and taking a hit in `damage` all put heat
  into a hull without ever consulting the ceiling.
- **A single fault took a hull sitting at the ceiling to 2.36x its cap** —
  the incident fires *after* `travel_to` clamps, so it lands on top. That is
  precisely the compounding the ceiling exists to stop, since every penalty
  for running hot scales with how far over you are.
- **The fix is not another `cook()` call.** `ship.add_heat` is now the only
  way to put heat into a hull, and it clamps on the way in. Asking six callers
  to remember is what four of them did not do. Measured after: eight hard
  burns with faults land at exactly 2.00x, never past it.
- **A smaller thing in the same function.** A fuel fault rolled two to eight
  tonnes, took as much as the tank actually held, and reported the *roll*.
  One in five told a captain with three tonnes aboard that eight had gone.

**On the guard, and on redundant guards.** The check that would have found all
four is a static one: nothing outside `sim/ship.py` may write `\.heat +=`. It
needs one deliberate exception noted in the file — `sim/customs.py` has its own
`add_heat`, which is scrutiny from the revenue and shares nothing with the
thermal system.

One mutation missed: removing `add_heat`'s own `max(0.0, ...)` changed
nothing, because `cook` already floors at zero. That is a redundant guard
rather than a hole in the check, so I removed the redundancy instead of
excusing it — one floor, in one place — and pointed the mutation at the floor
that is actually load-bearing. It bites.

Five checks in a new `test_thermal_doors` suite, every one proven to bite.
660 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a turn where nobody flew the ship

Priority three: positional combat with crew stations. Two doors again, and
this time the older one switched the whole system off.

- **`take_turn` takes two shapes of action.** `{"type": "station", "order":
  ...}` runs the crew stations — your seat takes your order, officers hold the
  other two. The older `{"type": "fire", "weapon_id": ...}` family never
  called `_run_stations` at all.
- **The battle screen still sends the older shape** for the firing picture's
  per-mount buttons and for abilities. So a captain who picked a mount instead
  of ordering a salvo lost their crew for that turn: nobody flew the ship,
  nobody stood in the engineering section. Measured on a hull at 30 heat, the
  turn ended at 24.0 through the old door against 19.44 through the new, and
  `helm_order` was still `None` afterwards.
- **Only `move` had ever been migrated**, which is how it stayed hidden. The
  obvious comparison — salvo against salvo — agrees whatever you do: on a
  light hull the seats have nothing to show, and on a heavy one the heat
  ceiling erases the difference before it can be read. It only appears below
  the ceiling, on a hull carrying heat.
- **`_run_seats` is called from both paths now.** All 650 existing checks
  stayed green, and outcomes over thirty seeds are identical either way.

**Four of my six mutations missed on the first run, and two of those were my
checks' fault.** The brace check asserted an upper bound — "sheds no more than
three vents" — which a skipped section and an unattended one both satisfy. It
asserts the exact three now: the brace, the section standing *attended*
because that is where the captain is, and the end of the turn. The other two
misses were bad mutations that left the calls in place and only discarded
their return values, which changes nothing.

Worth knowing rather than fixing: the helm runs before the guns, so a mount
that bears when you press the button may not bear when the shot goes. That was
already true of the station path; it is now true of the named-mount buttons
too, which is the point of the change rather than a side effect.

Five checks in a new `test_seatwork` suite, every one proven to bite.
655 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a treaty that was free if you waited to be asked

Every area of the breadth list has now had a cycle, so back to the top of the
priority list: diplomacy. Last time was the overtures you make; this is the
half where the powers come to you.

`approach.answer` carries the comment "everything here must match `preview`
exactly". Four things did not.

- **Signing a treaty was free through one door.** `diplomacy.perform` charges
  the signatory's enemies when you propose one; `approach.answer` appended
  the treaty and charged nobody. Measured with all four powers at −70 with
  each other: proposing cost −6 with each of the other three, accepting the
  identical instrument cost **nothing at all**. A treaty is the most public
  act in the game, and there was a door through which it was invisible —
  which is precisely what the last diplomacy cycle set out to end.
  `TREATY_WEIGHT` now lives in `data/diplomacy.py` and both doors read it.
- **Haggling claimed the treasury.** The envoy screen printed "Treasury:
  +794" for a push. Pushing raises what is *on the table*; nothing is paid
  until you accept. `preview` reports `offer` separately from `credits` now,
  and the card reads "What is on the table: +794 credits".
- **Two silences**: accepting a denunciation drives the two powers a further
  six apart, and refusing a levy is filed as a grievance. Both happened, and
  neither appeared in the preview the screen is built from. Both do now.

**A detail worth keeping.** The existing check `pushing moves the price once
and only once` compared the movement of the offer against `preview["credits"]`
— and was right about the semantics all along. The screen read the same field
as the treasury. One number, two readings, and the screen had the wrong one; a
check can be correct and still leave a defect standing if something else reads
its subject differently.

The envoy triggers themselves measured clean: all five kinds reachable once
their preconditions are built, and my first sweep only missed two because the
driver never raised standing or planted a colony — the same confounding as the
combat cycle, caught by constructing the conditions instead.

Seven checks in a new `test_envoy` suite, every one proven to bite.
650 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a bench that was never fully stocked

Research, the last area of the breadth list this run had not touched. The
technology tree measured clean — all 61 reachable, no dangling prerequisites,
all eight bonus keys consumed. The defect was in the suite that measures it.

- **`test_provisional` hand-typed its evidence kinds and got three of them
  wrong.** It stocked `survey`, `specimen`, `field`, `relic`, `trade`,
  `hardware`. There are four kinds: `survey`, `specimen`, `hardware`,
  `reading`. So three names did nothing — `inquiry.add` returns 0.0 for a name
  it does not know, silently — and `reading`, which is real, was never stocked
  at all.
- **Six of the ten branch mixes ask for `reading`.** Cognition wants 35% of
  it, xenology 65%. So every programme in those branches was being measured on
  a bench starved of a quarter to a third of its input, in the suite that
  decides whether any research approach dominates. Measured: cognition
  unlocks in 165 days on a full bench and 214 without it; xenology 170 against
  215.
- **The conclusion survived, but the numbers moved a long way.** With the
  bench correct, `push` is now the *slowest* route to sound technology at 420
  days where it had been the fastest. "No approach is best at everything"
  still holds, and now holds against a measurement that is true.
- **The screen was right all along** — the research panel has always shown
  "Xenolith readings · 140 held · 33 wanted". Only the fixture was wrong.

**The guard, and the first version of it that did not work.** I wrote a check
that scans call sites for evidence-kind literals. It passed the mutation that
restored the bad tuple — because `test_provisional` passes a *variable*, so no
search of call sites could ever have seen the bug it was written for. It now
also walks the AST for any `*KINDS` constant that is a plain list of strings,
under the rule that a list naming any real kind must name only real ones —
which catches the hand-typed six and leaves `test_cargo`'s `CARGO_KINDS`,
about contracts and mentioning no evidence, alone.

Five checks in a new `test_bench_kinds` suite, every one proven to bite.
643 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: five things the bridge never noticed

Political machinations — the convictions officers hold and what moves them.
The audit that found the dead colony effect, asked here: does every event an
officer has an opinion about ever actually happen? Five did not.

- **`promoted`, +5 to every officer aboard**, because it sits in `UNIVERSAL`
  and applies whatever they believe. `crew.grant_xp` returns the list of
  people it has just promoted — the return value exists for this — and **all
  eight call sites threw it away**. So a career built over a decade moved
  nobody, and was not even written in the log. It now reports itself: the ship
  feels the event, the officer promoted gets `PROMOTION_OWN` on top (+14
  against a bystander's +5), and the log reads "Feodor Sarkis is made Science
  Officer 4."
- **`licence_served` and `free_served`, +11 each** — the largest single thing
  either conviction believes in, and never delivered. A Charter partisan could
  run Charter commissions for ten years and feel it only as the
  `commission_done` everybody else felt. `loyalty.served` fires when a
  commission is paid, and only for partisans of the power that issued it.
- **`burner_served` and `xeno_served`** were unreachable — their convictions
  have no aligned power — and duplicated `bloom_cleansed` and
  `xeno_incorporated`, which do fire. Removed, rather than left in the data
  claiming something untrue.
- **Loyalty still bites**, checked deliberately so none of this makes it
  toothless: an unpaid bridge goes restless around month eight and is empty by
  month twelve.

**Two of my own checks were too weak and mutation caught both.**
- "Finishing a commission delivers it" asserted only that loyalty moved. But
  `_pay` also adjusts standing, and `loyalty.align` drags partisans along at a
  quarter rate — about +1.25, enough to pass with `served` deleted entirely.
  It now asserts the partisan moves by at least what the conviction declares.
- Both promotion checks asserted that officers were *reported* promoted and
  never that their level rose. Deleting `o.level += 1` passed everything.

Six checks in a new `test_conviction` suite, every one proven to bite.
638 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a chart that never went off

Exploration and mapping, which had not had a cycle. Surveys measured clean —
the forecast matches the days actually spent, including on a dry tank; all
four find categories are consumed; all four methods are reachable, `sweep`
included once you are parked in-system rather than out at the arrival radius.
Charts were where it was.

- **`charts.freshness` says "a chart made long ago is worth less. The sector
  moves." It was never once true.** Dating a finished chart lived in
  `actions.survey`, the single-method call the four survey methods replaced.
  The screen calls `survey.perform`, which did not date it. So no chart a
  player ever made was stamped, freshness returned 1.0 for ever, and
  `FRESH_DAYS` and `STALE_FLOOR` decided nothing at all.
- **The survey office had been written for this the whole time**, carrying an
  "Age of the survey" row behind `if fresh < 0.95` that could not fire. It now
  reads "62% of fresh" in amber beside a price that has fallen with it.
- **Measured after:** ₡14,794 fresh, ₡10,726 at a year, ₡6,657 at the floor.
  Selling a chart while it is current is a decision again.

**Why nothing caught it, which is the part worth keeping.** Surveying a body
has two doors: `actions.survey`, used by the remote bridge and by every test
driver in the suite, and `survey.perform`, used by the screen. They did
different things — and every driver went through the door that worked, so the
suite saw a system behaving correctly while no player ever could. The first
check in the new suite asks the general question directly: do both doors leave
the same state behind.

**And I wrote a tautology, and mutation caught it.** The ageing check measured
freshness at `FRESH_DAYS // 2`, `FRESH_DAYS` and `FRESH_DAYS * 3` — so
widening the window to ten thousand years passed cleanly, because the check
simply waited ten thousand years. It moves the ruler with the thing it
measures. The ages are plain numbers now: 360 days, 730, 2200.

Five checks in a new `test_charting` suite, every one proven to bite.
632 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a penalty that paid better than the reward

Surface expeditions, which had not had a cycle.

- **Stranding was the best way to play the ground.** `haul_kept` applied the
  carrying limit when the party walked home and **skipped it entirely when
  they stranded**, returning 40% of everything ever picked up, uncapped. Five
  hundred tonnes collected came home as **200 t stranded against 60 t
  returned**. Measured end to end: a leader who never turned back kept 933 t,
  one who always walked home kept 41 t. Twenty-three times better to fail.
- **It also contradicted its own ending**, which says everything not on their
  backs stays where it fell.
- **The order is the fix**: what they can carry, and *then* what stranding
  costs. Now 500 t is 60 t home and 24 t stranded, and walking home wins.
- **The turn-back margin is a real decision again**, with a peak in the
  middle: 29 t at margin 0, 35 t at 4, 23 t at 14. Too little strands the
  party; too much spends the expedition walking.
- **Supply could go to −1**, because a crossing costing two could be paid out
  of one. Floored, so no screen has to print it.
- **The screen says what the lander will lift.** "Carrying 140 / 60" in amber
  left the captain to infer that eighty tonnes would cease to exist, and said
  nothing about stranding. It now reads "Comes up 60 t — 80 t stays" and "If
  they strand 24 t", both off `landing_forecast`, which is `haul_kept` — so
  the forecast and the outcome cannot drift.

**`tests/ground_ai.py`, because there was no way to measure this.** The same
gap combat had before `captain_ai`: a driver that wanders and grabs never goes
back to the lander, so every party strands and every policy scores identically.
The one decision the ground poses is how much supply to keep for the walk home,
and it was invisible to a driver that never walked home.

**On thresholds.** The peak-in-the-middle check first failed at 40 seeds a
margin — the gap to margin 0 wobbles between 1.12x and 1.21x there. Rather
than loosen the threshold to whatever passed, I measured at 120 (three seconds
for six hundred expeditions) and asserted below what that showed. The claim
that held at every sample size is the structural one: the best margin is
inside the range rather than at an end of it.

Six checks in a new `test_landing` suite, every one proven to bite.
627 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a favour that was never granted

Trading, which had not had a cycle. `market.quote_buy`'s own docstring names
the invariant worth checking — "a screen that quotes one number and charges
another is the defect this project keeps finding" — so I checked it.

- **The office rate was applied at the till.** With it running the board
  showed 36/t and the counter charged 31.68; the board said the port paid 29
  and it paid 32.95. Exactly the split that helper exists to prevent.
- **Except it never ran.** `Favour.lasts` is a window in days, a quiet price
  is granted "this once", so it carries `lasts=0` — and `ask()` recorded
  favours under `if favour.lasts:`. A zero-day favour fell straight through.
  Measured by playing: asking cost **12.7 regard**, stored nothing, and the
  purchase that followed was charged the full posted price. One of the five
  favours the game advertises as "read somewhere real" bought nothing at all.
- **Fixed both ways.** A one-shot is held in its own list until used, and the
  rate lives in `quote_buy`/`quote_sell` so board and counter cannot disagree.
  The desk says "good once, next time you deal here"; the market board
  explains why its numbers are not the posted ones.

**The check that should have caught it, and why it did not.** `test_officials`
had "every favour is read somewhere in the game", and for the quiet price it
wrote the favour straight into the dated `favours` dict by hand. That state is
unreachable — `ask` could never produce it — so the check proved the price
code worked given something the game cannot do, and read as coverage. It now
grants through `ask`, and reintroducing the bug fails it.

That is three cycles running where the lesson was the same: a whitelist of
known keys, a coverage run pinned to one lucky seed, and now a fixture that
sets up a state the game cannot reach.

**Two files were over five hundred lines and are not now.**
- `ui/port_view.py` hit 509. The contract board came out into
  `ui/board_panel.py`. I extracted it mechanically and then ran a static
  undefined-name scan, which found three names — `Panel`, `spacer`,
  `FACTIONS_BY_ID` — that had travelled without their imports, and fourteen
  left orphaned behind. Worth doing *before* the suite, not after.
- `tests/__main__.py` hit 525, because every cycle added another five-line
  `if "name" in wanted:` block. Seventy-eight of them, all the same block. It
  is a table in `tests/suites.py` now and the dispatch is 50 lines. The
  hand-kept `ALL_SUITES` beside it had already drifted from the real dispatch
  order at index 46, which is what a second copy always does.

Five checks in a new `test_counter` suite, every one proven to bite, plus the
repaired `test_officials` check. 621 checks green, and nothing over 500 lines.

## 2026-07-28 — SEEDFALL: a board that offers work you can reach

Missions, which had not had a cycle. The general question again: is every
posting on the contract board actually doable?

- **65% of targeted postings named a system outside the reachable component.**
  `_pick_target`'s docstring said "reachable in principle" and its whole test
  was `bloom < 0.4`. Reachability is transitive and nothing checked it. At the
  opening drive 15 of 42 systems can be flown to; deliver ran 69% unreachable,
  survey 63%, expedition 57%. Letting one lapse costs standing with the issuer.
- **And the card never said where the work was** — reward, deadline, standing,
  cargo cost, allegiance cost, and no destination at all.
- **Both halves fixed.** The generator asks `reach.component`. `reach.route_to`
  gives fewest hops and the days they cost, checked against `jump_quote` for
  single hops. The card reads "Nine's Rise — 3 jump(s), about 20 days each
  way", and says so in warn colour if the deadline will not cover it.
- **Feasibility is judged one way, not round trip.** `check()` completes a
  delivery, a survey and a ground contract on *arrival*. Judging round-trip
  flagged three postings that are perfectly doable — a warning nobody needs
  teaches captains to ignore warnings.

**Then the full suite caught a regression, and it was not the one it looked
like.** `test_chronicle`'s "the chronicle does everything it claims" started
failing on `planted a colony`. My change had shifted the driver's path — but
sweeping seeds showed colonies were planted by **1 seed in 24 under the old
targeting too**. The check was pinned to the single seed that happened to work.

The real cause was a driver bug of some age. `chronicle._refit_here` still
tested "the system has a port", which stopped being the rule when
`shipyard.can_refit_here` tightened to "alongside a yard" — so the driver
called `apply_refit` from wherever it was, got "you are not alongside a yard"
back, and dropped it. Measured: 822 of 1506 founding refusals were "no seed
bay fitted". Teaching it to put in at a yard first took that to 100, and
planting from 1 seed in 24 to 6 in 48. The original check seed passes again on
its own merits, and the first chronicle check went from 0 colonies to 5.

I have recorded the measured rarity in the check itself, because a capability
only one seed in twenty-four exercises is not being covered, it is being got
away with.

Five checks in a new `test_postings` suite, every one proven to bite —
including one that needed a deliberately impossible deadline, because with
every real posting comfortably in time, "always says yes" and "is right" look
identical. 616 checks green.

## 2026-07-28 — SEEDFALL: a grant that does nothing, and a card that says nothing

Empire-building, which had not had a cycle. Measured the nineteen colony
classes for payback first — that turned up nothing damning (pomona_grove pays
back in 45 days, the negative-income classes justify themselves on effects) —
so I asked instead whether the effects they advertise are read at all.

- **`megastructure` was declared by the ARCA Habitat and read by nothing.**
  400,000 credits, 2,600 tonnes of ore, 900 days, a million people, and the
  one property that made it an ARCA Habitat rather than a very good mine was
  consulted by no line of the game. A five-by-ten-kilometre drum of spun rock
  was overgrown by the Bloom on exactly the same roll as a lichen farm.
- **It now means what it should.** `bloom_attack` already had the machinery —
  a colony's own `ward` halves its chance of being taken — so a megastructure
  guards at 0.85. Measured: a farm is taken in 29% of attacks, the drum in 4%.
  Not immunity; `bloom_attack`'s own comment promises the Bloom gets
  everything unattended eventually, and a check holds it to that.
- **The founding screen printed the internal keys.** `"Grants: " + ", ".join
  (effects)` — so a captain weighing nine hundred days read "Grants:
  megastructure" and could not find out what it meant, which was just as well.
  `EFFECT_TEXT` gives all fourteen a sentence and the cards print those.

**What actually found it.** Not a whitelist. Two suites already listed
`megastructure` in a `KNOWN_EFFECTS` set — but that only asserts nobody
declares an *unknown* key, never that a declared one is consumed. It read like
coverage and was not. The new check asks the general question instead — *is
every declared effect read by something* — and on its first run found a
**second** dead key I had not looked for: `drydock`.

**And `drydock` turned out not to be the bug it looked like.** Its card says
"refits and repairs here, without flying to a yard", and I nearly reported it
as a broken promise. Playing it showed refitting at an Orbital Drydock works
fine — because every class granting `drydock` also grants `build_here`, which
`_colony_services` does read. So the promise was kept by a second flag
happening to be set. `drydock` now reads alongside `build_here`: nothing
currently plantable changes, and a dock that is only a dock works as its card
reads instead of silently granting nothing.

My own error worth keeping: I first "found" that a lichen dome lets you refit.
It does not — I had parked the ship on the body the Fleet Hub orbits, so
`docked_at` returned the Hub, which has a yard. Checked before reporting.

`ui/system_view.py` is at 494 lines. The next thing added to it should split
it first.

Five checks in a new `test_grants` suite, every one proven to bite.
611 checks green.

## 2026-07-28 — SEEDFALL: the helm, and the half of the fix I missed

Richer helm and flight simulation, the next standing priority. It turned into
finishing last cycle's job properly and then finding what a *general* question
catches that a specific one does not.

- **Last cycle bounded heat in the guns and left the helm wide open.** A hard
  burn adds heat on arrival; only `cool()` takes it away, at 0.84 a day
  against the ~32 a burn puts in. Bouncing between two bodies drove a hull to
  **5.4x its rated cap**, climbing linearly with nothing to stop it.
- **And it was worse than in combat, because it was quiet.** Ten hard burns
  then an engagement: the captain **routed on turn three at 51% hull while
  holding fire every single turn**. They lost to their own radiators without
  firing a shot. Now: driven off on turn 35 at 88% hull.
- **One rule, one place.** `HEAT_CEILING` and `cook()` moved to `sim/ship.py`
  beside `cool()`, because the hull owns its physics and both the guns and the
  helm put heat into it. `combat` re-exports them. A check asserts they are
  the *same objects*, because two copies of this rule drifted within a cycle.
- **Flying hot still costs.** Fourteen hard burns: 87 days at 68% hull against
  economy's 235 days at 100%, and double the incident rate. Bounded, not free.

**Then the general check earned its keep.** The burn board quotes a risk, and
that risk is the profile plus *three* surcharges. Two were charged silently:
the heat in the hull (a captain saw coast at 0.34 where its profile says 0.06)
and the star at your back (`_heat_risk` takes the nearer end of the leg, so a
hull parked at 0.40 AU paid on every departure, including one nine AU outward,
while the note only ever described arrivals).

I wrote a check asking the general question — *does anything cost more than
its profile without the screen saying why* — and it immediately found a
**third** surcharge I had not looked for: a distance term, up to +0.10, never
mentioned anywhere. All three are stated now, with their amounts.

**And the check was too weak at first, which I caught by mutation.** It asked
only whether *some* note existed. With the star warning deleted, the distance
note kept the quote looking explained and nothing failed. It now checks each
component separately, reconciles the components against the quoted total so a
fourth surcharge cannot appear unnamed, and caps what may go unsaid so the
noise threshold cannot be raised to hide something large.

Five checks in a new `test_helm` suite and four more in `test_thermal`, every
one proven to bite — including a mutation that raises the threshold to hide a
surcharge. 606 checks green.

## 2026-07-28 — SEEDFALL: a warship that can fire its own guns

Positional combat with crew stations, the next standing priority. Measure
first, as usual — but this time the measurement took several passes because
the first three readings were all my own errors.

- **False start one:** drove fights with a repeated order and got 0 wins and
  0 losses in 280 fights. INTERFACE.md already warns about this in writing —
  "driving a fight with one repeated order measures nothing, use
  `tests/captain_ai.py`" — and I had not read my own note.
- **False start two:** the test ship's magazine was empty, so the slug battery
  could never fire. Same class as the 9000 t of fuel in a 340 t hold.
- **False start three:** concluded heat was dead because a two-gun mining ship
  never overheats. It is not dead; that hull is simply not thermally limited.

**The real finding, once the measurements were sound.** Heat had no ceiling.
A Bastion firing the five heavy mounts it has slots for makes 74 heat a turn
against a rated cap of 50 and a vent of 6, so heat ran 68 → 132 → 187 → 243 →
279 and kept climbing. The overheat penalty is a share of how far over you
are, so it compounded — resolve fell 26, then 39, then 53, then 65 — and the
ship routed on turn five **at 93% hull**, beaten by its own radiators while
the enemy did almost nothing. There was no way back either: cooling from 279
at six a turn takes 38 turns, longer than the engagement, so `vent` could
never catch up and only cost you the gunnery seat.

So every thermal decision in the game was fake: salvo's "far more heat", the
aimed shot's "less heat", holding fire to cool, both power routings.

- **`combat.cook()` holds heat at twice the rated cap.** Measured over 40
  fights with the heavy battery: favourable outcomes 7/40 → 24/40, kills
  4 → 12. Recovery is back inside a fight — two turns of venting hard.
- **And salvo against aimed became a real choice**: salvo decisive and swingy
  (12 kills, 16 routs), aimed attritional (24 driven off, 2 kills).
- **The light explorer is untouched** — it peaks at 9% of its cap, so the
  ceiling is never consulted. This is a fix for a broken regime, not a
  rebalance.
- **One clamp, not two.** An end-of-turn clamp was tried and measured to
  change nothing (peak 2.32x either way), so it came out again.

**A costly mistake worth recording.** While measuring which clamp mattered I
used `git checkout seedfall/sim/combat.py` to undo a scratch mutation. That
restores from the index and threw away the entire cycle's uncommitted work on
that file. Rebuilt it, and the mutation harness now keeps the original bytes
in memory and writes them back in a `finally:`. Added to the traps list in
INTERFACE.md.

Eight checks in a new `test_thermal` suite, every one proven to bite.
597 checks green.

## 2026-07-28 — SEEDFALL: a gift is a public act

Diplomacy, the standing priority. Same method as the last three cycles —
measure the system for a dominant strategy before touching it.

- **The measurement.** A captain with money ended a chronicle at 92, 100, 100
  and 100 with all four powers, while the Concordat and the Freeholds sat at
  −67 with each other. The three gift overtures — tribute, intelligence,
  relief — added standing with their target and cost **nothing** anywhere
  else. So the relations matrix was scenery, there was never a side to take,
  and `broker`, the only action that moves that matrix, bought nothing you
  could not get by ignoring it entirely.
- **The fix used machinery that was already there.** `sim/allegiance.py` knows
  how much a rift is worth and was already wired to contracts, treaties and
  territory — including a `note()` for showing the price before you commit.
  Gifts go through it now. Nothing new was invented.
- **Measured after:** courting one side of an implacable feud reaches 100 with
  them and −100 with the other; courting both reaches 69 and 63, neither at
  Kin. Brokering the rift first drops the toll from 7.8 standing to 1.0. That
  is the purpose brokering never had, and the diplomacy screen has been
  telling players to broker for as long as it has existed.
- **The screen shows all of it.** The overture card now reads `Concordat +9
  standing · Freeholds −4 standing · Charter −1 standing` before you press
  anything, because `preview()` and `perform()` share the arithmetic.

**A real bug, found by playing.** With gifts now costing standing elsewhere I
went looking for whether a captain could recover from a wrecked relationship.
They could not: at −100, courting a power with unlimited credits for 120
sessions moved them *not one point*. Below −60 every overture is refused and
the only move left is `denounce`, which makes it worse. A one-way door, true
before this cycle and made far easier to fall through by it. `tribute` reaches
to −100 now — the crude one that works on people who cannot stand you, which
is exactly what its own blurb always said. Climbing back from the floor takes
555 days of steady tribute.

Eight checks in a new `test_courting` suite, each proven to bite. One mutation
did *not* bite and the reason is worth keeping: the "peaceful powers take no
offence" claim is held up by two independent guards, so removing either one
alone leaves the other standing. Defence in depth, not a hole — recorded in
the check so nobody chases it.

589 checks green.

## 2026-07-28 — SEEDFALL: a ship that shows what has happened to her

Following the standing request to keep improving the graphics, especially of
the ships. Two things were wrong: the model was lit badly, and it was silent.

- **A ship at 25% hull rendered pixel-for-pixel identically to one fresh out
  of the yard.** Every reading of the damage was a percentage in a side panel;
  the picture — the one thing always on the screen — said nothing at all.
  Damage now shows as blight spreading over the hull, following the outermost
  layer, which is the one damage lands on first and the one you could see.
- **The blight is patches, not static.** The first version hashed each face on
  its own and produced a checkerboard, which reads as a broken texture rather
  than as a wound. `speckle()` is coherent now: everything inside one `PATCH`
  cube shares a number, so neighbouring faces rot together. Measured, touching
  faces agree 79% of the time against 50% for face-by-face scatter.
- **It scatters without dice.** Drawing happens many times a second, so using
  `game.rng()` would mean two captains who looked at their ship a different
  number of times got different chronicles. A check exists solely for this.
- **Lighting: key, fill, rim and specular** instead of one lambert term. The
  rim is what separates the silhouette from the void; the specular is keyed to
  material, so a grown membrane (gloss 0.10) and a fabricated plate (0.55)
  stop looking like the same plastic in two colours. Faces also fade with
  distance, and the flat black backdrop is a graded well of light, so the hull
  has something to sit against.
- **The per-face outline is gone.** It existed to hide the hairline seams
  antialiasing leaves between polygons, but drawn darker than the face it drew
  a lat/long grid over a hull that is supposed to be grown. Same purpose, same
  colour as the face.
- **The caption names the skin.** "hull 93%" beside a visibly rotten ship read
  as a rendering fault; it now reads "hull 93% · sacrificial epidermis 45%".

Eight checks in a new `test_picture` suite, every one proven to bite by
reintroducing the bug it exists for — including the two that first did not.
The pixel check compares two renders rather than inspecting fields, because a
field on a dataclass proves nothing about what the captain can see.

**My own error worth recording:** the first coherence check asked whether a
marked face had a marked neighbour. With half the hull marked that is true by
chance — per-face static scored 99% on it. The metric had to become neighbour
*agreement* against the chance baseline before it could tell the two apart.

581 checks green.

## 2026-07-28 — SEEDFALL: a seam that can actually be worked out

Same method as last cycle — measure a system for a dominant strategy before
touching it — this time on mining.

- **A body never ended.** It capped at 95% depleted and went on paying 1.1 t a
  session without limit: measured at trip 20 and still paying at trip 199. So
  "this seam is finished, move on" was never an event, and the gentle methods
  bought nothing, because the cap arrived whatever you did.
- **Now it refuses the rig**, and the four methods pull apart properly. From
  one body: `bore` 2.45 t/day for 202 t total; `leach` 1.01 t/day for 407.
  Rate against lifetime — a real decision, and one that depends on whether
  bodies are plentiful or scarce.
- **The panel states both**, because neither figure can be worked out from the
  other.
- **The forecast is calibrated against the thing it forecasts.** My midpoint
  estimate read 15% high, consistently, for every method — including `skim`,
  which has no mishap risk, so it was arithmetic and not collapses. Rather
  than ship a flattering forecast I measured the gap and named it
  `WORKING_LOSS`; `test_seams` re-measures it, and it now lands within 2%.
- **An existing check had encoded the old behaviour** — "a worked-out body
  still pays, but less" — and broke when the body started refusing outright.
  Updated to the stronger claim rather than softened.
- And my first two attempts to measure any of this failed on my own driver: I
  filled a 340-tonne hold with 9000 tonnes of fuel and then read "no room in
  the hold" as a mining bug.
- 573 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: pushing a programme finally costs something

Research, untouched until now. It looked deep — evidence types, four
approaches, setbacks and breakthroughs — so I measured it before touching it,
and found that `push` was simply the correct answer: 76 days to unlock against
`careful`'s 132, with its 28%-a-season setback already priced into that
number, because a setback costs progress and progress is exactly what the
measurement counts. Four ways to run a programme and one of them right.

- **A pushed result is provisional.** The blurb had said so all along — "build
  on results nobody has replicated" — and nothing read it. The technology
  unlocks and delivers 55% of its bonuses until somebody checks the work,
  which costs bench time and no evidence.
- **Measured after**: to two *sound* technologies, `parallel` wins with a full
  bench, `copy` with a thin one, and `push` — still fastest to raw capability
  — is now the slowest of the four to soundness. The screen states the
  unreplicated rate beside the pace, and the debt has its own panel.

**Four measurement errors of my own, all caught by looking twice.**

- I "found" that evidence scarcity did nothing — identical times whether the
  bench was flooded or starved. It was my trickle: the tech wanted `hardware`,
  which I never supplied, and even my "starved" rate of 8 a month exceeded the
  real requirement of 5–7. A genuinely empty bench takes 2.4× as long.
- I asserted confirming costs no credits. Days pass and wages are paid; that
  is the clock's business, not the bench's.
- I looked for a bonus-granting technology among the *starting* ones. None of
  them grants a passive bonus, so `next()` raised `StopIteration` and the
  harness reported an empty failure message.
- And I twice wrote a test file with a `def _();` stub in it, which is a
  syntax error, not a placeholder.
- 568 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: a near miss on the ground finally pays

Breadth, and a lead from the tripwire: `expedition.SPOILED` was a constant
sitting at its own degenerate value — `0.0`, commented "what a spoiled attempt
is worth, as a share", and read by nothing at all.

- **Every attempt on the ground was all-or-nothing.** Missing by one and
  fumbling by five were the same outcome: zero, plus a 40% chance of springing
  a hazard. An officer's level was a cliff rather than a slope, and the ground
  screen — which states the odds, the prize and the hazard — had nothing to
  say about failure at all.
- **A near miss now pays a tapering share.** Measured: 645 credits for missing
  by one against 351 for missing by two, nothing beyond the window, and
  12–36% of a clean attempt across every reward type.
- **The screen says so first**: "17% of the time, about 30% of the prize still
  comes back."
- **A guard for last cycle's lesson** — a suite that does not exist looks
  exactly like a suite that passes. `tests/test_harness_guard.py` asserts
  every name in `ALL_SUITES` dispatches to a real module with a `run`. Written
  as a subprocess first, which recursed until it timed out because it lives
  inside a suite.

**Four of my own checks were too weak, and trying to break them proved it.**

- The taper check compared two noisy means with a bare `>`, which passes about
  half the time with the taper deleted. It requires a 1.25× margin now.
- The fumble check counted empty-handed failures, but `lore` options never
  salvage, so deleting the near-miss window entirely still left plenty of
  empty hands. Then, corrected for that, it *still* passed — because the taper
  goes negative at a wide miss and zeroes small prizes on its own, so the two
  rules overlap. The precise claim is simply that nothing beyond the window
  ever pays, and that is what it asserts.
- The "missing by more" check originally asserted the constants existed and
  returned. That is not a measurement.
- And I read a "325 unit average salvage" as a bug when it was arithmetic
  nonsense of my own: averaging credits (900–3400) with ore (8–26). Compared
  per reward type it was 12–36% throughout.
- 562 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the approach, drawn and flyable

The last of the piloting request. The docking mini-game modelled an error and
a drift per axis, a blurred readout and a hull-set precision, and delivered
all of it as three integers and six buttons — with the drift not delivered at
all.

- **It is drawn now.** Range and attitude as a position against the collar,
  roll as the hull's tilt, the tolerance box at the centre, and a ghost of
  where the next correction lands with the drift counted. A roll error is not
  a position, so it is not drawn as one — that would be a prettier lie than
  the numbers were.
- **Every burn says what it leaves**, and which axes it lets slip while you
  make it. That was the invisible rule: firing on one axis walks the other
  two, and nothing ever said so.
- **A drive computer**, on the same `doctrine` stat as the battle computer. It
  weighs how far an axis is out against where its drift is taking it, and
  cannot fire harder than the hull allows.
- **And it is priced.** First measurement: the autopilot docked 59.5% of the
  time against a careful hand's 58.5% — identical, free, and therefore an
  argument for never flying an approach again. A computer-flown dock is graded
  as a bare clean one now: 68% at grade 1.00 against 68% at grade 2.39 by
  hand. The machine brings you alongside; it does not bring you alongside
  well.
- **A guard for last cycle's lesson.** A suite that does not exist looks
  exactly like a suite that passes — running a missing one prints nothing and
  exits zero. `tests/test_harness_guard.py` asserts every name in
  `ALL_SUITES` is dispatched to a real module with a `run`. Proven by removing
  a registration: it names the missing suite. Written as a subprocess first,
  which recursed until it timed out, because it lives inside a suite.
- **And the derived-state trap again**, in my own hands: I set
  `ship_stats.doctrine` for a screenshot and `recompute()` threw it away, so
  the screen reported no computer fitted. Third time; `stock_fx` is the input,
  `ship_stats` is the output.
- 557 checks green, every file under 500 lines — `test_sim` crossed it, so the
  harness checks moved out.

## 2026-07-28 — SEEDFALL: the hands get older, and can finally be replaced

A player asked why hands have no ages. Because `ship.crew` was an integer.

- **A mean and a spread on the hull**, aged by proper time at the lineage's
  rate. Still a mass — the game treats the hands as a headcount on purpose —
  but a mass that gets older. Measured: a fed crew goes from 29 to 98 over
  seventy years and falls from 34 aboard to 6.
- **The spread makes it a slope.** Forty hands started four years short of the
  span leave over seven years in six separate losses, not one cliff.
- **They can be signed on.** `ship.crew` only ever fell before — combat,
  hunger, a sleep somebody did not wake from — and there was no way to take
  anybody on at all. A crew that can only shrink is an unfixable loss rather
  than something you manage. Within the berths that exist, for a fee, and a
  young intake pulls an old deck from 80 back to 49.
- **Dormancy now reaches them**, which closes the loop on last cycle: a
  sleeping mess deck ages 0.21 years where an awake one ages 1.00. That saving
  was previously real and unmeasurable, which is precisely why the
  `put_under` bug hid.

**Three faults of my own, two of them found by the tool I built last cycle.**

- The tripwire immediately reported four of my *new* constants unprotected —
  including `SIGNING_FEE`, whose check asserted `spent == SIGNING_FEE * 8`.
  That is the tautology again, on brand-new code, caught before it shipped
  rather than three cycles later. It asserts a range written in the check now.
- It also reported them unprotected for a second, different reason: the
  tripwire kept its **own copy of the suite list**, which went stale the
  moment a suite was added, so the `hands` suite was never run and the
  constants it protects looked unguarded. `ALL_SUITES` is published from
  `tests/__main__` now and the tool derives from it.
- And a `git checkout` I ran to undo a bad edit quietly reverted this cycle's
  suite registration, so `python3 -m seedfall.tests hands` printed nothing at
  all and exited zero. A suite that does not exist looks exactly like a suite
  that passes.
- 550 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: auditing the tests instead of trusting them

Last cycle I said the tautological-check habit was mine and I would watch for
it. Watching is not a method, so: a tool that changes every tuning constant in
the game and reports the ones nothing notices.

- **`tests/tripwire.py`.** Zero, double or halve each of 131 module-level
  constants; run the suites; report the survivors. A survivor is dead code,
  a tautologically-checked number, or a genuinely unpinned one.
- **60 of 131 are unprotected.** The worst is `approaches.ODDS_PER_DAY` —
  zero it and no envoy ever arrives again, retiring the whole diplomacy
  feature I shipped two cycles ago, with 535 checks still green.
- **The tool poisoned itself first, and I nearly believed it.** Its first run
  said sixteen. It was rewriting source between runs while Python served
  `.pyc` files compiled from the *mutated* text, so restores did not reliably
  take — I found it when a check crashed with `PER_LOSS` reading 0.0 at
  runtime and 9.0 on disk. Bytecode is disabled in the children now, and the
  caches are cleared at the start. A tool that audits the tests has to be
  audited too, and the honest number is nearly four times the flattering one.
- **`tests/test_tuning.py`** pins the eight worst, every one against a figure
  written in the check rather than against the constant it guards. 52 remain,
  listed in the task queue.
- **A killed sweep left mutated source in the tree.** It restores on SIGINT,
  SIGTERM and exit now — a tool that edits source has to put it back on the
  way out, not only on the happy path.

**And two player questions, both of which found real holes.**

*"Why don't hands have ages?"* Because `ship.crew` is an integer. The 34 hands
are a headcount with nothing to hang an age on, so "your crew ages on a long
crossing" is true for 3 of 37 people — and it is exactly why last cycle's
dormancy bug hid so well. Queued with a design: a mean and a spread on the
ship, not 34 records.

*"Why can a ship refit when not docked at a shipyard?"* Because the rule was
in the button and not the simulation. `apply_refit` checked the design and the
cost and nothing else, so the remote bridge could strip a hull in deep space —
and the button's own rule tested "this system has a port", which is neither
being alongside nor being at a yard. `shipyard.can_refit_here` now expresses
it through the anchorages, and two existing checks that had been quietly
relying on the loophole had to be docked first.

- 543 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: sleeping through it, and a sugar that finally does something

The half of the player's time request I left undone. Ageing, lineages and
upkeep shipped; the counter-measures did not, so a long crossing had exactly
one answer — fly harder, pay in reaction mass. An engineering answer to a
biological problem.

- **`trehalose` finally does something.** It has been in the commodity tables
  from the beginning, described as vitrified sugar with CAHS proteins that
  replaces the water in a cell and holds it unbreathing — the sugar real
  tardigrades use — and nothing had ever consumed a gram of it.
- **Three methods and a null.** Cold sleep, trehalose vitrification, and
  low-power idle, which only a Dry Choir lineage can do because it is not
  sleep. Measured over 600 days: a sleeper ages 0.07 years against the watch's
  1.64 and eats 13 tonnes against 61.
- **It does not stack free with dilation.** Both cost the ship's own work, so
  doing both costs it twice: 712 research over a year awake at rest, 154
  asleep, 123 at dilation 4, 30 doing both.
- **A bug that made the headline benefit unreal.** `put_under` slept the hands
  first and the officers last, so with 34 hands and 30 sleepers *no officer
  ever went under* — and officers are the only people in the game who have an
  age. The saving the screen advertised was arithmetically invisible. Sleepers
  are drawn proportionally now, with at least one officer always on the
  bridge, and the measured ageing moved from 1.64 → 1.64 → 1.64 across all
  three methods to 1.64 → 0.58 → 0.07.
- **Ninety-nine tonnes of sugar.** The first vitrification rate put a third of
  the hold and sixty thousand credits into one crossing, which is not an
  expensive option but a closed door. Cut to 32 tonnes.
- **The screen quoted arithmetic about a crew that was not aboard** — the
  Dry-Choir-only method showed ageing and ration savings computed from *this*
  hull's wet lineage while being disabled. It states its case in words now.
- **Another tautological check of mine**, the third in as many cycles: the
  watch floor asserted `total - room >= round(total * MIN_WATCH)`, which reads
  the constant whose effect it tests and passes with it zeroed, because
  `max(1, …)` leaves one person awake and the arithmetic agrees. One person is
  not a watch on a thirty-seven-hand hull. It asserts an absolute floor now.
- 535 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: closing the crash class, and catching a signal

Last cycle a player segfaulted the game on a drop-down and I fixed the two
call sites that were missing a `defer`. That was the third time this rule has
cost a crash — a `Card`, a `QLineEdit` mid-keystroke, now a `QComboBox` — and
the third time the fix was one call site at a time, after a player found it.

- **The class is closed at the root.** `View.refresh` freed the old widgets
  synchronously, which is what let any handler destroy its own emitter. The
  outgoing widgets are now parked on the view and released on the next turn of
  the event loop, so whatever emitted outlives the event it emitted during
  whether or not the call site deferred. Measured no leak: 220 rebuilds, zero
  widgets still held.
- **A flaw in my own fix, caught by thinking about it rather than by a test.**
  Parking by assignment meant two rebuilds inside one event would drop the
  first batch synchronously — the same bug in a rarer hat. It extends now.
- **The suite can catch a segfault instead of being killed by one.** Every
  driver here chooses from a combo with `setCurrentIndex` or by emitting
  `activated`; neither opens a popup, and the crash lives entirely inside
  `QComboBoxPrivateContainer::eventFilter`. That is why five hundred checks
  missed it. `tests/popup_probe.py` sends real mouse events to the popup's
  viewport and runs out of process, so the failure mode is an exit code.
  Backing the fix out reports **exit -11**, which is the player's crash,
  reproduced.
- **The invariant, stated precisely.** The combo must be alive *at the instant
  Qt returns from delivering the click* — not afterwards. My first probe
  asserted aliveness after four `processEvents` and read False for a
  completely legitimate reason: the deferred rebuild had long since run. A
  check measuring the wrong moment would have condemned correct code.
- 526 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: somebody behind the counter, and a segfault from a combo box

**A crash first.** A player segfaulted the game choosing from a drop-down. The
stack named it exactly: `QComboBoxPrivateContainer::eventFilter` — the popup
was still delivering the mouse release that dismissed it when the handler
called `refresh()` and freed the combo underneath it. `widgets.defer` exists
for precisely this and `options_view` already used it; `diplomacy_view` and
`yard_view` did not. Both defer now.

525 checks had missed it because the driver sets `currentIndex`
programmatically, which never opens a popup and never takes that path. So the
new check tests the *invariant* rather than the path: **after emitting its own
signal, a control must still exist.** Writing it walked straight into the bug
under test — collecting the combos once and firing each in turn meant the
first deferred rebuild freed the rest, and the check itself died of a
use-after-delete. A fresh window per combo, the pattern `drive()` already used.

**And the cycle's feature: harbourmasters.** A quay was a bag of services with
nobody in it, while `memory.py` had supported a `port` mind since the day it
was written and never had one attached.

- **Derived identity, stored relationship.** Name, temper and the lever that
  could exist are seeded from the port; regard, memories, levers found and
  favours running live on the mind that persists.
- **Trading has a ceiling.** Squareness makes somebody helpful and stops. Past
  that you need what they want or what they fear — which is the whole point,
  because a relationship you can grind is not politics.
- **Leaning is a different transaction, not a cheaper one.** The first cut had
  it cheaper *and* unconditional, which made the lever strictly better than
  the relationship and deleted the decision. It now costs 1.6× asking, spends
  the lever, and permanently lowers the ceiling: 300 dealings afterwards reach
  36 where somebody who never leant reaches 48.
- **Every favour is read somewhere** — a search skipped, a board of 5 → 7 with
  better work on it, goods 12% inside the posted price. Checked against the
  systems they change rather than asserted.
- **A stranger read as "cold"** because `START_REGARD` sat inside the cold
  band. Somebody you have never met is not hostile; they are doing their job.
- **The `office` state was invisible to the save codec** — an attribute hung
  on a dataclass at runtime rather than a field, so every harbourmaster forgot
  you, your levers and your favours on reload. Found by the check, not by
  reading.
- **A tautological check of my own**, again: it asserted
  `after_cap == before_cap - CAP_PER_LEAN`, reading the very constant whose
  effect it claimed to test, and passed with that constant zeroed. Rewritten
  to compare two measured outcomes.
- Being boarded now costs you with the person who signed the order, not only
  with the power.
- 525 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the powers stop being a vending machine

Diplomacy was the top standing priority and I had spent three cycles on
piloting and combat, so: the board.

It ran one way. Six actions, all player→faction — send a tribute, share
intelligence, propose a treaty — and the four powers did exactly one thing
between them, `drift`, pulling their grievances back toward a baseline. You
put standing in and took tariffs out. Nobody ever knocked.

- **An approach has to be caused.** A power asks for silicon because its quays
  are short of silicon; it asks you to denounce the Freeholds because it is
  losing to the Freeholds; it warns you off a rival whose cargo you have been
  carrying; it offers terms because your standing passed 62; it levies ground
  you hold inside its space. The die only decides *when*, among reasons that
  already exist — pinned by a check that plays four hundred months with every
  trigger dead and demands zero envoys.
- **Three answers, all costed first**, and letting the window lapse costs
  exactly what refusing costs. An offer with a free deadline is a button that
  waits forever, not a decision.
- **Two bugs in my own new code, both the same shape as the ones this project
  keeps finding elsewhere.** `_shortage` read a `demand` mapping that `Market`
  does not have — it has `stock` — so `getattr(..., {})` returned empty every
  time and **requisitions could never fire at all**. Fixed, it then reported
  every power short of `wildseed`, which nothing stocks and no captain hauls:
  a shortage real in the data and meaningless as a request. Now restricted to
  tradeable goods actually in your hold, which is also what the flavour claims.
- **A dead wire I nearly shipped.** The clock hook was written against an
  eight-space indent, but `advance_days` had been dedented into `core/clock.py`
  two cycles ago, so the replacement silently did not apply. Measured before
  believing: eighty chronicle-years, zero approaches. With it wired, about
  eight per decade — one every fifteen months, which is a thing that happens
  to you rather than a weekly appointment.
- **Two of my mutation tests were inadequate rather than the checks weak.**
  Removing the "they are not talking to you" guard did not produce an uncaused
  envoy, because every other reason still required real state; and setting the
  quoted price to a constant kept preview and payment consistent, which is
  what the check actually verifies. Broken properly — reasons invented from
  nothing, and a payment 20% short of the quote — both bite.
- Ten years driven through the real window: 34 approaches, navigation held on
  every one, all answered by real button clicks.
- 514 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the plot finally shows what bears

The other half of #56. The tactical plot drew range rings and two triangles,
and never drew the one thing the whole geometry exists for.

- **Everything was already modelled and none of it shown.** The arc, the
  bearing, the range band, the magazine — all knowable before the turn, all
  reaching the player only afterwards as a log line saying the shot they had
  just spent a turn on did not happen.
- **`sim/firing.py` answers per mount, first**: bears or not, and if not
  exactly how far the bow must come round or how many bands to close. The plot
  draws one wedge per *arc* — one per mount stacked five identical broadsides
  on top of each other — lit when something in it bears, with the enemy's arcs
  faint, because sitting in a forward arc is a decision.
- **Three opinions about whether a gun can fire.** `combat._fire` refuses
  above 0.6; every selector picks only 0.5; `assessment.mounts` called
  anything above 0.5 out of range. **In practice the gap is empty** —
  `bears_at` steps 0.22 a band, so the reachable penalties are 0, 0.22, 0.44,
  0.66 and nothing lands between. A landmine, not a live bug, and saying
  otherwise would have been a better story than the true one. Both constants
  are named now, `assessment` delegates, and a check holds the gap shut.
- **The fire buttons tested range and nothing else.** A mount sixty degrees
  off the beam or with an empty magazine was offered, taken, and spent the
  turn on a log line explaining why it had not fired.
- **Two panels saying the same thing.** `assessment_panel` already listed
  mounts and bearings; the new picture supersedes it with the band, the
  magazine and the enemy's arcs, so the duplicate came out rather than being
  left to disagree.
- **Three of my own checks were wrong, in three different ways**, and only
  trying to break them showed it:
  - the closing-rate check excused `|rate| < 1` as agreement, which forgives
    precisely the failure of always returning zero — and once fixed it failed
    against the real code, because the rate is instantaneous and the hulls
    steer before advancing. The honest fix was to test it against its own
    definition and document what it is;
  - the assessment check compared one band, where "bears" and "worth firing"
    coincide, and passed with the two rules forked wide open. It sweeps every
    band now, and the fit carries a `lixiviant` on purpose so a mount can be
    in arc and genuinely unusable;
  - the marginal-mount check asserted a state the game cannot reach, which is
    how the landmine was discovered.
- `combat.py` crossed 500 lines, so a hit and its narration moved to
  `sim/damage.py`; the plot moved to `ui/tactical_plot.py`.
- 505 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the seats you leave stop being stupid

Task #56, the half about automatic piloting and battle systems. The gap turned
out to be sharper than "add an autopilot":

    if not directed:
        order_id = side.helm_order or "hold"     # repeat, forever

An unattended helm repeated your last order until you came back to it, and an
unattended gunner salvoed every turn whatever the heat and whatever bore. Order
*close* and walk to gunnery, and the helm flies you down the enemy's throat for
the rest of the engagement. That is a punishment for looking away, not a
decision about where to spend attention.

- **A battle computer chooses.** `sim/doctrine.py` reads band, aspect, heat,
  hull and what bears, and picks an order for every seat nobody is in.
- **It says so first.** The battle screen names the order and the reasoning
  before the turn resolves — a system that acts on your behalf without stating
  its intent is this project's signature defect wearing a uniform.
- **It is not free and not better than you.** `doctrine` comes off the compute
  fitting, 0.15 for the core you launch with to 1.00 for a Cold Ledger, and
  below 0.30 there is no computer at all — so the hull you start with behaves
  exactly as it always did, which is what the other 490 checks assume. A seat
  run by the machine works at the officer's rate: measured, it vents 90% of
  what you vent sitting in it. Measured effect over 24 fights: 12.1% of the
  enemy hull removed with no computer, 16.9% with an excellent one.
- **A bug that gave confident bad advice.** `_bearing_count` read
  `side.weapons`; the mounts hang off `side.st.weapons`. It returned an empty
  list every time, so every count was zero, gunnery always concluded "nothing
  bears", and the helm came about forever chasing an arc it was already in.
  Nothing raised. It simply advised badly, with complete confidence — the
  worst failure mode an advisory system has.
- **Doctrine was coupled to a Battle it never had.** The first cut took the
  range band off `battle.range_units`, but `run_helm` is handed two sides and
  nothing else. The two bodies already know how far apart they are.
- **A check that demanded variety where correctness implies constancy.** My
  first version asserted the computer's helm order *changed* over a fight — but
  a hull already in its preferred band should say "hold" every turn and be
  right to. It was failing the computer for being correct. Rewritten to the
  actual claim: does it *depart from what it was last told*, and does it adapt
  across situations rather than parroting one answer? 10/10 engagements depart.
- 498 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the sector stops being empty, and the chart starts predicting

Follow-on from the helm complaint. Quays got positions last cycle; ships had
none at all — encounters were rolled the instant you arrived and thrown away,
consorts followed you implicitly, ventures were a number in a ledger.

- **Traffic has somewhere to be.** A handful of hulls per system — traders,
  patrols, prospectors, couriers and the occasional unmarked hull — each with
  a name, a faction, an errand and a position that moves along its leg with
  the clock. Busyness follows the port: a capital works five, unclaimed space
  one, a bloomed system fewer than either, because the traffic left.
- **Derived, not stored**, like anchorages. Persistent identity with no
  migration, at the price that derivation must never touch `game.rng()` —
  that advances with the save, so a reload would hand you a different sector.
- **The chart predicts now, which is the whole point.** `roll_encounter`
  weighs who is actually present, so the hull that turns onto you is one you
  could have plotted first, by name. Measured: 18% of arrivals contested where
  something runs dark against 6% where nothing does — same system, same day.
- **Two hulls with the same name.** The pools hold four or five names each and
  a capital works five hulls, so the chart showed *Long Consent* twice — which
  makes "the hull you plotted" meaningless exactly when it starts to matter.
- **`position()` defaulted to the wrong system.** It fell back to
  `game.system`, so asking about traffic anywhere else indexed one system's
  body list with another's indices and raised `IndexError` — on the very call
  `hostiles()` makes to sort. A hull carries its own system id now.
- **Labels piled into a smear** where traffic converges on the quay. A hull is
  named on the chart only where there is room; the panel names them all.
- **Three of my own checks were weaker than they read**, and only trying to
  break them showed it:
  - "what is on the chart is what stops you" verified a linked id and nothing
    else — it passed with the name assignment deleted. It now asserts the ship
    you meet *is* the hull you plotted.
  - "running dark makes a system more dangerous" measured a **confound**:
    unmarked hulls appear in portless and bloomed systems, which were already
    the dangerous ones, so it passed with my contribution set to zero.
    Rewritten to hold the system fixed and vary only the traffic.
  - "hulls move" looked at one system whose hulls all held station, measured
    nothing, and passed. It scans fourteen systems now.
  - And one mutation of mine was inadequate rather than the check being wrong:
    running dark has two effects and zeroing the danger term left the
    guaranteed-encounter path, so the check was right to survive it.
- `HULL_NAMES` moved from `sim/encounters.py` to `data/lore.py` — encounters
  asks traffic who is present, so traffic cannot import encounters.
- 491 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: a quay is a place, not a screen you switch to

A player at the helm: *"the map only shows the sun and planets. What about
other known ships or stations, the fleet hub and other shipyards? I think the
game starts at a shipyard but it is hard to tell... How would I navigate back
to a shipyard if it is not on the map?"*

They were right, and the reason was worse than a missing marker.

- **A `Port` had no position at all.** No body, no orbit, no coordinates — it
  hung off a `System` as a bag of services. The quay you were standing on was
  nowhere in space, and docking was a screen you switched to from the chart.
  So the one view you actually fly from could not show you the one place you
  most need to fly back to. That is why nothing was drawn: there was nothing
  to draw.
- **An anchorage is now anchored to a body**, so it inherits a real orbit that
  moves with the clock — and every intercept, burn profile and transfer quote
  works on it unchanged, because flying to a quay *is* flying to the body it
  orbits. No special case anywhere in `sim/flight`.
- **Derived, never stored**, like `ship.stats()`. One source of truth, no save
  migration, and no way for a stored quay to disagree with its port.
- **The helm answers the question now.** Quays, capitals and your own holdings
  are drawn and labelled; the header says *"In orbit of Loam Span I, alongside
  Fleet Hub"* rather than a bare body name; and a panel lists everywhere you
  can put in with a course and a fuel bill. `offering(game, "shipyard")` is
  the literal answer to "how do I get back to a shipyard".
- **The confusion was real and measurable.** A fresh chronicle starts in a
  system *with* a Fleet Hub but 4.26 AU off it, not at it — which is exactly
  why the player could not tell whether they had started at a shipyard.
- **Two layout defects caught by rendering it.** Three columns fitted a wide
  desktop and silently dropped the third at any ordinary window size, so the
  new panel was invisible at 1400px; it is stacked under the chart now. And
  the sector chart named a port without saying what it offers, which makes
  "which of these has a yard" unanswerable.
- **A tautological check, caught by trying to break it.** The stability check
  passed with the anchor deliberately broken, because my mutation was still
  deterministic — the property could not fail given the function's signature.
  Rewritten to something that genuinely can: the berth must survive time, RNG
  draws *and* a save/reload, which is the real risk for derived state. It now
  fails against a truly wandering anchor.
- **Not done, and not pretended:** known hulls are still not plotted. Nothing
  in the game gives another ship a persistent position, so that is a separate
  piece of work rather than a marker.
- 484 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: two clocks, and four kinds of person to feel them

The player asked for time to matter — ageing over long crossings, hibernation,
lifespans, and different needs for wet crew, cyborgs and synthetics — then
added the thing that reframes it: *"Don't forget that time is relative."*

- **A lineage is a substrate.** Everyone aboard used to be the same thing:
  immortal, breathing, eating nothing. Four lineages now, differing in span
  (96 to 900 years), ageing rate (1.00× to 0.07×), what they consume, and
  whether the atmosphere plant matters to them at all.
- **The Choir stops suffocating.** The opening screen sells a Dry Choir
  lineage on "no air to run out of", and the daily tick killed recordings by
  asphyxiation on exactly the same schedule as a wet crew. The purest form of
  the defect this project keeps finding: a screen promising a consequence the
  simulation never read. A wet crew now dies in 120 airless days; a Choir crew
  does not notice.
- **Two clocks.** `Game.day` is the Verge's and drives every deadline, market,
  colony and faction. `Game.ship_day` is proper time and drives ageing,
  upkeep, repair, refining, wages and the research bench. `advance_days(n,
  dilation)` writes both. The split is what stops a hard burn being free: at
  dilation 6 a year of clock ages the crew 0.14 years instead of 1.0 and eats
  a sixth of the food — and banks 320 fewer research points.
- **Four ways to fly a crossing**, from a long coast (1.55× days, 0.45× fuel,
  clocks agree) to a relativistic run (11× dilation, 5× fuel). The map states
  all four costs before you commit: days out here, days lived aboard, reaction
  mass, what the crew eats and what it does to their span.
- **Provisioning follows the crew.** A hull launches with 220 days of what
  *its own* lineage eats, so a Choir captain is not punished on day one for a
  choice made on the character screen.
- **Two promises I broke and fixed.** Provisioning by lineage made the opening
  screen's forecast wrong twice — first the biomass (the screen quoted the
  chassis's fifty berths against the thirty-four that actually sail; `crew =
  34` was a bare literal inside `new_game` that the screen had no way to read)
  and then the alloy (routing `new_game` through the same helper double-counted
  the origin's stores, which `apply` already adds). Both are now one function
  with one caller each, which is the only durable fix for that class.
- **A ten-minute hang, from my own new control.** The suite stopped dead on
  `system/'Close pass'` against a wrecked hull: the survey flies seventeen days,
  the crew dies, the ending dialog returns nothing, and the fall-through starts
  a *new* chronicle — which opens the opening dialog and waits forever for an
  answer nobody was going to give. `interact.py` had already learned this from
  the shipyard's name prompt; `test_verbs` now neutralises modals too.
- **A dead promise, wired up.** Three colony classes advertise sensor reach and
  `colony.effects` had tallied it per system since the day they were written —
  nothing ever read the tally. Surveys gave the number teeth, so a relay node
  now doubles what you can sweep from where you are.
- **My own measurement errors, twice.** A check that overrode `ship_stats` and
  another that overrode `colony_fx`: both are *derived*, both are rebuilt by
  `recompute`, and both threw the override away mid-check — so the check
  measured a sharp instrument for the forecast and a blunt one for the survey,
  then blamed the forecast. And an airless-crew check that advanced 120 days in
  one call, letting `repair_tick` heal the life layer so the air came back.
- All four new time checks proven to bite by reintroducing the bug. 477 checks
  green. `core/state.py` crossed 500 lines the day time stopped being uniform,
  so the daily tick moved to `core/clock.py`.

## 2026-07-28 — SEEDFALL: four ways to look at a world, and three that never paid

Answering a question from the player: *"how are surveys carried out? They seem
to have no cost and are all the same."* They were. One button, three days, no
cost, no risk, and the same kind of answer for a comet as for an ocean world —
while thirteen sensor fittings and a drone technology existed only to nudge a
single `scan` float.

- **Four methods, deliberately not a ladder.** A long-range sweep is not a worse
  close pass; it is a different question. It costs no travel and no stores, and
  it cannot see anything that moves or anything buried. A probe swarm goes where
  the hull will not, needs `dronework` and eats silicon and alloy every time. A
  deep survey is the only thing that reliably finds a buried site, and it wants
  nine days, reaction mass for the charges and a real sensor suite. Each names
  what it `finds`, and `world/planets.survey_body` is filtered by that list, so
  a method that says it cannot see lifeforms genuinely cannot.
- **The panel states the whole bill before you commit** — days, stores, what it
  will find and, the part that makes it a decision, *what it will be blind to.*
- **A forecast that lied by nine days.** `flight.ensure_at` quietly drops to a
  coast when there is not enough reaction mass for a standard burn, and a coast
  is slower. The preview always quoted the standard burn, so on a dry tank it
  promised seven days for a trip that took sixteen. Fixed by forecasting the
  profile that will actually be used.
- **A bill that hid most of itself.** The deep survey quoted four tonnes of
  charges and spent seven: flying the hull alongside burns reaction mass on top,
  and the card never mentioned it. `full_cost()` now folds the flight in.
- **Three colony works that paid nothing.** Vigil viva, a CHORUS node and a
  reactivated array all advertise sensor reach, and `colony.effects` has tallied
  it per system since the day they were written — and *nothing ever read the
  tally.* `stats()` also dropped any `sensor` bonus on the floor, summing only
  fittings. Both were invisible because until surveys the number decided
  nothing; now it gates the free method. A relay node takes reach from 4.00 to
  8.00 AU. It stays per-system rather than folded into `ship_stats`: a dish
  spread across one system should not help you three jumps away.
- **Two of my own measurement errors, caught before they became findings.**
  I "fixed" a forecast mismatch that was really my check poking `ship_stats`,
  which `advance_days` rebuilds from the hull and throws away — the check
  measured a sharp instrument for the forecast and a blunt one for the survey,
  then blamed the forecast. Same lesson a second time with `colony_fx`. Derived
  state cannot be overridden by a test that moves the clock; the fixture now
  goes through real inputs and plants a real colony.
- **Proving the checks bite.** Reintroduced all four bugs. Three failed
  immediately; the coast-forecast one **passed**, because the fixture always had
  fuel for a standard burn — so the fix was unproven and the path untested.
  Added a dry-tank case: it now fails with "said 7 days, took 16".
- 466 checks green, every file under 500 lines. `system_view.py` had crossed the
  limit at 505, so the survey report moved to `ui/survey_panel.py`, where it
  belonged anyway.

## 2026-07-28 — SEEDFALL: playing by pressing, and a helm warning that said nothing

- **Measured the gap first.** A six-year chronicle makes **zero** fractional
  day advances, which is why nothing in the suite could reach the crash a
  player hit in four minutes. The chronicle plays by calling `sim` with the
  ship already in place; a player presses *Open cut*, and the handler flies
  the ship first. `tests/interact.py` plays by pressing instead — 132 presses
  of 107 distinct controls over 651 days in the committed check.
- **Two things had to be neutralised before a session could run at all.**
  `QDialog.exec` blocks, and so does `QInputDialog.getText`, which is static
  and does not go through it — the shipyard uses it to ask a hull's name, and
  a session that pressed *Lay down* hung for ten minutes waiting.
- **A player found the helm lying.** Every body in the system reported "you
  will be working 0.40 AU from the star", including one nine AU out. The note
  took the *minimum* of the ship's distance and the target's, so a hull parked
  close in reported its own position whatever you clicked. It is the
  destination's distance now, and a check requires the notes across a system
  to tell the destinations apart.
- **A watcher saw a pop-up, not the game.** `--new --bridge` ran the opening
  briefing, which is modal; the bridge's queued commands executed *behind* it,
  so the game was played invisibly. `--bridge` skips the modal opening now,
  and `blocked`/`dismiss` let a caller see and clear anything in the way.
- **Said plainly**: the session driver does *not* reproduce the fractional-day
  path, and I could not find which caller produces one — five seeds give no
  fractional flight quote. The calendar check pins the behaviour directly
  instead, which is the honest guard.
- Suites: 55 — 458 checks green. 239 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: driving the real window, and the clock it broke

- **Asked to play the game through its GUI as a watched systems test.** The
  bridge existed but held its own headless game, which is useless for
  watching. `bridge/attached.py` puts the same protocol in front of the
  *running* `MainWindow`, with `python -m seedfall --bridge`, and adds the
  verbs a watcher needs — `go`, `tab`, `screen`, `shot`.
- **What makes it safe is marshalling.** The socket runs on its own thread and
  the whole interface reads the `Game` from Qt's; mutating from one while the
  other paints is a data race. Every command is posted to the Qt event loop
  and the socket thread waits for the answer.
- **The test found a live crash within four minutes.** Putting the rig on a
  body killed the heading bar: `stardate` formats the day with `:03d`, and
  `advance_days` — annotated `n: int` and never coercing — had let a
  fractional transit turn `game.day` into a float. Everything downstream
  assumes whole days. The clock now carries the fraction rather than dropping
  it, with an epsilon, because a hundred tenth-days sum to 9.999999999999998
  and would otherwise lose a day every ten.
- **Two more, from reading what the game said aloud.** The ship's computer
  reported "before any of this, *they* were refused a berth" — a captain's
  backstory, because the bridge verb could not say what kind of thing was
  speaking. And the harbourmaster introduced himself as "Harbourmaster Vell,
  harbourmaster", a frame prefixing a title onto a name that already had one.
  Both pinned: every speaker must draw on its own kind of past, and no persona
  may say its own title twice in a greeting.
- The rest of the tour was clean: twelve screens, every tab, survey, trade,
  mine, jump, sixty days of clock, diplomacy, the 3D plans, and a voice.
- Suites: 55 — 456 checks green. 238 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the rest of the controls, and a second segfault

- **Generalised last cycle's crash rather than waiting for the next one.** A
  player hit an abort clicking a card, and the reason it survived 450 checks
  was that `test_verbs` drives `QPushButton`s — which Qt emits safely after the
  press — and nothing else. So I counted what else a player can touch: 135
  buttons and 98 cards covered, and **14 line edits, 13 spin boxes and 5 combo
  boxes that nothing had ever driven**.
- **The first one I drove segfaulted the process.** Typing a single character
  into the manual's search field killed the game — signal 11, not a catchable
  exception. `textChanged` fires *during* the keystroke, the handler rebuilt
  the view, `View.refresh` freed the field being typed into, and Qt returned
  into it. Two more connections on the options page had the same hazard.
- The rule now lives in one place: `widgets.defer()` runs a handler after the
  current event has finished being delivered, and `View.refresh_later()` uses
  it. Anything that rebuilds the widget which emitted the signal goes through
  it.
- **Fixing the crash was not enough to make the field work.** Deferred, it
  stopped dying and still accepted only one character, because the rebuild
  replaced the box and focus went nowhere. It restores focus and the cursor
  now — and the check types a whole word one key at a time into whatever holds
  focus, which is the only way to notice.
- Verified by putting each fault back: the card crash fails its check, and the
  search segfault takes the whole suite down with exit 139, which the "only
  commit if green" rule catches.
- `test_verbs` crossed 500 lines; the non-button controls moved to
  `test_controls.py`, driven from the same offscreen app.
- Suites: 55 — 453 checks green. 237 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a fight with one outcome, and a crash on every card

- **The task list was clear, so I went looking by playing.** The chronicle
  suite claimed to do everything and had never fired a shot: encounters were
  rolled on arrival and thrown away. Wiring combat into it produced thirty
  engagements in a decade — and every single one ended the same way.
- **Combat had exactly one outcome.** Measured over 360 engagements with the
  test captain: 100% "driven-off", both hulls at 100%, median 34 turns. No
  kills, no routs, no parleys, no damage at all.
- The cause was one rule with two implementations. `_fire` floors damage at
  `max(dmg * 0.15, dmg - armour)` — the comment says "something always gets
  through, or two well-armoured hulls would shoot at each other until the sun
  went out" — and `_apply_to_layers` then ran `while left > 0.5`, discarding
  anything smaller. For a three-damage weapon the floor is 0.45, so it was
  swallowed entirely: **the Photic Flash Organ, the only armament a new
  captain starts with, dealt exactly nothing to any armoured hull**, forever,
  while the log said "hits for 0" and the read panel correctly reported 0.45 a
  turn. The honest number was on screen; the ledger delivered none of it.
- Fixed the guard to an epsilon, and stopped the bridge reporting a landed hit
  as zero — thirty turns of "hits for 0" reads exactly like a broken weapon.
  A check now compares what the read panel says a shot lands against what the
  guns actually deliver.
- **Then a player hit a hard crash and sent it.** Clicking any card — a body on
  the System screen, a node on Research — aborted the process:
  `Card.mousePressEvent` emitted `clicked` inline, the handler rebuilt the
  screen, `View.refresh` unparented the old widgets and freed them, and the
  next statement called `super().mousePressEvent(ev)` on a deleted object.
  The emit is deferred by one turn of the event loop now.
- **Why nothing caught it**: `test_verbs` drives every `QPushButton` on every
  screen, and Qt emits those safely after the press completes. Cards have a
  hand-written `mousePressEvent`, and nothing had ever clicked one. There is a
  check that does now, and it fails when the inline emit is put back.
- Suites: 55 — 451 checks green. 236 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: costing the way out of a pocket

- **Task #44, and the measurement changed what I built.** A quarter of sectors
  open with fewer than eight of 42 systems reachable and one in eight with
  three or fewer, which looked like a generation defect. Before touching
  generation I played a two-system pocket for twenty-five years: evidence still
  accumulates in the hundreds, both its markets sell magnetite, the whole
  fourteen-technology chain to the Foldrunner is open from inside, and one
  pocket earned 71,000 of the 78,000 credits needed in under seven years.
  **The wall is a gate, not a lock.** Changing generation would have been
  fixing the wrong thing.
- **The actual defect was the project's signature one**: the chart named a way
  out — "a Foldrunner Coil would open 40 more, once researched" — and stopped
  there, which is the same shape as a contract fee with no cargo cost beside
  it. Measured, that way out is twelve technologies, 4,990 research points,
  78,000 credits and 20 tonnes of magnetite. A project, not a purchase.
- `reach.plan()` costs it and the chart prints it: what is still to research
  and for how many points, the credits and how far short you are, and **each
  material with the reachable ports that stock it** — because whether the
  pocket can supply its own way out is the thing that decides whether you are
  working toward something or waiting for nothing.
- The check that carries the finding asks it continuously rather than once: 24
  walled sectors, the smallest two systems, every one able to supply its own
  exit. Making one material unobtainable fails it, so if generation ever
  produces a real trap the decision not to change generation gets revisited.
- Suites: 54 — 445 checks green. 235 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: grudges that cost something, and can say why

- **Task #53, and the loop's stated first priority.** Memory existed but only
  coloured what an envoy said. Measured before starting: a decade of play left
  exactly *one* mind holding anything — the Charter, from contracts — so
  grudges would have been dead content for three powers out of four.
- `sim/grudge.py` turns memory into behaviour. A quay **prices you by what it
  remembers** (bounded at 18% either way, so memory is felt without replacing
  the market); a power that holds enough against you **stops posting work**,
  which is a harder wall than a poor price; and feeling **travels** between
  powers close on the relations matrix, which is what makes that matrix
  something to think about rather than a readout.
- The rule that keeps it honest: `because()` names the memories responsible for
  whatever `feeling()` returns, with dates, and the diplomacy screen prints
  them. Nothing in this game may dislike you for a reason it cannot state.
- **Widened what writes memory**, which is what made the feature reach real
  play: every overture, a denunciation (which lands on the power denounced),
  and each of the three answers to a territorial demand. A played decade now
  leaves all four powers holding specific, dated, legible reasons.
- **A defect I created and the suite caught the same run**: `contracts.
  cargo_cost` priced the board's quote with the raw `buy_price` while the till
  went through the new helper — nearly nine hundred credits apart on one
  cargo. Both read `market.quote_buy` now.
- **A defect found by playing rather than by checking**: brokering the same
  pair eight times wrote eight identical memories and pinned the power at the
  +100 cap, so the readout could not say which of them mattered. Repeating
  something now reinforces one memory with diminishing returns and moves its
  date forward, which is both truer and legible: "you sat us down with
  Concordat +37.7 · relief +31.0 · tribute +25.9".
- An efficacy lever switches the price bias off; the harness reports it inert
  when it is.
- Suites: 54 — 442 checks green. 235 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a tutorial that will not take your word for it

- **Asked for an optional tutorial at the start.** Eight lessons — survey
  something, look at a market, sell what you learned, buy reaction mass, go
  somewhere, take on work, look at what you are flying, see who is who — shown
  as a strip along the top rather than as dialogs.
- **The design point is that it watches rather than trusts.** A step that
  advances because Next was pressed teaches nobody anything and will march a
  confused player through eight screens of congratulation. So every lesson
  names a watcher, and every watcher is a function of game state compared
  against a **mark taken when the lesson opened** — "survey a body" means one
  more than you had, not "a body is surveyed", so a captain who surveyed
  something before starting is not waved through.
- **It never blocks anything.** The window's guard diverts for a battle, an
  open trench and an aftermath question; the tutorial is deliberately not among
  them, in a game whose premise is that there is no track. A check walks all
  twelve screens with a lesson open.
- It lives on the `Game` with an `.over` flag like everything else you can be
  part-way through, so it survives a save — including mid-explanation, which a
  check reloads and carries on from. Skipping is final until it is started
  again from the Help screen, and the `tutorial` option is back on the options
  page now that something reads it.
- **Three of my own errors, caught by the checks rather than shipped**: a
  fixture that added cargo and then sold it, so the hold returned to the mark
  and the watcher correctly saw nothing; a starting system with only two
  bodies, which the survey fixture assumed away; and a "does it block
  navigation" check that read `go()` for the word "tutorial" and tripped over
  the import line — it walks the screens now.
- Found by looking: `deleteLater()` alone leaves the previous lesson's text
  painted under the new one until the event loop catches up.
- Suites: 53 — 432 checks green. 233 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a menu bar, and options you can actually set

- **Asked for an options page reachable from a menu bar, including the LLM
  choices.** There was no menu bar at all — the theme had styled `QMenuBar`
  since the beginning and nothing ever built one.
- `ui/menubar.py` builds it from the same tables as everything else: screens
  and their keys from `data/screens.py`, instruments from `monitors.SHAPES`, so
  a screen or an instrument added tomorrow appears without anybody editing a
  list. Four menus — Chronicle (save, options, begin again, quit), Screens,
  Instruments, Help.
- `ui/options_view.py` is **one** options page, shown either in its own window
  from the menu or embedded in the Help screen. Two options pages is two places
  for the bounds to disagree.
- **The LLM is settable from the game now, not only from the environment.**
  `core/llm.py` gained `configure()`; the player picks the provider from what
  is on the machine and names a model, and `options.apply()` pushes it down. A
  fresh process still starts off and no check ever turns it on. The page probes
  only when you press *Look for models*, and *Say something* prints a line so
  "a model is answering" is a claim you can check.
- **A live bug, mine, from last cycle.** Three call sites used `win.save()` and
  `MainWindow` had no such method: carrying on past an ending, answering an
  aftermath situation, and changing a setting. Every one raised inside a Qt
  slot, where it is swallowed. The aftermath checks drove `sim/legacy.py`
  directly and never pressed the button. There is now a check that answers a
  situation *through the view*, and one that fires all 25 menu actions with
  `sys.excepthook` armed. Both fail when `save()` is removed.
- **A second, subtler one, found by the suite after splitting `window.py`:**
  `credits` is a Python builtin. Calling it by mistake does not raise
  `NameError` — it calls the interpreter's `_Printer` and fails two suites
  away with a message about positional arguments.
- `window.py` crossed 500 lines; the heading bar moved to `ui/hud.py`.
- **My own check was wrong first**: "every option does something" scanned for
  the setting's name elsewhere in the package, which cannot see a setting that
  `options.apply()` *forwards* into `core/llm.py`. It reported two live
  settings as dead. It now moves each unnamed setting and watches for an
  observable change.
- Suites: 52 — 424 checks green. 229 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a manual that cannot go stale, and options that bite

- **Asked for an extensive help system and an options screen.** Nineteen
  topics ordered the way a captain meets them, a search, contextual help from
  every screen, a Keys page, and five settings.
- **The manual counts rather than restates.** A page that says "thirty-five
  hulls" is wrong the day somebody adds one and nothing would notice, so
  `data/help.py` holds prose and `sim/manual.py` generates every countable
  claim from the table it describes — the ten endings and the epoch each opens,
  the burn profiles with this hull's heat, what this sector can actually reach,
  the powers and how each regards you now. A check fails if a topic names a
  fact nothing can resolve, and it caught a dangling cross-reference (`trade`
  pointed at a `customs` topic that did not exist — smuggling has its own page
  now).
- **Every option does something, and the screen says so.** `sim/options.py`
  holds the settings and their bounds; a check reads the whole package and
  fails if a setting is not consumed outside the module that defines it. That
  discipline cost two entries: a tutorial toggle and a seen-endings list, both
  taken off the screen until the thing they configure exists. Model speech
  needs *two* switches — the machine's and the player's — and the panel names
  which one is missing rather than offering a toggle that silently fails.
- **A real defect, found while documenting it.** The rail derived shortcuts as
  "1–9, then 0 for the rest", so when an eleventh screen was added the Codex
  and the Aftermath both bound `0` and the Aftermath had no key at all. Keys
  now live in `data/screens.py`, read by the window and by `sim/manual.py` —
  which is across the layer rule, so the Keys page is built from the same table
  as the rail.
- Also found by looking: generated facts can be any length, and an unwrapped
  label forces a minimum width wider than the view, which pushed the whole
  manual off the right edge.
- Suites: 52 — 420 checks green. 226 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a bridge, so the game can be driven from outside

- **Asked for a way to drive the game remotely, for a chatbot to play
  characters, and as a route to multiplayer with autonomous seats.** `bridge/`
  is that: seventeen verbs over a running `Game`, a loopback JSON-lines
  transport, and a seat mechanism.
- **The protocol is separate from the transport on purpose.** Verbs are plain
  functions over a `Game` with no Qt and no socket, so the suite drives all of
  them in-process and the transport is a detail that could be swapped. No verb
  reimplements anything: each calls the same `sim/` function the window does.
- **Local only.** It binds 127.0.0.1, mints a token per session, and refuses
  anything untokenised. No discovery, no broadcast, nothing routable.
- A **seat** is a named role an outside caller speaks for — how a second
  captain joins and how an agent holds a rival. Claiming one is a declaration
  rather than a lock, which is what makes somebody stepping away survivable.
- **The bug it shipped with, found over a real socket.** `survey` returns a
  `Lifeform` object among its results; the reply was merged straight into the
  envelope and `json.dumps` raised *inside the connection thread*. The socket
  died silently and the caller read an empty line with nothing to go on. Fixed
  by making the boundary total — `plain()` flattens anything, the writer never
  lets a bad reply kill a connection, and a check hands the dispatcher eleven
  kinds of rubbish and requires a polite answer to each.
- Suites: 51 — 410 checks green. 220 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: minds that remember, and voices (asked for)

- **Asked for LLM-driven speech for ships, crew, other captains and anything
  that communicates, with personalities, and persistent characters whose
  memories update from interactions and from what happens in the universe.**
  This is the foundation: providers, personas, minds, and the speaking layer.
- **The binding constraint, taken seriously**: the game ships with no network
  and the suite is hermetic. So `core/llm.py` is **off by default**, gated on
  `SEEDFALL_LLM`, hard-timeout, and `complete()` returns `None` whenever there
  is nothing there — which is the ordinary case, not an error, because every
  speaking path had to work offline anyway. `test_voices.py` replaces
  `llm.complete` with something that *raises*, so a check that reaches for a
  model fails loudly; what the suite measures is the written voice.
- Providers detected from whatever is on the machine: Ollama on localhost, an
  Anthropic key, an OpenAI-compatible endpoint.
- `data/personas.py` makes personality data rather than prompt strings: eight
  voices — the ship's computer, an officer, a harbourmaster, another captain, a
  raider, a faction envoy, a Dry Choir lineage, and plain — each with a
  register, tics, a temperature and **sentence frames for seven moods**, which
  is what the offline path speaks with. It is the default, so it has to be
  worth reading; a check holds all fifty-six combinations to being distinct and
  slot-free.
- `sim/memory.py` gives officers, captains, ships, factions and ports a `Mind`:
  memories with a day, a kind, a salience and tags, from three sources —
  direct, heard (sector news), and prior (a past generated before you ever meet
  them). Salience decays; recall is by fit to the situation rather than
  recency, so a customs desk raises the seizure and a counter raises the cargo.
  An impression is derived from what is held, and `grudge()` names the
  memories responsible for it.
- **It is wired to real events, not a system beside the game**: a kill, a
  parley, a rout, a seizure at customs and a finished contract each write a
  memory, and losing a colony or turning the sector over into an epoch is
  broadcast as news that every power and quay hears.
- **The mood is decided by the game, never by the model.** A model is told how
  a character feels and asked only for the prose; its answer is validated for
  length, leaked instructions and line count before use, and falls back
  silently. Speech reads state and never writes it, which is what makes the
  whole feature removable.
- Two phrasing defects found by reading the output rather than the code: leads
  ending on a pronoun produced "I have not forgotten that you you left…", and
  unweighted backstory made every greeting open with two pieces of somebody's
  childhood.
- Suites: 50 — 404 checks green. 210 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: pop-out instruments (asked for)

- **Asked for pop-up windows for monitoring ship systems and sensors, with
  good graphics.** Six of them — power, heat, integrity, hold, crew and a
  scope — each in its own window, staying on top, re-reading the live game
  every nine-tenths of a second. Windows rather than another tab on purpose:
  the point is watching heat while you fly, and a tab cannot do that.
- Painted, not assembled from labels: `ui/gauges.py` draws a 240° dial with
  ticks and a needle, a segmented stack for the hull and the hold, and a scope
  with a sweep, range rings, bodies on the inner third and stars in sensor
  range on the outer. All QPainter, so it renders identically offscreen and the
  suite can look at it.
- `sim/telemetry.py` holds the readings so the layer rule stands and the checks
  can ask what an instrument *says* without painting it. Each reading carries
  its own band — good, watch, bad — from the sim's thresholds rather than the
  panel's opinion.
- **The defect, found by looking**: the crew dial drew a needle over "0/0 d"
  while its own caption on the same face read "124 days of air", because `Dial`
  paints `now`/`cap` and the crew reading supplied neither. Every dial-able
  reading carries them now, and a check holds all three to agreeing with
  themselves.
- Suites: 49 — 396 checks green. 206 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: ten endings, and a game that carries on past them

- **Asked for a wider range of endings, and for the game to continue after any
  of them with more play afterwards.** There were five victories, one loss and
  death, and reaching one showed a dialog and called `clear_save()`.
- **Five more endings**, each measured off machinery that already existed:
  **Lineage** (four grown hulls of your own gestation, signed for), **Xenarchy**
  (all twelve alien technologies incorporated), **The Cartel** (most of the
  sector's prices in your register, and a purse), **Apostasy** (a synthetic hull
  with nobody aboard, at Kin with the Choir), and **Ruin** — outliving the
  sector, which required checking endings *before* letting the Bloom kill you,
  since the old order set `dead` first and Ruin could never fire.
- **Every ending now opens an epoch.** `data/epochs.py` rewrites the world once
  and starts a new clock in place of the Bloom: containment leaves four powers
  with no common enemy and a cleared sector to divide; concord leaves a unified
  Verge with something on a heading toward it; dominion makes you a power, with
  secession. Forty situations across the ten, each a choice whose answers state
  what they do — and `legacy.apply` reads the same dict the card was rendered
  from. An epoch closes badly at full pressure or well after four years held,
  and the next one can follow; the chronicle keeps all of them.
- A situation waiting on an answer is a field on the `Game` with an `.over`
  flag, like a battle or an open trench, so the navigation guard diverts to it
  and it survives a save.
- **The checks found two things.** The Cartel ending was unreachable by
  construction — 25 systems' prices demanded, 17 to 24 markets in a sector,
  which is the same defect as a work gated behind a technology that does not
  exist; it is a share of what exists now. And `test_play`'s standing "every
  ending can actually fire" check caught that five new endings had been added
  without extending it.
- Two of my own measurement errors, caught before they became findings:
  measuring a card that buys time while the gauge sat at its floor of zero
  ("said −9, moved 0"), and a fixture that priced the first thirty systems
  rather than the twenty that have markets.
- Suites: 48 — 391 checks green. 203 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: an opening worth choosing (asked for)

- **Asked for more choices at the start: ship, crew, starting place, race and
  background.** Every chronicle used to open the same way — a NAVIS called
  *Patient Increment*, three officers, five technologies, the Charter capital —
  and every one of those was already a real axis in the simulation that was not
  the player's to pick.
- `data/beginnings.py` adds three **stocks** (substrate, not ancestry: Wet
  crews breathe, Dry Choir ones do not and nothing they fly ever mends, Grafted
  pay both bills), six **origins** (Charter Surveyor, Yards Journeyman, Freehold
  Grafter, Choir Cantor, Bloom Survivor, Registry Fugitive), a **hull** from
  those the stock will crew, and five **postings**. Each carries what it gives
  *and* what it costs, and the screen's fourth column is the chronicle you would
  actually open — pinned by a check that opens it and compares.
- **The invariant that mattered most**: `new_game()` with no choices is exactly
  the game as it shipped. Three hundred and eighty checks are written against
  that opening; a default that quietly differed would leave all of them passing
  while measuring a different game. The canonical origin's deltas are all zero
  and a check compares hull, outfit, purse, standing, crew and start across
  three seeds.
- **It found a live soft-lock in the shipped game.** The NAVIS launches with a
  Reaction-Mass Organ, a Radiator Bloom and a Mining Root whose technologies
  were not in `STARTING_TECH`, and the Refit tab offers Remove on every fitted
  part. Pull the drive on day one and `parts_available("drive", …)` returns an
  empty list: the slot can never be filled again, jump falls to the bare
  chassis, and nothing tells you. Fixed structurally — whatever `new_game`
  fits, it grants the technology for — so no future hull can reintroduce it.
  Verified by putting the old constant back.
- **A second defect, from the same checks**: the stock's effects were stored on
  the Game and never folded into `bonuses`, so "superb instruments" was a
  sentence the simulation did not read. `test_orders` caught it as a field
  written and never read.
- Suites: 47 — 383 checks green. 199 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: 3D ship plans (asked for)

- **Asked for 3D plans of the ship so a player can see what is going on with
  it — fittings, changes, storage, crew.** Everything on the ship screen was
  already true and none of it was a picture: you could read that a Polyp
  Laboratory was fitted and the ablative layer was at 41% and have no idea what
  you were flying.
- **A software renderer, not OpenGL.** `core/solid.py` is primitives, a
  painter's-algorithm depth sort and flat shading; `ui/plans_panel.py` fills the
  polygons with QPainter. No new dependency — and, the point, it renders
  identically offscreen, so the suite can look at the ship instead of taking its
  word. `models3d/` stays what it was: a trimesh export tool the game cannot
  import. The shape vocabulary is shared, so the two read as the same ship.
- `data/hullforms.py` gives each of the five families a silhouette, a faceting
  and a set of mounts; `sim/plans.py` assembles the model from the *actual*
  ship — chassis, every fitted part at its slot, the hold filled from the floor
  with what is really aboard, one berth per crewman lit if somebody is in it.
  Because the model is a function of the fitted list, the shipyard can hand it
  `design_fitted` and show the refit before you buy it.
- **The bug it shipped with, and how it was caught.** The ellipsoid was wound
  inside-out. Half the faces cull either way, so the count looked right and the
  ship drew as an x-ray of its own far wall with the cargo floating in front —
  which looked deliberate. Found by rendering it and looking, then pinned by two
  checks: normals on every primitive, and a box inside a sphere that the sphere
  must occlude. Both fail when the winding is put back.
- Two further defects found by looking: mounts written as a radius buried every
  fitting inside the beam (the hull is tapered, so where the skin is depends on
  height), and drawing every family at one resolution made them the same ship in
  different colours — a Yards hull is 6×8 facets now, welded plate against a
  gestated 16×24.
- `test_reachable` caught two helpers I wrote and never called. Deleted.
- Suites: 46 — 374 checks green. 196 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the chart now says what you can get to

- **The chart answered the wrong question.** It drew a dashed ring at the jump
  range and greyed one button to "Out of range" — which is "can I jump there in
  one hop". The question is "can I get there at all", by hopping, and often the
  answer is no. Flooding from the start at starting jump range reaches 2 to all
  42 systems depending on seed: median 13, a quarter of sectors under eight, one
  in eight at three or fewer. A captain handed a two-system pocket saw forty
  stars drawn no differently from the one next door.
- `sim/reach.py` computes the reachable component, what lies beyond the wall,
  and what each drive *this hull would actually accept* would open. The chart
  strikes through walled stars and prints the line: "2 of 42 systems are
  reachable at 8.9 ly — 40 lie beyond a gap no amount of hopping closes. A
  Foldrunner Coil would reach 13.7 ly and open 40 more, once researched."
- **Why the ladder is so steep, which the screen now admits.** `ion_cluster`,
  `plasma_drive` and `fusion_torch` are fabricated-family and a grown hull
  refuses them, so a NAVIS ladder is reaction organ 8.9, sail film 9.0,
  foldrunner 13.6. `opens()` lists only graftable drives, because naming the
  others would make one very expensive step look like a gentle climb.
- **Checked before concluding**: a shipyard is within reach in 80 of 80 seeds,
  so nobody is permanently stranded — the exit exists, it was just unsigned.
  `MAX_LANE` does not prevent this and never claimed to: it stops a *star*
  sitting alone, not a *cluster*.
- Fuel is deliberately not modelled in reachability: ice can be cut anywhere,
  so it paces a voyage rather than bounding it, and a wall that moved with the
  tank would be a worse lie than no wall.
- Suites: 45 — 366 checks green. 191 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: one chronicle, ten years, every screen

- **Turned last cycle's accident into a standing check.** The README
  screenshots found a shipped crash in minutes because they were one long-lived
  save touching every screen in sequence — the kind of play forty-three suites
  were not doing. `tests/chronicle.py` now flies a single captain for ten
  years: surveying whole systems, refitting, hiring, trading off the freight
  desk, mining, digging, landing parties, planting colonies, running works and
  moving the relations matrix. `test_chronicle.py` repaints every screen and
  every tab against that save as it accumulates, with `sys.excepthook` armed
  because Qt swallows what a slot raises.
- **It found a real one on its second run.** `Dig` held a `body_index` and no
  system, and `_fatigue` resolved it against `game.system` — whatever system
  the ship was in *now*. Fly away with an open trench and keep working it, and
  you read a different body's fatigue, or hit `IndexError` on a shorter body
  list. Digs are saved, so the wrong body outlived the session. `Dig.system_id`
  pins it, `site_of()`/`at_site()` resolve through it, `work()` refuses from
  elsewhere, and backfilling still works from anywhere — which is the one thing
  you must be able to do with a trench you have left. Old saves migrate.
  Verified by putting the bug back: the check fails, and the chronicle's screen
  check fails with the original `'int' object has no attribute 'sell'` when the
  register bug is reintroduced.
- **Most of the cycle went on the driver, and every correction was a
  measurement.** In order: `_move_on` mined ice and returned "moved", so a
  broke captain moved on 170 times and saw six systems; ranking the freight
  run above unexplored space shuttled one profitable lane 144 times; selling
  everything but volatiles sold the biomass and phosphate a seed bay is built
  from, so the bay never fitted and nothing was ever planted; a greedy refit
  loop bought every cheap part with a jump term and *lost* a light-year to
  fitted mass; surveying three bodies a round and leaving meant `scanned` never
  went true and a decade charted two systems; and exploring blind parked the
  captain in a pocket of portless systems for thirteen rounds on eleven tonnes
  of biomass. Each fix carries the number that justified it in a comment.
- **Two things the driver found that are the game's, not the driver's.**
  Every ground option that pays a field note wants comms or medicine, and the
  opening crew is science, nav and engineering — 168 notes offered in a decade,
  none takeable, until the captain visited the berths. Both specialists recruit
  at ordinary rates, so that is a station to fill rather than dead content, and
  the driver now hires. And flood-filling from the start at starting jump range
  reaches 3 to 18 of 42 systems depending on seed, median about 5 — logged as
  task #44 with the per-seed numbers rather than fixed blind.
- **The suite is honest about its one concession**: `play()` tops the purse up
  to a floor each round. Solvency is `test_play`'s question; this one is
  whether accumulated state breaks a screen. Every action is the real one, only
  the money is a gift, and `play`'s docstring says so.
- Painting every sixth round cost 3m45 for the same three verdicts; every
  twentieth costs 35s and still makes 387 paints plus a full reload pass.
- Suites: 44 — 360 checks green. 189 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a README, and the crash it found

- **Asked for a README with screenshots of every major feature.** Wrote
  `seedfall/tests/capture.py`, which builds one developed chronicle — a
  half-charted sector, colonies online, contracts in hand, a programme under
  way, a party on the ground — and renders fourteen screens offscreen. The game
  README is `seedfall/README.md`; the root programme README keeps its own shape
  and links to it.
- **Rendering them found a shipped crash.** `charts.stamp()` wrote each chart's
  completion day into `game.register` — which is the *price* register.
  `market.best_markets` walks every value in that dict and reads `.sell`, so
  charting any system and then opening a port raised `AttributeError` from
  inside a Qt slot, where Qt swallows the traceback and the freight desk simply
  fails to draw. It had been there since the charts cycle.
- **`test_verbs` never caught it** because its fixture does not survey a system
  to completion, so no chart was ever stamped. Chart dates have their own field
  now, with a migration for old saves, and a check asserts the price register
  contains nothing but quotes.
- **Worth naming: taking screenshots is a kind of play the suite was not
  doing** — one long-lived save touching every screen in sequence, rather than
  a fresh game per check. That is exactly the shape of state the collision
  needed.
- Suites: 44 — 356 checks green. 187 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the odds on the ground

- **The expedition screen said "(science, difficulty 3)" and stopped.**
  Resolution is `1d6 + officer level >= difficulty + 2`, so that exact string
  is a one-in-three attempt with a green officer and a five-in-six with a
  level-three one — the same nine characters either way. The reward was
  unpacked into a variable named `_reward` and discarded, so the player was
  never told what success paid. And a failure springs a hazard 40% of the time,
  costing supply, the rover and sometimes an officer, which was also unstated.
- **The ground game is nothing but a sequence of these choices**, which is what
  made this the one worth doing: every tile with a feature on it is a decision
  between two or three options and the screen gave a stat name and a number
  with no scale attached to it.
- **`expedition.odds_for()` gives the chance, the officer who would take it,
  the prize and the risk**, and the panel reads "83% — Marek Nazari on
  engineering · 900–3,400 credits · If it goes wrong: 7% chance of springing
  something". Reading a flight recorder with nobody on comms is 33% with a 27%
  chance of springing something; stripping the salvage next to it is 83%. That
  is the decision, and it was invisible.
- **The check rolls each option six hundred times** and fails unless the
  empirical rate matches the quote, because the resolution lives in `attempt`
  and the quote in `odds_for` and the whole point is that they cannot drift.
  Worst discrepancy across nine options: 3.0%. Dropping the `+2` from the quote
  makes it report "said 67% rolled 32%".
- **Eighth cycle running where the defect was a readout.** Seven of the eight
  now have a preview or forecast function in the sim with a check pinning it to
  what actually happens: contracts, freight, mining, the bench, overtures,
  seats, colonies, and now ground options.
- Suites: 44, **6 attempts** (new) among them — 355 checks green. 186 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: what will grow there

- **Seventh cycle running the defect is a readout, and this time I went looking
  for it deliberately** rather than stumbling on it. The plant-a-seed dialog
  was the obvious remaining candidate: founding is the core empire decision,
  months long and tens of thousands of credits, and the screen gave a price and
  a gestation time and nothing else.
- **Measured on a single rocky body: fourteen classes on offer**, yielding
  anything from 2.6 tonnes of ore a day (RADIX Mine, 12,000 credits) to 260
  credits a day (Free Port, 74,000) to 4.2 research a day (Reactivated Array,
  96,000). Three of the nineteen classes yield nothing at all and buy effects
  instead — a GRAVID Nursery at 60,000 credits produces not one tonne of
  anything, which is legitimate and needs saying.
- **`colony.forecast()` gives yield, upkeep, effects and a rough payback**, and
  the card shows them: "2.6 ore/day, 0.11 phosphate/day · Upkeep: 0.1
  biomass/day · Pays for itself in about 0.3 year(s) once it is up." Payback
  ranges from 0.1 years to 3.6 across the classes, which is the comparison the
  dialog existed to support and could not.
- **Priced at a flat table rather than a market**, deliberately: a payback that
  swings with whichever port you happen to be standing in is not something
  anybody can compare classes with.
- **The check plants all fourteen classes a body will take**, matures each, and
  fails unless yield, upkeep, effects and gestation are what was forecast.
  Forecasting nothing makes four of the five checks fail, the first reporting
  "radix_mine: forecast {}, yields {'ore': 2.6, 'phosphate': 0.11}".
- **One fixture error of my own**, caught immediately: I stocked a guessed list
  of commodities and the check died on spidroin, for a class it was not
  testing. It stocks the whole commodity table now.
- Suites: 43, **5 founding** (new) among them — 348 checks green. 185 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: what a seat is worth

- **Measured the crew stations, and the combat sim is sound.** Directed gunnery
  really does shoot markedly better than automatic: +0.10 against −0.12 + 0.02 a
  tactical level. An unattended helm repeats its last order at 0.7 + 0.06 a nav
  level of the turn rate. An unattended engineering section sheds a fraction of
  its vent and can do nothing else — no venting hard, no routing power, no
  damage control. All three claims hold.
- **The orders panel stated none of it.** It printed the station name, the
  officer's level and a blurb. So a captain could not tell that gunnery is
  worth +0.22 with a green officer and only +0.10 with a veteran — that *who
  you have* decides *where you should sit*, which is the entire point of the
  one-seat rule.
- **`stations.seat_value()` says what each seat buys**, given the officers
  aboard, and the bridge draws it: "turn at full rate instead of 82%", "+22% to
  hit over the officer", "vent 72 heat instead of 25, or route power, or patch
  a breach". Sixth cycle running where the defect was a readout rather than a
  rule.
- **The checks drive the claims through `run_helm` and `run_engineering`**
  rather than re-deriving their formulas, so changing the sim and not the
  quoted figure is caught. Halving the unattended turn rate makes it report
  "said an officer turns at 70% and it turned at 50%".
- **Three of my own measurement errors this cycle, all caught before they were
  written down as findings.** My first driver set `action["station"]`, which
  the sim ignores — the station is derived from the order — so four
  configurations produced identical results and looked like proof the choice
  did not matter. Then `hull_pct` rounding 99.3% to 100% read as the player
  taking no damage at all. Then the fixture promoted "the tactical officer" on
  a crew that has none, so a green bridge was compared with itself.
- Suites: 42, **6 seats** (new) among them — 342 checks green. 184 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: what an overture buys

- **Measured the six diplomatic overtures.** They all work and they are
  properly differentiated: tribute 12,000 credits for +9 standing, intelligence
  6 survey sets for +7, relief 40 t of biomass for +11, treaty 30,000 for +14
  and a signature, denounce free but −14 with the target, broker 20,000 to move
  the relations matrix +28. Only brokering repairs the matrix and only
  denouncing tears it, which is exactly as designed.
- **The screen showed the price and never the benefit.** Relief is about six
  times better per credit than tribute (193 a point against 1,333) and three
  times better than intelligence, and a player had no way to see any of it —
  three overtures, three costs, no numbers on the other side.
- **And a treaty had a cost stated nowhere at all.** Beyond its 30,000 it
  charges standing with the signatory's enemies through `allegiance`. You
  signed, and two other powers thought less of you for a reason the game never
  mentioned. In a sector at war it is six points with each of the other three.
- **`dip.preview()` is a pure function** returning what an overture will move —
  the target, third parties, and the matrix — and the screen draws it under
  each one, with the cooldown. A treaty now reads "Charter +14, Freeholds −2,
  Concordat −1" before you commit rather than after.
- **The check that matters is the honesty one:** perform every overture and
  fail unless standing and matrix move exactly as previewed. Hiding the
  treaty's rivals again makes it report "said {charter: 14}, did {charter: 14,
  concordat: −1, freeholds: −2.2}". There is a second check that previewing
  moves nothing, because a preview that quietly performs is worse than none.
- **Nothing was wrong with the diplomacy sim itself** and I have not touched
  it. This cycle is entirely about the screen telling the truth about what it
  offers — the fifth time that has been the defect, after the contract fee, the
  freight spread, the mining rate and the research bench.
- Suites: 41, **5 overtures** (new) among them — 335 checks green. 183 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a work nobody could build

- **Measured colony works for the first time, and got it wrong twice before
  getting it right.** First pass compared each work across a *different* seed,
  so I was comparing different colonies on different bodies. Second pass fixed
  the seed and still showed four works with large negative yields — building a
  garrison apparently cutting output 29%. That was market drift: I was pricing
  the yield in credits at a market whose prices move over the 70–140 days of
  construction. Measured in tonnes, every work does exactly what its table
  says. Sixth measurement artefact of this project; caught before it became a
  finding.
- **Then a real one, and it took a third correction to see.** `annex` was
  offered by no colony. My first reachability sweep had not unlocked the tech
  it wants, so `available()` returned it as *not ok* and my filter dropped it —
  seventh artefact. Unlocking everything in the game and running it again:
  **buildable by 0 of 19 classes.**
- **"Build a xenology annex" was gated on a technology that does not exist.**
  A hundred days, eleven thousand credits and twenty-two alloy, granting half a
  research point a day and four points of diplomacy, behind
  `tech="xenolinguistics"` — which is in neither the sixty-one-node research
  tree nor the twelve xenotechnologies. Nobody could ever build it.
- **It is the only broken gate in the whole content set.** Works, colonies,
  parts, chassis and every tech prerequisite: 131 gated entries, one wrong.
  Pointed at `xenobiology`, and there is now a check over all of them.
- **A test fixture was part of why it hid.** `test_verbs` appended the phantom
  id to `research.unlocked`, so the sweep that clicks every control in the game
  saw a work no real chronicle could reach. A fixture that invents content is a
  fixture that stops the suite noticing content is missing — that is fixed too.
- Suites: 40, **5 works** (new) among them — 329 checks green. 182 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: a bench that eats what it says

- **Measured the research bench for the first time.** Most of it is sound: the
  approaches are a real decision (careful 112 days, parallel 75, push 58 with
  setbacks), a starved bench crawls at 180 days but is never a dead end, and
  evidence saturates per project at about 160 units — which is correct, because
  it is *consumed*, so across 61 techs you need some ten thousand of it.
- **But the readout was out by a factor of two.** `needs()` is documented as
  "how much of each kind a programme will consume end to end" and the screen
  prints it as "26 wanted". `draw()` then spent `total / 60` a day, while a
  careful programme runs about 128 days — so the bench ate **2.1x** what it
  advertised, on every track, for every technology. The sixty was a duration
  nobody had checked against the real one.
- **And it ignored the approach.** Running parallel tracks costs, in its own
  blurb, "three benches' worth of material" — and the shelves were read against
  the careful figure. The screen now quotes ×1.9 for parallel because that is
  what parallel takes.
- **Fixed by pacing the draw over the programme's actual expected length**
  rather than a constant. Wanted and used now agree within 7%, and the panel
  reads "Hardware 40 held · 64 wanted" in amber when you are short.
- **A false alarm of my own, checked before it became a finding.** A test
  showed the bench *gaining* survey evidence during a run — 400 stocked, 28
  spent, 426 left — which looked like something generating evidence out of
  nothing. It was my arithmetic: a chronicle opens with 55 survey and 25
  specimen already on the shelves, so `stock=400` starts at 455. Idle time
  generates nothing, as it should.
- **And one stale lever.** Adding a `rate` argument to `draw()` broke the
  existing `research-evidence` lever, whose patch was a three-argument lambda.
  The efficacy harness reported it as a signature error rather than silently
  passing, which is the whole reason it checks its own substitutions.
- Suites: 39, **5 bench** (new) among them — 323 checks green. 181 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: a hard burn that costs something

- **Set out to build a launch-window planner, and the measurement killed it.**
  A leg's cost varies 1.9x on average and up to 5x as the bodies move, which
  looked like the missing decision in piloting. Then I measured the orbital
  periods: **1,486 to 9,855 days**. The windows are four to twenty-seven years
  apart, and waiting 1,400 days to save 3 t of volatiles — about 120 credits —
  is not a trade anyone would take. I had `window()` and `hold()` written and
  deleted them rather than ship a feature nobody would use. A decorative
  feature is exactly what the efficacy harness exists to catch, and I would
  rather catch it before writing the screen.
- **What the measuring found instead.** Flying a system end to end took 55 days
  coasting and 10 on hard burns. The hard burn cost about three hundred credits
  of reaction mass and 1.2% of a hull that heals itself, so the four profiles
  collapsed to "always hard burn". Its own blurb promised that "the crew will
  feel it and the radiators will complain", and a burn never touched heat.
- **Heat was a one-way ratchet.** Nothing outside combat added it and nothing
  shed it: a ship sat at thirty for twelve hundred days with radiators rated at
  twenty-four a turn. The only thing that ever generated heat outside a fight
  was one flight incident, and it followed you around for ever.
- **So: a burn leaves heat, and heat is a state you fly in.** Hard burn arrives
  at 62% of cap; a hot hull is riskier to burn again in; over the cap the
  radiators stop keeping up and the hull cooks. Measured over a four-leg tour
  plus a month sitting: coast 89 days and no hull, economy 59 days for 6 t,
  hard 41 days for 24 t and **11% of the hull**. One hard burn from cold is
  still free — it arrives under the cap. It is the habit that costs.
- **`REST_VENT` is written down as what it is:** not a physical ratio but the
  rate that makes heat a state you fly in rather than one that has gone by the
  time you arrive. At 0.5 a hard burn cleared in four days and never stacked;
  at 0.14 it takes a fortnight.
- **The efficacy harness rejected my first lever**, correctly: it patched the
  `BURNS` list, which `travel_to` never reads (it goes through `BURNS_BY_ID`),
  and it demanded a callable target. Routing the heat through `burn_heat()`
  fixed both and is better code.
- Suites: 38, **7 burns** (new) among them — 317 checks green. 180 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: a rig that knows when to stop

- **Mining, measured for the first time.** It pays 11–104 credits a day and the
  four methods are a real decision: boring lifts most and takes 0.81 of a body,
  bioleach lifts nearly as much per day for 0.13. Over a body's life, leaching
  wins. That part was already right.
- **The fifth measurement artefact of this project nearly became a finding.**
  I measured the panel's quoted rate against the actual haul and got 36–54% —
  "the screen lies". It does not: my probe had loaded 300 t of volatiles to
  fund the bore's upkeep, leaving 40 t of hold. With room, quoted matches
  actual at 101%. Checked before claiming, which is the only reason it did not
  go in the log as a bug.
- **But it led straight to a real one.** Working a body for sixty days with an
  empty hold takes 106.2 t and works it out by 0.384. With the hold 97% full it
  takes 10.2 t — and works the body out by the **identical 0.384**. Ninety-six
  tonnes raised and thrown away, a third of a body spent to recover a tenth of
  what the rig lifted, sixty days gone, and nothing anywhere said so.
- **The working stops when there is nowhere to put what it raises.** Time and
  depletion both follow what was actually lifted: 10 t in 3 days for 0.019 of
  the body instead of 60 days for 0.384. Ten seconds of arithmetic on the panel
  now says "25 t in 14 days — the hold fills first".
- **A second bug, found by the regression check rather than by me.** Everything
  that can refuse a working ran *after* `flight.ensure_at()`, so being told
  there was no room cost twelve days of flying out to the body first. The check
  asserted no time passes on a refusal and reported "12 days spent on a refused
  working".
- **And a vacuous check of mine, caught the same way.** The proportionality
  check picked a hold fill fraction blind, and on that seed the body raised
  less than the hold anyway, so no capping happened and it passed measuring
  nothing. It now computes the room to leave from the haul the spell would
  actually raise, and asserts capping occurred before drawing any conclusion
  from it.
- **And then my own fix deadlocked the game, which the playability bot caught
  by hanging.** Refusing to work a body with a full hold is correct — but it
  left a captain with a full hold and an empty tank unable to mine ice for
  reaction mass, unable to jump, and with no way to dump anything: the only
  jettison in the game was on the contraband panel, which appears solely when
  carrying contraband at a hostile port. The bot span forever because `extract`
  refused without advancing the clock, so the five-year limit never arrived.
  The full suite went from five minutes to never finishing, which is how I
  found it.
- **`trade.jettison()` is general now** and the hold has a vent control, so the
  affordance the bot needed is one a player has too. The project already holds
  that an empty tank must not be a deadlock; this is the same rule from the
  other side, and there is a check for it.
- **`test_play.py` crossed 500 lines**, so the long-game captain moved to
  `captain_bot.py` — it is the thing that catches deadlocks and deserves to be
  findable.
- Suites: 37, **7 workings** (new) among them — 309 checks green. 179 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: somewhere to take a cargo

- **Took the task I deferred last cycle**, and the measuring went four rounds
  before it told me the truth.
- **First finding: the runs exist and are invisible.** Within a starting jump
  only 5% of lane/goods pairs show a positive spread — but there are about
  twenty per sector, worth up to 1,400 a tonne, and the rate climbs to 16% as
  the drive improves. Finding one meant visiting every neighbour and writing
  down prices first. So: an information problem, and I built a freight desk
  with two honest sources — your own register, and the harbourmaster, who names
  his own power's ports and what they are short of without quoting their board.
- **Then a bug of mine, found by flying it.** Zero runs at Halcyon Wake, every
  time. `COLD` was −8, the floor of the Neutral band — and the Dry Choir
  *starts* at −10. A new captain standing on a Dry Choir quay was locked out of
  the whole mechanic on day one for no reason of their own. Set against the
  standing bands now, at Distrusted.
- **Then the careers still lost money, with 35 runs made.** Traced one:
  the desk said the port paid 590, it paid 530 by the time the hull got there,
  and the margin had been 14. The desk was recommending spreads smaller than
  the noise — `tick_market` moves supply about 1.8% a day with a random walk on
  top.
- **Then I nearly tuned my way out of it.** I had confidence discounting the
  *takings*, which says you only receive three quarters of the price; removing
  it made things worse, because the wrong model had accidentally been filtering
  bad runs. Rather than keep adjusting the knob I flew 120 openings and banded
  the outcome by advertised spread: every band under a fifth loses money on
  average. `MIN_SPREAD` is 0.20, derived, with the table in the source.
- **Result: 981 credits on your own notes, 33,069 following the desk**, over
  two-year careers — and the desk now refuses to name a run rather than name a
  bad one.
- **The efficacy harness caught my probe measuring the wrong scenario.** It
  noted every port in the sector first, and for a captain whose register holds
  everything the harbourmaster has nothing to add — so the lever read as inert,
  correctly. Rewritten for a captain who has not been there yet, which is the
  case the feature is actually for.
- **Honest about the limit.** Short-range legal arbitrage is thin because
  ports of one power want the same things; trading means crossing into
  somebody else's space. I checked the early game is not stranded by it: all
  twelve openings have affordable work on the contracts board, which last
  cycle's fix made pay properly.
- **`levers.py` crossed 500 lines** as the list grew; the newer probes moved to
  `probes.py`, split by age rather than theme, because a cargo probe belongs to
  `customs`, `trade` and `contracts` equally.
- Suites: 36, **7 freight** (new) among them — 301 checks green. 177 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a board that was half traps

- **Used last cycle's extraction to measure trading for the first time.**
  Moving buy and sell into `sim/trade.py` made an honest trading career
  something a script can fly. So I flew ten of them, and every one lost money.
- **The driver was not the problem this time — but the first finding was
  still not the real one.** Honest arbitrage is close to dead: only 10–14% of
  lane/goods combinations are profitable anywhere in a sector, 1–9% within a
  starting jump, and **six of twelve openings offer no profitable legal run at
  all** from the first port. The spread is 20%, so a destination has to price
  25% above the source, and your neighbours are usually your own power's ports
  with the same supply skews.
- **Which made the contract board the intended answer, so I checked it — and
  it was a trap.** `shape()` priced a cargo contract at
  `amount * (base * 0.55 + rate * 0.4)`. `base * 0.55` is the *floor* price:
  what a market holding none of a good will pay for it. Nobody sells at the
  floor; a counter with stock charges about `base * 1.1`. So the board priced
  its own work against a number that does not exist. Measured: **44% of cargo
  contracts paid less than buying their cargo cost at the port that posted
  them**, worst case −50,151 credits on a silicon prospecting job.
- **The inversion was cruel in the right way to go unnoticed.** Cheap goods
  survived because the flat rate term carried them; it was silicon, magnetite
  and trehalose — exactly the cargoes worth carrying — that were guaranteed
  losses. And the card showed a fee and nothing else, so a trap looked
  identical to a living.
- **Priced against real cost now**, with distance paying *haulage* per tonne
  per light-year rather than multiplying the value of the goods — the old
  multiplicative premium turned an eighty-tonne silicon run into 130,000 clear.
  Worst contract now clears +989, median +12,311. And the board shows the
  arithmetic: "Cargo costs about ₡39,060 here — clears ₡27,975".
- **A bug in my own fix, caught by the equivalence check.** The quote priced at
  rep 0 with no trade bonus while the player pays their own price, so it was
  wrong by two per cent. Generation must price neutrally — a fee cannot depend
  on who reads the board — but a quote must price for the captain standing
  there. Both, now.
- **And a check of mine that measured the wrong thing.** My haulage check
  asserted reward/cost < 4 and failed at 11.7x — on ore hauled a long way. That
  is not a fault: freight is priced by mass and distance, so a tonne is a tonne
  in the hold and the ratio to a cheap good's value says nothing. Rewritten to
  measure net and net-per-tonne, with the reasoning written down so the next
  person does not re-tighten it.
- **The arbitrage finding is queued, not acted on** — fixing the contract board
  and redesigning the trade economy in one cycle would have been two things.
- Suites: 35, **6 cargo** (new) among them — 293 checks green. 173 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: no screen writes the ledger

- **The debt I flagged twice, paid.** Seventeen sites across four view modules
  spent credits and moved standing directly. Buying, selling, signing an officer
  on, paying the bridge a bonus, repairing a hull, paying for a lead,
  commissioning bench time, breaking a hull up, tying up at a quay, and moving
  contraband off the books — every one of them a rule that only a mouse could
  perform and no headless run could measure. Same defect as last cycle's
  engagement aftermath, spread thinner across more files.
- **Eleven operations moved down**, into `sim/trade.py` and `sim/services.py`
  (new) and into `crew.py`, `shipyard.py`, `customs.py` and `minigames.py`
  where they belonged. `port_view.py` went from 484 lines to 427 and the views
  now call and draw rather than decide.
- **The rule is enforced now, not stated.** `test_layers.py` matches ledger
  writes structurally — assignment to `.credits`, augmented assignment,
  `game.rep[…] = …`, any call to `adjust_rep` — across every module under
  `ui/`. Putting one line back names the file and the line number.
- **It carries a self-check, and that was not paranoia.** A structural matcher
  that silently matches nothing would have passed on the day the defect was at
  its worst — which is precisely the failure mode this project has hit before,
  twice, with regression checks that passed with the fix removed. The check
  plants all three shapes of write and fails if it recognises fewer than three.
- **And an equivalence check**, the same discipline the aftermath got: buy
  twelve tonnes and sell five, once through `sim/trade.py` and once by clicking
  the port screen, and fail unless credits, standing and hold come out
  identical.
- **The Qt check moved** out of `test_aftermath.py` into `test_layers.py`,
  where somebody looking for the layer rule will actually find it. Neither
  breach the project suffered was an import pointing the wrong way; both were
  rules written upward, so the Qt half was never going to be enough on its own.
- Suites: 34, **5 layers** (new) among them — 286 checks green. 172 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: what the ground told you

- **Three wrong measurements before one right one.** Setting out to check
  whether an expedition pays, my first driver stranded 40 parties out of 40 and
  reported the ground game as worthless. It was the driver: it never went home.
  Second version budgeted one supply per step when rough ground costs two, and
  still stranded 26 of 40. Third version returned 28 of 40 but priced the haul
  through `sell_price(market, "credits")`, which returns None — so the single
  largest reward in the ground game, 900–3,400 credits a find, counted as zero.
  Only the fourth attempt measured the thing I meant to measure. I have made
  this exact mistake before, on the combat balance harness, and changed real
  numbers on false evidence; this time I checked the driver first.
- **The honest number: 1,438 credits, 8.8 research and 7.3 study for 37
  party-days** — about 39 credits a day against ~750 for charting. Low, but
  the ground clock and the ship clock are not the same thing, so I have written
  it down rather than acted on it.
- **What the measuring actually found was better than a balance problem.**
  Recovered lore lived in `expedition.lore`, was read out once in the report
  dialog, and went out with the expedition object when recovery set
  `game.expedition = None`. It never reached the `Game`, never appeared in the
  codex, and `REWARD_SCALE["lore"]` was (0, 0) — so finding one granted nothing
  whatever. Three feature options across two features existed purely to print a
  sentence and take it away, and eight written discoveries sat in the data under
  a comment calling them "the reason anyone reads an expedition report twice",
  which you could not do.
- **Notes have identity now** and are filed against the game with the body, the
  system and the day. There is a Field notes tab in the codex, and each one is
  evidence on an inquiry track — 206 points across three tracks, so a party that
  reads the room is doing something no other activity in the sector does.
- **A note is not cargo.** Stranding costs 60% of the haul; it does not cost
  what somebody already read and remembered. That is a check, not an opinion.
- **Proved it bites** by restoring the throw-away: three of eight checks fail,
  including the save one, which reports "nothing to save".
- Suites: 33, **8 notes** (new) among them — 282 checks green. 169 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: what a fight leaves behind

- **I said last cycle I would take the `test_reachable` task next unless a
  bigger hole turned up, so I measured it first.** Across 473 public functions
  the bare-name matcher currently masks *zero* real orphans — the five
  candidates are my own scratch matcher's false positives (aliased imports,
  re-exports, decorators, callables passed as arguments). So that task would
  prevent a future defect rather than fix a live one, and it lost again to
  something that was actually broken. Worth saying plainly rather than quietly
  reordering.
- **Every consequence of an engagement lived in `ui/battle_view.py`.** The
  salvage, the loot, the cargo pulled off the wreck, bounty progress, seized
  xenology files, instar kills, consorts lost, loyalty, and every standing
  change that follows from shooting at somebody. `sim/combat.py` held a loot
  dict and nothing else. That breaks the one-directional rule the project is
  built on, and it meant nothing headless could resolve a fight: every balance
  run that fought a battle collected no loot, no standing, no bounty credit.
- **It is `sim/aftermath.resolve()` now** and the view reads what it returns.
  `battle_view.py` went from 468 lines to 425 and stopped importing six sim
  modules it no longer needs.
- **A kill told only its victim.** Destroying a Concordat hull was −14 with the
  Concordat and nothing to anybody else, in a sector whose entire politics is a
  relations matrix. It now pays the victim's rivals a share on the same
  severity ramp `allegiance` uses: measured, a Concordat kill gives the
  Freeholds +3.4 (they are at −45) and the Charter +0.6 (at −20), and leaves
  the Dry Choir cold (+5). At peace nobody gloats at all.
- **A Bloom kill used to please the Charter alone, hardcoded, in a screen.**
  All four powers approve of one less instar now.
- **The check the project never had:** no module under `sim/`, `data/`,
  `world/` or `core/` may import Qt. 93 modules, clean — but it was never
  verified, and the rule it protects had just been broken in spirit for the
  whole life of the combat screen.
- **And the sharper one:** the same engagement is played out twice, once
  through the sim and once through the view, and the credits, standing and
  research must come out identical. Paying a 250-credit bonus from the screen
  fails it and prints both ledgers side by side.
- **Found and did not fix:** 17 more sites across four view modules still write
  `game.credits` and `game.rep` directly. Same defect, spread thinner. That is
  a four-file refactor and would have meant starting a second thing, so it is
  queued rather than half-done.
- Suites: 32, **8 aftermath** (new) among them — 273 checks green. 166 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a chart worth the flying

- **Exploring was the worst-paying thing in the game by about fifty to one.**
  Measured before writing anything: charting the five-body home system takes 53
  days and the chart sold for 1,510 credits — 28 a day, against roughly 1,600
  for a smuggling run. Charting the *entire* 42-system sector and selling every
  chart came to 55,014, which is about one run of unlicensed seed. Meanwhile
  `intel.py`'s own docstring called the Charted level "the only one worth
  anything to a buyer, and the reason to go back to somewhere you have already
  been". The code said one thing and the arithmetic said another.
- **`survey_value()` priced a chart by weight** — `460 + 210 * len(bodies)`.
  A system with a buried Abyssal site, nine catalogued organisms and ground
  worth crossing the sector for fetched exactly what five bare rocks fetched.
- **A chart is information, so it is now worth what it says.** Relics,
  anomalies, life, ore grade, somewhere to tie up, Bloom, and how far it is
  from the buyer's nearest holding. Dearest chart in a sector is about 10x the
  cheapest, so which system you go and chart is a decision.
- **And it is worth that to somebody in particular.** The Dry Choir pays over
  the odds for wet cognition and anything unaccounted for; the Yards want rock
  and somewhere to stand a hull; the Charter wants anything alive, anything old
  and early warning. Best and worst buyer differ by 1.6x on average, and the
  best buyer varies by system — so a chart is something you carry to the right
  quay rather than sell where you happen to be standing.
- **Charts go stale**, decaying to 45% over two years, which makes a survey
  circuit a living rather than one sweep of the sector.
- **I overshot on the first pass and the measurement caught it.** The initial
  price list made a remarkable system's chart worth 92,000 — over three times
  the best contract in the game — and charting worth 1,137 credits a day. That
  fixes exploration being worthless by making it the best-paying thing in the
  sector. Rescaled against the actual economy (best contract ~27,000, dearest
  hull 900,000) to a median chart near 26,000 and about 750 a day.
- **A second measurement error, in my own check.** The "charting is a living"
  check first read 1,127 credits a day off a single seed. Across ten seeds the
  median is 763 and the range 630–837 — the seed I happened to pick was half
  again the median. The check now averages six sectors, so the band is set by
  the distribution rather than by luck.
- **Proved it bites** by restoring the flat rate: four of eight checks fail,
  the last reporting "charting still pays 35 credits a day".
- Suites: 31, **8 charts** (new) among them — 264 checks green. 164 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: contested ground

- **The sector had claims and it had holdings and they never touched.**
  `ventures._claimable()` explicitly excluded any system the player held a
  colony in — the powers politely stepped around your ground — and
  `colony.can_found()` never looked at `system.faction`, so you could plant
  inside somebody's declared space and nobody said a word. An empire game where
  territory is never contested has the empire taken out of it.
- **Both directions are live now.** Planting on a power's register costs
  standing with them (and pleases their enemies, via last cycle's allegiance
  module), and at Distrusted they simply will not have you. The cost is shown
  in the plant-a-seed dialog, before you commit, rather than in the log after.
- **A power will annex ground you hold**, and that is a question rather than a
  news item. Three answers, all measured to be genuinely different: pay the
  levy and keep it, giving up 30% of what it makes; hand it over and read best
  with them; or refuse — which keeps it, costs 18 standing, and means somebody
  comes for it eventually. 12 of 12 defiant holdings were seized within eight
  years. If the claim later lapses, the standoff ends with it.
- **The demand lives on the `Game`**, because it is something you can be in the
  middle of. `test_resume` picked it up as the sixth guarded activity without
  being told — which is exactly why that check was written as a rule about
  `window.go()` rather than a list of activities.
- **A bug in my own test helper, found by a seed that disagreed with me.** One
  of twelve trials failed with an empty assertion message. The cause: a holding
  can mature *and* be overgrown by the Bloom inside the same `advance_days`
  call, so `colony.online` was True on an object already removed from
  `game.colonies`. The helper now asserts membership rather than a flag, and
  keeps the Bloom out of the system so the check measures territory and not
  luck.
- **Proved the central check bites** by restoring the one-line exclusion that
  made territory uncontestable: exactly one check fails, and it says "the
  powers still step around anywhere the player holds".
- Suites: 30, **8 territory** (new) among them — 255 checks green. 161 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: whose work you take

- **`contracts.py` did not import `diplomacy`.** Six powers, a relations matrix
  that starts hostile in most pairs, and the thing a player actually does all
  day touched none of it. You could run the Charter's deliveries, collect a
  Concordat bounty and take Freehold prospecting money in the same week while
  all three were at each other's throats, and every one of them thought better
  of you for it. Standing was accumulation with no tension anywhere in it.
- **Serving a power now costs you with its enemies**, in proportion to how bad
  the rift actually is. The precedent was already in the game and inconsistent:
  diplomacy actions offended rivals (crudely — a flat −4 that ignored the
  severity), ventures offended a named other party, and contracts, by far the
  most frequent faction interaction, offended nobody. One module now does it
  for all three, and the flat −4 is gone.
- **The penalty is not the point. The escape is.** Severity ramps from nothing
  at −15 to full at −70, so dragging a pair from implacable to merely bad is
  worth doing. Measured across the same 28 jobs: 108 total standing in a
  hostile sector, 170 in a brokered one — and the per-power split goes from
  62/18/8/25 to 80/40/35/25. The relations matrix finally has a job in ordinary
  play instead of only at the Concord ending.
- **It enforces an order rather than closing a door.** Serve one power
  exclusively and you end up its partisan: Charter +100, Concordat −30,
  Freeholds −42. Make peace first and you can still work all four to Kin, so
  the Concord is reachable — you just cannot get there by being everyone's
  courier. Verified both directions, since a penalty that quietly foreclosed an
  ending would be a worse bug than the one I set out to fix.
- **The Dry Choir falls out as the neutral employer** — nobody is at odds with
  them at the opening, so their work costs nothing. That was not designed; it
  is what the opening relations happen to say, and it gives the map a safe
  harbour worth knowing about.
- **Proved all three checks bite** by reintroducing each defect: a flat
  threshold instead of the ramp fails exactly the gradient check and nothing
  else, and dropping the charge fails both integration checks — the second
  naming the discrepancy outright ("quoted charter −2.4 and actually moved
  −0.0").
- Suites: 29, **8 allegiance** (new) among them — 245 checks green. 157 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a run worth making

- **Contraband was free money and nobody had noticed.** Unlicensed seed was the
  dearest good in the table and flagged illegal, and neither fact did anything.
  The Freeholds both sold it and bought it, so a hold full of it never had to
  cross anybody else's space; nobody ever looked in the hold; and the standing
  penalty for selling it did not apply at the ports where you sold it. Measured
  across six sectors before writing a line: +971 to +2,118 the tonne against
  +997 to +1,680 for the best legal arbitrage anywhere in the sector.
- **The Charter's entire identity is the licensing regime**, and you could fly
  a hold of unlicensed seed through their space unexamined. Both halves are in
  now: a power that outlaws a good has no posted price for it and a much better
  unposted one, and that same power opens your hold at the dock.
- **Neither half is worth having alone.** A premium nobody can seize is what
  the game already had. A search with nothing worth carrying through it is a
  tax nobody would choose to pay. The run now goes Freeholds → Charter space,
  which is the one direction it never went before.
- **The first cut was a trap and playing it said so.** Both careers — bare hull
  and fully fitted out — ended down: heat went on faster than it came off, so
  the premium fell under the buy price and the odds pinned at the ceiling.
  Retuned the cooling rate and the fine against measured careers rather than
  taste. Now: bare hull +188k over eight runs, fitted out +402k with half the
  seizures. Committing to the trade roughly doubles it.
- **Mitigations multiply rather than subtract.** My first version subtracted
  them, so a void hold plus a manifest loom plus Trusted standing drove the
  odds under the floor — a smuggler who could not be caught. They now take a
  share each: 21% bare down to 9% fully fitted out, and never zero.
- **The screens found a bug I had written myself.** Rendering the quiet word on
  a Concordat quay showed the posted market *also* still listing Unlicensed
  Seed with a live Sell button — you could hand contraband over the desk at the
  station whose boarding party exists to stop you. The market now reads "seized
  on sight" with no counter, and the check that pins it names the defect
  exactly when I put the button back.
- **And one I caused elsewhere.** Two new parts went straight into the NPC
  outfit pool, so enemy warships started rolling smugglers' false manifests and
  the combat-assessment check went red — a feature about trade silently
  re-tuning every encounter. Parts that are kit for a trade are now marked
  `civilian` and NPC loadouts skip them. The guard checks both directions:
  never on a warship, still fittable by the player.
- **`test_verbs` could not see the quiet quay**, the same blind spot the trench
  was in last cycle. Added it: 21 controls with a hold full of contraband, all
  clean.
- Suites: 28, **9 customs** (new) among them — 236 checks green. 155 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a dig you work

- **Excavating was one call.** Press the button, lose twelve days, receive a
  number of points, and occasionally read that the face collapsed. Everything
  the setting says about Abyssal sites — that they are layered, that they are
  fragile, that the interesting part is always under the part that is easy to
  reach — was written in the codex and present nowhere in the game.
- **A site now has four strata**: spoil and overburden, the casing, the works,
  and whatever it was for. Each holds more of the site's understanding than the
  one above it and each is more fragile, so the value and the risk both climb
  together as you go down.
- **Three ways to take a layer**, and the choice is real rather than a difficulty
  slider. Working properly takes a fortnight and loses almost nothing; cutting
  straight down takes four days, spoils most of what is in a deep layer, and can
  bring the face in on the party. Measured over sixty digs: careful 138 points in
  56 days, brisk 121 in 28, cut 47 in 16.
- **That produces an actual strategy** rather than a dominant option: cut through
  the overburden, which holds 8% of the value and spoils at 5%, then work the
  deep strata properly, where cutting spoils at the 85% cap. The screen shows all
  three numbers side by side, so the decision is legible before you commit.
- **Understanding banks per layer, not at the end** — which is the whole point.
  A trench abandoned after the casing is worth the casing, so backfilling is a
  choice rather than a way of throwing the dig away. Restoring bank-at-the-end
  passes every other dig check and fails that one alone; I verified that by
  putting the old behaviour back and watching exactly one check go red.
- **A dig lives on the `Game`**, so last cycle's rule held on its first new
  case — `test_resume` picked it up as a guarded activity with no prompting.
- **`test_verbs` could not see the trench**, since it is only reachable with a
  dig open. Added it: four controls, all clean. That is the same blind spot the
  flee-and-hail NameError lived in.
- **Found a hole in `test_reachable` by falling into it.** I wrote a `summary()`
  in `dig.py` that nothing calls, and the check passed — it matches bare names,
  so any other module's `summary` covers for it. Measured the blast radius
  before reacting: across 433 public functions it currently masks exactly that
  one, and resolving calls to their defining module throws five false alarms
  unless aliased imports and re-exports are followed properly. So: deleted the
  dead function, wrote the limitation into the check's own docstring, and queued
  the real fix rather than bolting it on mid-cycle.
- Suites: 26, **6 dig** (new) among them — 223 checks green. 151 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: put it down and pick it up again

- **A save taken mid-approach lost the approach.** `docking`, `decoding` and
  `decoding_tech` lived on the window rather than the game, so reloading
  silently dropped them: the guard that had been holding you in the docking
  screen simply stopped, and the passes you had spent were gone. It had been
  that way for many cycles and nothing noticed. Last cycle's transit work
  exposed it by fixing only itself.
- **All three are on the `Game` now**, with `Docking` and `Decoding` registered
  with the save codec, and the window exposing them as properties over game
  fields so nothing else had to change.
- **The sharper half is the decoding secret.** Had the code been regenerated on
  load rather than persisted, a player could save, guess, reload and guess
  again against a fresh code until it fell out. The check asserts the secret
  itself survives, not merely that an exchange exists.
- **A `Battle` deliberately stays on the window**, which `battle_state` has
  said since it was written: combat resolves in one sitting and no clock runs
  during it. It is in the check's allowlist with that reason attached.
- **The general check is the one worth having.** It reads `window.go()`, takes
  every activity the guard will divert you into — recognised by its `.over`
  flag — and fails on any that is not a field on the `Game`. Put docking back
  on the window and it reports it by name. A new mode that guards navigation
  and keeps its state on the window now fails the suite rather than quietly
  losing a player's evening.
- **My first version of that check flagged five things that were never state**
  — `self.views`, `self.current`, `self.toast` and friends — because it matched
  every `self.X` in the method rather than the ones with a finished state.
- Suites: 25, **5 resume** (new) among them — 215 checks green. 147 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a crossing you fly

- **Travel was a wait.** Pick a destination, pay the reaction mass, watch the
  calendar move, occasionally read a line about something that had already
  happened to you. The helm could plot an intercept and route around a star and
  then had nothing to do for eleven days.
- **A crossing now runs in watches.** Two to four of them depending on the leg,
  and a watch may bring something that wants an answer: debris across the
  course, a radiator lobe that will not seat, a bad slug of reaction mass, a
  hull adrift with no beacon, a flare off the star, the intima fruiting, a
  contact on the same lane. Seven of them, twenty options, and every option
  spends one of the three things a crossing has — time, mass, or the hull.
- **The tension is measurable, which is the test.** Flying the same crossings
  hurried against careful: 7.4 days and 0.6% of the hull, against 8.5 days and
  none of it. Neither policy is better on both axes, which is what makes the
  watch a decision rather than a formality.
- **Nothing is charged up front**, so cutting the burn halfway is a real
  option: you keep the mass you have not yet burned and lose what you have,
  and you are where you started.
- **Two things I got wrong and caught by playing it.** The last watch of every
  crossing could never bring anything, because I rolled for events only when
  not yet at the destination — the final leg, when a captain is most tired and
  least stocked, was always the quiet one. And I first held the crossing on the
  window rather than on the `Game`, which loses it over a save exactly as
  docking and decoding state still does.
- **A lever for it in the efficacy harness**, so the watches have to keep
  earning their place: switch them off and a crossing takes 6.5 days instead of
  7.5.
- Suites: 24, **6 transit** (new) and a fourteenth lever among them — 223
  checks green. 146 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: every feature has to move something

- **Reachability was a floor, and I said so at the time.** A function called
  only from a readout passes it: the Bloom's growth multiplier was consumed by
  `summary()` from the day it was written while contributing nothing whatever
  to the simulation. This cycle closes that gap.
- **Ten levers, one per claim the game makes about a number.** Each names a
  feature, a way to switch it off, and a measurement of the world. Neutralise
  the lever, run the same seeded scenario, and the measurement has to move.
  Provocation, hull loading, consort screening, relation drift, ground weather,
  colony works, crew loyalty, market shocks, mining method, research evidence —
  all ten prove themselves, several emphatically: screening cuts damage to the
  flag from 54 to 9, a deep bore doubles what comes off a body.
- **The demonstration that matters**: disconnect the Bloom multiplier again and
  reachability still reports "416 public functions, every one reachable" while
  efficacy fails with "11.45 with the feature, 11.45 without".
- **Two of my probes were wrong before any feature was.** The Bloom one ran
  long enough that every system pinned at its ceiling of 1.0, so a Bloom
  growing half again as fast reached exactly the same total; the research one
  stocked the bench full in *both* runs and compared full against full. Both
  read as inert features when the features were fine — a saturating or
  already-satisfied probe is the failure mode to watch for here.
- **And I got the sign convention backwards on every lever at once**, which was
  at least an efficient mistake. The field is now named for what happens when
  the feature is *removed* rather than what it does when present.
- **The harness carries two checks on itself**: that a deliberately decorative
  feature fails it, and that every lever's substitution actually changes its
  number rather than quietly missing its target. A harness that cannot fail is
  worse than none.
- Suites: 23, **13 efficacy** (new) among them — 203 checks green. 142 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: nothing written and never called

- **Three cycles running, a feature shipped a number the game never read** — a
  levy counter, a death reason, a Bloom growth multiplier. The `Game`-fields
  check catches persistent state; this is the other half. `test_reachable.py`
  walks the package and fails on any public function called from nowhere at
  all.
- **It found three real holes, not just dead code.**
  - **Treaties bought nothing.** `treaty_bonus()` promised that signing made
    everyone easier to trade with and was called by nobody, so a treaty cost
    goods, paid standing, and added a label. It is folded into the trade bonus
    now: four treaties move it 0.00 → 0.12.
  - **Instars could not be killed.** `kill_instar()` was called from nowhere,
    so roaming masses seeded systems and ate colonies with no counterplay
    whatever — and the provocation table paid seventy for a kill nobody could
    make. A mass in your system is now announced and can be intercepted.
  - **Convictions never felt your standing.** `loyalty.align()` — a
    Charter-raised officer taking your Charter standing personally — existed
    from the day convictions were written and was called by nothing. It runs
    from `adjust_rep` now.
- **And fourteen genuinely dead functions removed**, including
  `planets.extraction_rate`, orphaned when mining was rewritten.
- **Two things the check taught me about itself.** `return None` is not a
  result — counting it flagged every early-exit function, and the self-check
  caught that on its first run. And restricting the scan to value-returning
  functions missed `kill_instar` entirely, which mutates and returns nothing;
  widening it to every public function added exactly one more finding and no
  noise at all.
- **What it does not catch, stated in the check itself.** A function called
  only from a readout, or only by the suite, passes. The Bloom's growth
  multiplier was consumed by `summary()` from the day it was written while
  contributing nothing to the simulation — I verified this check would have
  passed on it. Reachability is a floor, not a guarantee.
- Suites: 22 of them, **4 reachable** (new) among them — 190 checks green.
  139 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the Bloom starts paying attention

- **The arc had two ends and nothing between them.** Growth is detected, it
  spreads on a timer, and eventually you burn into the heart. Five stages,
  roaming instars and weapon-family resistance were all in place, and none of
  it responded to *you*.
- **Provocation is the middle.** Burning a system, clearing one, killing an
  instar and striking the heart all cost it something, and it keeps count.
  Past each threshold it answers: it grows harder, then it hardens
  specifically against whatever family you have been using, then it detaches a
  seeding wave, and finally it starts sending masses after your hull across
  nine light years without stopping at the colonies on the way. Provocation
  bleeds away if you leave it alone, so this is a response to a campaign rather
  than a doom counter.
- **Study or burn, not both.** Nine days alongside a living mass yields
  xenolith and readings scaled by how much of it there is — and it grows while
  you watch. Burning it removes exactly the thing you would have studied. The
  setting has always described that tension and the game had never once made
  you feel it; the system screen now offers both buttons side by side with what
  each is worth.
- **I nearly shipped the levy bug again.** `growth_multiplier()` was computed
  from the responses and read by nothing whatever — the Bloom would have
  "answered" by printing a line and changing nothing at all. It is now consumed
  in `threat.tick`, and the check measures actual spread with and without,
  because a multiplier nobody reads looks exactly like one that works. It fails
  against the unwired version: "spread 35.0 against 35.0".
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, 6 assessment, 7 balance,
  **7 bloom** (new), 7 verbs, 23 interface — 186 checks green. 138 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: every verb in the game, driven once

- **Rendering a screen does not press its buttons.** Splitting `combat.py` last
  cycle left fleeing and hailing calling names that no longer existed, and
  nothing noticed — `test_ui.py` draws every screen and passed throughout. The
  new suite clicks **210 enabled controls**: the ten standing screens, an
  engagement in progress, a party on the ground, all four port tabs, and both
  mini-games, each on a fresh game because clicking one control can end the
  fight or spend the money the next one needs.
- **The trap that made the bug invisible is worth stating.** Qt *swallows*
  exceptions raised inside a slot — it prints a traceback to stderr and carries
  on, so `button.click()` returns perfectly happily and the obvious version of
  this check sees nothing at all. Catching them needs a `sys.excepthook`. I
  verified the whole thing by reintroducing last cycle's bug: it reports
  `battle/'Hail them': NameError name 'is_destroyed' is not defined`.
- **And a check for the trap itself**, because if the hook ever stops working
  every verb check goes quietly green whatever is broken.
- **Also driven on a wreck**: the same controls with no money, no crew, no air
  and a hull open to space — 78 of them stay enabled in states their handlers
  were never written for. All clean, which is a genuinely reassuring answer
  rather than a vacuous one.
- **What it did not find is worth saying too.** No new bugs: 210 controls in
  five contexts, plus 78 on a wrecked ship, all ran without raising. The value
  this cycle is the check, not a fix.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, 6 assessment, 7 balance,
  **7 verbs** (new), 23 interface — 179 checks green in about seventy seconds.
  135 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: difficulty that means something

- **Encounter difficulty was very nearly decorative**, and three separate
  things were wrong. Every weapon below tier two is grown-family, so a
  *fabricated* warship at low difficulty could mount none of them and arrived
  unable to fire a shot — 100% of scale-one Concordat hulls were unarmed. The
  chassis was drawn uniformly from the faction's whole list, so a scale-four
  patrol could turn up in a scout. And `tier = round(difficulty)` is a step, so
  everything from 1.5 to 2.4 drew identical parts.
- **All three are fixed**: armament is fitted separately and the tier rises
  until something fits, hulls are drawn weighted toward the threat, and a
  fractional difficulty rolls between the tiers either side of it. The curve
  now descends smoothly across eight steps instead of falling off a cliff
  between 2 and 3.
- **The real culprit was nerve.** Resolve drained on `(turn - 9) × 0.45`,
  purely on the clock, and the enemy lost it *twice as fast as the player*. A
  hull with no armament at all drove off a scale-four battleship 75% of the
  time by sitting there. Nerve now turns on damage taken, being behind on
  damage, and futility — an unarmed hull wins 6% at scale four, while a TESTUDO
  built to be hit still wins by outlasting, which the game has always said it
  should.
- **I spent an afternoon tuning against a measurement artefact.** My harness
  reused one ship object across every fight, so the second fight onward started
  with a wreck. That read as "encounters are brutally hard", and on that basis
  I changed armour from subtractive to diminishing and tripled enemy hull —
  both reverted once a fresh hull per fight showed the player was in fact
  winning almost everything. The note is now in `INTERFACE.md` and at the top
  of the balance suite.
- **Splitting `combat.py` at 504 lines broke fleeing and hailing**, and nothing
  in the suite drove either path — every attempt to break off would have raised
  `NameError` in a live game. There is a check for both now.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, 6 assessment, **7 balance** (new),
  23 interface — 172 checks green. 134 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a defeat that teaches something

- **You could lose a NAVIS in two turns and be told nothing.** Combat had arcs,
  bands, crew stations, consorts and abilities, and a scrolling list of damage
  lines. Playing a losing fight, the one actionable line — "nothing will bear
  at this range" — was buried among fourteen hits, and nothing before the first
  shot suggested a scale-3 battleship would end it inside a minute.
- **The read** now sits beside the plot: who breaks whom first, what the enemy
  is armed for and doing, whether you can outrun it, which of your mounts are
  bearing and by how many degrees the rest are off, and two or three things
  worth doing about it. Against that battleship it opens with "outmatched",
  "they break you in 3 turns", "can you outrun them: no", and "breaking off
  costs you very little; this does not."
- **My first model was worse than useless — it was not even monotonic.** I
  compared raw hull and raw damage, and measured it: a scale-0.5 scout read as
  a *harder* fight than a scale-2 warship. Enemy hull turns out to be a chassis
  lottery that ignores difficulty entirely, while armament (0 damage at scale
  1, 121 at scale 3) and armour both track it. Comparing turns-to-break after
  armour fixed the direction.
- **Then the thresholds were wrong, and only measurement found it.** A ratio of
  0.19 was reading "outmatched" in fights the player won 70% of the time,
  because most wins come from the enemy breaking off rather than dying — a pure
  damage race reads far bleaker than the game plays. The bands are now set from
  320 fights across two hulls and eight difficulties, and the reasoning is
  recorded beside the constants.
- **The check that matters** plays forty fights and fails if a worse-sounding
  verdict wins more often than a better-sounding one. Against the raw-hull
  model it fails exactly as it should: outmatched 31%, lighter hull 37%, a real
  fight 25%, heavier hull 39%.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, **6 assessment** (new), 23
  interface — 165 checks green. 132 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: an audit, not a sixteenth system

- **The seam was discoverability.** Fifteen cycles each added a system that was
  perfectly obvious to whoever had just built it. A first-time captain got a
  sector chart, one line of log — "The Patient Increment is under way" — and no
  indication that commissions, consorts, colony works, the research bench or
  the register existed. Checking every screen on turn one for a trace of each
  system found three entirely invisible and several behind tabs nobody had a
  reason to open.
- **Standing orders** are the fix: twenty conditions worth acting on, each with
  a predicate and a screen it points at, the four most pressing shown above the
  chart. A brand-new captain is now told that a commission is on offer, nothing
  is on the bench, nothing here has been surveyed and there is word going
  round. Ten years into a game the same panel leads with the Bloom.
- **Placement was the whole point and I got it wrong first.** The panel went in
  below the chart and the system detail, where a first-time player would never
  scroll to find it — the exact problem it was written to solve. It reads
  compactly now and sits directly under the heading.
- **A check for state written but never read found two more seams.** A levy
  venture incremented a counter that nothing anywhere consulted: the venture
  succeeded, the save grew a number, and the sector was exactly as before.
  Levies now make everything that power tries next easier, which is visible on
  the diplomacy desk. And `death_reason` had been recorded on every death since
  the game was written and never shown — the game always knew why you died and
  simply never said.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, **8 orders** (new), 23 interface — 159 checks
  green. 129 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: mass is the price of everything

- **Fitted mass was free.** A NAVIS carrying 267 tonnes of armour and reactors
  flew exactly as fast as one carrying 52, and jumped *further*, because
  nothing anywhere read the tonnage. Every design was therefore the same
  design: the heaviest, best part in every slot. Loading now sets speed,
  evasion and (dampened) jump range.
- **The trade is legible.** A maxed NAVIS with a full hold reads "overloaded"
  at 1.32 of its capacity and pays 18% of its loading factor; a stripped one
  reads "light" and gains 14%. The design sheet shows fitted mass, loading
  against capacity, and what it is costing — beside the existing power deficit,
  so two tensions now argue with each other on the same screen.
- **Heavy is not simply worse.** A second drive adds 210 tonnes and buys 6.9 ly
  of jump range. That is the design question: what do you want the hull to be
  good at.
- **I calibrated it wrong twice, and the play-testing caught both.** First I
  sized capacity against `chassis.mass_t` — which runs from a sixty-tonne SPORE
  to a twelve-billion-tonne LEVIATHAN, so every hull read as "light" and the
  penalty never engaged. Rebasing on slot count and hold rating put it on the
  right scale, and then I calibrated against fully-maxed fits and found every
  chassis pinned at the floor: a realistic design fills two-thirds of its
  slots, not all of them with the heaviest thing available. The check now
  builds all thirty-five hulls at a sensible fit and fails if any is penalised
  for it.
- **The stranding trap was live again.** Loading cuts jump range as well as
  speed, and a captain who fills the hold and cannot reach the nearest system
  is the deadlock this project has hit twice before. Jump takes the loading
  effect at 45% strength, and the check measures a fully laden starting hull
  against its nearest neighbour: 98% of empty range, 2.7 ly of margin.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, **6 design** (new), 23 interface — 151 checks green.
  125 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the powers start doing things

- **Diplomacy waited for the player.** Four factions tracked how they regarded
  you and each other, and nothing they wanted ever made them act. They now run
  **ventures** on their own account: annexing an unclaimed system, embargoing a
  rival, courting one, raising a levy, letting a concession, or assembling a
  censure. Each runs a season or two and resolves whether or not you were
  involved.
- **You can back one, work against it, or let it happen.** Backing costs
  credits and buys standing with the sponsor at the expense of its target;
  opposing costs standing and needs only nerve. Either moves the odds by 30
  points. Letting it happen is a choice too — over twelve years the powers
  annexed five systems between them without asking.
- **The first version quietly broke a victory condition.** Every blockade and
  censure is a permanent debit to a pair of relations, and nothing ever pushed
  the other way: the worst pair slid from -45 to -94.5 within a decade and kept
  going. Concord needs *every* pair at +15, so a long game was foreclosing an
  ending the player is entitled to reach, through pure background churn.
  Grievances now fade toward where the sector rests; relations reach
  equilibrium around year ten instead of sliding, and a determined broker
  reaches Concord in 4/4 test games.
- **My first attempt to measure that was wrong twice.** I advanced twenty years
  in a single `advance_days` call and saw nothing move at all — the tick does
  not iterate, so four ventures were created and none resolved. Then, having
  fixed the measurement, my regression check *passed with the fix removed*,
  because relations plateau against the -100 floor either way and the emergent
  numbers barely differ. It now tests the mechanism directly: push a relation
  down 40 points, leave it alone for twenty years, and it must come back.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, **8 politics** (new), 23 interface — 145 checks green. 123 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: weather on the ground

- **Terrain was fixed and the sky was empty.** An expedition already had
  supply, a rover, hazards and injuries, but nothing about the surface changed
  while you were on it. Seven **weather** conditions now roll in and out over
  the days you are down there: dust storms, whiteouts, radiation squalls,
  downpours, ground tremors and katabatic gales, with clear weather about 57%
  of the time.
- **It bites on all three axes.** A gale takes a two-day crossing to five,
  multiplies the hazard chance by 2.6, and cuts sight to one tile. Measured
  over 24 expeditions, a party covers 13.8 tiles in enforced fair weather and
  11.1 with real weather — the walk home is longer than the walk out, which is
  the whole point.
- **A gale pins the party entirely**, so *Sit out the weather* is always
  available and always costs a day of supply. That is not a convenience: a
  party that can neither move nor die is an expedition that stops, and the
  first version had exactly that hole — the existing playability check spun its
  driver 150 times and failed with "expedition never terminated".
- **Two of my seven conditions were dead on arrival.** I gated whiteouts on
  biomes called "ice" and "frozen" and downpours on "ocean" and "temperate",
  none of which the generator produces — it makes `cryo`, `subsurface`,
  `verdant`, `microbial`, `sulfuric` and three others. Both conditions were
  unreachable. The check now validates every gate against a real galaxy, and
  fails if a condition can never occur.
- **One thing that looked like a bug and was not.** Two direction buttons
  showed no movement cost in the screenshot; I read that as a rendering fault,
  and it was the party standing in the bottom-right corner with two of its four
  neighbours off the grid. Worth confirming from the data before fixing the
  wrong thing.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  **7 ground** (new), 23 interface — 137 checks green. 119 modules, all under
  500 lines.

## 2026-07-28 — SEEDFALL: a market with news in it

- **Prices drifted and nothing ever happened.** Markets already responded to
  what you personally bought and sold, but no event ever struck one. Seven
  kinds of **shock** now do: a blight through the growing stacks, the yards
  downing tools, a convoy that never arrived, a seam coming in, the Concordat
  dumping a stockpile, a quarantine, somebody quietly rearming. Each names
  itself, moves local supply hard, and lifts after a season or two.
- **Shocks are kept apart from supply on purpose.** The daily drift pulls
  supply back toward equilibrium, so folding a blight into it would let the
  drift quietly erase the blight — and expiring it could never restore the
  original price. `Stock.shock` is a separate multiplier, recomputed wholesale
  from the live shocks each tick.
- **The register makes information worth having.** You write down what a port
  pays only while standing in it, and what you wrote goes stale: full
  confidence today, half at two hundred days, worthless at four hundred. The
  market screen now tells you where your own notes say to take what is in your
  hold, how far it is, and how old the note is. Nothing reads a distant market
  directly — that is the entire mechanic.
- **News only reaches you from places you know.** A shock at a system you have
  never visited and hold no colony in happens silently.
- **The regression check that mattered most** puts a shock on a market, checks
  the price moves, then expires it and checks the price comes *back*. Written
  the obvious way — adjust the multiplier when a shock is live — an expired
  shock never lifts, and a long game accumulates permanent distortions across
  the sector. I verified the check fails against that version.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research,
  **8 trade** (new), 23 interface — 130 checks green. 116 modules, all under
  500 lines.

## 2026-07-28 — SEEDFALL: research grows inputs

- **Research was one pool.** Everything you did anywhere fed a single number
  and a single bar, so nothing you chose to do changed what you could learn. A
  programme now consumes **evidence** of four kinds, each from a different part
  of the game: survey data from charting, specimens from landing parties and
  dives, hardware off hulls you take apart, xenolith readings from digs. A
  propulsion programme cannot be fed by botany.
- **The mix is derived from a technology's branch**, not written out for each
  of sixty-one entries, so the whole tech tree got inputs without being
  touched. Adding a technology needs no work; adding a *branch* does, and the
  suite fails if one is missing a mix.
- **Four approaches, four bargains.** Measured over 24 runs each: careful 120
  days and never a setback; parallel tracks 90 days for nearly twice the
  material; push it 60 days with a 28% chance a season of going backwards;
  reverse-engineer 90 days and cheap, but only if you hold alien work or
  salvaged hardware to take apart.
- **It measurably pays to go and look.** A captain who surveys as he goes
  reaches his first technology in 52 days against 225 for one who simply flies.
- **I bricked the opening and the playtest caught it.** Gating all progress on
  evidence meant a fresh captain who set a project and flew made *literally
  zero* progress — 0.0/150 at twelve months. A bench with nothing on it now
  still runs at 35%: reading, arguing and going over old results. Evidence buys
  the other two thirds. The regression check sets a project on turn one, does
  nothing else, and demands the technology arrive.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, **8 research** (new),
  23 interface — 122 checks green. 112 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: mining becomes a decision

- **Extraction was a rate.** Park in orbit, pick 30 or 90 days, tonnage
  appears. It was the last pillar with no choice in it. A body now has
  **seams** at three depths, and you choose **how** to work it.
- **Four methods, four bargains.** Measured over twenty 60-day runs each:
  *skim* 26 t with no wear and a tenth of the depletion; *open cut* 149 t at
  0.9% hull and 38% worked out; *deep bore* 244 t at 3.2% hull and 81% worked
  out, with mishaps three times as often; *bioleach* 140 t, no wear, 13%
  depletion, but it burns biomass and needs a harvest tendril. A bore reaches
  seams nothing else can, which is often the whole reason to fit one.
- **Depth is derived, not stored.** `hash_seed` of the body and resource, so
  every existing save has seams without a migration and the same rock always
  hides the same thing in the same place.
- **The first version reintroduced a deadlock the game had already fixed.**
  Burying volatiles at depth two meant a captain with no bore and no reaction
  mass had no way to make fuel — exactly the trap the mining root's `drink`
  was added to prevent two cycles into this project. The existing playability
  check caught it on the first run. Fuel now never sits below an open cut, and
  neither does whatever a body is advertised as: a rock listed as ore-bearing
  that needs a shaft is a survey that lied.
- **Two readout bugs from the screenshots.** "Wear on the hull 13.5% a month"
  was quoting damage to the *outermost layer* as if it were overall integrity —
  five times worse than the truth. And a 0.02-grade trace seam listed as
  "0.0 t volatiles/day" made the panel look broken.
- **My own measurement was wrong first.** The initial method comparison
  reported zero tonnes for all four, which looked like the feature was dead.
  I had loaded 400 t of fuel into a 340 t hold, so there was nowhere to put
  the ore.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, **7 mining** (new), 23 interface
  — 114 checks green. 108 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: knowing where you are going

- **Discovery was one boolean.** A system was visited or it was not. It now
  climbs four rungs — **Catalogued** (a name and a position the registry will
  not stand behind), **Scanned** (read at range or bought as a chart),
  **Visited**, and **Charted** (every body surveyed). The map draws all four
  differently: an outline, a faded disc, a solid one, and a dotted ring around
  anything complete.
- **Charts can be bought, and surveys sold.** You can pay a broker for a scan
  rather than flying out to make your own, and a *complete* survey — every body
  in a system, not the interesting ones — sells once, to anybody. That is the
  reason to go back to somewhere you have already been.
- **Rumours point somewhere before you go.** Five kinds circulate at ports:
  buried relics, rich seams, unlicensed growth, lost hulls, and systems people
  are odd about. Pay to be told properly or just listen and risk them shutting
  up. Arriving settles the story either way.
- **A true rumour plants what it claims.** My first version tested the story
  against whatever the galaxy had already generated, and measured 0% true on
  the first three rolls — the conditions almost never held, which made the
  whole feature worthless. A true rumour now buries the relic, seeds the
  growth, enriches the seam. Measured over 90: 73% come good.
- **That fix created a much worse bug, which I caught before it shipped.**
  Planting inside the truth test meant `circulating()` mutated the sector — and
  it runs every time the port desk is drawn. Merely *looking* at a noticeboard
  seeded bloom and buried relics across the galaxy. Truth is now a pure dice
  roll; the planting happens in `take()`, when you have committed. The
  regression check runs thirty passes over the desk and demands the galaxy come
  back identical.
- **Two smaller things from the screenshots.** The map legend still described a
  two-state world, and a port offered "Nobody goes there" three times running,
  which reads like a broken generator rather than a rumour mill — one of each
  kind per port now.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, **8 exploration** (new), 23 interface — 107
  checks green. 104 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: work that leads somewhere

- **Contracts were a shopping list.** Independent jobs off a board — haul this,
  kill that, survey there — and nothing followed from finishing one.
  **Commissions** are four chains of three stages each, from the Charter, the
  Freeholds, the Dry Choir and the Concordat, where each stage escalates and
  the last one pays properly.
- **A stage is an ordinary contract.** `sim/chains.py` builds one through
  `contracts.shape()` — the same function the board uses — so deadlines, cargo,
  bounties and expeditions needed no changes at all. What makes it a chain is a
  `chain` field on the contract and what happens when it completes.
- **They close doors.** The Charter's assay office and the Freeholds' sluice
  are the same seam seen from two sides; taking either refuses the other, and
  the refusal holds at the rival's own port. Missing a deadline withdraws the
  commission for good rather than merely failing a job.
- **They land on the crew.** Finishing one raises loyalty for the officers
  whose convictions it served, so a career of Charter work and a career of
  Freehold work leave you with a different bridge.
- **Two bugs found by playing it.** A stage that asked for half the usual
  tonnage was titled with the *full* figure and completed at the halved one —
  "carry 62 t" that finished at 31 — because the scale was applied after the
  title was written. And a commission stage was sitting on the ordinary board,
  showing twice and eating one of the six contract slots; it is now held apart
  from both.
- **One refactor worth noting.** Pulling the per-kind contract shaping out of
  `generate()` so chains could reuse it was the whole reason this cycle stayed
  small. My first attempt at that extraction was a mechanical dedent that broke
  the file; doing it deliberately with the block in front of me took two
  minutes and worked. `port_view.py` crossed 500 lines on the way and the
  berths tab became `ui/berths_panel.py`.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, **7 missions** (new), 23 interface — 99 checks green.
  99 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a bridge with opinions

- **Officers were stat blocks with wages.** They modified rolls, gained levels,
  and never wanted anything or noticed anything. Each one now signs on with a
  **conviction** — believes in the licence, wants the Bloom burned, thinks it
  should be studied, Freehold to the bone, wants something left behind, in it
  for the money, loyal to the hull — and a **loyalty** that moves with what the
  ship actually does.
- **The same act reads differently from three seats.** Burning a Bloom system
  is a good day's work to a veteran of Kessel's Reach and a lost library to a
  xenologist; a treaty with the Charter costs you both Freeholders on the
  bridge. Measured across four convictions and four events, they end 38 points
  apart.
- **Loyalty is felt at the stations, not on a roster screen.** `officer_level()`
  — the number the helm, gunnery and engineering seats read — now returns the
  level an officer is *working* at: 1.2× when devoted, 0.72× when restless,
  0.45× when mutinous. It plugs straight into the crew stations built in the
  combat cycle.
- **A year of missed payroll costs you the bridge**, first walkout in month
  eleven. Paying properly and keeping the hull whole ends a year at mean
  loyalty 84. Two port actions push back: a bonus, and shore leave that costs
  you a week of the calendar.
- **My first balance pass was wrong and the playtest showed it.** Loyalty drift
  toward ship morale was strong enough to flatten every officer onto the same
  number within a year — 76.4, 76.4, 76.4 — which threw the convictions away
  entirely. Drift is now a fifth as strong: what you did has to outweigh the
  ambient weather.
- **A check that greps the source found ten dead beliefs.** Convictions name
  the events they react to, and nothing was raising `xeno_study`,
  `xeno_incorporated`, `first_contact`, `bloom_cleansed`, `bloom_spread`,
  `colony_lost`, `crew_death`, `trade_profit` or `repair` — the xenologist's
  entire belief set among them. All now hooked at real sites.
- **Two smaller fixes.** The display bands were named on their own scale, so an
  officer reading "Mutinous" was mechanically merely restless; they now turn on
  the same constants the mechanics do. And the starting bridge drew names at
  random from a list of 27, which put two officers with the same first name on
  the same bridge about one game in ten — I got three Mareks on the first run.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, **7 crew** (new), 23 interface — 92 checks green. 94 modules, all
  under 500 lines.

## 2026-07-27 — SEEDFALL: colonies that keep growing

- **A colony was a purchase, not a place.** Plant it, wait out the gestation,
  and it emitted the same numbers forever; the only thing that could ever
  change was starving to death when upkeep went unpaid. Colonies now undertake
  **works** — commitments of material and time that change what the settlement
  *is*.
- **Eight works, one at a time, four to a colony.** Deepen the workings (ore
  ×1.7, and it costs more to run), raise a garrison, lay a slipway, erect a
  sensor mast, ring the habitat, build a xenology annex, open a free harbour,
  sink a lineage vault. Some are gated on family or research, some only offered
  to colonies that already produce the right thing. Material is charged up
  front, which is the point: it is the reason to fly ore somewhere rather than
  sell it.
- **Everything reads through one layer.** `sim/works.py` combines the class
  definition with the finished works, so ward, build sites, sensors, diplomacy
  and population all feel a work without anything else knowing works exist.
  Verified end to end: garrison 0.00 → 0.28 ward, slipway opens a build site,
  mast adds 2 ly of sensor.
- **A bug I predicted, then confirmed, then fixed.** The `port` effect was only
  read when a colony matured, so a harbour *built later* granted the effect and
  opened no market — the system stayed portless. Now handled where the work
  completes. The regression check fails without the fix.
- **A layout fault the screenshot caught.** Panels sit side by side and are
  given equal height; the shorter one had its rows dragged apart to fill the
  space. In the first render of the new empire screen the colony rows were
  spread over 600px of nothing. Panels now pack their contents to the top while
  the frame still matches its neighbour.
- **My first attempt to test that fault measured the wrong thing.** I asserted
  on the *gaps* between rows, and it passed with the fix disabled — because the
  spare height goes into stretching the row widgets themselves, not the space
  between them. Comparing each row against its own size hint shows it plainly:
  120px rows asking for 18–31px. Both new interface checks now fail without
  their fix and pass with it, verified in both directions.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  **6 empire** (new), 23 interface — 85 checks green. 91 modules, all under
  500 lines.

## 2026-07-27 — SEEDFALL: the fleet joins the fight

- **Escorts existed and did nothing.** `combat.py` contained no reference to
  `game.fleet` at all, so a second hull you had designed, paid for and fitted
  sat in a berth while you fought alone. Hulls can now be ordered to sail in
  company: they follow the flag, deploy onto the tactical plane, and fight.
- **A consort is a `Side`.** Subclassing the existing side means `_fire`, the
  layer model and every arc check work on one unmodified. What a consort adds
  is a standing order and a captain who follows it — you have one pair of hands
  and they stay on your own helm.
- **Three orders that are genuinely different bargains.** *Screen* spends the
  escort to keep you whole; *flank* spends patience getting behind something;
  *concentrate* spends everyone's safety to end it quickly. Measured over 24
  fights each: the flag took 50 damage alone and 12 with two screens, while
  flankers put out 34 to a screen's 3. Screening consorts also physically sit
  between you and the enemy, which weights the fire they draw.
- **Losses are permanent.** A consort below 22% hull breaks off; one that dies
  is struck from the fleet whatever the outcome, so bringing a hull to a fight
  is a real wager rather than free damage.
- **Two older bugs found while testing.** `_fire()` measured its range band
  between the flag and the enemy rather than between the two hulls actually
  shooting, which was invisible with two sides and wrong the moment a consort
  fired from a flank. And the Bloom's resisted-hit branch called an undefined
  `say()` — a `NameError` that crashed any late-game Bloom fight where a
  bearing mount hit tissue that had learned that weapon family. It needed
  stage 4, accumulated resistance, a mount in arc and a 25% roll, which is why
  nothing had tripped it.
- **The varied opening aspect was unreachable.** `tac.initial_layout()`, built
  last cycle to vary how an engagement starts, was never used in play: the
  battle screen called `combat.start()` without an rng, so every fight in the
  game began with the enemy dead ahead at band 3. Now seeded from the game's
  own stream. Measured across 40 fights, outcomes are unchanged — it buys
  variety, not difficulty.
- **My test captain was the problem, twice.** Driving fights with a repeated
  "salvo" reported the player dealing *zero* damage, which looked like combat
  was broken; the ship's mounts were all broadside and the order never turned
  it beam-on. Fixing that to steer toward the target still failed, because
  closing puts the target at 0° — outside a broadside arc entirely. Combat was
  behaving correctly the whole time. The arc-aware pilot now lives in
  `tests/captain_ai.py` so the next change to combat is measured against a
  captain that can actually fight.
- Suites: 27 simulation, 5 xenotech, 14 playability, **5 tactical**, 5 flight,
  22 interface — 78 checks green. 87 modules, all under 500 lines.

## 2026-07-27 — SEEDFALL: the helm learns to lead a moving target

- **Transfers now aim where the body will be.** The helm panel told the player
  "bodies move while you fly", and the code did not do it: every quote was
  measured against where the target sat *today*, and arrival teleported you to
  wherever it had drifted. `flight.intercept()` solves the lead as a fixed
  point — guess a flight time, look up where the body will be then, re-time the
  leg, repeat. It settles in at most two passes across 380 solves, and a flown
  transfer now arrives on the predicted day with the aim point 0.0000 AU from
  the body.
- **Courses route around the star.** With the aim point drawn on the chart it
  was immediately obvious that a target on the far side produced a straight line
  passing 0.03 AU from the star. `flight.route()` bends the course around a hot
  radius and charges the detour in distance and days, so an opposite conjunction
  is expensive rather than lethal. The clearance never closes tighter than the
  destination, so the innermost rock is still reachable — and still hot.
- **The chart shows the plan.** The orbit chart draws the routed course as a
  polyline, a crosshair at the aim point, an amber arc for the ground the target
  covers while you are under way, and the star's heat zone when the leg runs
  near it. A burn selector re-plots without committing. The chart also now
  scales to the outermost body, having previously cropped comets off the plot.
- **`hash()` was moving every planet on every launch.** Orbital phase was
  derived from `hash((body.name, body.id))`, and Python randomises string
  hashing per process — so the same seed grew the same galaxy and then scattered
  its orbits differently every time the game started, including between saving
  and loading. Now derived from `core.rng.hash_seed`. A regression check runs
  three subprocesses under different `PYTHONHASHSEED` values and demands one
  answer.
- **A first-frame layout fault, honestly scoped.** Rebuilding a view's column
  did not tell its `QScrollArea` the contents had changed size, so a screen
  taller than the viewport painted once squashed. My first reading of this was
  far more dramatic — nine of ten screens "unable to scroll" — and it was wrong:
  measuring how many event-loop turns the unfixed code needed showed Qt
  recovering by the second turn, so a running app was never broken. What the
  fault really cost was one frame of reflow, and trustworthy screenshots. Since
  reviewing these screens by rendering them offscreen is how this loop works,
  that second thing matters: the bug fooled me before it could fool a player.
- **Two of my own regression checks did not bite, and I caught both.** The
  first asserted a course never dips inside its tighter endpoint — geometrically
  impossible, since a chord between two points at similar radii always sags. The
  second passed with the fix deliberately disabled, because every earlier check
  had already called `grab()` on those views and forced the layout. Rewritten to
  build its own window and measure exactly one event-loop turn, it now fails
  without the fix and passes with it — verified in both directions.
- Suites: 27 simulation, 5 xenotech, 14 playability, 2 tactical, **5 flight**
  (new), 22 interface — 75 checks green. 84 modules, all under 500 lines.

## 2026-07-27 — SEEDFALL: combat becomes positional, with crew stations

- **A real plane.** Ships now carry a position, heading and speed. The five range
  bands survive — every weapon is specified in them — but the band is *derived*
  from an actual separation rather than stored, so all the existing band logic
  kept working while closing became a manoeuvre instead of a menu pick.
- **Firing arcs.** Every mount fires through fore, broadside or turret, derived
  from what it is: fixed lances look forward, point defence and anything
  self-guiding traverses. A mount outside its arc refuses to fire and says how
  many degrees off it is, so turning to bring a gun to bear is a decision worth a
  turn.
- **Three crew stations, one of you.** Each turn you take Helm, Gunnery or
  Engineering personally; your officers hold the other two at their own level.
  Directed gunnery shoots markedly better than automatic. Engineering routes
  power to the mounts or the drive, patches the outermost breach, or dumps heat.
  Twelve orders across the three.
- **The enemy uses the same geometry** — it steers for the range its mounts want
  and comes about when its fixed arcs are pointing the wrong way. It does not
  cheat the plot.
- **A tactical plot** on the battle screen: range rings, both hulls drawn as
  headings, the line of sight labelled with the range, your forward arc sketched,
  and a per-mount readout saying "bears", "60° off arc" or "out of range".
- Modules split to stay under the line limit: `tactical`, `stations`,
  `battle_state`, `enemy_ai` and `abilities` came out of `combat`. Two interface
  bugs fixed on the way — a nav hint reading "keys 1–90", and a salvo control
  duplicated between the fire row and the gunnery station.
- Suites: 27 simulation, 5 xenotech, 14 playability, 2 tactical, 21 interface.

## 2026-07-27 — SEEDFALL: diplomacy with two axes

- **A relations matrix between the powers.** Standing with a faction was a number
  that went up when you sold them charts. There is now a second axis: how the
  four powers regard *each other*, starting hostile in four of six pairs (the
  Concordat and the Freeholds at -45 over stolen frames; the Charter and the
  Freeholds at -35 over forged licences).
- **Six overtures**, each with a cooldown and a standing floor: tribute,
  intelligence, relief supplies, treaties, denouncement (which buys you standing
  with everyone who dislikes your target) and **brokering**, the only action that
  moves faction-to-faction relations at all — and it requires both parties to
  think well of you first.
- **Faction agendas**: each power is chronically short of something (the Charter
  of phosphate, the Yards of ore, the Dry Choir of recordings) and pays extra
  standing for it.
- **Concord is now a diplomatic achievement**: all four powers at Kin *and* all
  six pairs at peace, rather than four separate grinds against one meter.
- **Two balance defects found by playing.** The naive survey-and-sell strategy
  was sitting on exactly zero credits after five years — in-system flight costs
  had quietly made it unviable — which also made the solvency check flaky. Fixed
  by moving the jump arrival point inside the system rather than beyond its outer
  orbit, and repricing survey data from 300 to 460; the check now asserts a floor
  rather than merely "not in debt". Also: ten nav destinations were binding a
  shortcut to a nonexistent "10" key.

## 2026-07-27 — SEEDFALL: the Bloom becomes an antagonist

- **The problem, measured first**: a BASTION with five mounts cleared the whole
  sector inside one in-game year, and the Bloom opened on only 2.8 of 42 systems.
  The game's central threat was frightening while you were poor and irrelevant
  the moment you could afford a warship.
- **Five named growth stages** — Latent, Vegetative, Motile, Adaptive, Sovereign —
  advanced by the sector-wide burden, each raising growth and spread and each
  announced in the log. A test seed runs Latent → Vegetative (yr 2) → Motile
  (yr 5) → Adaptive (yr 6) → Sovereign (yr 7), so there are years of grace before
  it starts hunting.
- **Motile instars**: once past stage 2 it keeps masses in the field that travel
  between systems, preferring *your* colonies, and take them.
- **Adaptation**: from stage 3 it builds resistance to whatever weapon family you
  keep using — up to 55% — and forgets what you stop using. Vary the loadout or
  watch your guns stop working. Verified: 200 fabricated hits gives 55%
  resistance to fabricated and none to grown.
- **The First Instar** at Kessel's Reach: the original husk, Charter serial still
  legible, found by surveying the origin system. Containment now requires the
  sector clean *and* the heart dead — 21 burn passes from a battleship, each
  costing days and taking backlash. Clearing the map is no longer enough.

## 2026-07-27 — SEEDFALL: the helm, and two games inside the game

- **The helm — in-system spaceflight.** A jump now drops you at the system edge
  rather than alongside whatever you came to see. Bodies sit on real orbits with
  Keplerian periods and keep moving while you fly, so the range to a target
  depends on when you leave. Four burn profiles trade reaction mass against days,
  each with its own risk of dust, debris, a radiator flutter or an attitude fault.
  **Coasting is always free**, which is deliberate: without it an empty tank could
  not reach the ice that would refill it, which would have re-introduced the
  deadlock fixed the day before. Local work flies the ship alongside on the
  standard profile, so nobody is forced through the helm to survey a rock.
- **Docking, as the nervous-system study describes it.** Sense with the wet
  organs, compute on the dry core, act with the muscles, hold homeostasis
  meanwhile. Three axes drift; you correct one per pass; the readout is blurred
  in proportion to how poor your sensors are and the correction is as precise as
  your navigator and compute allow. A clean approach earns standing, a botched
  one buys a tug.
- **A decoding bench** for alien emissions: four positions, a hidden pattern, and
  a response saying how many glyphs are exactly right and how many are present
  but misplaced — never which. Worth real study points toward whichever
  technology you are working on, and it costs nothing but attempts, so it is the
  poor captain's route into xenotechnology.
- **A real bug the playability suite caught**: a transit event where a Freehold
  skiff sells you volatiles subtracted credits without checking you could afford
  them, so a poor captain went into debt. You now buy what you can pay for and
  the goods scale to match.
- Suites: 27 simulation, 5 xenotech, 9 playability, 19 interface.

## 2026-07-27 — SEEDFALL: playability audit, then the ground game

- **Playability audit first, and it found two showstoppers.** `exodus_launched`
  was read by the victory check and set by nothing, so one of the five endings
  could never fire. And a captain could deadlock: broke, no fuel, ore in the hold
  and no way to convert one into the other away from a port. Both fixed — there
  is now a `launch_exodus` action, the mining root cracks ice for reaction mass
  (which is its third ingest route in the metabolism document anyway), and a
  distress beacon will get you towed for standing and money if there is genuinely
  no ice either.
- **A new `playability` suite** exists so neither class of defect returns: every
  ending must fire from conditions a player can actually reach, twelve destitute
  starts must all be recoverable, and a plain survey-and-sell run must stay
  solvent for five years.
- **Ground expeditions — a game within the game.** A lander puts a party on a 7×7
  zone revealed one tile at a time. Supply is the clock; terrain costs days and
  springs hazards; site features (worked stone, downed hulls, vents, sealed
  caches, standing arrays) offer choices resolved against an officer's stat.
  Nothing is banked until the party walks back to the lander. Known ground costs
  one day to re-cross, which is the difference between tension and a death trap —
  the first cut had seven expeditions in eight stranding, and now it is one.
- **Contracts.** Six kinds — delivery, prospecting, survey commission, bounty,
  antiquities, ground contract — posted per port, priced by distance, checked on
  the clock so they close the moment their terms are met. Failing one costs
  standing. Nothing requires taking any of them.
- Two real bugs caught by rendering the screens: a zone map cached on the view was
  destroyed with its container on every refresh, and the research card grid sized
  its columns to content so the third column was clipped.
- Suites: 27 simulation, 5 xenotech, 7 playability, 17 interface.

## 2026-07-27 — SEEDFALL: alien technology as its own progression

- **Four alien cultures, twelve technologies, found rather than researched.** The
  Abyssals (still living, under the ice), the Ossuary (a lineage that spent its
  last centuries preparing to be found), the Weft (matter worked at nanometre
  pitch, no bodies and no writing) and the Tessellate (crystalline, and fond of
  standing waves that do not decay). Their remains are seeded as buried sites on
  body kinds that suit them, and every technology is guaranteed at least one site
  so no chronicle is unwinnable.
- **Discover, trade, steal, incorporate** — all four verbs the brief asked for.
  Understanding accrues in study points from excavating a site (which wears out
  as you return to it), analysing relics in a polyp lab, buying field notes at a
  port (the Dry Choir has the best and knows it), or seizing them off a hull you
  destroy. At full understanding the technology is *incorporated*: its id joins
  `research.unlocked`, unlocking one of twelve new parts — most of them family
  `any`, because the point of alien work is bolting it to the hull you already
  fly. Study banked past a prerequisite is kept and settles later.
- **A xenology desk** on the Research screen shows each culture, what has been
  recovered, what remains "an unrecovered technology", and the analyse controls.
- **Three UI bugs fixed on the way, two of them long-standing.** A dozen research
  tabs forced a minimum width wider than the view, clipping everything beside it
  — tabs now wrap onto fixed rows. The card grid sized columns to content, so the
  third column of the research tree, the codex and the hull picker was cut off —
  columns now share the width equally. And an over-clever height-for-width flow
  layout, tried first, collapsed the whole column inside the scroll area; it was
  replaced with something deterministic, which is the lesson.
- Suites split and grown: 27 simulation, 5 xenotech, 17 interface.

## 2026-07-27 — SEEDFALL: five technologies, not one

- **Hull roster 21 → 35, stations 12 → 19**, across five technology families
  rather than three. The GESTALT grown fleet is now one option among several
  instead of the only real choice.
- **Two new families.** *Synthetic* — Dry Choir vessels (CANTOR, LATTICE,
  ORDINAL, THEOREM): crewless, no atmosphere plant, a photonic skin over a
  spaceframe wrapped around a substrate vault, superb instruments and no
  self-repair whatsoever. *Xeno* — REVENANT and ANTIPHON, laid down to a plan
  nobody in the Verge wrote; they mend like a grown hull and ring audibly when
  something large moves nearby.
- **Seven new fabricated hulls** filling the gaps the Yards line had — TENDER
  (tug), AWL (smuggler), KILN (mobile refinery), CARAVEL (passenger liner),
  SPINDLE (deep survey), PORTCULLIS (system monitor), HAMMERFALL (siege) — plus
  the MIDDEN hybrid ship-breaker.
- **Eight new stations spanning the technologies**: Orbital Drydock, Refinery
  Platform, Monitor Station and Helium Skimmer (fabricated), Free Port (hybrid),
  Relay Choir (synthetic) and Reactivated Array (xeno).
- **Two new station mechanics.** A **Free Port** opens a market in a system that
  had none, which is worth considerably more than its docking fees. A **Monitor
  Station** wards its system: it slows the Bloom, burns back what it can reach,
  and — since it is the thing with the guns — defends itself far better than the
  farm next door. Averaged over eight trials, two unattended years take a system
  from 0.24 to 0.75 infestation; watched, it falls to 0.20.
- **Three new technologies** (Autonomous Munitions, Synthetic Cognition, Xenolith
  Metallurgy) and ten new parts, including a smelter bay that turns ore into
  alloy in the hold on the way home.
- **Structural change**: hulls moved out of `data/chassis.py` into
  `hull_types.py` (layer stacks and the family rules), `hulls_grown.py` and
  `hulls_built.py`, with `chassis.py` reduced to the registry. Every import site
  in the game was left untouched, and no file crossed 500 lines.
- **Six new checks** covering the new ground: every family complete and coherent
  (layer weights summing to one, a critical layer, a build requirement, a tint);
  the graft rules that let a hybrid take an intima and refuse a coherent beam;
  only the mechanical families refusing to heal; every station's effect keys
  drawn from a closed vocabulary; the Free Port opening a real market; and the
  monitor ward. That last one caught two real bugs — the station was being eaten
  by the Bloom before its ward could apply, and the hull picker kept editing a
  SPORE while showing you synthetic hull cards. Suite now 27 simulation + 15
  interface checks.

## 2026-07-27 — SEEDFALL: the programme as a playable RPG (PyQt6)

- **New `seedfall/` package**: a native desktop space exploration / trading /
  combat RPG — a modern Starflight with a Civilization layer — built entirely on
  the thirteen documents. PyQt6, 53 modules, every file under the 500-line limit,
  no server and no build step. `python -m seedfall`.
- **The documents are the mechanics, not the flavour.** The Class Reference
  becomes 21 hull chassis; the Dossier's six-layer hull becomes the damage model
  (shots ablate epidermis → rind → mycelium → osteoid, and the crew only starts
  dying when the pneumostat opens); Metabolism becomes the economy, with
  phosphorus scarce because chondrite is 0.1% P; the Cell Atlas becomes the
  fittings; the Nervous System becomes a cognition branch where you must *buy*
  silicon because nobody can grow a processor; the Compendium becomes a 58-node,
  ten-branch tech tree; and the Registry's six named containment failures become
  the six factions — including the Bloom, a lineage with its Hayflick counter cut
  out, which simply grows.
- **Design intent — many paths.** Grown / fabricated / hybrid hull families with
  real trade-offs (grown heals but gestates for months and eats phosphate;
  fabricated is instant, expensive and never repairs itself). Combat on a
  five-band range track where destruction is only one win condition: resolve lets
  a TESTUDO with no weapons at all win by outlasting, which is the programme's
  actual doctrine. Five simultaneous victory conditions (Containment, Exodus,
  Concord, Genesis, Dominion).
- **Built first as a browser build, then ported to PyQt6 and the web build
  retired**, so there is exactly one implementation of the rules and no chance of
  the two drifting apart. The `/game` viewer route was removed with it.
- **Tested headlessly, and it mattered.** `python -m seedfall.tests` runs 21
  simulation checks and 15 interface checks; the interface suite builds the real
  `MainWindow` on Qt's `offscreen` platform and paints every screen and tab,
  including a live engagement. Between the two builds the suites caught nine real
  defects, several of them unplayable: sector generation that could **strand the
  player with nothing in jump range** (fixed with a lane-relaxation pass
  guaranteeing every star has a neighbour within a starting jump); combat that
  **never terminated** because armour could fully null a weapon (armour now floors
  at 15% leak-through, plus late-onset resolve attrition and a turn cap); weapon
  mounts beyond the first doing nothing (added the full-salvo order); hulls so
  large relative to damage that an escape pod drove off a battleship (hull scale
  retuned — fights now run ~18 turns and span destroyed / driven-off / lost);
  derived ship stats being written into save files; a negative ice-harvest rate
  from the reaction organ's fuel draw; and a clipped HUD caption.
- `seedfall/INTERFACE.md` documents the module map, the one-directional layer
  rule (`data → world → sim → ui`), and the constants that will bite anyone
  retuning it. Root `INTERFACE.md` and `README.md` updated.

## 2026-07-26 — Working 3D models (glTF/OBJ/STL) + an interactive viewer

- **New `models3d/` package**: builds solid, colour-coded 3D meshes of the
  seven main designs (trimesh) and exports each to **three working formats** —
  `.glb` (glTF, coloured), `.obj`, and `.stl` (printing) — into
  `assets/models3d/`, plus a preview PNG. Modular: `build.py` (per-design mesh
  builders), `render.py` (matplotlib preview), `run.py` (CLI
  `python -m models3d.run [--check]`). `dome_half` is hand-triangulated so it
  needs no external triangulation engine; each GLB is round-trip-validated.
- **Interactive gallery in the local viewer**: added a `/models` route
  (`viewer/models_page.py`) that shows the models lit, rotatable and AR-capable
  via `<model-viewer>`, with download links, plus static serving of the
  glb/obj/stl at `/models/<file>` (path-traversal guarded) and a "Working 3D
  Models" card on the landing page.
- README gains a "Working 3D models" section with the seven previews. Verified
  every mesh by eye from a rendered frame (fixed the preview's cross-part depth
  sorting so the LICHEN/TESTUDO domes show).

## 2026-07-26 — Nervous System (13th document): sensing, cognition, comms

- **New 13th document — Nervous System** (`gestalt-nervous.html`): how a grown
  vessel senses, thinks, controls and communicates. Its thesis: a km-scale ship
  needs both a **grown "wet" nervous system** (real sensory organs, bioelectric
  signalling, grown neural computation — DishBrain-style) for sensing,
  homeostasis, reflex and learning, and a **fabricated "dry" silicon core** (fast
  deterministic compute, navigation, comms, the human digital interface) —
  because biology can't grow a fast transistor or a radio, and silicon can't
  self-repair or sense. The two are joined by a real bio-electronic **interface**
  (OECTs, microelectrode arrays, electrogenetics, optogenetics, conductive
  nanowires). It is, honestly, a cyborg. Covers senses, the signalling
  speed-limit, the four kinds of organic computation, the silicon side & the
  interface, communication (crew + fleet), and a worked docking control loop.
  Three house-style figures (control stack, bio-electronic interface, docking
  loop), 14 citations. Registered in the catalog (slug `nervous`); canonical nav
  regenerated to **thirteen** entries across every document; all thirteen
  artifacts republished.

## 2026-07-26 — Python simulations of the designs' major systems (animated 3D)

- **New `sim/` package**: dependency-light Python (numpy + matplotlib) that
  models the major systems of the four main designs and renders them as
  **animated 3D GIFs** (`assets/sim/`). Modular — `params.py` (canonical
  numbers, single source of truth), `systems.py` (grounded dynamics: growth,
  life support, spin gravity, thermal, gestation), `geometry.py` (3D meshes),
  `animate.py` (per-design 3D-scene-plus-gauge builders), `run.py` (CLI:
  `python -m sim.run [design] [--fast] [--check]`).
- **Four simulations**, each a 3D scene + live gauges: **NAVIS** grows from a
  seed to ~24,000 t on the mining-limited curve with day/night intima glow;
  **ARCA** spins to 1 g at the rim with crew on the inner surface, a Coriolis
  drop, and a stable ~125-yr O₂ reserve; **LICHEN** swings ~160–265 K on the
  Martian surface while the interior holds 293 K; **GRAVID** gestates vessels in
  staggered cradle cycles. Each verified by eye from a rendered frame.
- Added `sim/INTERFACE.md`, a README "Simulations" section (the four GIFs), the
  project INTERFACE tree, and a gitignore for the preview frames.

## 2026-07-26 — Metabolism (12th document): ingest → digest → metabolise → excrete

- **New 12th document — Metabolism** (`gestalt-metabolism.html`): the nutrition-
  and-waste physiology of a grown vessel across four acts. Python-grounded
  mass-and-energy budget yields the document's thesis: photosynthesis on the hull
  makes only ~0.45 t/day of biomass (matching 13 t/day growth would need 29× the
  hull area), so the intima only makes the crew's **air** — the **body** is grown
  by *eating the rock* (digesting a carbonaceous asteroid's reduced organic
  carbon, ~1.4 MW, and oxidising its minerals), which is why growth is
  mining-limited. Covers the two mouths, the mineral gut (bioleaching →
  separation → refinery → organics → absorption), the two-sap bloodstream, and
  the four waste streams (only heat truly leaves; ~100 t/day tailings re-used as
  shielding; C/H₂O/N closed). Five house-style figures (whole-body flow,
  ingestion, digestive tract, energy budget, excretion streams), 13 citations.
  Registered in the catalog (slug `metabolism`); canonical nav regenerated to
  **twelve** entries across every document and all twelve artifacts republished.
  (Recovered mid-build from a botched in-place figure swap by rebuilding the doc
  from source and re-injecting figures cleanly.)

## 2026-07-26 — Cell Atlas (11th document) + richer 3D interiors

- **New 11th document — the Cell Atlas** (`gestalt-cells.html`): a cell-level
  cytology of a grown vessel. Grounds the census in Python (~10¹⁹ cells per
  hull; ~42 distinct types across 8 functional classes) and catalogues every
  type — role, survival, chassis, metabolism, life-cycle, coordination and
  distribution — plus the internal ecosystem/trophic web, and how each type is
  engineered, grown and tested (cross-linked to the Compendium and Earth
  Program). Three new house-style figures (lineage tree, trophic web, hull
  cell-distribution map), 19 citations, honest `gap:` flags on the three big
  integration bets. Registered in the viewer catalog (slug `cells`); the
  canonical nav is regenerated to **eleven** entries across every document and
  all eleven artifacts republished.
- **3D models — richer cutaway interiors**: multi-level decks, habitation
  compartments, vascular cores, ARCA terraces/settlements/sun-cord nodes,
  LICHEN floors + taproot, GRAVID embryos at two growth stages with umbilicals,
  and SPORE/LEVIATHAN/TESTUDO occupants. All 14 builds node-verified.

## 2026-07-26 — Detailed illustrated README (+ a broken figure found & fixed)

- **Rewrote `README.md`** into a detailed, illustrated guide: hero, a mermaid program
  map + closed-loop-metabolism diagram, a per-document tour with real figures, a
  "by the numbers" table (python-verified), the honesty conventions, and run/structure
  sections.
- **Extracted 13 figures** straight from the documents' own inline SVGs into
  `assets/figures/` as PNGs. Each figure is made self-contained (the docs' CSS
  variables are resolved to literal dark-theme values, since librsvg does not evaluate
  `var()`; stray `&` escaped; a dark ground added) and rasterised with `rsvg-convert`,
  then eyeballed. Class-styled drawing sheets (Starship/Habitat/GRAVID/LICHEN) carry
  their doc's class rules so they render faithfully.
- **Found and fixed a real defect:** the Compendium's *defence-in-depth* cancer-control
  figure was an unfilled `{fig}` placeholder in the published doc. Rebuilt it from
  scratch as a python-grounded waterfall (10¹² → 0.1 uncontrolled tumour lineages
  across seven layered controls, ~10¹³× suppression, below the 1-per-lifetime
  threshold) and republished the Compendium.

## 2026-07-26 — Two new documents, consistency pass + GitHub

- **Grew to ten documents.** Added the **Fleet Class Reference**
  (`gestalt-classref.html`, 9th) — a detailed profile of all 18 grown-vehicle
  classes with a master comparison table — and **3D Models** (`gestalt-3d.html`,
  10th) — interactive, rotatable/zoomable solid models of all seven main forms,
  drawn by a self-contained (WebGL-free) software renderer with cutaway views,
  interior components, a live scale bar and labelled hotspots.
- **Consistency pass across all 10 docs.** The per-document navigation bars had
  drifted (each listed a different 5–8 subset of the set). Regenerated every
  `prog-nav` to one canonical 10-entry bar so all documents cross-link the whole
  program; verified 9 links + 1 current marker and balanced tags in each.
  Re-published all ten artifacts to their canonical URLs. Updated `README.md`,
  `INTERFACE.md`, and `viewer/catalog.py` to reflect ten documents.
- **Published the project to GitHub** (`git init` + first commit).

## 2026-07-26 — Persisted to project folder + Python viewer

- Copied all eight published documents from the (session-only) scratchpad into
  `docs/`, plus the design-loop state file `deepen-roadmap.md`.
- Built a zero-dependency **Python viewer** (`viewer/`, stdlib only):
  - `catalog.py` — document registry (source of truth).
  - `wrap.py` — wraps each artifact fragment into standalone HTML and rewrites
    cross-document `claude.ai/code/artifact/<id>` links to local `/d/<slug>`
    routes (preserving `#anchors`).
  - `index.py` — themed landing page (document grid, GESTALT identity, light/dark).
  - `app.py` — `http.server` app + CLI (`--check`, `--open`, `-p`).
  - Verified: `--check` passes for all 8 docs + index; live server returns 200 for
    `/` and `/d/<slug>`, 404 for unknown slugs; 0 residual external artifact links
    after rewriting.
- Added `INTERFACE.md`, `README.md`, and this log.

## Program state (design loop)

The documents are produced and refined by a recurring "deepening" design loop
whose full round-by-round history and queue live in `deepen-roadmap.md`.

- **Phase A** (rounds 1–20): deepen each document element; ground every figure
  in Python. Complete.
- **Phase B** (rounds 21–30): build the Earth Program (ground R&D roadmap) —
  six work packages, integration ladder, Gantt + budget, gated go/no-go. Complete.
- **Phase C** (rounds 31–44): cross-link all documents bidirectionally; audit and
  reconcile every figure against the Compendium §08 canonical-parameters table.
  Caught and fixed several real errors (ARCA atmosphere 828→113 Mt and its O₂-buffer
  cascade; LICHEN membrane 6.5→7.4 MN/m; the pressure-wall 6.5 cm→6.5 mm; the O₂
  buffer 160→140 yr to match the canonical 34% O₂; stale cross-doc phrasing).
- **Phase D**: upgrade all figures to professional architectural-diagram
  standard, and add real citations throughout (~108 references across the set).
- **Phase E** (user-directed): subsystem deep-dives (light delivery, healing &
  regeneration, sustainability) documented as chat answers + python-grounded
  figures; the **Fleet Class Reference** and interactive **3D Models** documents;
  and a whole-program consistency + cross-linking pass. Program now ten documents.
