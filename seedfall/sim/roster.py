"""The crew as a body: who is aboard, what they can do, and what they cost.

Every other crew module answers about *one* person — `sim/lifepath.py` what
they did, `sim/person.py` who they are, `sim/loyalty.py` how they feel,
`sim/lifespan.py` how long they have left. Nothing answered about the crew,
which is the question a captain actually has: *who is standing what watch,
what can this ship do between us, where is the hole, and what does the whole
of it cost me a day.*

So the Crew screen had nowhere to read from, and that is why the answer used
to be a grid of story cards on a tab of the Ship screen. This is the muster
book: it reads, it never writes, and everything on it is derived from what is
already saved — so it costs nothing to open and cannot drift from the truth.

**The ship's abilities are the interesting one.** A bridge is not six job
titles, it is the best level in every skill anybody aboard holds; a picket
gunner who spent a term on a survey hull is the reason the ship can read a
core sample at all. Asking it of the whole crew at once is what turns a list
of names into a capability.
"""

from __future__ import annotations

from ..data import backgrounds as bg
from ..data import careers as career_table
from ..data.lore import CREW_ROLES
from . import checks
from . import crew as crew_sim
from . import lifepath
from . import lifespan
from . import loyalty as loyalty_sim
from . import person as person_sim
from . import upkeep as upkeep_sim

#: The orders a roster can be read in, and what each is for. A crew list is
#: read to answer a question, and the question decides the order: who is where
#: (station), who is about to walk (loyalty), who is about to retire (age).
ORDERS = (
    ("station", "By station"),
    ("name", "By name"),
    ("loyalty", "By loyalty"),
    ("service", "By service"),
    ("age", "By age"),
)
ORDER_NAME = {oid: name for oid, name in ORDERS}

#: Skills below this are not worth a line in the ship's abilities. A level of
#: 0 is *trained*, which matters — `checks.UNTRAINED` is -3 — so the floor is
#: zero and not one.
ABILITY_FLOOR = 0


def active(game) -> list:
    """Everybody standing a watch, in the save's own order."""
    return lifespan.active(getattr(game, "officers", []) or [])


def muster(game) -> dict:
    """The whole complement in numbers: heads, money, food, mood.

    One call, because these are read together or not at all — a wage bill
    without the headcount beside it is a number nobody can act on.
    """
    officers = active(game)
    read = lifespan.crew_profile(game)
    mood = loyalty_sim.summary(game)
    want = upkeep_sim.demand(game)
    from . import dormancy
    under = dormancy.current(game)
    return {
        "officers": len(officers),
        "hands": read["count"],
        "heads": len(officers) + read["count"],
        "berths_free": lifespan.berths_free(game),
        "wages": crew_sim.daily_wages(officers),
        "bonus": crew_sim.bonus_cost(officers),
        "stores": sum(want.values()),
        "power": upkeep_sim.draw(game),
        "morale": float(getattr(game.ship, "morale", 0.0)),
        "loyalty": mood["mean"],
        "restless": mood["restless"],
        "asleep": (under.hands + len(under.officers)) if under else 0,
        "hands_note": lifespan.crew_note(game),
        "hands_band": read["band"],
        "over": read["over"],
    }


def stations(game) -> list:
    """The six watches, filled or empty, and what an empty one costs.

    A station nobody holds is the single most useful thing a crew screen can
    show, and it was shown nowhere: the berths board listed who was *offered*
    and you worked out the hole yourself.
    """
    held = {o.role: o for o in active(game)}
    rows = []
    for rid, name, stat, note in CREW_ROLES:
        officer = held.get(rid)
        band, tint = loyalty_sim.band(officer) if officer else ("", "warn")
        rows.append({"id": rid, "name": name, "stat": stat, "about": note,
                     "officer": officer, "band": band, "tint": tint,
                     "level": getattr(officer, "level", 0)})
    return rows


def abilities(game, floor: int = ABILITY_FLOOR) -> list:
    """Every skill the crew holds between them, best first, with whose it is.

    Read once for the whole bridge rather than `skill_aboard` per skill: a
    service record is derived and cheap, but forty skills times six officers
    is forty-two recomputations of the same six lives.
    """
    best: dict = {}
    for officer in active(game):
        record = lifepath.of(game, officer)
        for name, level in record.skills.items():
            if level < floor:
                continue
            if name not in best or level > best[name][0]:
                best[name] = (level, officer)
    rows = [{"skill": name, "level": level, "who": who,
             "about": career_table.SKILLS.get(name, "")}
            for name, (level, who) in best.items()]
    return sorted(rows, key=lambda r: (-r["level"], r["skill"]))


def missing(game) -> list:
    """Skills no one aboard has that this ship keeps needing.

    The other half of the abilities table, and the one that decides a hire.
    """
    have = {row["skill"] for row in abilities(game, floor=checks.UNTRAINED)}
    return [name for name in WANTED if name not in have]


