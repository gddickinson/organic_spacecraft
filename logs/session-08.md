# Session log, part 08 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-30 to 2026-07-30; undated entries keep their original place.

## 2026-07-30 — SEEDFALL: a captain may take the conn whenever they like (#109)

Reported by the player: *"There still doesn't seem to be a way to
independently pilot the ship when not engaged in some prescribed activity."*
Measured, exactly right. `berthing.can_conn` was the only door into the flight
pad and it wants a contact — it says so, "a position in empty space is
somewhere to steer for, not something to come alongside" — so the six axes,
the main drive, the six cameras and the 3D windows all existed and none of
them could be touched unless the ship was arriving somewhere. Between
structures, movement was the plotting board, which is plotting rather than
flying.

`sim/freeflight.py` is an approach with no target: open space, at the ship's
own position, the hull at the origin of its own frame. Everything downstream
keeps working because it is still a `Conn` — same axes, same tank, same
physics, same cameras.

Two things stop it being a screensaver. **It moves the ship**: `secure` writes
where she drifted to through `flight.stand_off`, the one door #103 built, so
the kilometres flown are kilometres moved on every screen that plots the
system. Measured end to end through the real window: 111 km flown by hand,
111 km moved. And **it is charged for**, through `berthing.commit` like any
other approach — 924 km flown, 8.69 t of reaction mass, 2.0 hours, and a
ledger line that says *"Under way on the conn"* rather than calling it a
broken-off approach on open space, which would have been two lies in one line.

The trap worth writing down: a free flight opens at zero range against a
target of radius zero, so `r <= hull` is 0 ≤ 0 and every arrival threshold in
`sim/outcome` is true at once. The first tick reported the ship as having
struck open space. It now returns early for open space and the flight ends
when the pilot says so and at no other time.

`hand_over` turns a free flight into an approach to something while keeping
the way on — 101.8 m/s flown by hand, handed to the computer still making
101.8 — so the last of an approach can be given away without the computer
starting again from a standing start.

Ten mutations, ten caught, but the tenth only after the check was fixed. The
refusal check used a target out of reach, which `can_conn` turns away *before*
the ship's position is touched — so the restore it claimed to cover was never
on the path, and deleting that restore passed. It now also uses a hostile
hull, which gets past the ship's own gate and is refused by the clearance,
after the position has been stood off.

`FAR_KM` was 20,000 km of advice nobody could ever be given: a full 20 t tank
spent flat out moves this hull about 17,000. It is derived now — a twentieth
of `berthing.REACH_KM`, 10,000 km — and the conn says, past it, that the
thrusters have become the slow way and the plotting board is the fast one.

1109 checks green.

## 2026-07-30 — SEEDFALL: the dock that comes out to you (#108, second slice)

At a fitting you arrive. At a **standoff** berth you hold still, and the
structure comes and gets you — which is a different manoeuvre, not a longer
one, and it needed the clearance protocol built in the last slice to be sayable
at all: a boom is a *procedure*, and no approaching pilot could infer it from
a mesh.

A holding's four gantry stubs became standoff berths. `berths3d.STANDOFF` puts
the berth 429 m out of a 400 m hull with `hinge_points` giving the other end of
the arm, so the thing the ship aims at is off the structure entirely.
`moorings.boom_step` runs the arm out over 90 seconds while the hull is inside
reach and steadier than `hold_rate` — a third of `ALONGSIDE_RATE`, 0.51 m/s —
and runs it back in the moment it is not. `outcome.alongside` now also asks
`moorings.captured`, so near and slow is no longer moored: the arm has to have
you. The clearance says so in its own words, with its own rate: *"Fleet Hub:
cleared for gantry 1. Hold station off the boom at 0.51 m/s or steadier and it
will come out to you; the gantry travels 0.38 m/s."* Flown end to end, the
computer holds and is captured at 47 minutes.

**The check was the defect, again, and this one is worth writing down.** The
drawing check counted lit pixels in the frame — 26 with the arm in, 43 at half,
63 at full — and rising numbers looked exactly like an arm coming out. They
were not. A mutation that drew the tip at the berth whatever `conn.boom` said,
an arm permanently at full stretch, passed at 44 against 43: the count was
mostly reading the change of tint and pen at capture (amber 1.8 px while it
travels, lumen 2.4 px once it has you), not length. Two effects moving the same
way, and only one of them was the claim.

