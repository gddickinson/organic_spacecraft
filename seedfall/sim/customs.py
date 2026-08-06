"""The contraband run: what it pays, and who looks in the hold.

A good is dear exactly where it is forbidden, and forbidden is a place you have
to dock. `premium()` is the reason to carry it; `inspect()` is the reason not
to. Neither is worth having without the other — a premium with no risk is free
money, and a risk with no premium is a tax nobody would ever choose to pay.

Scrutiny is the memory. Selling into a black market and being caught both raise
it; it decays over months. That is what stops the same run being repeatable
without limit at the same port.
"""

from __future__ import annotations

from ..data.commodities import BY_ID
from ..data.contraband import (CLEARANCES, REGIMES_BY_FACTION, SEIZURES)
from . import officials as officials_sim

#: Scrutiny at or above this and they are waiting for you.
BURNED = 1.0

#: How fast a power loses interest, per day. Tuned by playing careers rather
#: than guessed: at 0.004 a run put on more heat than a month shed, so scrutiny
#: ratcheted, the premium fell under the buy price and every career — fitted
#: out or not — ended down. Laying off for a season now actually clears you.
COOLING = 0.013

#: How far a fence knocks the price down where stolen cargo is arriving.
#:
#: A third at the very edge of raider country, nothing out on the safe lanes.
#: The point is that the quiet word is not one price everywhere: it used to
#: pay identically at a Charter capital and a Charter outpost, because nothing
#: in it knew where you were standing.
FENCE_GLUT = 0.35

#: How much more a practised fence can move, at the same place.
#:
#: The trade this makes: near the raiding you are paid about three quarters
#: and can shift roughly twice as much, so a full hold goes in one visit
#: instead of four and the total is better — while a policed capital pays top
#: price for as much as it can quietly take, which is not much.
FENCE_CHANNEL = 1.0


def regime(faction: str | None):
    return REGIMES_BY_FACTION.get(faction or "")


def outlaws(faction: str | None, cid: str) -> bool:
    reg = regime(faction)
    return bool(reg and cid in reg.outlaws)


def heat(game, faction: str | None) -> float:
    return float(game.scrutiny.get(faction or "", 0.0))


def add_heat(game, faction: str | None, amount: float) -> None:
    if not faction:
        return
    game.scrutiny[faction] = max(0.0, heat(game, faction) + amount)


def cool(game, days: int) -> None:
    """Interest fades. Called from the clock, so it fades whatever you do."""
    for faction, level in list(game.scrutiny.items()):
        left = level - COOLING * days
        if left <= 0.001:
            game.scrutiny.pop(faction, None)
        else:
            game.scrutiny[faction] = left


def aboard(game, faction: str | None) -> list[tuple[str, float]]:
    """What is in the hold that this power would seize."""
    reg = regime(faction)
    if not reg or not reg.outlaws:
        return []
    return [(cid, tonnes) for cid, tonnes in game.ship.cargo.items()
            if cid in reg.outlaws and tonnes > 0.01]


# ── what it pays ───────────────────────────────────────────────────────────

def premium(game, faction: str | None, cid: str) -> int | None:
    """What an unposted buyer pays here, or None if the good is not outlawed.

    Scarcity is the whole of it: a power that seizes a good on sight has no
    legal supply of it, and the harder it looks the less there is. Scrutiny
    cuts the price too — a market that has just been raided is a nervous one.
    """
    reg = regime(faction)
    if not reg or cid not in reg.outlaws:
        return None
    good = BY_ID.get(cid)
    if good is None:
        return None
    nerve = max(0.55, 1.0 - heat(game, faction) * 0.45)
    # And what is already on the wharf. A market close to where hulls are
    # being taken is a market with somebody else's cargo in it already, and
    # that is the half of contraband the game never had — see
    # `piracy.fence_pull`, and note it is a *distance*, because raiders never
    # work a system with a port and so can never supply one directly.
    from . import piracy as piracy_sim
    glut = 1.0 - FENCE_GLUT * piracy_sim.fence_pull(game, game.system)
    return max(1, round(good.base * (1.15 + reg.zeal * 0.7) * nerve * glut))