#: What a hull in the Verge is forever wishing somebody aboard could do. Not
#: every skill — a ship does not need Art — but the ones a crossing, a port
#: and a boarding actually ask for.
WANTED = ("astrogation", "pilot", "engineer", "mechanic", "medic", "gunnery",
          "broker", "admin", "vacc_suit", "electronics")


def roll(game, order: str = "station") -> list:
    """The crew in the order asked for."""
    officers = list(active(game))
    if order == "name":
        return sorted(officers, key=lambda o: o.name)
    if order == "loyalty":
        return sorted(officers, key=lambda o: loyalty_sim.loyalty_of(o))
    if order == "service":
        return sorted(officers,
                      key=lambda o: -len(lifepath.of(game, o).terms))
    if order == "age":
        return sorted(officers, key=lambda o: -lifespan.age_of(o, game))
    places = {rid: n for n, (rid, _nm, _s, _t) in enumerate(CREW_ROLES)}
    return sorted(officers, key=lambda o: places.get(o.role, 99))


def short_names(officers) -> dict:
    """The shortest label that still tells two people apart, by officer id.

    A name bar that reads "Okonkwo · Adeyemi · Okonkwo" is a bar with a
    broken button on it — two officers on one bridge shared a surname and
    both tabs looked like the same person. Surnames where they are unique,
    first names where they are not, and the whole name when even that
    collides.
    """
    rows = list(officers)
    last: dict = {}
    for officer in rows:
        bits = str(getattr(officer, "name", "")).split()
        last.setdefault(bits[-1] if bits else "", []).append(officer)
    out = {}
    for name, sharing in last.items():
        for officer in sharing:
            bits = str(getattr(officer, "name", "")).split()
            if len(sharing) == 1:
                out[officer.id] = name
            elif len(bits) > 1:
                out[officer.id] = f"{bits[0]} {name[:1]}."
            else:
                out[officer.id] = officer.name
    return out


def pretty(skill: str) -> str:
    """A skill id as a person would say it."""
    return skill.replace("_", " ").title()


def card(game, officer) -> dict:
    """The facts a roster line shows about one person, all in one read.

    Deliberately the *short* form: a station, a mood, a life in one clause
    and the one thing they are best at. The whole of them is the sheet.
    """
    whole = person_sim.of(game, officer)
    record = whole.record
    band, tint = loyalty_sim.band(officer)
    top = sorted(record.skills.items(), key=lambda r: (-r[1], r[0]))[:3]
    wants = whole.wants
    home = whole.home
    return {
        "person": whole, "record": record,
        "band": band, "tint": tint,
        "loyalty": loyalty_sim.loyalty_of(officer),
        "conviction": loyalty_sim.conviction_of(officer),
        "career": record.career_name, "rank": record.rank,
        "terms": len(record.terms),
        "home": home.name if home is not None else "",
        "wants": wants.name if wants is not None else "",
        "age": lifespan.age_of(officer, game),
        "stage": lifespan.stage(officer, game),
        "span": lifespan.note(officer, game),
        "best": [(pretty(name), level) for name, level in top],
        "friends": len(whole.friends()),
        "trouble": len(whole.trouble()),
        "kit": len(whole.kit),
    }


def ties_ashore(game) -> list:
    """Everybody aboard who knows somebody out there, and which way they lean.

    A crew's relationships were derived and then only ever printed on their
    own sheet. Gathered, they are a fact about the *ship*: four people with
    creditors at Charter ports is a reason to put in somewhere else.
    """
    rows = []
    for whole in person_sim.aboard(game):
        for tie in whole.ties:
            rows.append({"who": whole.name, "tie": tie,
                         "kind": bg.TIE_BY_ID.get(tie.kind)})
    return sorted(rows, key=lambda r: (r["tie"].helps, r["who"]))


def departed(game) -> list:
    """Who has left the bridge, and how.

    Retired officers stay in `game.officers` with `retired` set — they are
    the chronicle's memory of a crew, and nothing has ever shown them.
    """
    rows = []
    # Who died on a deck rather than of their years (`sim/afoot_ends.py`).
    fallen = (getattr(game, "walked", None) or {}).get("fallen", {})
    for officer in getattr(game, "officers", []) or []:
        if not getattr(officer, "retired", False):
            continue
        rows.append({"officer": officer,
                     "age": lifespan.age_of(officer, game),
                     "note": fallen.get(str(officer.id))
                     or lifespan.note(officer, game)})
    return sorted(rows, key=lambda r: r["officer"].name)


def wage_bill(game, days: float = 30.0) -> dict:
    """What the crew costs over a stretch, in money and in tonnage."""
    said = muster(game)
    return {"days": days,
            "wages": said["wages"] * days,
            "stores": said["stores"] * days,
            "per_day": said["wages"],
            "afford": (getattr(game, "credits", 0.0) / said["wages"]
                       if said["wages"] > 0 else float("inf"))}
