"""Where the law actually touches the ship. Every dead reader wired to a live one.

The survey's list of things that were built and not connected reads like a
checklist, and this file is the checklist answered:

- **Smuggling risk was opt-in.** `customs.inspect` had exactly one call site,
  inside the docking mini-game, while three UI buttons docked you around it —
  one of them captioned *"Skip the approach and dock directly."* `at_dock` is
  now called by the berthing itself, so the risk belongs to carrying the
  cargo rather than to choosing the scenic route.
- **Patrols were furniture.** `ERRANDS["patrol"]` is `hostile=False`, parked
  at the quay body, never intercepting — while `piracy.lawlessness` built a
  five-term model of how policed a volume is and had exactly one moment, the
  jump exit, in which to use it. A patrol stops hulls now, and what it does
  when it stops you depends on what its power has on your file.
- **`BURNED = 1.0` — "they are waiting for you" — was a screen label** that no
  code path read. It is an input to `stopped_odds` now, which is what the
  words were always describing.
- **Two purchasable favours bought nothing.** "A berth regardless" overrides
  an interdict at that quay, which is exactly what it says on the tin.
- **`may_engage` had no political gate**: you could open fire inside a
  capital's approaches and the station would not react, because its ladder
  only escalates on unauthorised *closing*. Firing inside somebody's volume
  is an offence now, reported from `engage.open_fire`.

The refusals are all shaped `(bool, why)` because that is the shape every
screen in this project already consumes, and they say *who* and *why* rather
than going quiet: being stonewalled without being told why is the one failure
mode a governance layer must not have.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from . import warrants as warrants_sim

#: Chance a patrol takes an interest, per day in a system, at full attention.
STOP_PER_DAY = 0.055

#: What each thing on your file is worth to that chance.
PER_WARRANT = 0.45
PER_FILED = 0.18
HEAT_WORTH = 0.35



def _short(power: str) -> str:
    who = FACTIONS_BY_ID.get(power)
    return who.short if who else (power or "somebody")


# ── the four refusals ──────────────────────────────────────────────────────

def may_berth(game, system, contact=None) -> tuple[bool, str]:
    """Will a quay here take you? Asked by `sim/clearance`.

    The Charter's whole armoury is this function returning False.
    """
    for bite in ("shun", "refuse"):
        for power in warrants_sim.holders(game, bite, system):
            from . import wharfage
            if wharfage.holder(game, system) not in (power, None):
                if getattr(system, "faction", None) != power:
                    continue
            # "A berth regardless" — bought from this office, and until now
            # read by nothing at all.
            from . import officials as officials_sim
            if officials_sim.favour_running(game, system, "berth"):
                continue
            if bite == "shun":
                return False, (f"{_short(power)} does not answer. There is no "
                               "refusal and no reply; the channel is simply "
                               "not there.")
            return False, (f"{_short(power)} has interdicted you. No quay of "
                           "theirs will clear you while it stands.")
    return True, ""


def may_pass(game, system_id: int) -> tuple[bool, str]:
    """Will a ring wake for you? Asked by `sim/gates`."""
    system = _system_by_id(game, system_id)
    for bite, said in (("shun", "The ring does not acknowledge you."),
                       ("refuse", "The ring is closed against you.")):
        for power in warrants_sim.holders(game, bite, system):
            from . import gates
            if gates.holder(game, system_id) != power:
                continue
            return False, f"{_short(power)}: {said}"
    return True, ""


def may_trade(game, system) -> tuple[bool, str]:
    """Will a market price for you? Asked by `sim/market` and the port screen.

    Only anathema closes a counter. An interdict stops you *docking*; if you
    are somehow alongside anyway, they will still take your money — which is
    the difference between a power that excludes you and one that has removed
    you from the record.
    """
    if not warrants_sim.bites(game, "shun", system):
        return True, ""
    from . import wharfage
    keeper = wharfage.holder(game, system)
    for power in warrants_sim.holders(game, "shun", system):
        if keeper != power:
            continue
        return False, (f"{_short(power)} has struck you from the record. "
                       "Nothing here is priced for you.")
    return True, ""


def may_seed(game) -> tuple[bool, str]:
    """Is your licence in force? Asked wherever seed goes in the ground.

    The Charter's licence was a tradeable commodity with a price, no issuing
    authority, no revocation and no register of who held one. Now there is a
    revocation, and it is the sharpest instrument in the game against a
    captain whose whole plan was an empire of holdings.
    """
    for warrant in warrants_sim.in_force(game):
        if warrant.bite != "licence":
            continue
        return False, (f"{_short(warrant.power)} has suspended your licence. "
                       "No seed goes in the ground until it is restored.")
    return True, ""


def answers_hail(game, power: str) -> tuple[bool, str]:
    """Will they take the call? Asked by `sim/hail`."""
    if any(w.power == power and w.bite == "shun"
           for w in warrants_sim.in_force(game)):
        return False, (f"{_short(power)} does not answer. You are not being "
                       "refused; you have been removed from the record.")
    return True, ""


def _system_by_id(game, system_id):
    return next((s for s in game.galaxy.systems if s.id == system_id), None)


# ── being stopped ──────────────────────────────────────────────────────────

def watchers(game, system=None) -> list[str]:
    """Powers with hulls here that have something on you."""
    system = system if system is not None else getattr(game, "system", None)
    if system is None:
        return []
    from . import dockets
    from . import fleets as fleets_sim
    out = []
    for power in ("charter", "concordat", "freeholds", "sanhedrin"):
        if not fleets_sim.guard_at(game, system, power):
            continue
        if (dockets.exposure(game, power) > 0
                or warrants_sim.in_force(game, power)):
            out.append(power)
    return out


def stopped_odds(game, power: str, system=None) -> float:
    """How likely this power's patrol is to take an interest today.

    `customs.BURNED` finally means something: heat is "they are waiting for
    you", and this is the waiting.
    """
    from . import customs
    from . import law as law_sim
    live = warrants_sim.in_force(game, power)
    filed_n = len([c for c in law_sim.open_charges(game, power)
                   if c.state in ("filed", "answered")])
    odds = STOP_PER_DAY
    odds += PER_WARRANT * len(live)
    odds += PER_FILED * filed_n
    odds += HEAT_WORTH * min(1.0, customs.heat(game, power))
    return max(0.0, min(0.9, odds))


def stop(game, power: str, rng, system=None) -> dict:
    """A patrol comes alongside. What happens depends on what they hold.

    Four outcomes, in order of how much trouble you are in: they shoot, they
    take the cargo, they serve the summons, or they look and let you go.
    """
    system = system if system is not None else getattr(game, "system", None)
    short = _short(power)
    lines: list = []
    live = warrants_sim.in_force(game, power)
    bites = {w.bite for w in live if warrants_sim.reaches(game, w, system)}

    if "hunt" in bites:
        return {"kind": "hunt", "power": power,
                "said": (f"A {short} hull closes without hailing. There is a "
                         "price on you and they mean to collect it."),
                "lines": [("bad", f"{short}: they are not here to talk.")]}

    if "bond" in bites or _bond_defaulted(game, power):
        return _distrain(game, power, rng, system, seizing=True)

    filed = _serveable(game, power)
    if filed is not None:
        filed.state = "filed"
        lines.append(("bad", f"{short} put a boat across and served you. "
                             "The summons is aboard."))
        return {"kind": "served", "power": power, "charge": filed.id,
                "said": (f"A {short} patrol comes alongside and a rating "
                         "hands across a despatch. You have been served."),
                "lines": lines}

    # Nothing outstanding they can act on — so they do what a patrol does.
    from . import customs
    if customs.aboard(game, power):
        out = customs.inspect(game, rng)
        said = out.get("said") or "They searched, and found what you had."
        return {"kind": "searched", "power": power, "said": said,
                "lines": [("bad", f"{short}: {said}")], "result": out}
    # **No clock inside the clock.** The first draft charged the captain two
    # days here with `advance_days`, and `advance_days` runs `governance.tick`,
    # which runs this — measured as a RecursionError surfacing three modules
    # away in `settlement.maturity`, which is what re-entrancy always looks
    # like from the outside. Being stopped and cleared costs the afternoon in
    # the telling and nothing on the calendar.
    return {"kind": "clear", "power": power,
            "said": (f"A {short} patrol looks you over, opens two holds, "
                     "finds nothing, and lets you go."),
            "lines": [("warn", f"{short}: stopped, searched, released.")]}


def _serveable(game, power):
    """An alleged charge a patrol could serve in person, or None."""
    from . import dockets
    from . import law as law_sim
    for charge in law_sim.open_charges(game, power):
        if charge.state == "alleged" and dockets.will_file(game, charge):
            from ..data.forums import forum_of
            forum = forum_of(power)
            if forum is None:
                continue
            charge.filed_on = float(game.day)
            charge.due = float(game.day) + max(0.0, forum.notice)
            return charge
    return None


def _bond_defaulted(game, power: str) -> bool:
    from . import debts as debts_sim
    return any(d.kind == "bond" and float(game.day) > d.due
               for d in debts_sim.live(game, creditor=power))


def _distrain(game, power: str, rng, system, seizing: bool = False) -> dict:
    """They take goods against what they are owed."""
    from ..data.commodities import BY_ID as GOODS
    from . import debts as debts_sim
    short = _short(power)
    owed = debts_sim.total_owed(game, power)
    if owed <= 0:
        return {"kind": "clear", "power": power,
                "said": f"A {short} hull looks you over and sheers off.",
                "lines": []}
    taken: dict = {}
    worth = 0.0
    for cid, tonnes in sorted(game.ship.cargo.items(),
                              key=lambda kv: -kv[1]):
        if worth >= owed or tonnes <= 0:
            break
        good = GOODS.get(cid)
        unit = float(good.base) if good else 100.0
        want = min(tonnes, max(1.0, (owed - worth) / max(1.0, unit)))
        taken[cid] = round(want, 2)
        worth += want * unit
    for cid, tonnes in taken.items():
        game.ship.cargo[cid] = max(0.0, game.ship.cargo.get(cid, 0) - tonnes)
        if game.ship.cargo[cid] <= 0:
            game.ship.cargo.pop(cid, None)
    for debt in debts_sim.live(game, creditor=power):
        bite = min(worth, debts_sim.balance(game, debt))
        debt.paid += bite
        worth -= bite
        if debts_sim.balance(game, debt) <= debts_sim.SETTLED_UNDER:
            debt.settled = True
        if worth <= 0:
            break
    goods = ", ".join(f"{t:.0f} t of {c}" for c, t in taken.items()) or "nothing"
    return {"kind": "distrained", "power": power, "took": taken,
            "said": (f"A {short} cutter comes alongside and takes {goods} "
                     "against what you owe. Nobody asks."),
            "lines": [("bad", f"{short}: distrained — {goods}.")]}


def tick(game, days: float, rng) -> list:
    """Patrols taking an interest. Called from the clock."""
    out: list = []
    if getattr(game, "dead", None) or getattr(game, "victory", None):
        return out
    system = getattr(game, "system", None)
    if system is None:
        return out
    for power in watchers(game, system):
        odds = stopped_odds(game, power, system) * min(3.0, max(0.2, days))
        if not rng.chance(min(0.75, odds)):
            continue
        result = stop(game, power, rng, system)
        out.extend(result.get("lines") or [])
        if result["kind"] == "hunt":
            game.flags["law_hunted_by"] = power
        break                       # one boarding a tick is plenty
    return out


def note(game, system=None) -> str:
    """One line for the flight screens: who is looking, and how hard."""
    watching = watchers(game, system)
    if not watching:
        return ""
    worst = max(watching, key=lambda p: stopped_odds(game, p, system))
    return (f"{_short(worst)} hulls on station, and they have your file.")