# ── who looks ──────────────────────────────────────────────────────────────

def chance(game, faction: str | None, approach: float = 0.0) -> float:
    """Odds the hold is opened at this dock.

    The port sets the exposure; standing, a clean approach and a concealed hold
    each take a *share* off it. Subtracting them instead let a fitted-out hull
    with good standing drive the number under the floor and stop being a
    smuggler at all — the three together should roughly halve the risk, not
    retire it. It is never zero and never certain: a run you cannot lose is not
    a run.
    """
    reg = regime(faction)
    if not reg or not reg.zeal:
        return 0.0
    port = game.system.port
    level = port.level if port else 1

    odds = reg.zeal * (0.14 + 0.06 * level) + heat(game, faction) * 0.45
    relief = ((1 - min(0.45, getattr(game.ship_stats, "conceal", 0.0)))
              * (1 - min(0.22, max(0.0, game.rep.get(faction, 0)) / 100 * 0.22))
              * (1 - min(0.18, approach * 0.06)))
    return min(0.92, max(0.03, odds * relief))


def absorbs(game, faction: str | None) -> float:
    """Tonnage an unposted buyer will take in one visit.

    Without this the quiet word scales without limit and a large enough hold
    is a money printer. They will move what they can move.
    """
    port = game.system.port
    level = port.level if port else 1
    # A place used to handling stolen cargo has the people and the paperwork
    # to move more of it, which is the other side of `FENCE_GLUT`: near the
    # raiding you are paid less and can shift far more.
    from . import piracy as piracy_sim
    channel = 1.0 + FENCE_CHANNEL * piracy_sim.fence_pull(game, game.system)
    return round(6 + 9 * level * max(0.4, 1 - heat(game, faction) * 0.5)
                 * channel, 1)


def value(game, faction: str | None) -> float:
    """What the seizable cargo is worth at this port's unposted price."""
    total = 0.0
    for cid, tonnes in aboard(game, faction):
        price = premium(game, faction, cid)
        total += (price or BY_ID[cid].base) * tonnes
    return total


def tonnage_of(carrying) -> float:
    """Total tonnes in a seizure list, for the lines that quote it."""
    return sum(t for _cid, t in carrying)


