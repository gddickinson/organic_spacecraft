# IMPROVEMENTS.md — the live backlog

What could be better, honestly sized, kept current. The done column stays,
because a list that forgets what it cost is a list that re-estimates badly.
History and reasoning live in [`notes/`](notes/README.md) and
`SESSION_LOG.md`; this file is only the state of play.

## Where the done list went

Every pass that closed something is kept, unchanged, under
[`improvements/`](improvements/): the done column stays, split so no file
passes 500 lines.

- [done-01.md](improvements/done-01.md) — Done — the flight-deck campaign; Done — the third pass; Done — the fourth pass; Done — the fifth pass; Done — the sixth pass; Done — the eighth pass; Done — the ninth pass; Done — the tenth pass
- [done-02.md](improvements/done-02.md) — Done — the eleventh pass; Done — the twelfth pass; Done — the thirteenth pass; Done — the fourteenth pass; Done — the fifteenth pass; Done — the sixteenth pass; Done — the seventeenth pass
- [done-03.md](improvements/done-03.md) — Done — the nineteenth pass; Closed by the nineteenth pass — the 2026-08-05 e; Done — the eighteenth pass; Closed by the eighteenth pass — the governance s

## Closed by the 2026-09 review and its ten innovations

The whole-project review (`../reviews/2026-09-17/`, with `STATUS.md` mapping
each item to its fix) closed these from the lists below:

- **No sound** — a synthesised soundscape, about thirty cues made at first
  run behind a no-op façade (`ui/synth`, `ui/audio`, `ui/soundmap`; `audio`,
  `soundmap`).
- **Lawlessness had one moment to bite** — beside the jump exit,
  `piracy.lawlessness` is now read by the hunt board (where raiders work) and
  by every freight line's route risk, and two Assembly resolutions move it.
- **One save slot** — named slots and a chronicle picker (`core/slots.py`).
- **The header clipped the ship name** — `widgets.Elided`.
- **Forced-answer screens locked navigation** for envoys — "Leave it for
  now" sets one aside until its day (`approach.set_aside`). A power's demand
  and a legacy situation still hold the window (see below).
- **Nine length debts** — every file is under 500 lines, and
  `tests/test_length.ALLOWED` is empty.
- **Dead imports** — the tree-wide ruff sweep, and the `exports` suite, which
  catches a sweep that removes a re-export a caller reads.
- **Let the captain hide too** — `sim/running_dark.py`: fewer meetings, a
  first volley, suspicion where the law is; a shroud deepens it.

## Closed on 2026-09-19 — a contact you can see

The flight model knew everything about a collision and drew none of it:
measured, a 55 m/s arrival at a Fleet Hub cost 1,134 of a 336-point hull and
moved nothing on the screen but a line of nine-point italic type — in a
window whose main camera was not even pointing at the structure.

- **`sim/shock.py`** — the one door between the fact and the picture. It
  reads a resolved approach (or a turn of an engagement) and hands back what
  passed between the two: kind, bearing, both sides' damage, the shove, the
  fitting that was missed, the words. Qt-free; every figure is the flight's.
- **`ui/effects.py` / `effect_marks.py` / `effect_paint.py` /
  `effect_clock.py`** — the timeline, the marks, the composition, and a
  second 40 ms timer, because a collision *stops* the flight clock and the
  first frame of an explosion is not an explosion.
- Ten kinds of contact are drawn, plus the volley you take in combat; the
  conn turns to the camera that saw it (`viewport.best_view`); the outside
  view draws what the *other* side took. Two new sound cues: `impact`,
  `graze`. New suite: `shock`, twelve checks.

## Open — Afoot, begun 2026-09-21

The walking layer landed (`sim/afoot*.py`, `ui/afoot_*.py`; design in
`../reviews/2026-09-21/afoot.md`): deck plans derived from every kind of
place and hull, a party of up to four, Traveller's personal combat on
squares, talk through the counters that already exist, incidents from state
the game already keeps, and endings that bank through the existing doors.
Everything the first list named is closed; item 19 is what is left:

1. ~~**Counsel and the tutorial do not know it exists.**~~ Landed
   2026-09-22: counsel offers the dead hull adrift here and a word with the
   officer nobody has stopped at in months (`counsel_doors.afoot`, acted by
   `counsel._walk`); the Academy has *On your own two feet* — walk, talk,
   shoot back (`data/lessons`, `tutorial_watch`).
2. ~~**No sound.**~~ Landed on the day: a shot sounds its weapon's volley, a
   hit on one of yours the hit, one of yours going down the breach
   (`ui/soundmap.afoot`), all existing cues.
3. ~~**No bridge verbs.**~~ Landed on the day: `bridge/afoot.py` — sites,
   begin, look (with a text map), move, attack (and burst), suppress,
   throw, act, talk, end turn, surrender — and every other acting verb is
   refused while a party is out.
4. ~~**A clinic does not know about kept wounds.**~~ Landed on the day: a
   `care` treatment closes the kept wound, and its quote says so.
5. ~~**Renown has no milestones afoot.**~~ Landed 2026-09-22: five rungs
   (`data/milestones`, topic "afoot") read off `afoot_ends.progress` —
   walks, prizes boarded, wrecks cleared, kinds of place, nests burned.
