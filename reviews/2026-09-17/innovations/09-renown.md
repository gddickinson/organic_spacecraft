# Innovation 9 — Renown and the Voyage (progression and onboarding)

## Why

The play-test's sharpest finding: **20 honest three-year careers reached no
ending**. Honest progress bars sat at 0/12, 0/12 and 1–2/10, and the sector
was usually overgrown by years 5–6.5. The endings are all-or-nothing: nothing
rewards being a third of the way to Dominion. New players also faced 29
lessons and 15 screens without a clear "what now". There is an orders index
(`sim/orders.py`) and a freight desk, but nothing that turns state into
counsel.

## What the player gets

### Renown, a career ladder

**Renown** is a career score earned from **milestones** in every activity:
first survey sold, first colony, first deep gate lit, a nemesis destroyed, a
resolution passed, an arc finished, a Kith exchange, and so on (about 60 in
all).

It climbs ranks: **Master → Captain → Commodore → Admiral of the Verge →
Legend**. Each rank carries a **real perk**:
- priority berthing (shorter clearance queues);
- better recruits (+1 officer level floor);
- a standing floor with all four powers;
- the Assembly lets you table one resolution per year;
- Legend: your name on the chart ("⟨Name⟩'s Reach", a system you choose is
  renamed).

Milestones are read from state that already exists, by predicates: the log
of what happened, counts, flags. They are **never granted twice**, and they
are checked in the clock. A milestone that fires shows a moment: a despatch, a
log line and a renown chip on the HUD.

### Ending tracks

Each of the ten endings gains **three intermediate milestones**. Each has a
concrete reward (credits, standing, a unique fitting, a title), and they are
tuned so that **an honest captain reaches at least one full ending within
about five years on most seeds**, measured by bot.

| Ending | Milestones (examples) |
|---|---|
| Dominion | 3 colonies online → 6 plus 100k citizens → 9 plus 400k citizens |
| Concord | first treaty → 3 pairs at peace → all four powers Trusted |
| Containment | first Bloom system cleansed → 5 cleansed → the First Instar found |
| Xenarchy | 3 xenotech incorporated → 6 → 9 |
| Cartel | 10 live quotes → 30% of markets → a purse of 500k |
| Lineage | first grown hull gestated → 2 → a grown hull of class ≥ NAVIS |
| Exodus | LEVIATHAN researched → the keel laid → half grown |
| Genesis | an Abyssal signal decoded → an ice dive to 50 MPa → contact made |
| Apostasy | Dry Choir Trusted → a crewless hull flown → Kin |
| Ruin | (loss-side) a quiet track recording what was lost; no rewards |

Some ending *requirements* may be retuned where the measured honest-path
numbers show one is unreachable. Adjust them in `sim/threat.py` with the
measurement cited, and **keep every ending failable and triumphable**: the
project pins this arithmetically (`test_endgame`).

### Counsel, "what now"

The **first officer's counsel** is three concrete next moves computed from
state. Each has a reason and a "take me there" button that opens the right
screen with the right thing selected. Sources, in priority order:
1. anything urgent (hunger, fuel, hull, crew);
2. a waiting answer;
3. the best freight run from here (`sim/freight`);
4. a contract you can complete;
5. the next milestone on your leading ending track;
6. an unsurveyed body nearby;
7. a Reaches gate you can nearly afford;
8. an arc beat waiting;
9. an Assembly session coming.

Only moves that are **actionable now**: a check verifies that every
suggestion's action succeeds when taken, or is refused only for the reason
shown.

### Memoir and the Hall of Captains

At an ending or a death, the game writes a **memoir**: a one-page career
record. It is generated from the milestones, the log, the nemeses defeated,
the regions opened, the colonies, the arcs finished and the ending.
- It is shown on the Aftermath screen.
- It is appended to the **Hall of Captains**: `hall.json` beside the save
  directory, persistent across chronicles and slots, and never deleted by New.
- The title screen lists the Hall.

## Design

- **Content:** `data/milestones.py` holds about 60 career milestones plus 27
  ending-track milestones: id, name, renown, predicate key, reward and text.
  The predicates are small functions in `sim/renown.py` keyed by id, so the
  data stays data.
