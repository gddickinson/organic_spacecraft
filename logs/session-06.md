# Session log, part 06 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-31 to 2026-07-31; undated entries keep their original place.

## 2026-07-31 — SEEDFALL: an order of battle, and three things the measuring found

#110. The powers have real purses — income, outlay, a margin, and they found
and promote ports with them. The sector has eighty-four hulls, twenty-one on
patrol, each flying somebody's flag. **The two had nothing to do with each
other:**

    traffic._busyness = 1 + port.level (+1 capital, +2 lit anchor, −1 bloom)

A power's presence was a reading of its infrastructure and never of its
treasury, so a bankrupt power had exactly as many hulls on station as a
thriving one.

`sim/fleets.py` derives the whole order of battle every time it is asked —
nothing stored, the discipline `anchorage` uses for a quay. Measured across
ten sectors at three dates, 120 power-days: margin p10 98, p50 274, p90 336.
At **45 a day per hull** that is a median fleet of 6, most 10, and 10 of 120
power-days with none at all. Played out over 600 days in six sectors the
sector fields 18–30 hulls, median 24.5 — against the 21 patrols already there.

The payoff: `control.means` grants the top rung, *repelled*, only where a
squadron is actually on station. Being driven off needs something that can
come out after you; a capital without one still shoots from its own batteries.

**Three things the measuring found, and two of them killed a plan.**

*The clock.* The first pass at "how often does a power lose its squadron"
advanced 900 days in one call and reported 12 of 24 capitals losing theirs.
Stepped ten days at a time over the same span it is 1 of 24. `advance_days`
runs each subsystem's tick once with `n` as an argument, so a per-day
*decision* fires once for the whole jump. Every number in that first round was
measured on an economy the game never reaches. Task #116.

*The trade that does not exist.* This was built around "ports are paid for in
hulls" and the economy says no: founding costs the purse nothing and pays 60 a
day immediately — six foundings took the freeholds from 7 hulls to 15 with the
purse unmoved at 30,000 — and promoting moves margin by exactly zero. There is
no choice a power can make that costs it margin. Task #117. The check claims
what is true instead: the fleet follows the margin *down* as well as up, shown
by losing holdings, which is what annexation already does.

*A constant that was never distinguishable.* `CAPITAL_WEIGHT` tripled a
capital's share — and **every capital in the game is level 3 and no ordinary
port ever is**, so it and the port level were never separable. Dropping it to
1.0 changed no verdict. Deleted rather than pinned: one door, and the level had
been doing the work all along.

The capital-weight check was wrong three times before it said something true.
`>=` (a tie satisfies it). Then "two more hulls than a same-level holding"
(there is no such holding). Then "a gap of two by level" — measured, exactly
one power in six sectors produces one, because with fleets of 4–8 over 3–6
holdings largest-remainder rounding is bigger than the weighting. What the
numbers support is the *ordering*: 22 of 24 pairs put more at the developed
holding and **none** put fewer.

Five mutations run, five red.

## 2026-07-31 — SEEDFALL: twelve relics, four makers, and the last words-only page

Finishing #80. Audited every catalogue of objects in the game against whether
it has pictures, and found exactly one gap: **xenotech**. Twelve artefacts left
by four cultures that are not people, and the codex had ten tabs — fleet
classes, colony classes, machines, fittings, the sky, powers, life, field
notes, glossary, about — and not one of them was this. A captain could carry a
Pressure Song for a whole chronicle and never see it.

The four languages come straight off culture blurbs that already describe
physical things: abyssal pressure vessels (lobed, nothing flat), ossuary bone
(struts and sockets), weft weave (interlaced bands with daylight through them),
tessellate facets (prisms stacked at repeating offsets).

