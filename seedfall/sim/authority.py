"""Who runs this place, and what they will do to you while you are on it.

Everything in this file already existed and none of it was ever asked *about
a place*. The governance layer is deep — `sim/law` holds the charges,
`sim/tribunal` hears them, `sim/warrants` says what a power will do and how
far it will follow, `sim/enforce` puts hulls alongside, `sim/piracy` says how
far the law actually reaches out here, `sim/officials` puts a person behind
the harbourmaster's counter, `sim/territory` says whose ground this is and
`sim/grudge` says what they think of you — and a captain standing on a
concourse had no way to ask any of it.

So this is the noticeboard at the gate. One call, one place, and the answer
to the only question that matters when you walk down a gangway: **is this
somewhere I can be arrested, and by whom.**

It reads and never writes. Every number on it is somebody else's; the work
here is joining them to a *place* rather than to a system, which is what
makes the answer different at the Charter quay and at the free port in the
same orbit.
"""

from __future__ import annotations

from ..data import uwp
from ..data.factions import FACTIONS_BY_ID
from . import grudge as grudge_sim
from . import law as law_sim
from . import piracy as piracy_sim
from . import territory as territory_sim
from . import warrants as warrants_sim

#: What a law level actually means at the gate, in the words a crew uses.
#: The digit is Traveller's; the sentences are the Verge's.
LAW_WORDS = (
    (0, "No law at all. Whatever you brought, you may keep."),
    (2, "Almost nothing is forbidden. Nobody will look in your bag."),
    (4, "The obvious weapons. A polite question at the gate."),
    (6, "Most weapons, and some tools. They will look if you are unlucky."),
    (8, "Weapons, and a good deal else. They will look."),
    (10, "They will search you, and they will find it."),
    (99, "Papers at every door, and a reason wanted for each."),
)

#: How hard a place is policed, from `sim/piracy.lawlessness` — which runs
#: the other way, so this inverts it. A place is only as lawful as the space
#: around it: a class-A port in a system nobody patrols is a signboard.
def policing(game, system) -> float:
    """Between 0 (nobody is watching) and 1 (you will be stopped)."""
    return max(0.0, min(1.0, 1.0 - piracy_sim.lawlessness(game, system)))


def law_words(law: int) -> str:
    for ceiling, words in LAW_WORDS:
        if law <= ceiling:
            return words
    return LAW_WORDS[-1][1]


def government(game, place) -> tuple:
    """What sort of government runs this place: `(digit, name, note)`.

    A holding of yours is the one case with no answer in the table — the
    government is you — and saying so is better than dealing a digit.
    """
    if place.mine:
        return (-1, "Yours", "You run it, and it shows.")
    from . import profile as profile_sim
    system = next((s for s in game.galaxy.systems
                   if s.id == place.system_id), None)
    body = next((b for b in system.bodies if b.id == place.body_id), None) \
        if system is not None else None
    if system is None or body is None:
        return (-1, "Nobody's", "Nothing here answers for anything.")
    got = profile_sim.profile(game, system, body)
    row = uwp.GOVERNMENTS.get(got.government)
    if row is None:
        return (got.government, "Unrecorded", "Nobody has written it down.")
    return (got.government, row[0], row[1])


def holder(game, place) -> dict:
    """Whose ground this is, and what they currently think of you."""
    system = next((s for s in game.galaxy.systems
                   if s.id == place.system_id), None)
    power = place.faction or (territory_sim.claimant(game, system)
                              if system is not None else None)
    if not power:
        return {"power": "", "name": "Nobody", "regard": 0.0,
                "note": "Unclaimed. Nobody here answers for anybody."}
    faction = FACTIONS_BY_ID.get(power)
    return {"power": power,
            "name": faction.name if faction else power.title(),
            "regard": grudge_sim.feeling(game, power),
            "note": grudge_sim.standing_note(game, power),
            "hostile": grudge_sim.hostile_open(game, power)}


def against_you(game, place) -> dict:
    """What the law here actually has on you, and what it would do.

    The join the governance layer never had: a warrant is issued by a power
    and *reaches* a system, and the question a captain has is whether it
    reaches **this gangway**.
    """
    system = next((s for s in game.galaxy.systems
                   if s.id == place.system_id), None)
    held = warrants_sim.against(game, system) if system is not None else []
    power = place.faction
    charges = law_sim.open_charges(game, power) if power else \
        law_sim.open_charges(game)
    bites = [b for b in ("fine", "seize", "detain", "fire")
             if system is not None
             and warrants_sim.bites(game, b, system, power or None)]
    return {"warrants": held, "charges": charges, "bites": bites,
            "bounty": warrants_sim.bounty(game, system)
            if system is not None else 0.0,
            "worst": warrants_sim.worst(game, system)
            if system is not None else None}


def garrison(game, place) -> dict:
    """What force is actually here, and who it belongs to.

    A place with a `bastion` on it is policed by people standing on it; a
    quay in a system somebody patrols is policed by hulls that will arrive.
    Both matter and they are not the same thing.
    """
    system = next((s for s in game.galaxy.systems
                   if s.id == place.system_id), None)
    watch = policing(game, system) if system is not None else 0.0
    from ..data.colonies import COLONIES_BY_ID
    armed = 0
    for colony in getattr(game, "colonies", []) or []:
        if colony.system_id != place.system_id or not colony.online:
            continue
        klass = COLONIES_BY_ID.get(colony.class_id)
        if klass is not None and klass.effects.get("ward"):
            armed += 1
    return {"watch": watch, "posts": armed,
            "note": _watch_words(watch)}


def _watch_words(watch: float) -> str:
    if watch >= 0.8:
        return "Patrolled hard. Somebody will ask what you are doing."
    if watch >= 0.55:
        return "Patrolled. A hull goes past often enough to matter."
    if watch >= 0.3:
        return "Thin. The law is a signboard and a man with a list."
    return "Nobody is watching. Whatever happens here is between you and "\
           "whoever else is here."


def says(game, place) -> list:
    """The whole noticeboard, in the order somebody would read it."""
    said = []
    digit, name, note = government(game, place)
    said.append(f"Government: {name.lower()}"
                + (f" ({digit})" if digit >= 0 else "") + f" — {note}")
    said.append(f"Law level {place.law}: {law_words(place.law)}")
    who = holder(game, place)
    said.append(f"Held by {who['name']}. {who['note']}")
    watch = garrison(game, place)
    said.append(f"Policing: {watch['note']}")
    risk = against_you(game, place)
    if risk["charges"]:
        said.append(f"{len(risk['charges'])} charge(s) still open against "
                    "you.")
    if risk["bites"]:
        said.append("A warrant here would " + ", ".join(risk["bites"]) + ".")
    return said
