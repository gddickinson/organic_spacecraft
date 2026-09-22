# Afoot — the Verge at walking pace

*Design for the 2026-09-21 expansion: turn-based play on 2D deck plans.*

## Why

Everything in SEEDFALL happens at the scale of a hull. The game already knows
a great deal about *people* and *places* and never lets you stand anywhere:

- **People.** Every officer has six characteristics, a service record,
  skills, a lineage, a stage of life, a conviction, a story arc, ties to
  people elsewhere, and things they own (`sim/lifepath.py`, `sim/person.py`).
  All of it resolves through one grammar: 2D6 + skill + DM ≥ 8
  (`sim/checks.py`). None of it has ever been *played*.
- **Places.** A place is anywhere with people in it (`sim/places.py`): a quay,
  a habitat drum, a holding, a settlement, your own hull. Each answers four
  questions (people, amenity, tech, law), and 94 kinds of door open or not
  against them (`data/venues*.py`). The concourse is drawn (`ui/place_scene.py`)
  but it cannot be walked.
- **Things.** About 130 pieces of personal kit exist, with tech and law
  levels (`data/kit.py`): pistols, flak jackets and vacc suits. Nobody has
  ever fired one.

**Afoot** is the missing scale: a Star Frontiers / Traveller style
turn-based layer played on deck plans of the places the game already has.

## What the player gets

From the new **Afoot** screen (`o` on the rail), or from a door on another
screen, the captain picks somewhere walkable where the hull is, then a party
of one to four from the captain, the officers and any walking machines
aboard. The map opens.

| Site | Where it comes from | What it is for |
|---|---|---|
| **Your hull** | `game.ship`, always | Walk the decks. The officers are at their stations: talk to them. Things go wrong aboard: a stowaway, a fault. |
| **Starport** | `places` kind `port` | Docks, a concourse of open venues, and the administration deck. Staff behind the counters do business through the existing sims. Constables enforce the actual law level. |
| **Habitat** | `places` kind `habitat` | A drum, tower or bunker, laid out by its class. |
| **Settlement** | `places` kind `downside` | Sheds, a bunkhouse, a bar, the works. |
| **Your holding** | `places` kind `holding` | Your own people and machines. |
| **A struck prize** | a battle that ended `struck` | Board her. Holdouts, prisoners, the hold, the captain's cabin, the bridge. The prize decision stays the one door (`sim/prize.py`). |
| **A derelict** | seeded per system (`sim/afoot_sites.py`) | A dead hull adrift. Hazards, salvage, a log, sometimes a relic, sometimes the Bloom. |

## The rules

### One grammar

Every roll is `checks.roll`. Every offered act shows `checks.chance` for the
same arguments before it is committed (**preview equals act**). A party
officer's numbers are `lifepath.of(game, officer)`, read afresh on each roll,
so what a clinic fits mid-walk counts at once. The captain gets a derived
record from the seed and the opening choices (`sim/afoot_people.py`), stored
nowhere, like everyone else's.

### The map

- A **plan** is one or more **decks**. Each deck is a grid of terrain
  characters (wall, floor, void, window), plus **rooms** (named rectangles
  with a kind), **things** (doors, lockers, consoles, counters, lifts,
  airlocks, cargo, relics, spore nodes, cover) and **actors**.
- **Derived from the site.** A plan is a pure function of the seed and the
  site's key, `RNG(f"{seed}:afoot:{site.key}")`. The same station has the
  same layout every time you put in. Rooms come from what the site actually
  is: the venues open at a place, and the fitted parts and complement of a
  hull.
- **Styles** follow the hull families: grown (rounded chambers, sphincter
  doors, intima glow), fabricated (square corridors, bulkheads), hybrid,
  synthetic (no air; a vacc suit or a machine body is needed), xeno.
- A walk in progress is **saved whole**: `game.afoot` is a registered `Walk`
  holding the decks, the things, the actors and the log. You can be in the
  middle of one, so it lives on the `Game`.

### Characters