- **Rules:**
  - `sim/renown.py`: `check(game)` (fires new milestones, returns log tuples),
    `rank(game)`, `perks(game)` (effect keys read by berthing, recruit,
    diplomacy floors and the Assembly), and the ending tracks;
  - `sim/counsel.py`: `advise(game) -> list[{title, why, action}]` with
    action descriptors the UI can execute;
  - `sim/memoir.py`: the text, and the Hall file I/O (always under
    `save_path().parent`, so tests stay redirected).
- **State:** `Game.renown: object | None = None` holds a registered
  `RenownState`: achieved (id → day), score, and the rank-up history.
- **Clock:** `renown.check(game)` in the daily tick (cheap predicates;
  cache counts).
- **Perks:** each read at one point of use. An efficacy check turns each off.

## UI

- **Holdings gets a "Voyage" view.** Stream B has already split Holdings, so
  host it where the victory panel was. It shows:
  - the rank and progress to the next;
  - the ten ending tracks as horizontal ladders (milestones reached, the next
    one with what feeds it);
  - recent milestones.
- **Counsel** is a compact card on the HUD or the Sector screen ("First
  officer suggests…") with 3 rows and "take me there". It can be dismissed
  and reopened from the menu.
- **The Aftermath screen** shows the memoir. The title screen shows a "Hall
  of Captains" list.

## Balance targets (measured)

- An honest bot per strategy (trader, explorer, colonist, fighter, diplomat)
  reaches **at least one ending** within about 5 years on 3 or more of 5
  seeds, with the Phase 1 exploits closed.
- The first milestone arrives within about 10 days, and a rank-up within
  about 90.
- Counsel's top suggestion is actionable 100% of the time over 200 random
  game states.

## Tests (new suite `test_renown`)

- Each milestone fires exactly once, at its condition.
- Rewards apply exactly as stated.
- Perks move their numbers (efficacy).
- Ending tracks reflect the true state.
- The honest-ending bot measurement above.
- Every counsel suggestion is actionable, or refused with the stated reason.
- The memoir is written at an ending and at a death, and the Hall persists
  across a new game and across processes.
- Cross-process save.

## Notes from Wave A (read before building)

- **Honest income is the binding constraint.** Measured on the integrated
  tree (3 seeds × 3 years): the simple explorer bot ends at 35–70k; the
  trader, colonist and fighter bots end near zero, and 4 of 12 died (a lost
  battle is death in the sim since Phase 1). A trading house (innovation 5)
  needs ~30–45k to enter and was reached on only 1 of 5 seeds; a deep-anchor
  relight (innovation 1) costs ~50k and was reached by 3 of 12 bots.
- So rewards and perks should **open the mid-game**, not only decorate it:
  for example, a hauler grant or charter waiver at Captain, a relight
  subsidy toward the first deep gate, or credit rewards on the early
  milestones of each ending track. Measure that they do.
- Build a **careful captain** bot that plays the way the screens teach:
  it parleys or flees fights it cannot win (`sim/assessment`,
  `sim/parley`), runs dark on lawless legs (`sim/running_dark`), hunts
  bounties it can win (`sim/hunts`), opens a freight line when counsel says
  it can afford one (`sim/freightlines`), lobbies at the Assembly
  (`sim/assembly_lobby`) and relights a gate. Calibrate the ending-track
  milestones on that bot, not on the simple ones.
- **Milestones for Wave A systems** exist to be read: a line opened
  (`game.house`), a gate relit (`sim/relight.standing`), a rival destroyed or
  allied (`game.hunt`), a resolution passed or blocked (`game.assembly`), an
  adaptation set in (`ship.adaptations`), sound has no milestone. **Wave B
  systems** (the Kith, phenomena, officer arcs) are being built in parallel:
  design milestone predicates as a registry keyed by id, read state through
  `getattr(game, "kith", None)` / `"sky"` / officer `arc` fields
  defensively, and leave a documented one-line way to add their
  milestones; the maintainer adds them after the merge.
- **Counsel** should know every Wave A door: freight desk runs, a house
  line when affordable, a bounty it can win, the next Assembly sitting, a
  relight step, an adaptation waiting on an answer.