So the picture is now asked the question the code claims to answer: walk the
arm's own path — hinge to berth, from the data, through the same camera the
window builds — and find the furthest lit point along it. Commanded against
drawn: 0%→0%, 25%→32%, 50%→56%, 75%→82%, 100%→100%. The bias is the tip's own
dot. All three drawing mutations now die on it.

Thirteen mutations, twelve caught; the thirteenth is a no-op and recorded as
one in `viewport._boom` — `boom_step` already zeroes the boom at anything that
is not a standoff, so the window's own guard is a second bolt on a locked door,
kept deliberately.

**Next on this task**: bays inside structures big enough to fly into, with an
aperture to pass through and a berth within.

## 2026-07-30 — SEEDFALL: docking is granted, not taken (#108, first slice)

Berthing was something the *ship* worked out — read a table of fittings, pick
the nearest, fly at it. Nobody ever asked the quay whether it would have you,
so a hostile patrol and a Charter Fleet Hub offered the same welcome: none,
because neither was ever asked.

`sim/clearance.py` moves the authority to the structure. A quay, a shipyard or
a hull that will take you issues a clearance — which berth it has assigned,
where it is and how fast it travels, how long the structure takes to come
round, where to hold, and the rate it will be crossed at. Two gates now, and
they ask different sides: `can_conn` asks the ship, the clearance asks the
structure.

Four refusals in four sets of words: a world is orbited rather than docked
with; a Weave gate is a relic with nothing to tie up to; a hostile hull "does
not answer, and is closing"; and a port whose power has turned against you
shuts the quay. Writing that last one surfaced a gap — `track.Contact` carried
no faction though `Anchorage` has had one since it was written, so a port a
power had turned against still waved every hull in.

A ship clears you for **the collar**: one hard point amidships, no masts, no
arms, no rotation. Hull-to-hull docking through the same door.

**And a real bug of my own, caught by two checks at once.** The first version
refused any approach that was not granted a clearance — which shut every
*orbit*, because a world is not a thing that clears you and going into orbit
round one needs nobody's permission. The climb rungs and the conn's own
screens both went dark. A clearance is for docking, not for flying near
something.

The declared-field guard caught `Conn.cleared` stored and read by nothing, so
the flight panel shows what the structure actually said in its own words
rather than the game's general rule.

Nine mutations, nine caught.

**Next on this task**: berths that stand off the structure on a boom that
extends to capture a holding ship, and bays inside structures big enough to
fly into. `Clearance.sort` is already the field that will carry them, named
now so it means something rather than being widened later.

## 2026-07-30 — SEEDFALL: the stations turn (#107, second slice)

2001's stations rotate, and a rotating berth is not decoration — it is a
docking problem. Two things had to become true at once: the fitting has to
move, and everything that aims at it has to know.

**The rate is derived, not chosen.** A station coming round once a minute is
2001's, and on a 400 m hub that is eleven metres a second at the rim — eight
times what a berthing allows, so nobody could ever dock. Fixing a period per
class is no better: a big station becomes undockable and a small one static.
So every structure turns at whatever period gives its berths the *same* pace,
and that pace is a quarter of `ALONGSIDE_RATE` — derived from the gate it has
to fit inside. A Fleet Hub comes round in a little over two hours, 2.9 degrees
a minute: plainly moving over a three-quarter-hour approach, and leadable.

Measured at a whole metre a second — two thirds of the budget — a hand-flown
approach lost the fitting on one chronicle in three.

**`models3d.ATTITUDE` had been spinning berths at `1/900` all along** — a
decorative rate the docking model knew nothing about. The mesh came round
every fifteen minutes while the berths on it never moved at all. A picture
arguing with the game. The rate comes from `moorings.spin_at` now, which is
the same angle the berths are turned by and the computer aims at.

**Then three real consequences, each found by flying it.**

A ballistic arrival has to *lead* the berth: at half a metre a second the
fitting had gone 268° round by the time the hull got there, and a gentle
arrival read as a collision. `moorings.lead` and `where_at` are the door.

A pilot handed the controls at four times the berth reach on a *quay* is
already touching the hull — the fitting is 0.91 radii out — so the first
button press ended the approach. Hand over with room.

