"""An engagement, fought over the bridge the way the window fights one.

`actions.jump_to` hands back an encounter and leaves it to the caller, and the
window's caller does something with it: `map_view._jump` gives it to
`MainWindow.begin_combat`, the battle screen starts it with `combat.start`,
each order is one `combat.take_turn`, and the end is `aftermath.resolve` —
with a loss being `game.die` and a struck enemy a prize decision. The bridge's
`jump` verb dropped it on the floor (review 2026-09-17, #30), so a captain
flown from outside was never once ambushed on arrival: every raider in the
Verge was a line in a reply nobody read.

This is the same sequence, through the same doors and on the same draws of
the game's luck (`"engagement"`, `"combat"`, `"seize"`), held on the bridge's
side exactly as the window holds `win.battle`: not saved, because an
engagement never has been. While it is open, `waiting` reports it as
blocking and the acting verbs refuse, as the window's screens do.
"""

from __future__ import annotations

from ..sim import aftermath as aftermath_sim
from ..sim import combat as combat_sim
from ..sim import consorts as consort_sim
from ..sim import prize as prize_sim
from ..sim import stations as st_mod
from ..sim.ship import hull_pct
from . import checks
from .protocol import plain, verb

#: The engagement each game is in, by identity — what `win.battle` is.
_OPEN: dict = {}

#: Orders that are not a station's, as the battle screen's buttons send them.
PLAIN_ORDERS = ("salvo", "brace", "hail", "flee")

#: The verbs an open engagement still answers: it is what they are for.
ORDERS_VERBS = ("fight", "prize")

#: What a struck enemy can be made to do, as the dialog's three buttons.
PRIZES = {"take": prize_sim.take, "strip": prize_sim.strip,
          "release": prize_sim.release}


def current(game):
    """The engagement this game is in, or None."""
    held = _OPEN.get(id(game))
    if held is not None and held.game is not game:
        _OPEN.pop(id(game), None)       # a different game at a reused id
        return None
    return held


def begin(game, encounter: dict) -> dict:
    """Start the fight `jump_to` handed back — `BattleView.begin`, verbatim."""
    enemy = encounter["enemy"]
    b = combat_sim.start(
        game.ship, game.ship_stats, enemy,
        bonuses=game.bonuses, officers=game.officers,
        rep=game.rep.get(enemy.get("faction"), 0),
        no_parley=encounter.get("no_parley", False), game=game,
        rng=game.rng("engagement"), fleet=consort_sim.escorts_of(game))
    b.intro = encounter.get("intro", "")
    b.instar = encounter.get("instar")
    _OPEN[id(game)] = b
    return summary(b)


def orders(b) -> list:
    """Every order this turn will take, as the strings `fight` accepts."""
    out = [o.id for o in st_mod.ORDERS]
    out += list(PLAIN_ORDERS)
    out += [f"fire:{w.id}" for w in b.player.st.weapons if w.wpn]
    return out


def summary(b) -> dict:
    """The engagement as a caller needs it to decide the next order."""
    return {"enemy": b.enemy_name, "faction": b.enemy_faction,
            "intro": b.intro, "turn": b.turn, "band": b.band,
            "over": b.over, "result": b.result,
            "hull": round(hull_pct(b.player.ship), 3),
            "enemy_hull": round(hull_pct(b.enemy.ship), 3),
            "log": [entry[1] for entry in b.log[-6:]],     # (turn, text, kind)
            "prize": b.over and b.result == "struck" and not b.prized,
            "orders": [] if b.over else orders(b)}


def _action(b, order: str) -> dict:
    """An order string as the battle screen's action dict."""
    if order in st_mod.ORDERS_BY_ID:
        return {"type": "station", "order": order}
    if order in PLAIN_ORDERS:
        return {"type": order}
    if order.startswith("fire:"):
        weapon = order.split(":", 1)[1]
        if any(w.id == weapon and w.wpn for w in b.player.st.weapons):
            return {"type": "fire", "weapon_id": weapon}
    raise checks.Refused(f"No such order: {order!r}. Orders: "
                         f"{', '.join(orders(b))}.")


@verb("fight", "Give the next order in the engagement you are in.",
      acts=True)
def fight(game, order: str) -> dict:
    """One turn, through `MainWindow.battle_act`'s door, and the end through
    `BattleView._finish`'s: the aftermath, and a loss as a death."""
    b = current(game)
    if b is None or b.over:
        return {"ok": False, "why": "Nothing is shooting at you."}
    action = _action(b, checks.words(order, "order", 60, required=True))
    combat_sim.take_turn(b, action, game.rng("combat"))
    game.recompute()
    b.player.st = game.ship_stats
    out = {"ok": True, **summary(b)}
    if b.over:
        out["aftermath"] = plain(aftermath_sim.resolve(game, b,
                                                       game.rng("seize")))
        if b.result == "lost":
            game.die("Destroyed in action.")
            out["dead"] = game.dead
        if not out["prize"]:
            _OPEN.pop(id(game), None)
    return out


@verb("prize", "Decide a struck enemy: take, strip or release.", acts=True)
def prize(game, choice: str = "release") -> dict:
    """The dialog's three buttons. Releasing is also what closing it does."""
    b = current(game)
    if b is None or not (b.over and b.result == "struck") or b.prized:
        return {"ok": False, "why": "Nothing here has struck to you."}
    act = PRIZES.get(checks.words(choice, "choice", 20))
    if act is None:
        return {"ok": False, "why": f"take, strip or release, not {choice!r}."}
    told = act(game, b)
    if b.prized:
        _OPEN.pop(id(game), None)
    return {**told, "prized": b.prized}


def waiting_on(game) -> dict | None:
    """The engagement as `waiting` reports it, or None when there is none."""
    b = current(game)
    return None if b is None else summary(b)
