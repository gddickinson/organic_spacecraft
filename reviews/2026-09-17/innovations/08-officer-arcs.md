# Innovation 8 — Officer arcs (characters)

## Why

Officers already have a good deal of machinery:
- convictions (`data/convictions.py`) that react to events;
- loyalty, with walkouts;
- lineages and lifespans;
- traits;
- minds (`sim/memory.py`) that remember the captain.

But they have **no story of their own**. Nothing an officer wants is ever
*about them*, so a veteran of ten years reads much like a new hire with the
same numbers.

## What the player gets

Each officer, when hired or at the start, draws one **personal arc** from a
table of 12. An arc is three **beats** long. Each beat:
- arrives as a despatch addressed to the captain from that officer, through
  `sim/comms`;
- offers 2–3 costed choices (what it costs, what it may win, and what the
  officer will think), using the despatch answer machinery (`answer_signal`);
- is triggered by a **place** (a named system, perhaps in the Reaches), a
  **date window**, a **loyalty** threshold, or an **event** (a fight, a Bloom
  burn, a colony founded);
- has a response window. **Neglected**, it lapses: loyalty falls, and a
  neglected final beat may cost you the officer.

The last beat, well resolved, grants a **signature trait**: a permanent,
named, officer-specific ability, stronger than the existing traits and
thematically bound to the story. Examples:

| Arc | Beats (short) | Signature trait |
|---|---|---|
| **The last signal** | A sibling's distress beacon from a Bloom-held system → go there, and burn or search → find them, or their log | *Kessel-steady*: +20% to Bloom burns while this officer holds a seat |
| **Old debts** | A Freehold cartel calls in a debt → pay, hide or confront → the cartel's answer | *Paid in full*: Freeholds standing never falls below Tolerated |
| **The defector** | A Dry Choir recording wants asylum aboard → hide it from the Choir → it offers what it knows | *Second mind*: one extra decoding attempt and +scan |
| **The disgraced scientist** | A Charter inquiry into their old work → defend, recant or publish → vindicated or ruined | *Peer reviewed*: provisional results confirm 30% faster |
| **The deserter** | A Yards warrant for them → shield or surrender → their old unit comes calling | *Drill*: helm manoeuvres +10% when unattended |
| **The grower** | They want to seed a garden on a moon → find the site → it blooms (or the Bloom takes it) | *Green thumb*: colony yields +8% |
| **The cartographer** | An unfinished chart of a lost route → fly its legs → it points into the Hollow | *Dead reckoning*: +0.5 ly jump, and a free chart of one Reaches region |
| **The pilgrim** | Wants to see the Cradle's stars → the gate → the Kith sing to them | *Light-tongued*: Kith comprehension +25% (only if the Kith exist; otherwise a generic comms bonus) |
| **The widow** | Their partner died on a hull you now fly with → find the wreck → bury or salvage | *Remembered*: crew morale floor raised |
| **The gambler** | Owes a Freehold card room → a bet on a race → win it (a timed jump race) | *Lucky*: small chance to reroll a failed ground attempt |
| **The heretic** | Believes the Bloom is a new life to be understood → help study a mass → the Charter notices | *Unafraid*: Bloom study yields +30% |
| **The heir** | Stands to inherit a Station share → reach the reading of the will → claim or give it away | *Landed*: a monthly income, or a large standing gain if given away |

Each beat's text is in the officer's voice, using `data/personas.py`
registers, and every choice's consequences are shown before choosing.

## Design

- **Content:** `data/arcs.py` holds the 12 arcs, each 3 beats with triggers,
  choices, consequences (standing, credits, loyalty, flags, items) and the
  signature trait with its effect key.
- **Rules:** `sim/arcs.py` covers:
  - assignment (seeded per officer: `RNG(f"{seed}:arc:{officer.id}")`);
  - trigger checks;
  - opening a beat as a despatch;
  - resolving a choice with a preview;
  - lapses;
  - signature effects, which are read where the effect applies and keyed like
    trait effects through `crew.trait_effects` or a parallel
    `arcs.signature_effects(officers)` read by `ship.stats` and the named
    systems.
- **State:** `Officer.arc: str | None = None`, `Officer.arc_beat: int = 0`,
  `Officer.arc_state: dict = {}` and `Officer.signature: str | None = None`,
  all defaulted.
- **Places** are chosen deterministically from the galaxy at assignment: the
  nearest Bloom-held system, a Freehold capital, a moon suitable for a garden.
  If an arc names the Reaches and they are unopened, the beat waits
  (patiently: no lapse while unreachable) and the despatch says what would
  open the way.
- **Clock:** `arcs.tick(game, n, r)` in sector time. Arcs don't fire in the
  first 45 days, or during the tutorial's first chapters.
- **Walkouts:** a lapsed final beat can make an officer leave. Use the
  existing loyalty and walkout path, and never delete an officer anywhere
  else.

## UI

- **Ship screen, crew tab:** each officer shows their arc title, the beat
  progress (○●●), the next beat's hint ("wants to go to Pale Fall") and the
  lapse countdown.
- **Despatches:** beats appear with their choices; answering uses the
  existing flow.
- **Codex:** "The crew" page with finished arcs and signatures.

## Balance targets

- An officer who stays about 3 years usually reaches the end of their arc if
  the captain engages.
- A signature trait is worth about a tier-2 fitting in its niche and nothing
  outside it.
- Ignoring all arcs costs some loyalty, not a mutiny.

## Tests (new suite `test_arcs`)

- Every arc is completable by a scripted captain from any officer.
- Each trigger type fires.
- Choice previews equal their consequences.
- Lapses cost loyalty, and a lapsed final beat can walk the officer out
  through the one path.
- Signature traits move their numbers (efficacy).
- Assignment is deterministic, and opening the crew tab changes nothing.
- An arc waiting on unopened Reaches does not lapse.
- Cross-process save mid-arc.
- The despatch board shows each beat.

## Notes from Wave A (read before building)

- Places may be in the Reaches (`sim/regions.opened`, `world/galaxy.local`);
  a beat that needs an unopened region waits without lapsing and says what
  would open the way (the deep anchor relight, `sim/relight`).
- Rivals exist (`sim/nemeses`, `game.hunt`): an arc may name one (the deserter's
  old unit, the gambler's creditor) — read it defensively.
- The Assembly exists (`sim/assembly`): an arc beat may ask the captain to
  speak at a sitting (the heir, the heretic).
- The Kith are being built in parallel: the pilgrim arc must work without
  them (generic comms bonus) and use `getattr(game, "kith", None)`.
