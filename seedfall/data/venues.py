"""What there is at a port besides a cargo counter: somewhere to spend money.

Until now a port was a market, a services desk and a berths board. A captain
with forty thousand credits could buy a fuel bunker and a hull refit and had
nowhere at all to buy a meal — which is strange, because the whole of the
Verge's social life happens on a concourse.

Four kinds of place, and **what is open depends on the world profile**
(`data/uwp.py`): a class-A port on a world of millions has a chandler that
stocks everything, three kinds of eating house and a licensed bank; a class-D
rock with four hundred people has a chandler's shed and somewhere that will
sell you a bowl of something. The port a captain flies to is a *choice* as a
result, which is what a profile is for.

Every venue here takes money and gives something back that is not money:
morale, loyalty, a rumour, a contact, a night's rest, or the standing that
comes of being seen in the right room. Nothing here creates credits — the one
rule this game holds above all others — and the bank is a place to *keep*
money and move it, not to make it.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The kinds of place, in the order a concourse board lists them.
KINDS = (
    ("chandler", "Chandlers", "everything a person can carry"),
    ("bank", "Banking", "somewhere to keep it, and a way to move it"),
    ("eatery", "Eating houses", "a meal, and who else is at the table"),
    ("entertainment", "Entertainments", "what the crew does with a night"),
)
KIND_NAME = {k[0]: k[1] for k in KINDS}


@dataclass(frozen=True)
class Venue:
    """One place on the concourse."""

    id: str
    name: str
    kind: str
    #: What it costs a head, in credits. A chandler and a bank charge nothing
    #: to walk into; the price is in what you do there.
    cr: int
    #: The smallest starport class and population digit that will carry it.
    #: A shipyard world has a members' club; a mining outpost does not.
    port: int = 1
    people: int = 0
    #: What it does: a morale lift for the crew, a loyalty lift for whoever
    #: went, and the chance of hearing something worth hearing.
    morale: float = 0.0
    loyalty: float = 0.0
    rumour: float = 0.0
    #: Standing with the port's own power, for being seen in the right room.
    standing: float = 0.0
    #: What it feels like, for the screen.
    note: str = ""
    #: A skill the evening favours — somebody with it gets more out of it.
    favours: str = ""


VENUES: tuple = (
    # ── chandlers ──────────────────────────────────────────────────────────
    Venue("shed", "The chandler's shed", "chandler", 0, 1, 0,
          note="A counter, a back room, and whatever came in last."),
    Venue("chandlery", "Port chandlery", "chandler", 0, 2, 3,
          note="Proper shelves, and somebody who knows what is on them."),
    Venue("emporium", "The emporium", "chandler", 0, 4, 5,
          note="Four floors. They will order in what they do not have."),
    Venue("backroom", "A back-room dealer", "chandler", 0, 1, 2,
          note="No sign, no receipt, and a wider catalogue.",
          favours="streetwise"),

    # ── banking ────────────────────────────────────────────────────────────
    Venue("strongbox", "The port strongbox", "bank", 0, 1, 0,
          note="A hole in a wall with a ledger beside it."),
    Venue("counting_house", "A counting house", "bank", 0, 2, 3,
          note="Deposits, letters of credit, and a man who remembers you."),
    Venue("charter_bank", "The Chartered Bank", "bank", 0, 3, 5,
          standing=0.2,
          note="Licensed, audited, and it will lend against a hull."),

    # ── eating houses ──────────────────────────────────────────────────────
    Venue("mess", "The crews' mess", "eatery", 12, 1, 0,
          morale=0.02, rumour=0.25,
          note="Whatever the vats made. Everybody is here."),
    Venue("noodle_stall", "A noodle stall", "eatery", 20, 1, 1,
          morale=0.03, rumour=0.30,
          note="Hot, fast, and the queue is where you hear things."),
    Venue("chophouse", "A chophouse", "eatery", 90, 2, 3,
          morale=0.06, loyalty=1.0, rumour=0.20,
          note="Grown meat, and they do not apologise for it."),
    Venue("garden_table", "A garden table", "eatery", 260, 3, 4,
          morale=0.09, loyalty=2.0, standing=0.1,
          note="Things that were grown in soil. On this world. Recently.",
          favours="steward"),
    Venue("orders_refectory", "The Orders' refectory", "eatery", 30, 2, 3,
          morale=0.04, loyalty=1.5, rumour=0.15,
          note="Plain, quiet, and nobody asks you anything.",
          favours="xenology"),
    Venue("captains_table", "The captains' table", "eatery", 600, 4, 5,
          morale=0.05, loyalty=1.0, standing=0.35, rumour=0.45,
          note="You are not paying for the food.", favours="diplomat"),

    # ── entertainments ─────────────────────────────────────────────────────
    Venue("dive", "A dockside dive", "entertainment", 25, 1, 0,
          morale=0.05, loyalty=1.0, rumour=0.40,
          note="Loud, cheap, and everybody has a hull to complain about.",
          favours="carouse"),
    Venue("gaming_floor", "The gaming floor", "entertainment", 120, 2, 3,
          morale=0.04, rumour=0.30,
          note="The odds are known and people play anyway.",
          favours="gambler"),
    Venue("bathhouse", "The bathhouse", "entertainment", 60, 2, 2,
          morale=0.08, loyalty=1.5,
          note="Hot water, at length. On a hull this is a luxury."),
    Venue("playhouse", "A playhouse", "entertainment", 80, 3, 4,
          morale=0.07, loyalty=1.0, standing=0.1,
          note="Four hours about somebody else's problems.", favours="art"),
    Venue("vault_concert", "A vault concert", "entertainment", 150, 3, 4,
          morale=0.09, loyalty=2.0, standing=0.15,
          note="Under the hab ring, where the acoustics are.", favours="art"),
    Venue("fight_pit", "The fight pit", "entertainment", 40, 1, 2,
          morale=0.04, loyalty=1.0, rumour=0.35,
          note="Nobody dies. Usually.", favours="athletics"),
    Venue("observation", "The observation deck", "entertainment", 15, 2, 1,
          morale=0.06, loyalty=1.0,
          note="A window, and the system going about its business."),
    Venue("club", "A members' club", "entertainment", 450, 4, 5,
          morale=0.04, standing=0.40, rumour=0.35,
          note="The door is the point.", favours="persuade"),
    Venue("kith_gathering", "A Kith gathering", "entertainment", 0, 1, 1,
          morale=0.05, loyalty=1.5, standing=0.1,
          note="You are a guest. Behave like one.", favours="xenology"),
)

VENUE_BY_ID = {v.id: v for v in VENUES}
BY_KIND = {kid: tuple(v for v in VENUES if v.kind == kid)
           for kid, _n, _note in KINDS}

#: How much a night ashore costs per head beyond the venue's own price —
#: the berth, the transit, the things nobody itemises.
ASHORE_OVERHEAD = 8

#: What a rumour heard on a concourse is worth knowing, and how often a place
#: that offers them actually produces one. Both kept here so the screen can
#: quote the odds before the captain spends anything.
RUMOUR_WORTH = "a name, a cargo, or where somebody has gone"