And the one worth keeping: **"kill the lateral drift" is the wrong instruction
at a turning station.** `conn.closing` and `autopilot.lateral` are measured
against the structure's *centre*, so a hull perfectly matched to a moving
berth still reads a metre a second of drift, and a pilot told to null it
fights the rotation instead of joining it — measured, spending the whole
budget and arriving 482 m from the fitting. `moorings.rates` gives closing and
cross **relative to the berth**, and the panel shows them whenever the berth
is moving. That is the manoeuvre 2001 is actually about.

**And a segfault.** The full suite began dying at exit 139 with every check
passing and nothing to read — "QPaintDevice: Cannot destroy paint device that
is being painted". Two causes, both mine: a `paintEvent` that returns early
without `painter.end()` leaves the painter attached to the widget, and Qt
takes the process down when it is destroyed; and checks that closed a parent
window while its pop-outs still had repaints queued. Painters end in `finally`
now and the checks close what they opened, innermost first.

Buffered output cost an hour of that: the last flushed line said the crash was
in `knock`, a suite with no Qt in it at all. Unbuffered, it was `showflying`,
which is exactly where the new windows are.

## 2026-07-30 — SEEDFALL: one hard sun (#107, first slice)

Going for a 2001 look, and 2001 is above all one hard sun and no fill: a
sunward face near white, a shadowed face near black, and a terminator you can
see.

The renderer lit everything with `AMBIENT = 0.40`, which is a studio fill and
not a star. Measured on a Fleet Hub at 943 m: the whole structure between 20
and 215 with a median of 47, and nothing in the frame saying where the light
was. Three changes, and none works alone:

- ambient to 0.06 — not zero, because a face at pure black is a hole rather
  than a shadow;
- diffuse to 1.40, so the *sum* stays where it was. `spheres.py` paints worlds
  by the same law and a surface of 154 at `AMBIENT + DIFFUSE` has to land
  under 255, or the sub-stellar point clips and the lit half goes flat. So
  this is not more light, it is light in one place;
- built things painted bone white. Dropping the fill alone moved the median
  from 47 to 42 and nothing else, because `_shade` multiplies a base colour
  and a dark base can never reach white however hard the sun is. The paint was
  the limit. It also draws the line the fiction has always claimed and never
  shown: a quay is built, a hull is grown, and they stop looking like the same
  material.

**The smoothness check was measuring the wrong thing, and had been for as long
as it existed.** It bounded the biggest jump between neighbouring pixels at 18
levels — and `AMBIENT + DIFFUSE·cos θ` changes by 19.6 levels across one pixel
of that disc under the constants the bar was written for. The law was always
steeper than the bar. The renderer passed because seven gradient stops let Qt
interpolate linearly between them and flatten the curve.

The tell, found while chasing it: **more stops made the measured step bigger**,
monotonically — 8.9 levels at seven, 24 at sixty. That is the opposite of a
resolution artefact and it says plainly what is happening. The picture was
smooth because it was wrong.

A facet is a departure from the law, so the check compares with the law now —
the span it covers, and no flat run across the curve — and the gradient is
sampled 48 times, uniformly in *screen radius*, which is what a radial
gradient is parameterised by. Four mutations, four caught, including putting
the fill light back.

`test_cameras` had the same disease in a milder form: it counted pixels above
a brightness threshold, which was a fine proxy for "the target is in frame"
only while the fill lifted everything, and reported 24 on a frame that used to
give 628. It renders each feed twice now, with the target and without, and
counts what changes: the nose loses 1,246 samples and every other camera loses
zero. A stronger claim than the ratio it replaced, and one that does not care
how the scene is lit.

Still to come on this task: turning stations, which are both the other half of
the look and a real docking problem.

## 2026-07-30 — SEEDFALL: showing the autopilot fly (#106)

The computer has flown the ship since it was written and nothing on any screen
said so. A captain watching the conn saw six identical buttons, no sign of
which thruster was firing, and no indication the autopilot was even on.

`conn.apply` records the burn it made — the axis, whether it was the drive or
the clusters, how far the throttle actually opened, and whether the tick was
spent swinging the hull round instead. **What happened, not a fresh ask of the
computer**: asking again would be a forecast, and the two differ every tick.
Both consoles light off that record; the autopilot's modes light too; arming
it from either window arms the one computer, and pressing the running mode
again turns it off, as does an explicit *Autopilot off*.