6. ~~**Holdings are quiet.**~~ Landed 2026-09-22: your own works can be
   failing, on strike or sabotaged (`sim/afoot_holdings.py`); set right by
   hand they run a quarter better for a month, walked away from a quarter
   worse, and the colony tick reads it (`afoot_holdings.factor`).
7. ~~**The captain's record is thin.**~~ Landed 2026-09-22: the captain's
   terms are played out by `sim/lifepath` like any officer's, from the
   origin's service and the lineage's prime, stable for the chronicle.
8. ~~**Combat is single shots.**~~ Landed 2026-09-22 (`sim/afoot_fire.py`):
   a burst adds a gun's Auto; suppressing fire pins the target and whoever
   is beside them; frag, stun and smoke grenades, bought at the counters
   under the law's gate, thrown with Athletics, off by a square on a miss.
9. ~~**The xeno hulk and the Kith hall are the least played.**~~ Landed
   2026-09-22: a relic gives itself up in three stages (the second stands
   its sentries down); the Kith sing a phrase to be answered, and an elder
   sings a domain's song of passage (`sim/afoot_kith.py`), both teaching the
   lexicon.
10. ~~**Incidents to add.**~~ Landed 2026-09-22 (`sim/afoot_trouble.py`): a
    quarrel between officers whose convictions collide, a shakedown and a
    brawl where the law is thin — each met head on or let be, and it tells.
11. ~~**Every plan was the same corridor of boxes.**~~ Landed the same day:
    plans in the shape of the thing (`sim/afoot_plans.py` and its
    blueprints) — a hull sliced through its own silhouette and holding its
    whole working program, a quay's can and arm and mast, a Fleet Hub's
    spine and rings, a drum's town, a tower's floors, a dome's ground, a
    ring round a hub, a mine dug into its rock, modules on a keel, sheds on
    breathable or airless ground. `tests/test_afoot_shapes.py` holds it.
12. ~~**Establishments are static, a base has no berth, yards build only
    their own.**~~ Fifteen kinds landed on 2026-09-21; closed 2026-09-22:
    **a stake** (a tenth of a house, paid monthly from its takings, a
    statement each quarter by despatch); **traffic** bound for the houses,
    which ties up at *their* berths and never fills a quay's; the quay's
    **gossip** naming them; **a base's pad** — its landing field's berth in
    orbit (`anchorage` kind `field`, a silhouette of its own), flown to,
    hailed, "Go down"; a sixteenth kind, **the breakers' yard**, drawn only
    where a dead hull is adrift, which wakes a derelict REVENANT (never lays
    down an ANTIPHON) and refits anything; and **a nursery refits the grown
    and hybrid hulls it grows**.
13. ~~**The play-test's leftovers.**~~ Landed 2026-09-22: voice lines in
    the first person and rotated; the hint bar and head elide; the latest
    three lines at the top of the column; two-letter party tokens; room
    names that never print across each other; the start page ticks what is
    chosen; somebody down in hand gets a panel of their own.
14. ~~**No system is ever in the "reaches".**~~ Not a defect: a fresh
    sector is all Verge by design, and a deep region's systems take its id
    when it is relit (`world/regions.py`) — measured, a relit Cradle's
    fourteen systems carry two xeno hulks. The Bloom's pool follows its
    spread (`system.bloom` over 0.05), three systems at the start.
15. ~~**Nothing weighs anything.**~~ Landed 2026-09-22: every deck has a
    gravity (`Deck.g`) — hulls and quays weightless, a Habitat Girdle's
    berths 0.4 g, ring levels spun at 0.8 g and drawn as unrolled strips
    whose ends join (`sim/afoot_ringplan.py`), a drum's floor 1 g, the
    ground its world's own. Weightless, the untrained go hand over hand,
    shoot unbraced and are set drifting by a gun's kick; Zero-G skill or
    magnetic boots put it right; heavy worlds slow everybody
    (`tests/test_afoot_weight.py`). From play, the same day: a walk round a
    Fleet Hub ring stopped at the strip's ends — a step off either end was
    refused and the screen's camera stopped at them. Now everything on a
    ring's level is asked the short way round (`afoot_map.apart`, `span`,
    `unroll`: steps, paths, sight, reach, cover, a grenade's burst), and the
    canvas turns the strip under whoever is in hand so it has no ends
    (`AfootCanvas.roll`).

