# Session log, part 17 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-29 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: half the diplomatic board was free

The fault I parked two cycles ago, finally taken. Every ordinary overture has
charged you for being seen since `allegiance.py` was written; `broker` and
`denounce` never did. Measured at 70 with everyone:

    relief   (concordat)             charter -0.2, concordat +3.3, freeholds -1.3
    broker   (concordat, freeholds)  concordat +1.8, freeholds +1.8  <- nobody else
    denounce (concordat, freeholds)  charter +6, concordat +6, freeholds -14

Brokering seats two powers at a table, thanks you with **both**, moves their
relation twenty-eight points and decides the Concord ending. The Charter sits
at -20 and -35 with the pair of them and did not notice.

`defenders_of` is the mirror of `offended_by` — who minds you *attacking* a
power rather than serving one. I kept it symmetric with the original (offence
below Cold, devotion above Correct) rather than tuning it to bite at dawn, and
the emergent property is better than anything I would have chosen: the Verge
opens with no friendships in it, so denouncing costs nothing at first and gets
steadily dearer **as you pacify the sector**. The more peace you make, the
more expensive it becomes to play powers off against each other.

**Where I was wrong first time.** I priced brokering's offence on what you are
*thanked* with. `courtship` has already shrunk that to under two points at any
standing where brokering is even permitted, so the loudest act on the board
cost a third power six tenths of a point — real, consumed, and beneath
noticing. It is priced on what it **moves** now. `TREATY_WEIGHT` existed for
exactly this reason and I had not joined the dots.

**Then the balance bit back, and an old check caught me.** At the new weight,
`test_politics`'s determined-broker bot reached the Concord 4 times in 20
against a floor of 7. My first instinct was to lower the weight — and the
measurements said the honest range was 0 to 3, which is back to a rounding
error. Splitting the difference would have been fitting to tests.

So I asked what the bot was actually modelling: a captain who brokers and
never rebuilds standing. That was a complete strategy while brokering was
free. Measured at the new weight — **brokering alone reaches the Concord 6
times in 20; brokering and courting, 19 times in 20.** The design is sound and
the bot was out of date. I updated its premise and said so in the check, and
it now clears the same bar far better than it used to.

**The sweep, again, found holes in my checks rather than my code.** 5/8 first
pass. The preview-versus-act agreement I had measured at 3,456 comparisons
while building the fix and never written down — so a mutation hiding the
denunciation cost from the board survived. Nothing held the two principals of
a settlement exempt from being charged for each other. And the
Bloom-takes-no-offence check was asked of a Bloom with no relation to anybody,
which scores zero devotion and drops out of the list on its own, proving
nothing. 8/8 after — and a ninth lesson: I split the checks into a new suite
and the sweep silently lost them, because its own suite list was stale.

**And one honest bug of my own.** Brokering charges a third party twice — once
as an enemy of each principal — and my `preview` quoted that as two separate
lines. `test_courtship` reads the board entry by entry and caught it: promised
the Freeholds -3.30, then -4.90, while the act moved them -8.20. Both halves
were true and neither was the number a captain needs. The board merges to one
line per power now. A stale three-argument stub in `tests/levers.py` fell over
on the new signature at the same time, which is the sort of thing that suite
exists to notice.

Shipped: `allegiance.defenders_of` / `price_attack` / `charge_attack` and an
`except_` on the existing pair, `BROKER_WEIGHT` and `DENOUNCE_WEIGHT`, the
costs wired into both `perform` and `preview`, and `tests/test_public.py`
(5 checks). Full suite green.

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
