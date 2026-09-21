"""Bodies: keeping them, mending them, improving them, and putting them away.

The part of a concourse the game had nothing of at all. A crew aged, took
wounds, lost levels to decline and went under on a crossing, and there was
nowhere in the Verge that would do anything about any of it — no surgery, no
anagathics, no cold berth you could buy by the year, no shop that would fit
you a better arm.

Four rungs, and the tech level decides which of them a place has reached:

- **Care** (any tech): a surgery, a physician, a bed for a week.
- **Surgery and graft** (TL 9+): the serious repairs, and cloned tissue.
- **Years** (TL 12+): anagathics, which buy back span and cost a fortune
  every month you stay on them.
- **Cyber and gene** (TL 11+ / TL 13+): fitted hardware, and the germ line.

The last two have a **second concourse** behind them (`data/venues_night.py`),
because the good clinics will not fit half of what exists and the shops that
will do not put a sign up. That is the whole shape of the thing: the law
level decides which door you go through, and the door decides what it costs
you — in money at one, and in something else at the other.
"""

from __future__ import annotations

from .venue_types import Venue

BODY: tuple = (
    # ── clinics: the ordinary repairs ──────────────────────────────────────
    Venue("sickbay", "The port sickbay", "clinic", 20, 1, 0,
          morale=0.02,
          note="One physician, two beds, and a queue.",
          favours="medic", offers=("care",)),
    Venue("surgery", "A surgery", "clinic", 60, 2, 2, tech=8,
          morale=0.03, loyalty=0.5,
          note="Clean, unhurried, and they will keep you in overnight.",
          favours="medic", offers=("care", "surgery")),
    Venue("infirmary", "The Orders' infirmary", "clinic", 25, 2, 2,
          morale=0.04, loyalty=1.5, standing=0.05,
          note="They will not ask what you can pay until afterwards.",
          favours="medic", offers=("care", "surgery")),
    Venue("hospital", "A hospital", "clinic", 140, 3, 4, tech=9,
          morale=0.05, loyalty=1.0,
          note="Wards, theatres, and somebody on the desk at four in the "
               "morning.",
          favours="medic", offers=("care", "surgery", "graft")),
    Venue("trauma_house", "A trauma house", "clinic", 200, 3, 3, tech=10,
          note="Built for a shipping accident. Very good at one.",
          favours="medic", offers=("care", "surgery", "graft")),

    # ── the long clinics: years, ice and the germ line ─────────────────────
    Venue("rejuve", "A rejuvenation clinic", "clinic", 0, 4, 5, tech=12,
          standing=0.10,
          note="Years, bought back a course at a time, at a price that "
               "explains a great deal about the Charter.",
          favours="pharmacy", offers=("care", "years", "graft")),
    Venue("cold_berths", "Commercial cold berths", "clinic", 0, 2, 2, tech=9,
          note="A rack of sleepers and a ledger. Paid by the year, in "
               "advance.",
          favours="medic", offers=("ice",)),
    Venue("vault_clinic", "A vitrification vault", "clinic", 0, 3, 4, tech=11,
          note="Sugar glass and patience. The Verge learned it from "
               "something older than the Verge.",
          favours="sciences", offers=("ice", "surgery")),
    Venue("germline", "A germ-line house", "clinic", 0, 4, 5, tech=13,
          standing=0.15,
          note="They will not touch you. They will discuss your children.",
          favours="sciences", offers=("gene",)),

    # ── bodywork: what can be fitted ───────────────────────────────────────
    Venue("prosthetics", "A prosthetist", "clinic", 0, 2, 3, tech=9,
          note="Hands, legs, eyes. Honest work, and it shows.",
          favours="cybernetics", offers=("graft", "cyber")),
    Venue("body_shop", "A body shop", "clinic", 0, 3, 4, tech=11,
          note="Fitted hardware, licensed and logged, with a warranty you "
               "will be glad of.",
          favours="cybernetics", offers=("cyber", "graft")),
    Venue("augment_house", "An augmentation house", "clinic", 0, 4, 5,
          tech=12, standing=0.10,
          note="The good work. Quiet rooms, and a waiting list.",
          favours="medic", offers=("cyber", "gene", "graft")),

    # ── sport, training and the use of a body ──────────────────────────────
    Venue("gym", "A gymnasium", "sport", 15, 1, 1,
          morale=0.03, loyalty=0.5,
          note="Weights bolted down, and somebody counting.",
          favours="athletics", offers=("train",)),
    Venue("zero_g_court", "The zero-g court", "sport", 35, 2, 2, tech=9,
          morale=0.06, loyalty=1.0,
          note="Three walls, no floor, and everybody is bad at it first.",
          favours="zero_g", offers=("train",)),
    Venue("range", "A shooting range", "sport", 30, 2, 2, most_law=7,
          morale=0.03,
          note="Lanes, ear defenders, and a bored marshal.",
          favours="gun_combat", offers=("train",)),
    Venue("dojo", "A training hall", "sport", 45, 2, 3,
          morale=0.04, loyalty=1.0,
          note="Somebody who has done it will show you how.",
          favours="teaching", offers=("train",)),
    Venue("academy", "A port academy", "sport", 0, 3, 4, tech=9,
          standing=0.05,
          note="Proper instruction, in a proper classroom, over weeks.",
          favours="teaching", offers=("train",)),
    Venue("pilots_sim", "The pilots' simulators", "sport", 55, 3, 3, tech=10,
          morale=0.04,
          note="Every approach you have ever got wrong, on demand.",
          favours="pilot", offers=("train",)),
    Venue("racing_pit", "The racing pits", "sport", 70, 3, 4, tech=10,
          morale=0.08, loyalty=1.0, rumour=0.25,
          note="Skiffs round the ring buoys, and money on all of it.",
          favours="pilot"),
    Venue("bathhouse", "The bathhouse", "sport", 60, 2, 2,
          morale=0.08, loyalty=1.5,
          note="Hot water, at length. On a hull this is a luxury."),

    # ── lodging ────────────────────────────────────────────────────────────
    Venue("bunkroom", "A dock bunkroom", "lodging", 14, 1, 0,
          morale=0.03,
          note="Twenty racks, one door, and it is not your watch.",
          offers=("bed",)),
    Venue("capsule_rack", "Capsule racks", "lodging", 22, 2, 2, tech=9,
          morale=0.04,
          note="A tube, a light and a lock. Better than it sounds.",
          offers=("bed",)),
    Venue("transit_hotel", "A transit hotel", "lodging", 85, 2, 3,
          morale=0.06, loyalty=1.0,
          note="A window, a door that locks, and nobody calling the watch.",
          offers=("bed",)),
    Venue("grand_hotel", "The grand hotel", "lodging", 420, 4, 5,
          morale=0.10, loyalty=2.0, standing=0.25, rumour=0.30,
          note="The lobby is the point, and the lobby knows it.",
          favours="persuade", offers=("bed",)),
    Venue("spa_resort", "A resort", "lodging", 300, 3, 4,
          morale=0.12, loyalty=2.5,
          note="A fortnight of not being aboard. It shows afterwards.",
          offers=("bed", "care")),
    Venue("flophouse", "A flophouse", "lodging", 6, 1, 1, most_law=7,
          morale=0.01, rumour=0.35,
          note="Nobody asks a name. Nobody remembers one either.",
          favours="streetwise", offers=("bed",)),
)
