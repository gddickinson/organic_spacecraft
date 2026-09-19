"""How a power votes at the Assembly, and what the vote does to the matrix.

A power's vote is its **interest**, a sum of named parts, every one of which
the forecast prints: its creed and doctrine (`data/assembly` stance, from
`data/factions`), pride in its own motion, what it thinks of whoever tabled it
(`sim/diplomacy.relation` — a rival's motion is a rival's motion), its agenda
(`data/diplomacy.AGENDAS`), its purse (`sim/exchequer`), the state of the
sector, and whatever the captain has done about it.

**The forecast is the vote.** `forecast` and `sit` read the same `interest`
through the same `tally`; a forecast taken on the sitting day with nothing
changed is the result, and `tests/test_assembly` holds it to that.
"""

from __future__ import annotations

from ..data.assembly import RESOLUTIONS_BY_ID
from ..data.diplomacy import AGENDAS, INITIAL_RELATIONS
from ..data.exchequer import WAR_CHEST
from ..data.factions import FACTIONS_BY_ID
from . import assembly
from . import diplomacy as dip

#: A power votes yes at this much interest, no at minus this, and abstains
#: between. The width of the abstention band is what makes a quiet word worth
#: having: most powers sit a point or two from a line.
YES_AT = 2.0

#: A power's pride in its own motion.
SPONSOR_PULL = 3.0

#: A grievance against the sponsor, measured from where the pair has always
#: stood (`data/diplomacy.INITIAL_RELATIONS`): a vote point against per
#: `REGARD_PER` of relation lost since, to a cap. Three things measured on the
#: way here, over ten idle sectors and five years each:
#:
#: - counted from zero, the opening grievances — already in the creed
#:   stances — were counted twice, and the Yards and the Freeholds voted down
#:   each other's every motion until both were at war with the Freeholds;
#: - counted for friends as well, every friendly pass made the next likelier
#:   and idle sectors ran up to +42 mean relation, Concord with nobody
#:   brokering it;
#: - counted against only (and with the ceasefire's lift, see
#:   `assembly_session.sit`), ten sectors nobody lobbies end at +3.7 on
#:   average (spread -26 to +30) with 49% of motions passing.
REGARD_PER = 12.0
REGARD_CAP = 2.5

#: A power whose agenda good the instrument feeds.
AGENDA_PULL = 1.5

#: What the Bloom's spread adds to every power's interest in the levy, in
#: full once `BLOOM_FULL` of the sector is growing. Idle sectors reach 40-70%
#: in five years, and at 4 points from a third the levy passed four-square
#: every time it was tabled: +18 mean relation from that one instrument.
BLOOM_PULL = 3.0
BLOOM_FULL = 0.5

#: What a sector full of smuggling adds for a power that searches holds.
SMUGGLING_PULL = 2.0

#: What an open war adds, for everyone not in it, to a ceasefire.
WAR_PULL = 2.0

#: What a relation moves by when the vote is counted. Co-voters — two powers
#: that voted the same way, yes or no — come closer; a power on the losing
#: side takes it out on each power that voted it down. Scaled within the
#: range by how hard they felt it: the top of each range is reached at
#: `CO_STRONG` and `LOST_STRONG` points of interest.
CO_VOTE = (3.0, 6.0)
LOST_VOTE = (4.0, 8.0)
CO_STRONG = 16.0
LOST_STRONG = 4.0


def party_names(item) -> tuple:
    """Who an instrument names, in the order it names them."""
    p = item.params
    if "power" in p:
        return (p["power"],)
    if "a" in p:
        return (p["a"], p["b"])
    return ()


def title(item) -> str:
    """The instrument's name with its parties written in."""
    res = RESOLUTIONS_BY_ID[item.res_id]
    return _fill(res.name, item)


def words(item) -> str:
    """What it does, in plain words, with its parties written in."""
    res = RESOLUTIONS_BY_ID[item.res_id]
    return _fill(res.plain, item)


def _fill(text: str, item) -> str:
    short = {p: FACTIONS_BY_ID[p].short for p in FACTIONS_BY_ID}
    p = item.params
    return text.format(power=short.get(p.get("power", ""), ""),
                       a=short.get(p.get("a", ""), ""),
                       b=short.get(p.get("b", ""), ""),
                       n=len(p.get("systems", ())))


def bloom_share(game) -> float:
    """How much of the sector is growing, 0..1."""
    from . import threat
    systems = game.galaxy.systems
    return len(threat.bloom_systems(game)) / max(1, len(systems))


def heat(game) -> float:
    """How hot the captain's holds have made the sector, 0..1."""
    return min(1.0, sum(float(v) for v in getattr(game, "scrutiny", {}).values()))


def wealth(game, power: str) -> float:
    """A purse against a war chest, 0..1 — what a cost is weighed against."""
    from . import exchequer
    return max(0.0, min(1.0, exchequer.purse(game, power).credits / WAR_CHEST))