**Measured, and one wrong turn worth keeping.** The four first came out at a
66% worst pair, ossuary against tessellate. Widening the tessellate stack to
separate them pulled abyssal-vs-tessellate from 52% down to 43% — and pushed
weft-vs-tessellate from 62% *up* to 70%. The worst pair got worse. Four shapes
sharing one bounding frame trade against each other, and the number that
matters is the worst pair and not the pair being worked on. Reverted; the final
figure is **61%** against a 70% bar, tighter than `parts3d`'s 0.72 because four
deliberately-unlike languages should beat seven slot silhouettes.

**Two defects the checks found, both the classic one for this project.**

A lit core at radius 0.10 sat inside a tessellate prism stack of radius 0.42,
so a relic drew *pixel for pixel identical* with and without its bonus. Moved
outside every language's widest point at 0.58 — the mark is now +311 to +496
pixels depending on the maker.

And `mesh_for` looked an object up by id and returned the **cached** mesh, so a
relic whose fields had been changed still drew the canonical one. That is why
the first mutation of the mark passed: the check was comparing one picture with
itself. Handed a relic, it draws that relic; the cache is a fast path for ids.

The mark check was also too weak in a way worth recording: it probed a single
relic, and passed with the mark buried at the centre because *that* maker's
prism stack leaks light between tiers. One shape's gaps are not evidence about
the other three. Sweeping all four made the mutation bite — `pressure_song
gains 0 pixels`.

Four mutations run, four red: one language for everyone, one palette for
everyone, study not reaching the bulk, and the mark back inside the form.

With this, every catalogue of objects in the game is rendered — hulls,
colonies, fittings, machines, life, worlds, stars, berths and now relics.
Colony *works* stay words: they are upgrades that modify a colony which already
has a picture, not standalone things.

## 2026-07-31 — SEEDFALL: the guard that had a blind spot with a name in it

Finishing #26. The reachability guard already resolved calls to the module
that defined them — 1,319 of 1,329 — and the remaining fallback was the
problem: a bare name credited **every** module with a function of that name,
and the loose bucket held 23,628 names.

That is not a theoretical hole. It hid a real orphan for weeks:
`control.provoked` was written the day the approach ladder landed, read by
nobody at all, and this guard passed on it — because `sim/threat.py` holds a
local variable spelled `provoked`. Reading a local is not a reference to
somebody else's function; it is a different word that happens to be spelled
the same.

**Two wrong turns before the right rule.**

First attempt: exclude any name bound *anywhere* in the tree. That drops the
loose bucket to 18,360 — and it is wrong, because a function passed as a
callback in one module is a loop variable in another, so genuine references
would stop counting. It happened to report 0 new orphans today, which is
exactly how a bad rule survives review.

The right rule is **per file**: a Load of a name *this file* binds is a local
read. Measured:

    loose bucket   23,628 → 20,894 names
    verdicts changed                0

So it cost nothing and closed the gap. Zero new orphans is the honest result —
the hole was real, and the one thing that had fallen through it was fixed
earlier today when `forcing.grievance` gave `provoked` a reader.

`_scan` is split out of `_used` so the regression check can drive the same
analysis over synthetic sources — the existing self-check's trick, because any
literal name written in that file would be found by the very scan being
tested. **Pinned in both directions**: loosen it and a local credits again;
tighten it further and a dispatch table stops counting. Both mutations were
run and both went red.

Full suite green at 1,192 checks.

## 2026-07-31 — SEEDFALL: the worlds get a say, and most of them are empty

`sim/control.py` gave a structure the right to hail, warn, fire on and refuse a
hull. **The worlds themselves had no say in any of it** — you could come down
on somebody's colony and the only thing that ever objected was gravity.

What made it cheap was refusing to write a second ladder. A world gets the
whole of approach control — the rungs, the patience, the ward that climbs, the
grievance that reaches the sector's memory — by answering the two questions
that machinery already asks. **One line distinguishes the two authorities**,
and it is the character of the whole feature:

    A world does not mind you in orbit. It minds you coming down.

