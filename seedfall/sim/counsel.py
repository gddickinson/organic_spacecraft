"""The first officer's counsel: three concrete next moves, computed from state.

New captains faced twenty-nine lessons and fifteen screens without a clear
"what now", and the standing orders (`sim/orders`) say what *kind* of thing
is worth doing without saying which one. Counsel names the one: this body,
that run, the paper on that raider — each with its reason and the act that
does it, ranked by the order a first officer would say them in:

1. anything urgent — fuel, food, hull, hands (`counsel_sources.urgent`);
2. a question waiting on an answer;
3. an idle bench, the desk's best run, survey data to sell;
4. a contract to fly, a house to charter or a line to open;
5. the next step on the road the captain follows, or the one furthest
   along (`sim/renown.focus`);
6. a body here nobody has surveyed; a bounty you can win;
7. a Reaches anchor under way; the living hull; an officer's arc; a dead
   hull to board, or an officer nobody has had a word with in months;
8. the Assembly sitting soon; a road to choose, if none is.

**Actionable, or refused for the reason shown.** Every suggestion names its
act (`verb`, `args`) — the sim function the matching button calls — and
`act` performs exactly that. A move whose act would refuse today carries the
refusal in `blocked`, word for word; `advise` puts every move that would go
through ahead of any that would not. `tests/test_renown` performs every
suggestion of 200 seeded states on a copy and holds it to that.
"""

from __future__ import annotations

from . import counsel_doors as doors
from . import counsel_sources as sources

#: How many the card shows.
SHOWN = 3


def moves(game) -> list:
    """Every suggestion today, ranked, before the cut to `SHOWN`."""
    from . import renown
    if getattr(game, "dead", False):
        return []
    track = renown.focus(game)
    out = (sources.urgent(game) + sources.answers(game)
           + sources.bench(game, track) + sources.freight(game)
           + doors.save_money(game) + sources.contracts(game)
           + doors.house(game) + doors.milestone(game, track)
           + sources.surveys(game) + doors.bounty(game)
           + doors.reaches(game) + doors.body(game) + doors.arcs(game)
           + doors.afoot(game)
           + doors.assembly(game) + doors.choose(game))
    seen: set = set()
    unique = []
    for s in out:
        if s["id"] in seen:
            continue
        seen.add(s["id"])
        unique.append(s)
    # Stable: equal weights keep the order above, which is the priority.
    return sorted(unique, key=lambda s: (bool(s["blocked"]), -s["weight"]))


def advise(game, limit: int = SHOWN) -> list:
    """The first officer's three."""
    return moves(game)[:limit]


def act(game, suggestion) -> dict:
    """Do what the suggestion says, through the door its button uses.

    Returns `{"ok", "why"}`; a suggestion that is only "look at this" (a
    question waiting, the next rung, an idle hauler) succeeds when the thing
    it points at is still there."""
    verb, args = suggestion["verb"], suggestion["args"]
    handler = _ACTS.get(verb)
    if handler is None:
        return {"ok": False, "why": f"No act called {verb!r}."}
    out = handler(game, **args)
    if isinstance(out, tuple):
        out = {"ok": out[0], "why": out[1]}
    return {"ok": bool(out.get("ok")), "why": out.get("why", "")}


def _buy(game, cid, units):
    from . import trade
    return trade.buy(game, cid, units)


def _jump(game, to):
    from . import actions
    return actions.jump_to(game, to)


def _repair(game):
    from . import services
    return services.repair(game)


def _sign_on(game, count):
    from . import lifespan
    return lifespan.sign_on(game, count)


def _research(game, tech):
    from . import research
    ok = research.set_project(game.research, tech)
    return {"ok": ok, "why": "" if ok else "That is not open to research."}


def _survey(game, body, method):
    from . import survey
    return survey.perform(game, body, method)


def _take_contract(game, id):          # noqa: A002 — the contract's own name
    from . import commitments, contracts
    board = contracts.board_for(game, game.system)
    c = next((c for c in board if c.id == id), None)
    if c is None:
        return {"ok": False, "why": "That posting is off the board."}
    return commitments.take_contract(game, c)


def _take_bounty(game, key):
    from . import hunts
    return hunts.take(game, key)


def _charter(game):
    from . import freightlines
    return freightlines.charter(game)


def _relight(game, region):
    from . import relight
    return relight.relight(game, region)


def _dive(game, body):
    from . import actions
    return actions.dive(game, body)


def _sell_survey(game):
    from . import trade
    return trade.sell_survey_data(game)


def _answer(game, what):
    """Navigation to a question: good while the question is still open."""
    from . import approach
    if what == "envoy":
        return {"ok": approach.holds(game), "why": "The envoy has gone."}
    held = getattr(game, what, None)
    live = held is not None and not getattr(held, "over", False)
    return {"ok": live, "why": "" if live else "Nothing is waiting."}


def _go(game):
    return {"ok": True, "why": ""}


def _walk(game, key, keys):
    """Put a party on a deck: the dead hull adrift, your own decks."""
    from . import afoot
    return afoot.begin(game, key, list(keys))


_ACTS = {"buy": _buy, "jump": _jump, "repair": _repair, "sign_on": _sign_on,
         "research": _research, "survey": _survey,
         "take_contract": _take_contract, "take_bounty": _take_bounty,
         "charter": _charter, "relight": _relight, "dive": _dive,
         "sell_survey": _sell_survey, "answer": _answer, "go": _go,
         "walk": _walk}
