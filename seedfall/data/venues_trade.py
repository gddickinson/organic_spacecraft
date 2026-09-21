"""The working half of a concourse: shops, counters, offices and the desk.

Everything here takes money and gives a thing or a piece of paper. Nothing
here is an evening — that is `data/venues_night.py` — and nothing here does
anything to a body, which is `data/venues_body.py`.

The two ends of the scale are the point. A class-E scratch on a frontier moon
has a chandler's shed, a strongbox with a ledger beside it and a man with a
flatbed who will drive you to the dome. A Charter arcology of ten million has
four floors of chandlery, a licensed bank, a commodity floor, a brokerage, a
notary, three kinds of shop and an orbital lift. Where a captain puts in is a
decision as a result, which is the whole reason a place has a profile.
"""

from __future__ import annotations

from .venue_types import Venue

TRADE: tuple = (
    # ── chandlers: what a person can carry ─────────────────────────────────
    Venue("shed", "The chandler's shed", "chandler", 0, 1, 0,
          note="A counter, a back room, and whatever came in last.",
          offers=("shelf",)),
    Venue("chandlery", "Port chandlery", "chandler", 0, 2, 3,
          note="Proper shelves, and somebody who knows what is on them.",
          offers=("shelf",)),
    Venue("emporium", "The emporium", "chandler", 0, 4, 5,
          note="Four floors. They will order in what they do not have.",
          offers=("shelf",)),
    Venue("backroom", "A back-room dealer", "chandler", 0, 1, 2, most_law=6,
          note="No sign, no receipt, and a wider catalogue.",
          favours="streetwise", offers=("shelf", "fence")),
    Venue("surplus", "Fleet surplus", "chandler", 0, 2, 3, tech=8,
          note="Somebody else's armour, at somebody else's price.",
          favours="admin", offers=("shelf",)),

    # ── markets: the ordinary shops ────────────────────────────────────────
    Venue("stalls", "The stalls", "market", 8, 1, 1,
          morale=0.02, rumour=0.20,
          note="Crates on the deck and everything haggled.",
          favours="broker", offers=("shelf",)),
    Venue("arcade", "The shopping arcade", "market", 30, 3, 4,
          morale=0.04, loyalty=0.5,
          note="Lit, warm, and designed so you walk the long way round."),
    Venue("outfitter", "An outfitter", "market", 0, 2, 3,
          note="Clothes that are not a ship suit. People notice.",
          standing=0.05, offers=("shelf",)),
    Venue("grocer", "The grocer's", "market", 0, 1, 2,
          note="Food for the hold that is not a commodity lot.",
          offers=("shelf",)),
    Venue("gift_hall", "The gift hall", "market", 0, 3, 4, tech=8,
          note="Things to take to somebody. The Verge runs on them.",
          favours="diplomat", offers=("shelf",)),

    # ── tech and data ──────────────────────────────────────────────────────
    Venue("board_shop", "A board shop", "tech", 0, 2, 3, tech=9,
          note="Boards, sensors, and a bench to test them on.",
          favours="electronics", offers=("shelf",)),
    Venue("software_house", "A software house", "tech", 0, 3, 4, tech=10,
          note="Expert systems, licensed by the seat and by the year.",
          favours="computers", offers=("shelf", "data")),
    Venue("data_haven", "A data haven", "tech", 0, 2, 3, tech=11, most_law=5,
          rumour=0.55,
          note="Nobody's jurisdiction, and everybody's back-ups.",
          favours="computers", offers=("data",)),
    Venue("fab_shop", "A fabrication shop", "tech", 0, 3, 4, tech=11,
          note="Give it a file and a day. It does not ask what for.",
          favours="mechanic", offers=("shelf",)),
    Venue("comms_house", "The comms house", "tech", 0, 2, 2, tech=9,
          rumour=0.30,
          note="Traffic in and out, and the people who read it.",
          favours="electronics", offers=("data",)),

    # ── banking ────────────────────────────────────────────────────────────
    Venue("strongbox", "The port strongbox", "bank", 0, 1, 0,
          note="A hole in a wall with a ledger beside it.",
          offers=("bank",)),
    Venue("counting_house", "A counting house", "bank", 0, 2, 3,
          note="Deposits, letters of credit, and a man who remembers you.",
          offers=("bank",)),
    Venue("charter_bank", "The Chartered Bank", "bank", 0, 3, 5,
          standing=0.2,
          note="Licensed, audited, and it will lend against a hull.",
          offers=("bank", "paper")),
    Venue("hawala", "A quiet remittance", "bank", 0, 1, 2, most_law=6,
          note="Money moves; no ledger says how.",
          favours="streetwise", offers=("bank",)),

    # ── offices, agents and hiring ─────────────────────────────────────────
    Venue("hiring_hall", "The hiring hall", "office", 0, 2, 3,
          rumour=0.25,
          note="Boards of berths, and people standing under them.",
          favours="leadership", offers=("hire",)),
    Venue("crew_agency", "A crewing agency", "office", 0, 3, 4,
          standing=0.05,
          note="Vetted hands, papers in order, and a fee on top.",
          favours="admin", offers=("hire", "paper")),
    Venue("brokerage", "A brokerage floor", "office", 0, 3, 4,
          rumour=0.35,
          note="Lots called, cargo moved, and nobody touches any of it.",
          favours="broker", offers=("data",)),
    Venue("insurer", "An insurer's office", "office", 0, 3, 4,
          note="They will quote you. You will not like it.",
          favours="admin", offers=("paper",)),
    Venue("assay", "An assay office", "office", 0, 2, 2,
          note="What your ore actually is, in writing.",
          favours="sciences", offers=("paper",)),
    Venue("factor", "A factor's rooms", "office", 0, 2, 3,
          rumour=0.30,
          note="Somebody who knows who wants what, and takes a cut.",
          favours="broker", offers=("data", "hire")),

    # ── law and licence ────────────────────────────────────────────────────
    Venue("notary", "A notary", "law", 0, 2, 2,
          note="A stamp, a witness, and a copy kept for forty years.",
          favours="law", offers=("paper",)),
    Venue("licence_office", "The licence office", "law", 0, 2, 3,
          note="Queues, forms, and a clerk who has seen everything.",
          favours="admin", offers=("paper",)),
    Venue("advocate", "An advocate's chambers", "law", 0, 3, 4,
          note="Expensive, and worth it exactly once.",
          favours="law", offers=("paper",)),
    Venue("bondsman", "A bail bondsman", "law", 0, 2, 2, most_law=8,
          note="They will stand for your hand. At a price, and with terms.",
          favours="streetwise", offers=("paper",)),
    Venue("constabulary", "The constabulary", "law", 0, 1, 1,
          note="Where a charge is answered, and where one is laid.",
          favours="security"),

    # ── getting about ──────────────────────────────────────────────────────
    Venue("flatbed", "A man with a flatbed", "transport", 6, 1, 0,
          note="It is a long walk otherwise.", favours="drive"),
    Venue("tramway", "The concourse tramway", "transport", 4, 2, 3,
          note="Every eleven minutes, and it is never eleven minutes."),
    Venue("orbital_lift", "The orbital lift", "transport", 40, 4, 5, tech=11,
          morale=0.03,
          note="Ninety minutes down a thread, with the world coming up."),
    Venue("shuttle_gate", "The shuttle gate", "transport", 25, 2, 2,
          note="Down, across, and back before the watch turns.",
          favours="flyer"),
    Venue("tour_boat", "A tour boat", "transport", 90, 3, 4,
          morale=0.06, loyalty=1.0,
          note="The rings, the wreck, and a drink at the turn.",
          favours="pilot"),
)