A station's question is which berth you were given. A world has no berths and
no opinion whatever about the sky above it, right up until a hull starts down
through it. So `control.welcome` learned one branch and everything else was
already built.

**And most defended worlds turn out to be ones nobody lives on**, which was the
better half of the idea and came from George mid-build: corporations and
governments protecting seams, and secret installations. Three kinds of claim,
asked in one order that matters — **people, then property, then secrets**:

    worked/2  44%   somebody is working it; a radio call and no more
    worked/3  29%   a seam worth a battery
    open      24%
    quiet/4    3%   a site nobody admits to

The first draft made **93% of bodies armed**: one threshold at 0.35 against a
generator whose median best seam is 0.72, in a sector where every home system
already has a claimant. A sky where nearly everything shoots teaches one rule
and then stops being read. Two figures at the quartiles fixed it, and made the
seam's *value* decide whether you get a battery or a radio.

The quiet sites are the part I like. `Claim.floor` starts one at the ward, so
**it does not hail** — the first you hear of it is being fired on. It names no
power, so there is nobody to bear the grudge. And `interdiction.line` says
nothing about it, deliberately: a readout that warned would hand over exactly
what the sim is keeping. Never on a body worth digging, because that is where
you would *not* put one.

Everything is derived — no new stored state. The same rock is the same secret
across a reload and across five draws off the game's own luck, which is the
discipline `sim/anchorage` uses for a quay's whole existence.

## 2026-07-31 — SEEDFALL: you cannot land, and now the game says so

Went to build "force a landing on the planet" — the last piece of the
approach-control brief — and found the game had no landing at all. The outcome
branch for a body had **no speed test**: every contact with a world, at any
rate, was `aground` with quadratic damage. A perfect descent and a ballistic
arrival were the same event.

The obvious fix is a rate threshold. Measuring says the obvious fix would have
been a lie:

    rocky world   3,771 km   10.371 m/s²   one 60 s tick of freefall: 622 m/s
    the ship this game starts you with:     0.071 m/s²

**A starship in this game cannot land on a world, and never could.** A hundred
and forty times more gravity than drive. That is not a defect — it is *why*
`sim/expedition.py` sends a party down in a lander and the ship stays in
orbit, a decision the code made long ago and never wrote down.

So three endings where there was one. `down` — the drive held the fall.
`ditched` — the captain chose the ground and paid. `aground` — a wreck.

And the answer to "or force a landing on the planet" turns out to be a number
rather than a rule:

    Loam Rise I (12.48 m/s²): 70,972 off a 336-point hull, broken up
    Grieve Reach V (0.059):        67, and she flies again

The order can be given anywhere. Where it kills you it kills you because of
arithmetic, which is better than a rule forbidding it.

Swept six sectors: **eighteen bodies can be set down on, every one an asteroid
or a comet.** Never a world — so the lander keeps its job.

Three things flying it taught:

- **A landing is a single-tick event, and the tick is a minute.** The rate
  budget is 4 m/s and one tick of freefall on the *softest* body in the sector
  costs 3.5. Let go from 84 m a hull arrives at 7.16 and wrecks; from 34 m it
  arrives at 3.61 and is down.
- **Two fields called `kind`.** `Target.kind` is `"body"` — what it is to an
  approach — while `Body.kind` is `"rocky"`. Asking the wrong one said every
  world in the sector had no surface.
- **Another two-door fact closed.** `BODY_KINDS` has carried a landable flag
  since the generator was written; `sim/contracts.py` asked the same question
  a second way as `kind not in ("gas", "star")`.

`outcome.impact_at` is new and is the point of the quote: `landing.quote` tells
you what putting her down will cost *before* you order it, from the curve that
charges it rather than a second copy.

## 2026-07-31 — SEEDFALL: forcing a berth, and two claims that were wrong

The refusal had no answer. A structure could decline to open — no boom, no
hatch, no lines — and a captain determined to get in had exactly the same
options as one who had never been refused. That made the refusal a wall rather
than a decision, and made every defence stacked above it decoration on a wall
that already held.

