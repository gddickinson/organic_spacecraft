"""What a concourse is made of: the kinds of place, and what one place is.

Split from `data/venues.py` so the tables can be themed across four files
without any of them importing a list from another — the dataclass and the
kinds live here, the venues live beside their own sort, and `venues.py`
assembles them.

**A venue is a door, not a service.** It says what sort of place it is, how
much of a place a world has to be to carry it, what a night in it costs and
what that night buys. What can actually be *bought* through the door — a
bed, a surgery, a set of years off, a limb, a berth on a hiring board — is
`offers`, and the modules that sell those things read that tag. So a body
shop on a class-D rock and one in a Charter arcology are the same door with
different prices behind it, and neither needs its own code.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The kinds of place, in the order a concourse board lists them: what you
#: need, what you buy, where you sleep, what you do with the evening, and
#: the parts of it nobody advertises.
KINDS = (
    ("chandler", "Chandlers", "everything a person can carry"),
    ("market", "Markets and shops", "clothes, food, gifts, and the rest"),
    ("tech", "Tech and data", "boards, software, and who will fit it"),
    ("bank", "Banking", "somewhere to keep it, and a way to move it"),
    ("office", "Offices and halls", "agents, brokers, insurers, hiring boards"),
    ("law", "Law and licence", "papers, bonds, and the people who hold them"),
    ("transport", "Getting about", "lifts, shuttles, and the long way round"),
    ("lodging", "Lodging", "a bed that is not your own berth"),
    ("eatery", "Eating houses", "a meal, and who else is at the table"),
    ("clinic", "Clinics and bodywork", "health, years, and what can be fitted"),
    ("sport", "Sport and training", "bodies, used hard, on purpose"),
    ("arts", "Arts and spectacle", "somebody else's problems, well told"),
    ("entertainment", "Entertainments", "what the crew does with a night"),
    ("temple", "Houses and orders", "quiet, and somebody who will listen"),
    ("vice", "The other concourse", "no sign, no receipt, no questions"),
)
KIND_NAME = {k[0]: k[1] for k in KINDS}
KIND_NOTE = {k[0]: k[2] for k in KINDS}

#: What a door can sell besides an evening. Read by `sim/clinic.py`,
#: `sim/shore.py` and the hiring board — a tag here is a promise that some
#: module will honour it, and `tests/test_concourse` checks that it does.
OFFERS = (
    ("shelf", "personal equipment, off a shelf"),
    ("bank", "deposits, and a letter of credit"),
    ("bed", "somewhere to sleep that is not a berth"),
    ("meal", "food somebody else made"),
    ("care", "injuries, illness and the ordinary repairs"),
    ("surgery", "the serious repairs, under"),
    ("years", "anagathics, and what they cost"),
    ("ice", "cold storage for a person, by the year"),
    ("graft", "cloned tissue, organs and limbs"),
    ("cyber", "fitted hardware, and what it does to you"),
    ("gene", "the germ line, edited"),
    ("train", "a skill, taught properly, over weeks"),
    ("hire", "people looking for a berth"),
    ("paper", "licences, bonds and a notary"),
    ("data", "what somebody knows, for money"),
    ("fence", "buyers who ask nothing"),
)
OFFER_NAME = {o[0]: o[1] for o in OFFERS}


@dataclass(frozen=True)
class Venue:
    """One place on a concourse."""

    id: str
    name: str
    kind: str
    #: What a night in it costs a head, in credits. A counter charges nothing
    #: to walk into; the price is in what you do there.
    cr: int
    #: The least a place has to be: its amenity rating on the starport scale
    #: (`sim/places.amenity_for`), and its population digit.
    port: int = 1
    people: int = 0
    #: The least tech level that can run it, and the highest law level that
    #: will tolerate it. A chop shop needs TL 11 and law 5 or under; a
    #: chartered bank needs neither.
    tech: int = 0
    most_law: int = 99
    #: What it does: a morale lift for the crew, a loyalty lift for whoever
    #: went, and the chance of hearing something worth hearing.
    morale: float = 0.0
    loyalty: float = 0.0
    rumour: float = 0.0
    #: Standing with whoever holds the place, for being seen in the right room.
    standing: float = 0.0
    #: What it feels like, for the screen.
    note: str = ""
    #: A skill the evening favours — somebody with it gets more out of it.
    favours: str = ""
    #: Which of `OFFERS` can be bought here.
    offers: tuple = ()
    #: True for a door on your own hull (`data/venues_aboard.py`). A door is
    #: aboard or ashore and never both — otherwise a grand hotel would open
    #: in a cutter's crew quarters the moment the crew got large enough, and
    #: a sickbay would appear on a Charter concourse.
    aboard: bool = False
    #: The establishments (`data/establishments.py`) this door belongs to.
    #: A signature door is open at those and nowhere else.
    at: tuple = ()

    def sells(self, what: str) -> bool:
        return what in self.offers


def open_to(venue: Venue, place) -> bool:
    """Whether this door is open at this place.

    Four gates: how much of a place it is, how many people are in it, how
    advanced it is, and whether the law here tolerates it — and, at an
    establishment, whether the door is the kind of business it is.
    """
    if venue.aboard != (getattr(place, "kind", "") == "ship"):
        return False
    # An establishment opens its own signature doors, and of everybody
    # else's only the kinds it carries: a hotel has no chop shop.
    from .establishments import ESTABLISHMENT_BY_ID
    look = getattr(place, "look", "")
    if venue.at and look not in venue.at:
        return False
    est = ESTABLISHMENT_BY_ID.get(look)
    if est is not None and not venue.at and venue.kind not in est.kinds:
        return False
    return (place.amenity >= venue.port
            and place.people >= venue.people
            and place.tech >= venue.tech
            and place.law <= venue.most_law)