A thruster fires **opposite** to the way the ship goes, so *Ahead* lights the
**aft** cluster. `data/mounts.RCS_CLUSTERS` has carried each cluster's shove
direction since it was written and no screen had used it — so the game could
say "the forward cluster" and mean the one that slows you down.
`ui/shipdiagram.py` draws the hull with a mark at every mount and a plume on
the lit ones. `render3d.place` had to come out of `draw` for it: a mark
rotated by a second copy of that arithmetic sits *near* the hull rather than
on it, which is the fault this project has hit every time a number was written
twice.

`ui/approach_window.py` is the third view — ship and target together from
outside, zoom, pan and tilt, with the predicted course drawn as a track with
the minutes written on it. The camera orbits the *midpoint of the pair*: the
first version orbited the target, which puts a ship twelve kilometres out in a
corner and leaves most of the window empty. It looked like a mistake because
it was one, and looking at the picture is what said so.

`sim/preview.track` is the prediction, and it is a dry run of the act — a
throwaway twin flown with the real `apply` under the real computer. Checked by
flying the real approach the same distance: 1,746 m predicted, 1,746 m flown.
Exact, because it is the same code.

**The framing check took three goes**, and the two that failed are the
instructive ones. A bounding box cannot tell "centred on the pair" from
"centred on the target" — with the target centred the ship is 111 px off and
both are still inside the frame. Nor can the 2D midpoint: perspective puts the
near object further from centre than the far one, so even correct centring
lands it 20–31 px out against 55 for the fault, and a bar between those is a
bar written to fit rather than to mean something. What is crisp is which
*side* of the centre each object falls on — opposite sides when it is centred
on both, and nothing straddling anything when it is not. Asked at three camera
angles, because one is a coincidence.

Fourteen mutations, fourteen caught.

And the declared-field guard from an earlier cycle caught `fired_share`:
written by `apply` and read by nothing. Wired up rather than deleted, because
it is the number that tells 62% of a drive from 25% — which the computer does
inside four ticks, and which a light with no figure on it cannot say.

## 2026-07-30 — SEEDFALL: berths you can see, and a panel you can fly (#105, stages 3 and 4)

**Stage 3.** Coming alongside was a distance from a point — `range_km <=
ALONGSIDE_KM + radius_km`, where `radius_km` is a bounding sphere. A hull that
crept up on the *far side* of a Fleet Hub, nowhere near a mast, and stopped,
was moored. The structure the window spends the whole approach drawing had
nothing to do with it.

Berth positions now live beside the mesh builders and are the same numbers:
the warn-lit box on a quay's arm is its berth; a hub's four lit masts are four
berths. So a berth is a thing you can see. The reach is a share of the
structure's own size rather than a distance in km — measured, that separates
"at the fitting" from "the far side" by 5× to 13× on a quay, a hub, a holding
and a gate alike.

Three things the measurements forced, each after watching it fail:

- aiming straight at a fitting means flying through whatever is in the way —
  two of eight off-axis approaches ran dry shuffling round a hub — so there is
  an approach corridor: a hold point on the berth's line, clear of the hull;
- handing over on *crossing the corridor radius* left a ship on the wrong side
  trying to crab round the hull, where `safe_rate` allows almost nothing. The
  corridor is a *place* now, and the run in starts from it;
- the berth is chosen freely far out and held once inside. Re-picking every
  tick chases a moving aim; committing at twelve kilometres picks a mast
  before the drift has played out.

**Stage 4.** `ui/flight_window.py`: range, closing **against the rate that is
allowed**, **lateral rate**, which berth and how far off, the gate in the
units the readouts are in, and every pad button labelled with the burn it
gives and an arrow saying whether it takes you toward the berth.

Everything in bold there was found by trying to fly it rather than by looking
at it. Three chronicles hit the structure at 9.2 m/s with nineteen of twenty
tonnes of thruster mass unspent, because nothing on the screen said when to
brake — and `autopilot.safe_rate` is what the computer holds to and had never
been on a screen. And the pad is in the ship's frame while the berth is off
the bow, so a pilot pressing *ahead* flies at the middle of the structure.