def interest(game, item, power: str) -> list[tuple[str, float]]:
    """Every reason this power has, with what each is worth. Never empty."""
    res = RESOLUTIONS_BY_ID[item.res_id]
    named = party_names(item)
    out: list[tuple[str, float]] = []
    if power in named:
        out.append(("named in it", res.party))
    else:
        out.append((res.why[power], res.stance[power]))
    if power == item.sponsor:
        out.append(("their own motion", SPONSOR_PULL))
    else:
        out.append(_regard(game, power, item.sponsor, "the sponsor", 1.0))
    if res.shape == "power" and power not in named:
        out.append(_regard(game, power, named[0], "the target", -1.0))
    agenda = AGENDAS.get(power)
    if agenda and agenda.wants in res.feeds:
        out.append((f"it feeds what they want ({agenda.wants})", AGENDA_PULL))
    if res.costs:
        short = 1.0 - wealth(game, power)
        out.append(("what it costs their purse" if res.costs > 0
                    else "what it saves their purse", -res.costs * short))
    out.extend(_pressure(game, res, power, named))
    swing = assembly.ensure(game).lobby.get(item.key, {}).get(power, 0.0)
    if swing:
        out.append(("your lobbying", swing))
    return [(why, round(v, 2)) for why, v in out if abs(v) >= 0.005] or [
        ("no view either way", 0.0)]


def _regard(game, power: str, other: str, role: str, sign: float):
    rel = dip.relation(game, power, other)
    usual = INITIAL_RELATIONS.get((power, other),
                                  INITIAL_RELATIONS.get((other, power), 0.0))
    lost = max(0.0, usual - rel) / REGARD_PER
    band, _tint = dip.relation_band(rel)
    trend = "cooler than of old" if lost > 0 else "no worse than of old"
    return (f"{band.lower()} with {role}, the {FACTIONS_BY_ID[other].short}"
            f" — {trend}", -sign * min(REGARD_CAP, lost))


def _pressure(game, res, power: str, named: tuple) -> list:
    if res.pressure == "bloom":
        return [("the Bloom's spread",
                 BLOOM_PULL * min(1.0, bloom_share(game) / BLOOM_FULL))]
    if res.pressure == "smuggling":
        from ..data.contraband import REGIMES_BY_FACTION
        reg = REGIMES_BY_FACTION.get(power)
        if reg is not None and reg.zeal > 0:
            return [("smuggling in their space", SMUGGLING_PULL * heat(game))]
    if res.pressure == "war" and power not in named and named:
        from . import war
        if war.at_war(game, *named):
            return [("the war is bad for everybody", WAR_PULL)]
    return []


def speech(game, power: str) -> float:
    """What the captain's voice is worth to this power, in vote points, if
    they are in the chamber on the day. Comms and standing, both."""
    from .assembly_lobby import SPEECH_BASE, SPEECH_PER_DIPLOMACY
    skill = max(0.0, float(getattr(game.ship_stats, "diplomacy", 0.0)))
    heard = 0.5 + max(0.0, min(100.0, game.rep.get(power, 0.0))) / 100.0
    return round((SPEECH_BASE + SPEECH_PER_DIPLOMACY * skill) * heard, 2)


def score(game, item, power: str, present: bool) -> tuple[float, list]:
    """This power's interest, with the captain's speech if they are there."""
    reasons = interest(game, item, power)
    side = assembly.ensure(game).positions.get(item.key, "")
    if present and side:
        sway = speech(game, power) * (1.0 if side == "for" else -1.0)
        reasons.append(("your speech in the chamber", sway))
    return round(sum(v for _why, v in reasons), 2), reasons


def vote_of(value: float) -> str:
    if value >= YES_AT:
        return "yes"
    if value <= -YES_AT:
        return "no"
    return "abstain"


def tally(votes: dict) -> tuple[int, int, int, bool]:
    """(yes, no, abstain, passed): three of four, or two with two abstaining."""
    yes = sum(1 for v in votes.values() if v == "yes")
    no = sum(1 for v in votes.values() if v == "no")
    return yes, no, len(votes) - yes - no, yes >= 3 or (yes == 2 and no == 0)


def forecast(game, key: str, present: bool | None = None) -> dict:
    """How every power would vote on the tabled instrument `key` today.

    `present` is whether the captain is in the chamber; left out, it is where
    the ship is now. Returns {"votes", "scores", "reasons", "yes", "no",
    "abstain", "passes"}.
    """
    item = find(game, key)
    if item is None:
        return {}
    if present is None:
        from . import assembly_session
        present = assembly_session.present(game)
    out = {"votes": {}, "scores": {}, "reasons": {}}
    for power in dip.POWERS:
        value, reasons = score(game, item, power, present)
        out["scores"][power] = value
        out["votes"][power] = vote_of(value)
        out["reasons"][power] = reasons
    out["yes"], out["no"], out["abstain"], out["passes"] = tally(out["votes"])
    return out


def find(game, key: str):
    for item in assembly.ensure(game).agenda:
        if item.key == key:
            return item
    return None


def moves(votes: dict, scores: dict, passed: bool) -> dict:
    """What the count does to each pair, as {pair key: delta}."""
    won = "yes" if passed else "no"
    out = {}
    powers = sorted(votes)
    for i, a in enumerate(powers):
        for b in powers[i + 1:]:
            va, vb = votes[a], votes[b]
            if "abstain" in (va, vb):
                continue
            if va == vb:
                felt = min(1.0, (abs(scores[a]) + abs(scores[b])) / 2 / CO_STRONG)
                out[assembly.pair_key(a, b)] = round(
                    CO_VOTE[0] + (CO_VOTE[1] - CO_VOTE[0]) * felt, 2)
                continue
            loser = a if va != won else b
            felt = min(1.0, abs(scores[loser]) / LOST_STRONG)
            out[assembly.pair_key(a, b)] = -round(
                LOST_VOTE[0] + (LOST_VOTE[1] - LOST_VOTE[0]) * felt, 2)
    return out
