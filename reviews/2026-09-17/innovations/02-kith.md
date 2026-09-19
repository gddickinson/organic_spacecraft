# Innovation 2 — The Kith (a living alien people)

## Why

The Verge's aliens are the dead and the unreachable:
- four extinct cultures known only through relics (xenotech);
- the Abyssals under the ice, reached only by the Genesis ending.

There is no living, reachable other: no one to *talk to* who is not human or
a machine. The Far Reaches (innovation 1) opened the Cradle and left it
unclaimed so that someone could live there.

## What the player gets

**The Kith**, a communal, spacefaring people native to the Cradle.
- **What they are like:**
  - Grown, not built, but *differently*: their hulls are colonial siphonophores
    of many bodies.
  - They speak in **modulated light**: a spectral song, not sound.
  - They trade by **reciprocity, not price**.
  - They are curious about grown ships and wary of fabricated ones.
- **Standing:** they have their own, *outside* the Concord set. The Concord
  stays the four powers, so no ending's requirement changes.
- **First meeting:** entering the Cradle for the first time triggers a first
  sighting. A Kith cluster keeps its distance, flashing, and a despatch
  records it.

### The lexicon (the core mechanic)

- 24 **signs** across 4 domains:
  - **Kin:** self, other, many, young, old, loss.
  - **Place:** here, there, far, light, dark, gate.
  - **Exchange:** give, take, enough, more, gift, debt.
  - **Intent:** peace, danger, question, yes, no, wait.
- Each sign's comprehension runs 0..1 and is learned by:
  - **Listening** at a Kith system: days spent, science officer and sensors.
  - **Decoding sessions** on the existing decoding bench (`sim/minigames.Decoding`),
    with the subject set to a Kith phrase. A win gives comprehension to the
    phrase's signs.
  - **Exchanges:** every gift exchange teaches the signs used in it.
  - **Phenomena observation** in the Cradle (innovation 7 hook). The Kith sing
    about their stars.
- **Comprehension gates acts:**
  - trade needs Exchange ≥ 0.4;
  - asking for passage or a berth needs Place plus Intent ≥ 0.5;
  - a **Kith accord** (treaty) needs every domain ≥ 0.7 plus standing.
- **Misunderstanding is real:** attempting an act with low comprehension has a
  stated chance of misreading, which costs Kith standing and sometimes means a
  fight.

### The gift economy

- Kith ports ("gatherings") have **no posted prices**. You offer a gift: any
  cargo from the hold.
- They **reciprocate** according to hidden **preferences**: each gathering
  values some goods and is offended by others. Biomass may read as offering
  corpses; condensate is prized; silicon is feared, "the stone".
- The preferences are learned: each exchange reveals the gathering's reaction,
  and the Exchange signs let you ask first ("more?", "enough?").
- **Reciprocation** is Kith goods:
  - **songglass**, a new commodity valued highly by the Charter and the Dry
    Choir;
  - **Kith grafts**, new organ parts for grown hulls only, e.g. a *chorus
    lens* (sensor), a *siphon bell* (cargo plus regen) and a *light-throat*
    (comms and diplomacy);
  - occasionally a **Kith pilot**, an officer of a new lineage.
- **Debt:** a gift you don't return keeps a debt, and a debt unpaid becomes an
  insult. This is the "no posted price" economy with its own honesty.

### Hulls

One or two Kith hull classes join the xeno family:
- the *choir-colony*, a mid-size siphonophore;
- a small *drifter*.

They are acquirable only at Kith accord. **Touch the hull tables carefully:**
"adding a family means touching all six" is about *families*, and this adds
classes *within* the existing xeno family.

### Connections to the other systems

- **Living hull (4):** Kith grafts react to adaptations. A graft set into a
  hull with a matching adaptation gains a bonus.
- **Renown (9):** first contact, the lexicon complete and a Kith accord are
  milestones.

## Design

- **Content:** `data/kith.py` holds the signs, domains, gatherings (templates
  for names, preferences and reactions), grafts (as parts, merged through
  `data/parts`), the songglass commodity and hull classes. Nameless signs are
  pictures: each sign has a glyph for the UI.
- **Rules:**
  - `sim/kith.py`: first contact, standing, the lexicon (learn, comprehension,
    `can(act)`), exchanges (offer → reaction → reciprocation → debt),
    misunderstanding odds (stated), and the accord;
  - `sim/kith_world.py`, only if needed for length: gathering placement in the
    Cradle, Kith traffic and movement.
- **Placement:** when the Cradle is generated (`world/regions`, from
  innovation 1), Kith gatherings are placed on 4–6 Cradle systems as
  `Port(..., faction="kith")` with a market flagged `gift_economy`. Use the
  region generator's own RNG stream so a Cradle generated before this
  innovation (an old save) can be **populated on load**: a migration step that
  adds gatherings to an already-open Cradle deterministically.
- **Faction:** add `kith` to `data/factions.py` as a **hidden** faction until
  first contact (like the Abyssals). Standing bands apply. `dip.POWERS` stays
  the four. Check every place that iterates `FACTIONS` for side effects (rep
  init, the Codex, diplomacy UI, encounters' candidate lists), and keep the
  Kith out of hostile encounter pools unless provoked.
- **State:** `Game.kith: object | None = None` holds a registered `KithState`:
  `met`, `lexicon` (sign → comprehension), `known_prefs` (gathering → good →
  reaction), `debts`, `accord`, `history`.
- **Trade gate:** where the port and market code assumes posted prices,
  refuse buying and selling at a gift-economy market with a reason that points
  to the exchange panel.

## UI

- **A Kith panel** at a gathering, replacing the market panel: the lexicon's
  domains as glyph rows filled by comprehension, the gift offer (pick cargo →
  preview of *expected* reaction given known preferences, with uncertainty
  stated), the reciprocation received, debts, and "listen for N days".
- **Decoding** reuses the bench (`ui/minigame_view`) with Kith glyphs.
- **Codex:** a Kith entry and a lexicon page.
- **Chart:** Cradle gatherings are marked once met.

## Tests (new suite `test_kith`)

- First contact fires on entering the Cradle, once.
- Each learning route raises comprehension (listening, decoding, exchange).
- The comprehension gates refuse with reasons, and the misunderstanding odds
  shown equal those rolled.
- The gift reaction preview is honest given known preferences.
- Debts become insults if unpaid.
- Songglass trades in the Verge.
- A graft fits only grown hulls.
- The accord unlocks the hulls.
- An old save with an open Cradle gets gatherings on load, deterministically.
- Cross-process save.
- The Concord ending is unchanged; the Kith are not in its set.

## Notes from Wave A (read before building)

- The Cradle exists (`world/regions.py`, `data/regions.py`, `sim/regions.py`):
  14 systems, **unclaimed, no ports**, generated when its deep anchor is relit.
  The `world/regions.py` docstring says how to add gatherings to an
  already-generated Cradle deterministically — follow it, and populate on
  load for saves whose Cradle was opened before the Kith existed.
- `regions.rule(game, system, "claimable")` is 0 in the regions: the powers
  cannot annex them. Kith gatherings are ports with `faction="kith"`.
- The Cradle dose (`sim/regions.dose`) already multiplies by the living hull's
  `adaptation.dose_multiplier`; Kith grafts may add to `ship.adaptations`
  synergy via `data/adaptations` (read it) — keep the graft bonus to one door.
- Sound (`ui/soundmap.py`) keys ambience off `System.region`; a gathering may
  want its own cue — optional, one table row in `data/sounds.py` if cheap.
- The decoding bench is `sim/minigames.Decoding` + `ui/minigame_view.py`.