`sim/forcing.py` is the answer back, and **it is not a die roll**. Forcing is
holding station on somebody's fitting and cutting into it: ten minutes at a
structure with nothing much to stop you, half an hour at a capital, and the
ward does not pause while you do it.

**The first claim was wrong.** I asserted a capital port could not be forced.
Flown, the cut went through in half an hour while the hull took 243. Nothing
in the design refuses it and nothing should — what stops you is arithmetic.

**The second claim was wrong too.** I then asserted you do not survive it.
Measured: a starting hull comes away with 93 of 336, alive, on its last two
layers, *inside a capital port it has just broken into*. Which is worse than
dying, and is the actual answer. So the check states the price rather than a
refusal:

    capital: 243 hull, 93 of 336 left — inside, on the last layers
    quay:     13 hull, 323 of 336

An 18× difference, and the same `means` buys the guns *and* the time they have
to fire, so the two halves cannot drift apart into separate difficulty knobs.

Three things fell out of flying it:

- **The station turns.** The first draft parked a hull exactly on a fitting and
  watched it slide off at 40% cut. Cutting is station-keeping on a moving
  collar, and costs reaction mass on top of hull — 0.198 t for the ten-minute
  case. That is not a defect, it is what the act is.
- **A standoff berth cannot be forced at all.** There is nothing to cut: the
  boom is inboard and a hull in open space has nothing to get hold of. Falls
  out of the physics rather than being a rule, and gives a kind of dock a real
  defensive property it did not have.
- **A memory nobody weighs is a memory nobody feels.** The grievance went in
  with kinds `approach` and `forced`, neither in `memory.WEIGHT`, and moved a
  power's opinion by exactly 0.00 in both directions. `trespass` and a new
  `forced: -21.0` fixed it: charter now goes +0.00 → −42.00 and can name the
  day.

And it closed a live orphan: **`control.provoked` was written the day the
ladder landed and read by nobody at all.** The reachability guard missed it
because an unrelated local variable in `sim/threat.py` is also called
`provoked` — a bare name credits every module that has one. It has a reader
now: `forcing.grievance`, the one door between an approach and the sector's
memory, deliberately silent below being fired on.

Also wired what was already there and invisible: the conn now shows the tug
line, the refusal and the cut, and has a **Cut in** button that says what it
would take. Every one of those lines had been written into the sim and read by
nothing but the suite.

`sim/control.py` hit 704 lines and split — the forcing section is its own
module, which is the right seam anyway: control is what a dock does about you,
forcing is what you do about a dock.

## 2026-07-31 — SEEDFALL: the boats come out for a hull that asked

The other side of approach control. Everything built for it so far is what a
structure does about a hull it does not want; this is what it does for one it
does, and without it clearance is a gate to get past rather than a service
worth asking for.

**It took three measurements to become a decision rather than a rounding
error**, and the wrong turns are the interesting part.

The boats first caught a hull only at the hold point, and only once it had
braked itself to a standstill: **0.04 t saved on a 0.98 t approach**. Letting
them catch one still moving took it to **0.08 t**. Both were nothing, and the
second attempt showed why the first could not be fixed by being more generous
about the catch — nearly all the mass goes into *reaching* the corridor, not
into the last five hundred metres. The saving was being measured on the wrong
segment.

So the boats come out to meet you where the approach opens, and the trade
became real:

    wait for the boats:  alongside, 10.5 km under tow, 0.00 t over 3.4 hours
    fly it yourself:     alongside,                    1.41 t over 0.7 hours

Free and slow against fast and expensive. Both halves are pinned: a tug that
saved nothing is a service nobody waits for, and one that cost no time would
make flying it yourself pointless. A wayside quay at level 1 keeps no boats, so
it stays a gate — which is right for a wayside quay.