16. ~~**Near the Fleet Hub, not docked, and walking in anyway.**~~ From
    play, 2026-09-22: a chronicle opened with the hull 7,698 km off the Hub
    on the flight deck — "in orbit of the world" was read both as *near*
    and as *inside* — while its doors stood open. Now two facts
    (`sim/crossing.py`): **made fast** (`Game.berth`: the hull at a berth,
    0.6 km off its centre; a chronicle starts that way at its home quay;
    the harbour's pilot or a conn that ends alongside makes it so; moving
    casts off) and **across** (`Game.ashore`): by **the ship's boat** (a
    hull of crew six or more; a boat bay aboard), **their shuttle** (a fare
    a head by amenity; your own holdings' free), or **suits on a line**
    (within 2 km of something in orbit; a vacc suit for whoever breathes).
    Every Concourse door that takes money, and every walk, asks it; the
    Concourse and the Afoot start page offer the ways. Cargo and yard
    business still go by lighter from orbit. `tests/test_crossing.py`.
17. ~~**The flight computer cannot bring a hull alongside a free port's
    arm.**~~ Closed 2026-09-22. The corridor leg was a straight line to a
    hold point out on the berth's line, whatever lay between; a Fleet Hub's
    masts sit on its pole, so that line seldom crossed anything, but a free
    port's one arm points sideways and an approach from the other side flew
    through the station. `moorings_steer.around` goes round: at the hold
    point's distance, turned from the hull's bearing toward it by the
    tangent angle, re-asked every tick, clear of the core by
    `bays.CLEARANCE` (now one constant for bays and berths alike). Twelve
    bearings each: a Grand 8 → 12 alongside, a breakers' yard 9 → 12, a slip
    10 → 11; over every berth in thirteen sectors, five collisions → none
    and the mean mass per approach 1.55 → 1.54 t.
18. ~~**Two approaches the computer still cannot fly.**~~ Closed
    2026-09-22, and the question widened to *every* docking variation: each
    of the 25 shapes a berth is drawn as, from twelve bearings and from
    above and below, by six hulls from a 26 m SPORE to a 990 m LEVIATHAN,
    with the harbour's boats and without, arriving stopped, drifting 6 m/s
    across, and hot at 18 m/s. 12,600 approaches measured (the harness is
    `tests/test_berths.py`'s shape, run wide). **957 failures → 19**, and
    the mean reaction mass per approach 1.57 t → 1.16 t. What was wrong:
    - **the braking law measured room to the bounding sphere**, not the
      solid core `sim/outcome` tests contact against, so a bay left a hull
      9 m of room at its own mouth, the rate came out under the thrusters'
      deadband, and the computer stopped asking (`autopilot.safe_rate`);
    - **inside the stop distance it read the room to the aim** — an aim
      across the structure is a long way off, so it accelerated beside the
      skin (a slip, 1.5 m/s, 284 m from the cradle);
    - **the way round was a quarter-turn step**, which chattered against
      "straight in" and dragged a hand pilot in and out for two thousand
      presses; it is now the smallest turn that clears the core, floored
      near the skin and fading by `ROUND_FADE` times it;
    - **the lead was capped at a quarter turn**, so a hull that could not
      keep up chased a berth running away round an arcology (174 t, a day
      and a half); it is an intercept now, fed back twice;
    - **the boats towed into a bay** and walked a hull in and out for ever
      (400 t, 314 hours at a gestation shell), and **kept a line on a hull
      under power**, cancelling her way every step so she paid to make it
      again (1.55 t against 1.03 t flying herself);
    - **nothing asked whether a hull fitted its berth**: a 990 m LEVIATHAN
      was cleared for a 672 m slip and a 192 m gestation mouth.
19. **Nineteen approaches in seven thousand still end badly**, all at awkward
    angles onto small structures and none of them tug-dependent: a base's
    pad approached from straight overhead (3 hulls), a slip's and a
    drydock's cradles from one bearing of twelve (4), and a STACK arcology
    from above or behind for a hull with no boats to call on (5, the rest
    drift). Worth another pass at the corridor geometry for a berth that
    sits under the structure's own shoulder.

## Open — small craft, begun 2026-09-22

Asked for: single-seat fighters, launched off a carrier or a station, flown
from their own screen, armed, and good for scouting and transport as well;
one aboard the ship from the first day, cradled outside with a way through
from inside. Landed (`data/craft.py`, `sim/craft.py`, `ui/craft_window.py`,
`ui/craft_panel.py`, suite `craft`): four classes; a cradle deck on the hull
plan with the craft's name on it; a Pilot ticket as the qualification (the
captain and — new — the navigator hold one); a sortie flown as a `sim/conn`
flight of the craft's own numbers, with the cockpit window's stick, drive,
computer modes and instruments; firing runs, an hour's scouting for real
survey data, and the craft as the ship's boat for a crossing.

**Closed 2026-09-22 — a craft joins the battle** (`sim/craft_battle.py`,
suite `craftbattle`, and a check in `craftui`). *Launch the craft* is an
order on the battle screen: she drops off the cradle in the middle of an
engagement and makes a run a turn on her own account, beside the consorts
(`combat._run_company`). A run is her guns' dice plus the pilot's Pilot
rating, soaked by the enemy's armour with the same 15% floor a shell gets
and landed through `sim/damage`, so it strips layers and breaches hulls like
anything else that hits. They answer with close-in fire — two dice and two
more for every mount still on them — and her armour is all that is between
that and the pilot; a dazzled hull shoots at where she was, which is what
the flash organ is suddenly worth. *Call her in* is the other half, and the
decision the whole thing is for. Shot down, the craft is gone for good and
the pilot comes home with a wound rather than in a box.

Measured over sixteen engagements: against a one-gun patrol she takes 48% off
the enemy (6% without her), makes ten runs a fight and was never lost in
eight; against a Concordat warship, 35% against 3%, and she was lost six
times in eight. What she is sent at is the gamble.

It cost a real fix underneath: **the engagement lived on the window**, so
`sim/craft.can_launch`'s refusal to launch a free-flight sortie mid-battle
had never once fired, and `ui/gunnery_view` read a `game.battle` that did not
exist — an AttributeError waiting for somebody to man a gun in a real fight.
`Game.battle` is a declared transient field now and `MainWindow.battle` is a
property onto it. `core/state.py` reached five hundred lines again in the
doing, and opening a chronicle came out into `core/state_begin.py` along the
seam `core/loading.py` came off.

**Closed 2026-09-22 — the hangar deck** (`sim/hangar.py`, `ui/craft_yard.py`,
suite `hangar`, a check in `craftui`). The Shipyard screen has a **Cradles**
tab. A cradle is fitted rather than assumed: `Ship.cradles` says how many are
on her and `hangar.most` how many a hull that size can work — one per thirty
hands, four at the most, and none at all on anything too small to crew a
ship's boat. A yard cuts another for ₡9,000 and seven days.

A craft is laid down where its family's hulls are, asked of
`shipyard.can_build_here` rather than a second copy of that rule going stale,
and it costs the class's own credits, matter and days (₡3,000 a day, six at
the least). **Mending was the thing that was missing**: a fighter that came
home at half stayed at half for good. A yard puts hull back by the point (₡45
and 0.05 t a point, forty points a day), and a *grown* craft knits herself
whole in her cradle off the hold's biomass at 1.5 points a day — which is
what grown is for, and the reason to buy a WASP over a SHRIKE. Selling pays
`data/craft.SALVAGE` scaled by condition, a constant that until now nothing
read; measured, every class is worth less back than it cost, whole or
wrecked, because a yard that pays what it charges is a money pump
(`shipyard.scrap_value` learned that at 146,470 credits a cycle).