- **Stamina** = STR + DEX + END. At 0 an actor is **down** and bleeding one
  point a round. At −END they are dead. First aid (Medic) stabilises.
- **Movement**: 6 squares a round (1.5 m each), ±DEX DM, less for heavy
  armour, a suit, a load over 30 kg, or being badly hurt. Never below 2.
- **One action a round**: attack, aim, first aid, use a thing, talk, stand
  watch, or carry a downed ally. Opening a door, riding a lift and changing
  stance cost movement, not the action.
- **Kit is what they carry.** The captain draws from `game.kit`; each
  officer carries what `person.of` says they own. `data/afoot_arms.py`
  gives each weapon and armour in `data/kit.py` its tactical numbers, keyed
  by the same ids, so a pistol bought on the concourse is the pistol in the
  corridor.

### Combat (Traveller 2e, squared)

- **To hit**: 2D6 + Gun Combat (or Athletics unarmed) + DEX DM (STR in
  melee) + the weapon's own kit bonus + range + aim + cover ≥ 8.
  Range: adjacent +1, short 0, long −2, extreme −4. Cover: half −1, full −2.
- **Damage**: weapon dice + the attack's Effect − armour. Lasers against
  ablative cloth meet its extra protection. Stun weapons put people down and
  never kill.
- **Watch**: spend the action; take one shot at the first enemy that moves in
  sight during their turn.
- **Nerve**: an NPC hurt past half, or whose friend goes down, throws 2D6
  plus their leadership DM against 8. Failing, they surrender or run.
  A surrendered actor can be questioned.
- **Noise and law**: shooting is heard. Where the law level forbids the
  weapon (`kit.legal_at`), violence seen by a constable or a citizen becomes
  a charge through `sim/law`'s one door.

### Two modes

- **Calm**: nobody hostile knows the party is there. Moving walks the whole
  path, and the others follow the leader. Rounds still pass, and the NPCs
  still act.
- **Action**: once a hostile notices, or anyone attacks. Side turns: the
  party moves and acts in any order, then **End turn**, and the NPCs act.
  An ambush gives the NPCs the first turn.
- **Noticing**: an NPC sees a party member in line of sight within its range.
  A party member who is sneaking can only be seen by a Recon check against
  their Stealth.

### People

`data/afoot_folk.py` holds the archetypes: patrons, dockhands, keepers,
clinicians, clerks, agents, harbourmasters, customs officers, constables,
fences, informants, thugs, raiders, holdouts, scavengers, frames, drones,
Bloom thralls and creepers, and the Kith. Each archetype has scores, skills,
kit, a disposition, a behaviour (wander, keep station, guard, patrol, hunt,
flee), and topics.

**Talk** (`sim/afoot_talk.py`) is the hail pattern from `sim/hail.py`. Each
option says whether it can be done, why not, and the odds, and each one is a
door that already exists:

- business: `shore.buy`/`sell`, `shore.ashore`, `crew.pool_here`/`hire`,
  and the Concourse screen for the full counter;
- a harbourmaster's favours: `officials.preview`/`ask`;
- persuading, leaning on and deceiving someone: `checks`, which move the
  disposition;
- a bribe, out of your purse (money leaves, and never arrives from nowhere);
- the word going round: rumours;
- your own officers aboard: a word (loyalty, once a month each), and their
  story if a beat is waiting;
- the struck crew: where the hold is, who sent them, sign on, let them go.

**Voices.** A named person — the harbourmaster, the master of a struck hull
— speaks through `sim/voice.speak`, which remembers you and uses a local
model if one is switched on. Everybody else speaks from their archetype's
own written lines, by mood, so a concourse of forty people does not fill the
chronicle's memory with strangers.

### Incidents