The shadowing trap appeared a third time: a second `from . import control`
inside `clearance.request` made the name local to that whole function and
unbound it at the earlier use. It is commented at both sites now.

And `preview._copy` learned its ninth field, which finally made the rule
sayable: **carry the state, leave the record.** `boom` and `tug` are how far
the equipment has come out and change what the next tick does, so they are
carried. `sheered` and `towed` are how far the station moved away or walked
the hull in — a trial run may not credit or bill a station for something it
has not done. 30 of 42 carried, 12 deliberately fresh.

Full suite green: **1,169 checks**.

## 2026-07-31 — SEEDFALL: a structure has authority over the volume round it

Asked for approach control — flightpaths, waiting areas, warnings, defences,
stations that move away, full berths, traffic. Measured first, by flying it,
and the ground was worse than the ask assumed:

    Fleet Hub: cleared for mast 4, hold at 555 m, 1.5 m/s or under.
    ... flew in regardless -> berthed at mast 3

**The clearance was advisory.** `Conn.cleared` had carried the whole
`Clearance` since the protocol landed, with a docstring promising a berth
"cannot be quietly swapped for one the ship preferred", and nothing downstream
read the field. And the berths were never full: four masts on a hub, five
hulls of traffic working the same system, and the docks and the traffic had
never met.

`sim/control.py` is the authority a structure has over the volume around it.

**Who holds each berth**, derived from where the traffic actually is rather
than stored — the discipline `sim/anchorage` uses to build a quay fresh every
call. *"3 of 4 berths clear; mast 3 (Held Breath) occupied."* A full structure
refuses and names the ships on it.

**What you were told**, enforced — and the enforcement needed no rule. Once
`moorings.assign` returns the granted berth, `nearest` measures the gap to
*that* fitting and no other, so a hull parked perfectly on somebody else's is
352 m from the only berth that counts. The extra condition I had written into
`control.withheld` came straight back out.

**The quiet refusal.** A dock that has not cleared you does not open and does
not swing its boom: cleared, the arm runs out to 1.00; refused, it stays in at
0.00. The machinery already existed and had no way to say no. It is the
defence every structure has whatever else it has.

**The ladder** — hail, warn, ward, repel. What a structure will do is what it
*has*, off `Port.level`, `Port.capital` and the system's ward: a wayside quay
can only shout, a capital can vector a response. Standing buys patience and
never a bigger gun — rep +80 gives ten ticks a rung, −80 gives two. And it
climbs only while the hull keeps closing, so a captain who blunders in and
corrects is hailed and forgiven: ignored, *warned* and 66 damage; corrected at
tick 14, *hailed* and none.

**A station simply leaves**, through `sim/knock` — the door a shove already
uses — so one that ran from you is off station on the plot, in the ranges and
in every forecast. Applied to the position rather than the velocity: it is not
pushing you, it is going.

**Six defects, and only two pre-dated the work.** The clearance being advisory
and the berths never filling were there all along. The other four were made by
turning a record into a rule, which is the honest cost of that: the occupancy
was invisible until docked hulls were drawn on their fittings; a docked hull
came out 418 km from a mast 444 m off the pole, because `sky.build` lifts
anything sharing the target's position and a berth is the one thing that must
never move; the flight computer and the port disagreed about which berth to
fly to, which sent a hand-flown approach to a door that would not open and
burned it to dry 22 m short; and **patience was counted in ticks**, so a hull
pressed in at full drive got a hail and a warning while one merely drifting got
all four rungs — ramming was safer than politeness. A station's clock is the
range: `control.haste` spends it against `Clearance.max_closing`, and pressed
in is now *repelled* in 25 ticks and 71 damage against 123 ticks and 2.

`preview._copy` learned its seventh and eighth fields, and the `fresh` entry
saying a twin is never cleared turned out to be a claim a measurement refuted —
a twin must know what was granted, because that decides where it flies.

Full suite green: **1,167 checks**.