**Closed 2026-09-22 — the seats and the hold are spent** (`sim/crossing.py`,
`sim/afoot_ends.py`, two checks in `crossing`). Both numbers in the class
table were decoration. Now:

- **Seats.** A boat takes `seats - 1` people across besides whoever is
  flying her — a DORY's three behind the pilot, a WASP's one at a pinch —
  and a bigger party is refused in the craft's own words ("WASP takes 1
  across besides the pilot; 2 are going"), which leaves the shuttle and the
  line as the ways a landing party of four actually gets anywhere.
- **The hold, on the way back.** A walk's haul went into the ship's hold
  *whole*, however the party had reached the place: twelve tonnes carried
  home across two kilometres of vacuum by three people on a line. The way
  out is the way back (`crossing.lift_t`, and `Walk.way` remembers it):
  made fast alongside there is no limit, a boat makes three trips of her own
  hold, a shuttle takes two tonnes as freight, and suits carry 0.2 t a head.
  What will not fit is left where it lay, and the report says so.

Measured on a twelve-tonne haul: 12 t home made fast, 1.2 t by a WASP,
0.2 t on a line — which is what makes a DORY (9 t over three trips) worth
buying from the hangar deck above. What is still not done: a craft running
freight between two places on its own account, with nobody aboard the hull
involved at all.

**Closed 2026-09-22 — somebody pays for the seat, and theirs fly too**
(`sim/craft.at_stations`, `sim/craft_battle`, two checks in `craftbattle`).
`craft.pilots` had always said "whoever goes is off their station until she
is back" and nothing made it so: `recompute` fed `ship.stats` the whole
officer list, so a navigator could fly a sortie and go on navigating.
`craft.at_stations` is the one door now, and the hull's own numbers move
while they are away — measured, the navigator out costs the starting NAVIS
its speed and its jump. A captain in a cockpit cannot take a station in a
battle either (`craft_battle.on_the_bridge`), which is why a launch left to
itself sends the best ticket that is *not* the captain's.

And the other side of it: a hull with the hands to work a cradle deck
(40 crew) carries up to three launches of its own, says so when the
engagement opens, and runs them in at you every turn wherever the range
track stands. Your close-in fire is what answers — a mount that bears takes
one apart, and the loss costs them their nerve. Measured over eight
engagements against Concordat warships: their flight costs a starting hull
about four points of its integrity and is usually gone in three or four
turns, which is a threat to answer rather than a fight-decider.

**The small-craft list is closed.** What a later cycle might still want: a
craft running freight between two places on its own account, and a flight of
more than one of yours at a time.

## Open — down to the ground, begun 2026-09-22

Asked for: attack craft that can land on planets; larger hulls that mostly
cannot, unless built for it; a **lander** on the starting ship beside the
fighter, fitted for extended stays — communications back to the hull in
orbit, supplies, and vehicles for exploring a surface; more ships of that
kind; a variety of surface vehicles for different worlds; habitations for
camps; and planets to explore as **2D maps** — undeveloped, part-developed
and developed — carrying everything from unexplored ground and abandoned
works to mining operations, outposts, villages, towns and cities. All of it
dovetailing with what is here.

A great deal of it already is here, unread or unowned, which is what makes
this a programme rather than a new game:

- `sim/landing.py` did the arithmetic that makes a lander necessary and
  wrote it down — **a starship cannot land on a world** — and named the
  lander as the reason an expedition works at all. Nobody owned one.