Flying by hand also found the real gap in stage 3's own gate: **there are two
roads to "alongside"**, the station-keeping branch and the contact branch, and
I had gated only the first. The panel berthed 477 m from the mast because it
had bumped the hull. A gentle touch away from a fitting is a scrape now.

What it can do, flown: the computer brings the hull to the hold point and a
pilot puts it on the mast in two to six presses, in three chronicles. From
twelve kilometres a six-axis pad genuinely cannot do it — the hold point and
the middle of the structure are 2.6° apart at that range — and that is the
honest division of labour rather than a shortcoming.

**And two of my own checks were not watching what they claimed.** The
guidance arrows were lost from the button labels at some point and nothing
noticed, because every check called `moorings.steer` directly instead of
reading the pad; and a mutation that doubled the figure printed on a button
passed, because the check compared the *quote* against the burn and never the
label. The promise is the thing printed on the button. Both read the buttons
now.

Fourteen mutations across the two stages, fourteen caught.

**And an existing check caught a regression I had introduced.** "More thrust
is never worse" failed: three hulls flew *worse* for a better engine — a SPORE
on a plasma drive recovered 80 m/s of drift and the same hull on a stronger
fusion torch only 5. The cause was the corridor. `safe_rate` measured the room
to the *structure*, so a powerful engine drove straight through the hold point
and then chased it back. It measures the room to whichever comes first now,
the structure or the waypoint, and the table is monotone again: 80→160 across
the drives on both hulls.

The duplicate-key trap caught me too, in the same table it caught me in
earlier this month: `berths3d` was already in the tripwire's fast paths and I
added it again. A dict literal keeps the last silently; the harness guard does
not.

## 2026-07-30 — SEEDFALL: the thing you hit is off station afterwards (#105, stage 2)

Stage one could only *say* what a collision did to the other body. The sector
had nowhere to put it: an anchorage's position is its body's, worked out from
the calendar every time it is asked, and a traffic hull's is interpolated
between two bodies. Neither has a place to hold "and then somebody hit it".

`sim/knock.py` is that place and `track.at` adds it, so a shoved station is
off station everywhere — the plot, an approach, the readiness board's ranges,
every forecast — because they all read the same function. Two carriers: a
manned berth or a crewed hull arrests the drift and works back
(`x(t) = v·t·e^(−t/τ)`), a derelict or a gate simply goes. Flown: 30 m/s into
a Fleet Hub leaves it 648 km off station a fortnight later and home inside
three months.

The bearing is drawn from the seed rather than derived from the approach, and
the module says why: the conn's frame carries no system orientation, because
an anchorage and its body share a position in the flight model. There is no
bearing at the moment of contact to take. Writing one that looked derived
would have been worse than admitting it.

**The mutation sweep found two faults, both in my own checks.**

The first is the worst kind: an **unbounded loop**. My settle check advanced
the calendar while the drift was still measurable — and the mutation that
removes the recovery leaves it growing for ever, so the check ran until the
harness was killed. It hung two runs before I understood what I was looking
at. A check that hangs is worse than one that fails, because a failure says
what is wrong. Bounded now, and the bound is the claim: a manned berth is
home inside a year.

The second: `KEEPING_DAYS` was **unpinned**. Every assertion in that check
asked about the *shape* of the curve — peaks, then comes home, derelict
overtakes it — and every one of those survives a rescale of the time
constant. `x(t) = v·t·e^(−t/τ)` peaks at `t = τ`, so the peak is where the
constant lives: found by walking the curve and checked against written
figures, a 2 m/s shove peaks on day 12 at 763 km. A 1.5× change is caught now.

Two process lessons, both about mutation sweeps.

**Killing a sweep mid-run loses the file.** It edits source in place, and it
lost a `knock.py` that was not yet committed and therefore not recoverable
from git. Snapshot first.

**A same-length edit can outlive its own restore.** `KEEPING_DAYS = 12.0` and
`KEEPING_DAYS = 48.0` are the same number of bytes, and Python validates a
`.pyc` on (mtime, size) — so the cached bytecode of the mutant survived the
restore and was imported by the *next* run. That is what the phantom "MISSED"
was, and then a full suite failing on intact source. `tests/tripwire.py` has
run with `-B` and `PYTHONDONTWRITEBYTECODE=1` since it was written, and says
why in a comment I had read and not applied to my own scripts. Every ad-hoc
sweep gets the same treatment now.

Eight of eight caught.
