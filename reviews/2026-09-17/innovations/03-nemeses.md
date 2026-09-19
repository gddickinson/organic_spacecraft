# Innovation 3 — Nemeses and the hunt (combat)

## Why

The play-test found **no combat career**:
- Encounters come about 1.3 times a year and cannot be sought.
- An armed fighter bot completed **0 bounties in 15 career-years**.
- An enemy is forgotten the moment a fight ends, and every encounter is a
  stranger.

The machinery for a better loop already exists:
- hull memory (`sim/memory.py` minds);
- warrants and bounties (`sim/warrants.py`, `law_hunted_by`);
- prize and aftermath (`sim/prize.py`, `sim/aftermath.py`, `battle_state.finish`);
- traffic with positions (`sim/traffic.py`);
- countermeasures describing signatures (`data/countermeasures.py`), which
  only the sky reads today. The backlog item "let the captain hide too" is
  unimplemented.

## What the player gets

**Named rivals who remember you, a hunt you can choose to start, and a way to
run dark.**

- **Nemeses.** At most 4 are active at a time. Each has:
  - a name, an archetype, a hull and fit scaled to the player's own power at
    the moment they rise;
  - a level from 1 to 5, and 1–2 traits;
  - a **grudge** in both directions;
  - a history (every meeting, who won, what was said);
  - a status: `active`, `wounded` (retreated to refit, back in N days),
    `dead`, `allied` or `retired`.

  | Archetype | Where they come from | Their style |
  |---|---|---|
  | Corsair | A raider you escaped from or drove off | Ambush, retreats early |
  | Warrant hunter | A power posts a hunt warrant on you (`warrants.holders(game, "hunt")`) | Relentless, follows you between systems |
  | Yards ace | A Concordat hull you struck and released, now humiliated | Duellist, closes to short band |
  | Freehold duellist | Rises from the cartel after you undercut their trade | Mercenary, can be bought off |
  | Bloom-ridden husk | A Charter hull the Bloom took, keeping its old name | No parley, adapts to your weapons like the Bloom (`bloom.record_damage`) |

- **Traits** include Ambusher (first volley), Duellist (accuracy at short
  band), Coward (breaks off at 50% hull), Relentless (never retreats twice),
  Shielded (+armour layer), Swarm (brings 1–2 escorts at level 4+), and Ghost
  (runs dark; hard to find).

- **They roam.** Once a day each active nemesis moves between systems along
  lanes, and a warrant hunter moves toward the player's last known system.
  **Sightings age:** each nemesis has a `last_seen = (system_id, day,
  confidence)`, and the confidence decays with days since the sighting. A port
  visit may refresh it through rumours or the harbourmaster, and bounty boards
  give one.

- **They find you.** In `encounters.roll_encounter`, a nemesis in the arrival
  system rolls first, with odds from its aggression against your signature.
  The encounter carries `"nemesis": id` and is built from their persistent
  ship, not `make_enemy`. Taunts and threats arrive as despatches through
  `sim/comms`, before and after meetings.

- **You can find them.** This is the **hunt**:
  - A **bounty board** at ports lists wanted nemeses and notorious raiders:
    the reward, the issuing power, the last-known system and the sighting's
    age.
  - Accepting a bounty gives a fresh sighting.
  - At a system you can **search** for a hull: spend days, with detection
    against their stealth. Odds are stated before you commit.
  - A successful search opens an engagement on your terms: you choose the
    band, or you get the first volley if you ran dark.

- **Endings for a nemesis:**
  - **Beaten:** they break off (wounded), come back 30–90 days later one level
    up with a new fitting, and the grudge deepens. At level 5 they don't
    retreat.
  - **Destroyed:** bounty paid, a **trophy fitting** (a unique named part
    derived from their best mount, e.g. "Vorn's Lance: +8% accuracy"), and
    standing with the issuing power.
  - **Struck colours and spared:** they may become **allied**, an ally that
    turns up to help in a later fight (reuse `consorts` if feasible, otherwise
    a one-battle assist), or they may betray you. It depends on archetype and
    grudge.
  - **You lose:** they gloat, take a cut of cargo, and are unlikely to kill a
    struck captain (reuse prize/struck logic).

