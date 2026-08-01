"""A settled world's authority, and the worlds nobody lives on that still bite.

The last piece of the approach-control brief. `sim/control.py` gave a structure
the right to hail, warn, fire on and refuse a hull. **The worlds themselves had
no say in any of it** — a hull could come down on somebody's colony and the
only thing that ever objected was gravity.

What makes it cheap is refusing to write a second ladder. A world gets the
whole of `sim/control.py` — the rungs, the patience, the ward that climbs, the
grievance that reaches the sector's memory — by answering the two questions
that machinery already asks. One line distinguishes the two authorities, and
it is the character of the whole feature:

    A world does not mind you in orbit. It minds you coming down.

The claims:

- **Orbiting is free and descending is not**, over the same world, in the same
  approach, changing nothing but the order.
- **Three kinds of claim, and most of them are on worlds nobody lives on.**
  Somebody working a seam will defend it; how good the seam is decides whether
  that means a battery or a radio call. Measured across twenty sectors:
  29% armed workings, 44% watched, 24% open, 2.7% something else.
- **The first draft made 93% of bodies armed** — a single threshold at 0.35
  against a generator whose median best seam is 0.72. A sky where nearly
  everything shoots teaches one rule and then stops being read.
- **A quiet site does not hail.** `Claim.floor` starts it at the ward, so the
  first you hear of it is being fired on — and `interdiction.line` says
  nothing about it, because a readout that warned would hand over what the
  sim is keeping.
- **A claim is derived, not rolled**, so the same rock is the same secret
  across a reload and across every screen that asks.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import clearance as clearance_sim
from ..sim import conn as conn_sim
from ..sim import control
from ..sim import interdiction as idn
from ..sim import landing
from ..sim import settlement as settlement_sim
from ..sim import targets as targets_sim
from ..sim import track as track_sim
from .harness import Suite

SEEDS = "abcdefghijklmnopqrst"


def _bodies(game):
    """(contact, body) for every world in the home system."""
    out = []
    for index, body in enumerate(game.system.bodies):
        found = next((c for c in track_sim.contacts(game)
                      if c.kind == "body" and c.body_index == index), None)
        if found is not None:
            out.append((found, body))
    return out


def _approach(game, contact):
    """A conn on this world, opened the way `berthing.begin` opens one.

    Not through `begin` itself only because that gate refuses anything more
    than a few thousand kilometres off and these worlds are AU away — the two
    lines that matter, the clearance and the watch, are the same two lines.
    """
    target = targets_sim.target_from_contact(game, contact)
    conn = conn_sim.start(game, target)
    conn.cleared = clearance_sim.request(game, contact, conn)
    conn.watch = control.post(game, contact)
    return conn


def _find(sort, means=None):
    """A game and a world whose sky is claimed in this particular way."""
    for seed in SEEDS:
        game = new_game(seed)
        for contact, body in _bodies(game):
            said = idn.claim(game, contact)
            if said is None or said.sort != sort:
                continue
            if means is not None and said.means != means:
                continue
            return game, contact, body, said
    raise AssertionError(f"no {sort!r} world at means {means} in twenty sectors")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a world does not mind you in orbit, and minds you coming down")
    def _():
        game, contact, body, said = _find("worked", means=idn.ARMED)
        conn = _approach(game, contact)
        assert control.has_control(conn), (
            "somebody is down there and nobody spoke for the world")
        assert control.welcome(conn), (
            "a hull merely in orbit was already unwelcome")
        assert control.step(conn, True) == "", "shot at for orbiting"

        landing.ditch(conn)
        assert not control.welcome(conn), (
            "ordered a descent onto somebody's workings and stayed welcome")
        assert idn.contested(conn)
        # And the ladder — the station's own, not a copy — now runs.
        rungs = []
        for _tick in range(60):
            told = control.step(conn, True)
            if told:
                rungs.append(control.LADDER[conn.told])
            if conn.told >= said.means:
                break
        assert rungs, "unwelcome and never told anything"
        assert control.ward_bite(conn) > 0.0, (
            f"climbed to {conn.told} and nothing was firing")
        return (f"{body.name}: orbit told nothing · descent → "
                f"{' → '.join(rungs)}, {control.ward_bite(conn):.2f} a tick")

    @check("most defended worlds are ones nobody lives on")
    def _():
        tally = {}
        for seed in SEEDS:
            game = new_game(seed)
            for contact, _body in _bodies(game):
                said = idn.claim(game, contact)
                key = f"{said.sort}/{said.means}" if said else "open"
                tally[key] = tally.get(key, 0) + 1
        total = sum(tally.values())
        armed = sum(v for k, v in tally.items()
                    if k != "open" and int(k.split("/")[1]) >= idn.ARMED)
        share = armed / total
        # The first draft: one threshold at 0.35 made this 0.93.
        assert 0.15 <= share <= 0.55, (
            f"{share:.0%} of the sector's bodies are armed — a sky where "
            "nearly everything shoots teaches one rule and stops being read")
        assert tally.get("open", 0) / total >= 0.1, (
            "nowhere in the sector can be flown at freely")
        assert not any(k.startswith("settled") for k in tally), (
            "a home system starts with people on a world, which #99 says it "
            "does not — this check is measuring the wrong thing")
        return " · ".join(f"{k} {v / total:.0%}"
                          for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))

    @check("what the seam is worth decides what they do about it")
    def _():
        rich = _find("worked", means=idn.ARMED)
        poor = _find("worked", means=idn.SPEAKS)
        def best(body):
            return max((getattr(body, "resources", None) or {}).values())
        assert best(rich[2]) >= idn.WORTH_KEEPING > best(poor[2]), (
            best(rich[2]), best(poor[2]))
        # And the difference is real at the sharp end: one can fire, one can
        # only talk, and `control.ward_bite` is the one door for both.
        for game, contact, _body, said in (rich, poor):
            conn = _approach(game, contact)
            landing.ditch(conn)
            for _tick in range(80):
                control.step(conn, True)
            assert conn.told == said.means, (conn.told, said.means)
        return (f"{rich[2].name} at {best(rich[2]):.2f} → batteries · "
                f"{poor[2].name} at {best(poor[2]):.2f} → a radio and no more")

    @check("a quiet site does not hail, and nothing warns you about it")
    def _():
        game, contact, body, said = _find("quiet")
        assert said.means == idn.QUIET_MEANS and said.floor == idn.ARMED
        assert said.who == "", (
            "a site nobody admits to named a power to bear the grudge")
        conn = _approach(game, contact)
        # The screen is silent. That is deliberate: a warning printed about a
        # thing that hides would give away what the sim is keeping.
        assert idn.line(game, conn) == "", idn.line(game, conn)
        landing.ditch(conn)
        first = ""
        for _tick in range(40):
            told = control.step(conn, True)
            if told:
                first = control.LADDER[conn.told]
                break
        assert first == control.LADDER[idn.ARMED], (
            f"the first thing it did was {first!r} — it hailed")
        assert control.ward_bite(conn) > 0.0, "opened at the ward and did not fire"
        return (f"{body.name}: no warning on any screen, and the opening move "
                f"is {first} — {control.ward_bite(conn):.2f} a tick")

    @check("a claim is derived, so the same rock is the same secret")
    def _():
        # The discipline `sim/anchorage` uses for a quay's whole existence. A
        # drawn number would make a site appear and vanish across a save.
        game, contact, body, said = _find("quiet")
        again = new_game(game.seed)
        twin = next(c for c in track_sim.contacts(again)
                    if c.kind == "body" and c.name == body.name)
        second = idn.claim(again, twin)
        assert second is not None and second == said, (said, second)
        # And five draws off the game's own luck do not move it.
        for _ in range(5):
            game.rng("shuffle").int(0, 99)
            assert idn.claim(game, contact) == said
        return f"{body.name} is the same claim after a fresh sector and five draws"

    @check("a world that is spoken for says so before you commit")
    def _():
        game, contact, body, said = _find("worked", means=idn.ARMED)
        conn = _approach(game, contact)
        told = idn.line(game, conn)
        assert told, "somebody has batteries down there and no screen says so"
        assert "under fire the whole way" in told, told
        # An open world says nothing, because there is nothing to say.
        for seed in SEEDS:
            free = new_game(seed)
            spare = next((c for c, _b in _bodies(free)
                          if idn.claim(free, c) is None), None)
            if spare is not None:
                assert idn.line(free, _approach(free, spare)) == ""
                break
        return told

    @check("shooting your way down reaches the power that owns the seam")
    def _():
        # `Claim.who` was declared and read by nothing — caught by the
        # project's own guard, which is what it is for. A body `Contact`
        # carries no faction, because until now no world answered for itself,
        # so the claim supplies the one the aftermath bills.
        from ..sim import forcing
        game, contact, body, said = _find("worked", means=idn.ARMED)
        conn = _approach(game, contact)
        assert conn.watch["faction"] == said.who, (conn.watch, said)
        landing.ditch(conn)
        for _tick in range(80):
            control.step(conn, True)
        grief = forcing.grievance(conn)
        assert grief and grief["faction"] == said.who, grief
        assert body.name in grief["text"], grief

        # And a quiet site leaves no record anywhere. `Claim.who` is "" for a
        # thing nobody admits to, so surviving one leaves nobody holding a
        # grudge — most of what makes it frightening.
        dark_game, dark_at, dark_body, _dark = _find("quiet")
        dark = _approach(dark_game, dark_at)
        assert dark.watch["faction"] == "", dark.watch
        landing.ditch(dark)
        for _tick in range(80):
            control.step(dark, True)
        assert not forcing.grievance(dark).get("faction"), (
            "a site nobody admits to filed a grudge under somebody's name")
        return (f"{said.who} remembers {body.name} · {dark_body.name} leaves "
                "nobody to remember it")

    @check("people outrank property, and secrets hide where neither is")
    def _():
        # The order `claim` asks in, which is the whole of how the three kinds
        # compose. Put people on a body that was already spoken for and the
        # settlement answers for it.
        game, contact, body, was = _find("worked")
        assert was.sort == "worked"
        made = settlement_sim.Settlement(
            id=9001, power="freeholds", system_id=game.system.id,
            body_id=body.id, good="ore", founded=game.day)
        settlement_sim.held(game).append(made)
        now = idn.claim(game, contact)
        assert now is not None and now.sort == "settled", now
        assert now.who == "freeholds", now
        # And a quiet site is never on a body worth working.
        for seed in SEEDS:
            spare = new_game(seed)
            for hidden, rock in _bodies(spare):
                found = idn.claim(spare, hidden)
                if found is not None and found.sort == "quiet":
                    grades = getattr(rock, "resources", None) or {}
                    assert max(grades.values()) < idn.WORTH_WATCHING, (
                        f"{rock.name} hides something and is worth digging")
        return (f"{body.name}: {was.sort} → {now.sort} once people are on it, "
                "and nothing hides on a body worth working")