- `sim/expedition.py` is a 7×7 landing zone with a fixed pad square, a
  supply clock and a `rover: int` gauge; `data/expedition.py` holds the
  game's **only terrain vocabulary** (nine kinds, each with a day's cost
  and a chance of a hazard) and a table of features to find.
- `data/surfaces.py` already gives every body deterministic surface
  features at a longitude and a latitude, and **nothing in `sim/` reads
  them**; `sim/profile.py` derives a Traveller profile per body, the same
  answer every time it is asked.
- `data/settlements.py` puts NPC settlements on bodies (four facts, flat,
  900 heads apiece) and `data/establishments.py` six kinds of ground base;
  `sim/afoot_groundplan.settlement` already draws a town with streets, a
  pad and an airless variant, and `sim/afoot_map` is a complete tile engine
  with sight, fog, reach and pathing.

The order, each piece playable on its own:

1. ~~**Landing is a rule, and the lander is a thing.**~~ **Closed
   2026-09-22** (`data/craft.py`, `sim/descent.py`, suite `descent`). A
   class says whether it `lands`, how many `days` it keeps a party alive,
   how many `bays` of vehicles it carries and how far its mast reaches
   (`link_km`); three landers join the four small craft — the grown
   **ISOPOD**, the Yards' **PINNACE**, and the **CATAPHRACT** built for the
   gravity wells nothing else leaves again. Where a craft may set down is
   her own thrust against the world's own pull with a reserve for lifting
   off loaded (`LIFT_RESERVE`), which is the ship's own landing arithmetic
   applied one scale down: a DORY to 0.89 g, a WASP to 1.78, a CATAPHRACT
   to 2.52. The starting hull sails with **two cradles full** — the fighter
   and a lander — and `sim/fieldwork.launch_expedition`, which used to
   conjure a lander out of prose, now needs a real one aboard that can lift
   off this world, takes the party from her seats and the supplies from her
   hold, sets her state to `down` while they are on the ground (not the
   ship's boat, not something a yard can reach) and brings her up with
   them.
2. ~~**Vehicles.**~~ **Closed 2026-09-22** (`data/vehicles.py`,
   `sim/vehicles.py`, suite `vehicles`). `Expedition.rover` was a number
   from nought to ten that bought one day off a step while it stayed above
   eight — no class, no mass, no seats, and no opinion about the nine
   terrains a party walks over, so a dune sea and a scarp were the same
   problem to it. Five classes now: the **ROVER** a captain starts with,
   the **CRAWLER** that will go up a scarp at walking pace, the
   ground-effect **SKIFF**, the fan-lift **KITE** that ignores the ground
   entirely, and the grown six-legged **STRIDER**. Each has ground it is
   made for (a day off the step) and ground it refuses (a day on, because
   the party leaves it and walks), a mass that comes out of the lander's
   hold *against the supplies*, and a build that decides how much of a
   hazard's toll it takes. A lift fan is dead weight where the profile says
   there is no air. They are built, mended by the point and sold back at a
   loss at the same counter craft are (`sim/hangar.py`'s garage), they wear
   and are kept between landings, and a party that walks out of the field
   leaves the machine where it stopped. **A party with nothing still
   walks** — the state the game shipped in — and `data/careers.SKILLS`'
   *drive* entry ("anything with wheels or tracks on a surface"), written
   with the lifepath and read by nothing since, has its first reader.
3. ~~**Camps.**~~ **Closed 2026-09-22** (`data/camps.py`, `sim/camps.py`,
   suite `camps`). The expedition's only building was the lander and the
   only place its supply clock could be refilled was orbit, so every
   landing was one walk out and one walk back and the shape of a survey was
   a star. A camp is the second building: BIVOUAC, FIELD CAMP, FIELD
   STATION and the grown BOLE, each riding down in the lander's hold *after*
   the supplies and the vehicle. It **holds days** — supply left in it is
   not carried, and a party that walks back into its own camp picks them up
   — it **sits out weather for nothing** (the day goes, the stores do not),
   and **a day's rest inside is worth more** than a day on regolith. What is
   still in it when they lift off is left. Bought and sold at the yard's
   garage (`sim/garage.py`, split off `sim/hangar.py` at five hundred
   lines: a cradle holds what flies out, a hold holds what goes down).
4. **The planet map.** `sim/worldmap.py`: a per-body 2D map, **derived and
   never stored**, seeded `RNG(f"{seed}:world:{system}:{body}")` the way
   every other derived thing here is. Elevation and moisture from a small
   value-noise field, terrain by a Whittaker-style table onto the nine
   terrains already written, keyed to the body's gravity, temperature and
   biome and to the profile's atmosphere and hydrographics. The
   expedition's 7×7 zone becomes one cell of it, so the game that already
   exists is what happens when you stop somewhere.
5. **What is on it.** `data/developments.py` and `sim/worldsites.py`: the
   taxonomy the request names — unexplored ground, abandoned works, ruins,
   mining operations, outposts, villages, towns, cities — placed by a
   suitability score off the map and the profile, and grown and decayed by
   a short history pass so a mine that runs dry leaves an abandoned mine
   and a town that loses its reason leaves a named ruin, with a line in the
   chronicle. Every one resolves to a `Place` → `afoot_sites.Site` → the
   ground plan already written, so walking into one needs no new plumbing.
6. **The screen.** `ui/worldmap_view.py`: the map as an image with marks on
   it — `ui/expedition_view.ZoneMap` for picking a cell, `ui/afoot_canvas`
   for fog and reach — with the lander's pad where she set down, the
   vehicle's range as a ring, and the sites anybody has seen.
7. **Orbit, and seeing it happen.** Asked for while stage three was
   landing: *a way to navigate the ship into orbit around a world, launch
   the lander to the surface from there, and see it out of the viewports —
   from the lander (which should see the mother ship and whatever else is
   about) and from the ship (which should see the lander leave and come
   back).* The pieces exist and have never been joined: `sim/flight`
   holds a hull at a body, `sim/conn` flies it, `sim/berthing` and
   `sim/moorings` bring it alongside a structure, `ui/viewport.py` draws
   what is out there from a `Conn`, and `sim/craft.launch` already builds
   the lander's own `Conn` so the cockpit window has instruments. What is
   missing is **orbit as a state you can be in and fly out of** (a hold at
   a body that a descent departs from), a **descent flown rather than
   charged** (the three days `fieldwork` takes are a number, not a
   manoeuvre), and **each hull in the other's sky**: a contact for the
   lander seen from the ship and for the ship seen from the lander, so both
   viewports draw the thing that is actually happening.

Two of the captain's own projects were read for ideas rather than code:
a world simulator (seeded value noise, a Whittaker biome table, a
settlement history that founds, grows, depletes and ruins, and an A* road
pass) and a building generator (an authored table of what rooms a building
of a kind has, and a grid-with-fractions layout schema). Ideas ported,
nothing copied.

## Open — the Traveller programme, begun 2026-09-20

The world profile landed (`data/uwp.py`, `sim/profile.py`): eight
characteristics per world, derived from the sector, with trade
classifications, bases and a travel advisory. It is the spine the rest of
*Traveller*'s breadth hangs off, in the order that gets the most out of what
SEEDFALL already has:

1. **Speculative trade** — the classifications moving prices, with a Broker
   check on the lot. *Built and backed out once already*: multiplying the
   counter's quotes re-balances the whole economy, breaking the freight
   desk's load clamp and the careful captain's five-year ending. It needs a
   balance pass of its own — re-pin `renown`, `chronicle`, `freight`,
   `freightlines` and `wharfage` against the new curve, and probably a
   smaller shift than the table's first draft.
2. ~~**A 2d6 grammar**~~ — landed as `sim/checks.py`: six characteristics, a
   seven-rung difficulty ladder, −3 untrained, and the Effect. **What is left
   is the bringing-across**: every act that still resolves on an ad-hoc curve
   (survey, dig, repair, haggling, the docking approach) could be re-stated
   in the grammar, one at a time, each with its own re-pinning.
3. ~~**Life-path beginnings**~~ — landed as `data/careers.py` and
   `sim/lifepath.py`, derived per officer. **What is left is the captain**:
   `ui/beginning_view.py` still asks who you are with three choices, where
   Traveller would have you play the terms out and take what they give you.
4. **Patrons and tickets** — work that comes from a person, with a chance the
   job is not what it was said to be. The contract board is the shape; what
   is missing is the person and the lie.
5. **The monthly bill** — a hull's mortgage, maintenance and life support.
   Traveller's whole economy is driven by a payment falling due; SEEDFALL's
   purse has no such pressure.
6. **Law level bites** — the profile has the digit; wire it to what the port
   will find in the hold (`sim/customs`, `sim/contraband`).

### Left over from the crew screen (2026-09-20)

- **A station cannot be reassigned.** An officer holds the station they were
  hired into for life. Traveller's answer is that the person is the skills
  and the post is a chair; SEEDFALL's bonuses are keyed to `officer.role`,
  so moving somebody is a balance change, not a button.
- **Hiring is still the quay's.** The berth board stays on the Port screen
  because who is looking for work is a fact about the port. The Crew screen
  has a door to it, which is right, but a captain planning a hire has to read
  the hole on one screen and fill it on another.
- **`lifespan.age_of` invents and stores an age on the first ask.** Fixed
  where it bit (`sim/lifepath.of` resolves the age itself now), but the shape
  is still there: a *read* that writes. Anything else deriving from
  `officer.age` has the same order-dependence waiting for it.

### Left over from the concourse (2026-09-21, mostly closed)

Closed the same day: a hull is a place (`data/venues_aboard.py`), anagathics
bill by the month (`sim/clinic.tick`), and hiring halls hire
(`crew.pool_here`). What is left:

- **The derived-silhouette renderer is out of vocabulary.** Three habitat
  classes were refused by `test_works3d` because everything with a crowd in
  it comes out a ring, and a ring dominates the outline. Adding a fifth
  ring-shaped class will hit the same wall. The fix is either more parts or
  a ring whose radius varies with what it carries.
- **The new careers never come up as a *first* career** for a bridge
  station whose `BY_STATION` list does not name them, which is most of
  them. That is correct for a navigator and wrong for a purser the game
  does not have.
- **A face is only ever drawn still.** The portraits carry mood, years and
  fitted hardware and nothing about what somebody is *doing*: a watch
  ashore, a surgery under way, a course running. The concourse scene has the
  crowd; the people on the crew screen are passport photographs.
- **A ship that is a clinic never needs a port**, which is now true and not
  yet balanced. A LAZARET with a vat deck can graft at sea; nothing charges
  it more for doing so than a hospital ashore would.

### Left over from the substrates (2026-09-21)

- **Robots are still two systems.** `sim/robots.py` has machines with hull
  numbers that work a holding, and `data/lineages.frame` is a machine that
  stands a watch, and neither knows the other exists. A Verger that earned
  its way onto a bridge would be the obvious story and is not wired.
- **A mind has no second body.** The fiction says it wears whatever body
  the watch needs; mechanically it is an officer like any other. Instancing
  one into two stations, or losing the body and not the person, is the
  thing that would make the substrate mean something.
- **Nobody refuses to serve.** The gates have views about the crew; the
  *crew* has a view only through the purist conviction. An officer who will
  not sign to a hull carrying a frame would close the loop.
- **The vatborn have no story.** They are a lifespan and a price. The
  specification somebody paid for, and who paid it, is a life-path career
  waiting to be written.

## Open — the 2026-08-04 review: the systems layers

A four-agent review (combat, economy, strategic layer, player experience)
plus a live play-through over the bridge, looking everywhere the flight-deck
campaigns did not. The verdict: the flight deck holds and the systems layers
do not — not one item below was on this list before, and every number was
measured by driving the sim, not by reading it. In rough value order.
(The worst of it — the session-brick, the data loss, the same-counter
arbitrage, the contract exploits, the dead board, the unreachable Bloom,
the flash organ, the diplomacy exploits — was fixed the same day; see the
tenth pass above.)

*(Most of this list was closed by the nineteenth pass above — the scrap
exploit, the raw prices, the contraband market, the promotion arithmetic,
the robots, SOL-FORGE, the Cartel ledger, threat scaling, surrender/prize,
`nonlethal`, the brace button, the Charter's warships, the comms UI and the
keyboard sweep. What follows is only what remains open.)*

- **Mining is the worst-paid thing in the game** at 129 cr/day median, and
  it is the one with hull wear and mishap risk. Now that colonies have a
  ceiling (eleventh pass) the comparison is fairer, but a rig should still
  beat sitting still.
- No window geometry persistence; flat buttons' border contrast is not yet
  measured against WCAG's 3:1 (it was 2.02:1 before the theme change);
  `chloro`/`osteo` luminance-identical for a deuteranope; 8–9 px type with
  no scale setting; the Bloom absent from the HUD (a burden chip off
  `threat.harbours_left`); the yard's "After refit" numbers at the default
  window size, unchecked since the `fit` work; a power's demand and a legacy
  situation still lock navigation, where an envoy can now be set aside.
- `comms.tick` itself still watches one fact (the standing band). The board
  is no longer quiet — the Assembly's sittings, the sky's forecasts and the
  nova, rivals, the Kith, officer arcs, colony losses and epoch turns all
  write to it from their own sites — but wars, port closures and harbour
  losses are still only log lines (`sim/threat.py`).

## Open — from the final play-test (2026-09-18)

An independent play-test (first hour over the bridge, three strategies for
two years each) found eleven things. Nine were fixed that day, with part of
the tenth: envoy money through the purses, the tests' save tidy-up, the
sky-data quote, the berth lesson, the chart and Helm layouts, the Academy,
the Hollow's reach wording, signing on crew, raw `**` in Help, "A The
Tessellate site", and raw floats in the Port. Still open:

- ~~**Where can you trade from?**~~ Closed 2026-09-22 (`sim/quayside.py`,
  suite `quayside`). One rule, and it is a ladder rather than a gate:
  **alongside the quay the cranes are theirs and cost nothing; from
  anywhere else in the system the goods are lightered, and the gap is the
  price** — your own boat carries what she lifts in a visit for nothing and
  only within her own range, and the port's lighters take the rest by the
  tonne at a rate that rises with the distance. Measured on 100 tonnes: 692
  credits in orbit off the quay, 1,400 from an AU, 6,300 from the seven the
  play-test sold survey data at. Handing over a bench of survey sets is a
  rule rather than a price — somebody has to be at the counter — and that
  was the play-test's own example. The board names the rate, the contract
  card prices the sourcing with it in (it under-quoted by the whole of it),
  the Port screen says where you are dealing from, and **"Let the
  harbourmaster bring you in" now docks**: it is `crossing.cross(..., "dock")`,
  the same door the walking layer uses, and the first officer offers it as
  *Come alongside* when there is business at a quay you are not made fast
  to. Re-measured on the reference captain (`tests/careful_captain`): it
  reaches the Genesis ending on day 1,415 of five years, paying 250 credits
  of lighterage in the whole career and dealing from orbit 6 times in 156 —
  because a captain who means to trade comes alongside, which is what the
  berth lesson always said.
- **The Assembly's listed reasons do not sum to the vote** shown (+0.3 of
  reasons against −0.2); one function should produce both.
- **"Payroll missed" repeats** on about one broke day in three. It draws on
  the day's luck, so quieting it changes every seed; do it with a pinned
  state-hash update.
- **Small words:** "On station: Charter 2 Well kept"; the log calls
  volatiles "Ice" and survey data "Data"; "Fly free — no destination" clips
  in its dialog, and "Magnetosome Biomineralisatio" at 1040 px; the tutorial
  says a close pass costs reaction mass (it cost 0); the Register says you
  have been nowhere that trades a good while you stand in such a port.
- **Balance:** a neutral trader who neither hails nor flees can be taken
  apart by a Concordat HAMMERFALL at standing −7 (14 turns); hail-then-flee
  escapes at 77% hull. Honest trading income varies wildly by seed (−₡940
  to +₡7,900 a month for the same bot).

## Open — defects and debts, in rough value order

1. **Tuning constants without a guard.** The tripwire's last clean sweep
   read 60 of 131 unprotected (`notes/design-01.md`, "Which numbers are
   actually held in place"); a few have been pinned since, and new constants
   (`path.py`, `engage.REACH_KM`, `freeflight.RUN_MARGIN`) joined the pool.
   Each pin is its own small piece of work: drive the sim to the bar,
   bracket with absolute values. Re-run the sweep before choosing targets.
2. **Other ships are not plotted on the helm chart.** Nothing gives a known
   hull a persistent position a chart could draw — honestly a design piece
   (where does a sighting live, how stale may it go), not a marker to add.
3. **The engine light lives one beat.** `fired_*` is truthfully "the burn
   that happened this tick", so at 250 ms the light flickers under an
   autopilot that corrects intermittently. A short UI-side latch (or a
   "last burn" row) would read better without lying about the record.
4. **The docking mini-game and the conn share a gate by accident.**
   `berthing.can_conn` refuses while `game.docking` (the mini-game) runs —
   two systems both named "approach" meeting in one check. Works, but the
   naming invites the next bug; worth a rename or a comment at the gate.
5. **The descent order is only on the conn console.** The flight window —
   the panel you'd actually fly a descent from — doesn't carry it.
6. **Run bill on the button as well as the board.** The ship board quotes
   it every beat; the `Run for X` button label could carry it too (stale
   between rebuilds — needs the label refreshed in `sync`).
7. ~~**`shock`'s volley check flakes under load.**~~ Fixed 2026-09-22 by
   measuring the peak rather than one instant: the shake is a pair of
   decaying sines whose phases come from the shock's own seed, so any single
   moment can land on a zero crossing — which is how the same picture read
   8.0, 9.7 and 11.8 px alone and 1.03 px once in a full `-j 8` run against
   a 2.0 px floor. The check now looks across the wobble's first fifth of a
   second and takes the worst of it (11-13 px over three runs), and grabs
   the engagement's picture on that same beat, which was the same flake
   waiting to happen to the pixel count.

## Ideas — not defects; would make it more fun or easier to pick up

(The first five ideas — dock-for-me, keyboard flying, the conn tutorial
lesson, time compression, brake-to-zero — shipped in the third pass.)

- **More for the effects layer, now it exists** (`ui/effects`): a dust plume
  when she is put down on a world rather than the same bloom a quay gets;
  the fractures carried onto the Ship screen's layer stack while the damage
  lasts; a scrape drawn as a streak along the skin rather than as a small
  bloom; and the engagement's own picture could use the rim arc for a shot
  that came from outside the frame, which it does not yet.
- **More HUD, now the layer exists** (`viewport_hud`): a ladder of tick
  marks on the predicted path (time-to labels), the corridor hold point
  drawn as a gate rather than a chevron, closing-rate colour on the mark,
  weapon-arc cones in the tactical plot's first-person view.
- **Throttle on the digit keys** beside the six axis keys.
- **A combat HUD in the battle screen's own viewport** — the band ring and
  arcs are on the tactical plot; the first-person cameras go dark in a
  fight today.
- **An orbit you fly is still flat.** `autopilot.across` shapes an orbit in
  the conn's *local* x/y plane and returns a tangent with `z` zero — a
  deliberate simplification, and untouched by this pass because the conn's
  frame is not the system's. Now that a heliocentric orbit has a tilt, the
  obvious next question is a polar or inclined orbit round a world, which is
  a real thing to want and would need the tangent, the rungs and the orbit
  test to agree about which plane is being held.
- **Sightings that age.** `Conn.sky` is a snapshot taken when the approach
  opens, so a dark raider can only be somewhere you did not look — it cannot
  *close* on you during a flight. This is the same missing piece as "other
  ships are not plotted on the helm chart" (defect 2): a sighting needs a
  home, a position and a staleness before either can be built. (The Sector
  Chart now draws a rival's last sighting as a ring that widens as it ages,
  `ui/hunt_marks` — the model for this, one level up.)
- **The height picker's refusal could say which gate refused it.** A rung
  can be unsold because the tank is too small *or* because `orbits.quotable`
  says the price cannot be believed on these thrusters; the tooltip blames
  the tank either way, and `flightdeck.can_arm` has to point at the picker
  rather than repeat the gate. One reason string, asked of `orbits`, would
  let both screens say the true one.