`data/afoot_incidents.py`: small, conditional events that give a walk a
reason to exist beyond shopping. Each has a condition read off state the game
already keeps: a **stop-and-search** (you carry openly what this law level
forbids), **somebody from an officer's past** (`person.of(...).ties`: a
creditor, a rival, a parent — met by name, and settling with them moves the
officer), a **bounty hunter** (paper on you reaches this system), and,
aboard, a **stowaway** (you are alongside a quay) and a **fault** (the hull
is hurt; fixing it puts some back). A low law level also puts a loiterer and
a hard case on the concourse, and an informant sells the word going round.
A quarrel aboard, a shakedown and a brawl are in the backlog
(`seedfall/IMPROVEMENTS.md`).

### Endings and what they cost

- **Leave** through an exit (an airlock or a gangway), with everyone who is
  still standing. The downed must be carried, or they are left behind.
- **Wiped**: on a lawful site the locals carry you out. The captain always
  comes home, at a price: a grave wound, lost kit, and a charge if you
  started it. On a hostile site, an officer left down may die.
- **Wounds** persist: `game.wounds` holds, by officer id, the stamina still
  missing. They mend a little every ship day, faster with a medic or a
  sickbay, and a wounded officer starts the next walk short.
- **Death** is `officer.retired` with the reason recorded, and it reaches
  the crew's book (`roster.departed`).
- **Time**: a round is six seconds. The walk's time is spent through
  `advance_days` when it ends.
- **Loot never conjures money.** It is kit (sellable at a counter), cargo
  (into the hold through `ship.add_cargo`), evidence (`inquiry.add`), relic
  study (`xeno.add_study`) and intel. Credits only change through doors
  that already account for them.

## The modules

As built (every one under 500 lines; the package maps list them under
"Afoot"):

```
data/afoot_arms.py       weapon and armour numbers, keyed by kit id
data/afoot_things.py     thing kinds and the closed vocabulary of verbs
data/afoot_rooms.py      room kinds: size, furniture, staff, loot; venue and part rooms
data/afoot_folk.py       NPC archetypes, the moods ladder, the topics of talk
data/afoot_derelicts.py  the dead hulls adrift, and what their end left aboard
data/afoot_incidents.py  incidents and what settling them is worth
sim/afoot.py             the front door: move, attack, act, talk, end turn, mend
sim/afoot_begin.py       beginning a walk: who, what they carry, where they stand
sim/afoot_state.py       the saved dataclasses: Walk, Deck, Room, Thing, Actor
sim/afoot_sites.py       what can be walked from where the hull is
sim/afoot_plans.py       the room lists: a hull, a quay, a drum, a holding, a wreck
sim/afoot_gen.py         laying a deck out: a spine, rooms on both sides, lifts
sim/afoot_furnish.py     furniture, never in a doorway, never cutting a room
sim/afoot_map.py         passable, sight, cover, reach, paths
sim/afoot_people.py      records: officers, the captain, machines, NPCs; the pool
sim/afoot_cast.py        who is there, and what is in the lockers
sim/afoot_incidents.py   the stop, the tie, the hunter, the stowaway, the fault
sim/afoot_fight.py       attacks, damage, going down, bleeding, first aid, nerve
sim/afoot_ai.py          the other side's turn; watch fire; the air
sim/afoot_acts.py        what can be done from here, with odds; witnesses
sim/afoot_deeds.py       each act, done (DEEDS)
sim/afoot_talk.py        what can be raised with somebody, with odds and prices
sim/afoot_said.py        each topic, answered (SAID)
sim/afoot_ends.py        leaving, being carried out, giving up; what is banked
ui/afoot_view.py         the screen
ui/afoot_canvas.py       the deck, painted, with fog, reach and paths
ui/afoot_panels.py       the party, what they can do, who is in sight, the log
ui/afoot_talk_panel.py   a conversation, and the counter behind it
ui/afoot_start.py        choosing a site, a party and how armed
tests/test_afoot.py      the ground and the rules
tests/test_afoot_play.py played: finished, kept, and answered for
tests/test_afoot_ui.py   on the screen, pressed
tests/afoot_kit.py       scenes: a settled sector, a wreck of a kind, a prize
tests/afoot_bot.py       a party leader good enough to test the decks with
```