def inspect(game, rng, approach: float = 0.0) -> dict:
    """Come alongside with a dirty hold and find out.

    Returns ``searched``/``caught`` and the copy to show. A clean hold is not
    searched at all: a dialog that fires on every dock and never says anything
    is noise, and noise is how a player learns to stop reading.
    """
    port = game.system.port
    faction = port.faction if port else None
    reg = regime(faction)
    carrying = aboard(game, faction)
    out = {"searched": False, "caught": False, "faction": faction,
           "regime": reg, "seized": [], "fine": 0.0, "goods": carrying}
    if not carrying or not reg:
        return out

    # A harbourmaster who owes you discretion signs the inspection off
    # without anybody opening a hold. This is what `wave_through` buys, and
    # the only place it is read.
    if officials_sim.anywhere(game, "wave_through"):
        out["waved"] = True
        out["copy"] = ("The inspection is signed off at the desk. Nobody "
                       "comes aboard, and nobody says why.")
        return out

    out["searched"] = True
    odds = chance(game, faction, approach)
    out["odds"] = odds
    if not rng.chance(odds):
        out["line"] = rng.pick(CLEARANCES)
        # Getting away with it is still being noticed a little.
        add_heat(game, faction, 0.05)
        game.add_log(f"Searched at {port.name} and cleared.", "")
        return out

    out["caught"] = True
    out["headline"], out["detail"] = rng.pick(SEIZURES)
    worth = value(game, faction)
    for cid, tonnes in carrying:
        out["seized"].append((cid, tonnes))
        game.ship.cargo.pop(cid, None)

    # Losing the cargo is most of the punishment already; a fine that doubled
    # it made a single bust unrecoverable at any volume worth carrying.
    fine = min(game.credits, worth * 0.35)
    out["fine"] = fine
    game.credits -= fine
    game.adjust_rep(faction, -max(4, min(22, worth / 2500)))
    # And it costs you with the person who runs the quay, not only with the
    # power. They signed the order; they are the one you have to face next
    # time you want a berth.
    officials_sim.adjust(
        game, game.system, -max(6.0, min(30.0, worth / 1800)),
        f"You were boarded here and {tonnage_of(carrying):.0f} t was seized.")
    add_heat(game, faction, 0.45)
    tonnage = sum(t for _c, t in carrying)
    game.add_log(f"Boarded at {port.name}: {tonnage:.0f} t seized for "
                 f"{reg.writ}. Fined {round(fine)}.", "bad")
    # The quay remembers the specific hold it opened, which is what the
    # harbourmaster brings up next time rather than a standing figure.
    from ..data.factions import FACTIONS_BY_ID
    from . import memory as memory_sim
    faction_name = getattr(FACTIONS_BY_ID.get(faction), "name", faction)
    memory_sim.note(game, f"port:{port.name}", "smuggling",
                    f"you brought {tonnage:.0f} t through this quay under "
                    f"{reg.writ}", 1.2, tags=["port", "customs", faction],
                    name=port.name, entity="port")
    memory_sim.note(game, f"faction:{faction}", "smuggling",
                    f"your hold was opened at {port.name}", 1.0,
                    tags=["customs", faction], name=faction_name,
                    entity="faction")
    # **And it goes on the file.** The fine above is the quay's own business,
    # settled at the counter; this is the power's, and it is what turns a bust
    # from a toll into something with a hearing at the end of it. They plainly
    # witnessed it — their people were in the hold — so the charge does not
    # have to guess.
    from . import dockets
    dockets.allege(game, faction, "contraband",
                   f"{tonnage:.0f} t taken out of your hold at {port.name}",
                   weight=min(2.5, 0.5 + tonnage / 14.0), seen=1.0)
    return out


def sell_quietly(game, cid: str) -> dict:
    """Move contraband off the books. Was a method on the port screen.

    They take what they can move and no more, and it puts their interest in
    you up whether or not anybody signed anything.
    """
    port = game.system.port
    faction = port.faction if port else None
    price = premium(game, faction, cid)
    held = game.ship.cargo.get(cid, 0.0)
    tonnes = min(held, absorbs(game, faction))
    if not price or tonnes <= 0:
        return {"ok": False, "why": "Nobody here wants it."}
    from .ship import add_cargo
    take = round(price * tonnes)
    game.credits += take
    add_cargo(game.ship, cid, -tonnes)
    add_heat(game, faction, 0.18)
    good = BY_ID.get(cid)
    game.add_log(f"Sold {tonnes:g} t of {good.short if good else cid} off the "
                 f"books at {port.name} — {take:,}.", "warn")
    # Off the books is not out of sight. Unlike a boarding, nobody has the
    # goods in their hands here, so `allege` works out for itself who could
    # plausibly have known — which is what makes a quiet sale at a frontier
    # quay a genuinely different proposition from one under a capital.
    from . import dockets
    dockets.allege(game, faction, "trafficking",
                   f"{tonnes:g} t moved off the register at {port.name}",
                   weight=min(2.0, 0.4 + tonnes / 18.0))
    return {"ok": True, "tonnes": tonnes, "price": price, "took": take,
            "all": tonnes >= held}


def jettison(game, cid: str) -> float:
    """Dump it before they board. Cheaper than a fine, dearer than nerve."""
    tonnes = game.ship.cargo.pop(cid, 0.0)
    if tonnes > 0:
        good = BY_ID.get(cid)
        game.add_log(f"Vented {tonnes:.0f} t of "
                     f"{good.short if good else cid} to space.", "warn")
    return tonnes


def standing_note(game, faction: str | None) -> tuple[str, str]:
    """How this power is currently disposed to look at you."""
    level = heat(game, faction)
    if level >= BURNED:
        return "they are waiting for you", "warn"
    if level >= 0.5:
        return "you are of interest here", "warn"
    if level >= 0.15:
        return "you have been noticed", "osteo"
    return "nothing on you here", "dim"