- **Run dark.** A ship-level toggle: transponder off, drive banked.
  - It lowers encounter odds (piracy and patrols), lets a hunt start with the
    first volley, and hides you from nemesis roaming.
  - Customs and patrol suspicion rise if you are caught running dark at a
    power's port (`sim/customs` and `enforce`).
  - A **shroud fitting**, a new part (grown and fabricated versions), deepens
    it.
  - Grounded in `data/countermeasures.py`, which already describes the
    signature of transponding, running dark, shrouded and cloaked hulls.

## Design

### State

- `Game.nemeses: list = []` of registered `Nemesis`, with fields including:
  - `id` (from `core/ids.next_id("nemesis")`; add the kind to `core/ids.KINDS`);
  - `name`, `archetype`, `level`, `traits`;
  - `ship`: a registered `Ship`, persistent, repaired while wounded;
  - `faction`, `grudge`, `status`, `back_on`;
  - `last_seen`: `system_id`, `day`, `conf`;
  - `location_id`;
  - `history`: short tuples;
  - `bounty`: reward and issuer, or None.
- `Game.dark: bool = False`, the run-dark switch.

### The rules module and its hooks

`sim/nemeses.py` holds the rules: rise, move, spot, encounter building,
outcome, level-up, trophy.

`sim/hunts.py` holds the bounty board, search odds and the search itself. A
separate module keeps each under 500 lines.

Clock hook: `nemeses.tick(game, n, r)` from `core/clock._one_step` in sector
time, returning log tuples.

**The outcome goes through the one door:** `battle_state.finish` / aftermath.
- Every ending id (`won`, `driven-off`, `struck`, `lost`, `parley`, …) is
  mapped explicitly.
- **Warning from the project's history:** "a new battle result id breaks every
  outcome tally", so don't invent new result ids.

The rise triggers are events that already happen: escaping a raider, a hunt
warrant being posted, striking a hull and releasing it, cartel undercutting,
and meeting a Bloom husk. Cap the number active. Rises should be rare enough
that a nemesis feels personal, about 1–3 in the first two years.

### Difficulty

A nemesis's hull scales with `encounters.draw_threat(game, rng)` at rise
time, plus 0.4 per level. They must stay beatable. Measure the win rate of a
reasonably fitted player against a level-1 and a level-5 nemesis over 200
seeded fights: level 1 about 60–75%, level 5 about 30–45% for a mid-game hull.

### UI

- **A "Hunts" tab on the Law screen** (`ui/law_view.py`), or a new
  `ui/hunts_panel.py` hosted there:
  - dossiers for each nemesis, with a portrait from `thumb3d` of their hull,
    level, traits, history, grudge and last-seen with its age;
  - the bounty board;
  - a "Search this system" action with stated odds.
- **The Sector Chart** marks last-known positions with a fading ring by
  confidence.
- **Run dark** is a toggle on the Ship screen and on the HUD (a small chip),
  with the trade-off stated in its tooltip.
- **The battle screen's header** names the nemesis and their history with you
  ("Third meeting. You drove her off at Pale Fall.").

### Balance targets

- An armed fighter bot that hunts bounties earns in the same band as the
  honest explorer (about 30–80 cr/day in years 1–3), not zero.
- Running dark lowers the per-arrival encounter rate by about 30–50% and
  raises the customs search rate when docked dark.
- A nemesis's return after being beaten is measurably stronger.

### Tests (new suite `test_nemeses`)

- A nemesis rises from each trigger.
- They roam, and a sighting's confidence decays with days.
- A search finds a nemesis at the stated odds (seeded, over N tries).
- An encounter with a nemesis uses their persistent hull (the same uid and
  damage state).
- Beaten → wounded → returns levelled.
- Destroyed → bounty, trophy and standing.
- Spared → allied or betrayal, depending on archetype.
- The run-dark efficacy check.
- Nemeses survive a cross-process save.
- No new battle result ids; the outcome tallies are unchanged for
  non-nemesis fights.
- The previews on the hunt panel equal the acts.

## Out of scope

- Assembly resolutions such as a "Bounty Compact" that honours bounties across
  powers (innovation 6 may add one after this merges).
- Nemeses living in the Reaches (a later integration).