Touched elsewhere, each through its own door: `core/state` (three fields:
`afoot`, `wounds`, `walked`), `core/ids` (the `walk` kind), `core/shiptime`
(one line: `afoot.mend`), `sim/prize` (its three doors on a hull as well as
a battle), `sim/clinic` (care closes a kept wound), `sim/roster` (a death
afoot in the crew's book), `data/offences` (assault, theft), `data/screens`
(`o` on the rail), `ui/window` (the lock), `ui/battle_view` ("Board her
first"), `ui/ship_view` ("Walk the decks"), `ui/concourse_view` ("Walk it").

## Checks

- Every site kind and every hull family generates a connected plan over many
  seeds: every room is reachable from the entry, and no door opens onto void.
- Line of sight is symmetric. A path never passes through a wall or a closed
  door it cannot open.
- **Preview equals act** for attacks, first aid and every talk option with a
  roll.
- Money: no walk ends with more credits than the counters paid.
- A walk saved mid-turn resumes in a fresh process.
- Painting the screen never moves `game.rng`.
- Efficacy: armour reduces damage, a weapon's bonus moves the hit chance,
  wounds heal and a medic heals them faster, and a word moves loyalty.
- A bot party plays each kind of site to an ending without jamming.
- The screen fits 1040×680, and every control on it runs (`verbs`).

## The rewrite: plans in the shape of the thing (same day)

**Asked:** do the maps correspond to the shape and construction of what they
are? Design maps for every element; add the places people want and need;
redesign whatever cannot hold what it has to; ships and stations should be
functional.

**Answer before:** no. Every plan was a spine of boxes, whatever it was.

### How a plan is drawn now

A blueprint **paints regions** onto a sheet (`sim/afoot_blocks.py`) — this
is corridor, that is the galley, these squares are open ground — and the
sheet does the rest the same way for every shape: walls where regions meet
(on the room's side) and wherever anything meets the outside, one door per
room nearest where it asked, links until every room can be reached from the
deck's own ways on (its locks and lifts, not just any corridor), and any
mark that landed on a wall nudged to open floor. So no blueprint places a
wall or a door, and none can get one wrong.

| What | Blueprint | Shape |
|---|---|---|
| any hull | `afoot_hullplan` | a slice through its own silhouette (`hullforms`, `hulls3d.proportions`): ellipse for grown, superellipse for Yards, between for hybrid, bent for xeno |
| a Dry Choir frame | `afoot_latticeplan` | nodes at their mounts on a spine, crawlways, struts, no air |
| a quay | `afoot_stationplan.quay` | a can on one lift core, the arm, the mast |
| a Fleet Hub | `afoot_stationplan.hub` | the spine, four arms with berths, two rings on spokes |
| drum · ring | `afoot_stationplan` | the axis and a town inside · a hub deck and its rim |
| tower · dome · keel · Kith | `afoot_worksplan` | square floors · ground under a shell · modules on a keel · the singing hall |
| settlement · base · dug-in works | `afoot_groundplan` | streets and sheds; tubes and a hangar where the air is not breathable |

Round decks share `afoot_loops`: a pie for a small can, concentric ring
corridors for a big one, only the rim for a habitation ring.

### Functional

A hull's **program** (`afoot_program.ship`) is read off its card: a bridge
(a cockpit for two) sized to the watch, berths for the whole complement, a
master's and officers' cabins, galley, heads, sickbay, air (grown hulls
breathe through an intima), water, tanks, stores, damage control, lifeboats,
suit lockers, holds by the cargo rating, a room for every fitting **at its
own slot's mount**, and what the role adds (`data/afoot_programs.ROLE`).
**Nothing is dropped**: a deck that cannot hold its share hands the rest on;
the last offers it back to any deck with room; then another deck is drawn,
up to what a hull of its length carries; then the hull is drawn longer.
Rooms grow to fill a quiet deck rather than leaving a cavern of void.
Holdings take a working space per structural trait
(`TRAIT_SPACE`, one per `works3d` trait, checked), plus what keeps a
station running.

### Establishments

Fifteen kinds (`data/establishments.py`) seeded per system without luck,
each a `Place` ("station" or "base"), a berth on the chart if a station,
with signature doors (`data/venues_establishments.py`, gated by
`Venue.at`), the ordinary kinds of door its business carries, its own law
and tech floor, and a shape to be walked as. A shipyard answers
`shipyard.can_build_here` and refits alongside; a nursery grows grown
hulls. Three new wrecks: a quarantined hospital ship (isolation wards,
spores), a gutted yard, a habitat ring gone quiet.

### Found and fixed on the way

- **Lifts never linked.** `_pair_lifts` tested `not u.link` on a field whose
  "none" is −1, so every lift in every plan went nowhere, and every check
  that counted dead lifts made the same mistake. Fixed, and the shapes suite
  now rides the lifts from the way aboard to every deck.
- The play-test's list: the fallen are brought home where people live; a
  stun is not a wound; crew at their stations keep their wounds; persuasion
  is once a person, a rolled word is the round's act, and a refused press
  spends no luck; a bribe buys one witness; your own are not targets and
  your own people's lockers not loot; a stop ignored is evasion; ties and
  stowaways are remembered for a season; spent consoles, relics and nests
  stay spent; a cleared wreck stays cleared; a claimed prize's hold sails
  with her, and leaving says it lets her go; a calm party rides a lift
  together; followers keep up when the leader is seen; nobody spawns or
  works in a doorway; a party squeezes past bystanders; a lodging's bed
  shows its price; theft says so before it is done; a voice line never
  waits on a model on the screen's thread.

### Checks added

`tests/test_afoot_shapes.py` (every hull inside its silhouette with its whole
program, bridge forward and drives aft, every deck reachable; every holding
class in its traits' shape; the quay and the hub; the breathable and the
sealed settlement; every trait with a space), `tests/test_establishments.py`
(seeded, every kind found, doors at home and only there, a yard builds and
refits, stations on the chart and bases not, every kind walked, the three
wrecks boarded), `tests/test_afoot_fair.py` (the play-test's rules).

## The open items closed (2026-09-22)

Every item on `seedfall/IMPROVEMENTS.md`'s Afoot list is closed but the
remainder of item 12 (a base's own berth; yards that build grown or xeno
hulls).

### Weight

Asked how anybody moves on a deck with no floor to stand on, the answer was
that nothing weighed anything. Now every deck carries a gravity (`Deck.g`)
from what it is: a hull or a quay is weightless, a Habitat Girdle's berths
0.4 g, a ring's levels spun at 0.8 g (a little more for each level further
out), a drum's floor 1 g, the ground its world's. A ring is not drawn as a
disc any more: each level is **an unrolled strip whose ends are the same
corridor** (`sim/afoot_ringplan.py`; `Deck.wrap`, and `afoot_map` steps
across the seam), stacked with the outermost the heaviest, reached by spokes
from the hub. Weightless, the untrained go hand over hand at twice the cost
of a step, shoot unbraced (`afoot_fight.UNBRACED`) and are set drifting by a
gun's kick; Zero-G or magnetic boots put it right, and anybody who lives
aboard is at home in it. A heavy world costs movement (`afoot_people.HEAVY`).

### Fire, trouble, and the career

- **Fire** (`sim/afoot_fire.py`): a burst adds the gun's Auto; suppressing
  fire pins the target and whoever is beside them for a round unless they
  have the nerve (`UNSHAKEN`); frag, stun and smoke grenades, sold under the
  law's gate, thrown with Athletics, a square off on a miss; smoke is an
  opaque thing that thins each round.
- **Trouble** (`sim/afoot_trouble.py`, `sim/afoot_holdings.py`): a quarrel
  between officers whose convictions collide, a shakedown and a brawl where
  the law is thin, and your own works failing, striking or sabotaged — set
  right by hand the holding yields a quarter more for a month, walked away
  from a quarter less (`afoot_holdings.factor`, read by the colony tick).
- **The Kith and the vault** (`sim/afoot_kith.py`, `afoot_deeds._relic`): a
  phrase sung to be answered, a domain's song of passage from an elder, both
  teaching the lexicon; a relic in three stages, the second standing its
  sentries down.
- **The career**: counsel suggests the wreck adrift here and the neglected
  officer (`counsel_doors.afoot`); the Academy's *On your own two feet*;
  five renown rungs off `afoot_ends.progress`; the captain's record played
  out term by term by `sim/lifepath`.
- **Establishments that do something**: a stake — a tenth of a house, paid
  monthly from its takings on the one clock, a quarter's statement by
  despatch, four-fifths back on selling; traffic bound for the houses; the
  quay's gossip naming them.

### Found and fixed on the way

- **A refused shot spent luck.** `afoot.attack` and `afoot.throw` drew
  `game.rng` before `afoot_fight`/`afoot_fire` had checked range, sight and
  whether the gun could burst at all, so an out-of-reach shot moved the
  chronicle's dice. Both now take a dice maker called only once the act is
  allowed, the way `afoot_acts.perform` already did.
- **The fire buttons pushed the column off the window.** A carbine and a
  grenade in hand put five buttons on one row; at the smallest window every
  button in the side column overflowed. Burst and Suppress now share a row
  of their own and each throw has one.
- **A ring had ends after all** (from play). The pathfinder crossed the
  seam, but `move` refused a step off either end, sight and every range
  measured the long way round, and the canvas's camera stopped at the
  strip's edges — so a walk round a Fleet Hub ring hit a wall of nothing.
  `afoot_map` now answers every question on a ring the short way round
  (`apart`, `span`, `unroll`; the ground wraps its own lookups), and the
  canvas turns the strip so whoever is in hand stays in the middle
  (`AfootCanvas.roll`). The canvas's helpers moved to `ui/afoot_marks.py`
  at the line ceiling.
- **The "reaches" gate was not a defect**: a fresh sector is all Verge, and
  a relit deep region's systems take its id (a relit Cradle's fourteen
  systems carry two xeno hulks).

### Made fast, or across — and item 12's remainder

From play: the chronicle opened with the hull 7,698 km off the Fleet Hub on
the flight deck while the Hub's doors were open to the crew. "In orbit of
the world the quay is over" had been read as *near* by the flight model and
as *inside* by every door. `sim/crossing.py` makes them two facts —
**made fast** (`Game.berth`, the hull 0.6 km off the berth's centre; a new
chronicle starts so at its home quay; the harbour's pilot or a conn that
ends alongside makes it; moving casts off) and **across** (`Game.ashore`:
the ship's boat for a hull of crew six or more, their shuttle for a fare,
suits on a line within 2 km of something in orbit). The money-taking doors
of the Concourse (`shore`, `clinic`, stakes) and every walk ask it.

Item 12 closed with it: a base's berth is a pad in orbit (`anchorage` kind
`field`, `berths3d.field`), a breakers' yard (drawn only where a dead hull
is adrift, on its own stream so no other house moves) wakes a derelict
REVENANT, a nursery refits what it grows, and traffic bound for a house
holds that house's berths and not the quay's (`control.holders`).

Found on the way, and left open (IMPROVEMENTS 17): the flight computer
touches a free port's skin at 2 m/s, 607 m from its one arm — a Grand is
built like one. It surfaced only because the first draft put the breakers
in the ordinary draw and reshuffled every sector's houses.

### Checks added

`tests/test_afoot_weight.py` (every deck's weight from its structure,
drifting and bracing, heavy worlds, the ring's seam),
`tests/test_afoot_career.py` (counsel, the Academy, renown and the captain,
the Kith exchange, the relic's stages, the three troubles, your own works),
`tests/test_afoot_fire.py` (burst, suppression, grenades, smoke), two checks
in `test_establishments` (stakes, traffic to the houses) and one in
`test_afoot_ui` (the fire buttons, the weight pill, the latest lines, the
down panel, tokens).
