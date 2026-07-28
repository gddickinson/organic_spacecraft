"""Standing orders — what the ship could usefully be doing next.

Fifteen systems went in one at a time, each perfectly discoverable to whoever
had just built it. A new captain gets a sector chart, one line of log, and no
indication that any of it exists: commissions sit behind a tab, consorts behind
owning a second hull, colony works behind a matured colony, the bench behind a
research screen nobody has a reason to open.

This is the index. Each entry names a condition worth acting on and where to go
about it, and `sim/orders.py` decides which apply. Nothing here is required —
the game never blocks on any of it — but nothing should stay invisible either.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Order:
    id: str
    title: str
    text: str
    #: Which screen answers it.
    goes_to: str
    #: Higher sorts first. Survival beats opportunity.
    weight: int
    tint: str = ""


ORDERS: list[Order] = [
    # ── things that will kill you ─────────────────────────────────────────
    Order("fuel", "Reaction mass is low",
          "Nothing else matters if the hull cannot move. Buy volatiles at a "
          "port, or crack ice off a comet with a harvest tendril.",
          goes_to="port", weight=100, tint="warn"),
    Order("air", "The air is going",
          "A breached pressure vessel or a dead intima. Dock and have it seen "
          "to before the reserve runs out.",
          goes_to="port", weight=99, tint="warn"),
    Order("breach", "The hull is open",
          "Something got through the pressure vessel. Every day it stays open "
          "costs you crew.",
          goes_to="port", weight=98, tint="warn"),
    Order("payroll", "The bridge has not been paid",
          "Officers notice immediately and remember for a long time. Find the "
          "money or expect to lose them.",
          goes_to="port", weight=90, tint="warn"),

    # ── the crew ──────────────────────────────────────────────────────────
    Order("restless", "Somebody wants a word",
          "An officer has had enough of how things are being run. A bonus or "
          "a week's shore leave buys back a great deal of goodwill.",
          goes_to="port", weight=70, tint="osteo"),

    # ── the ship ──────────────────────────────────────────────────────────
    Order("overloaded", "The hull is over its marks",
          "More is bolted on than the drive was built to shift, and it is "
          "costing speed and evasion. Something could come off.",
          goes_to="yard", weight=60, tint="osteo"),
    Order("escort", "A hull is sitting in a berth",
          "You own more than one and only one of them is doing anything. Order "
          "it to sail in company and it will fight beside you.",
          goes_to="yard", weight=45),

    # ── work worth having ─────────────────────────────────────────────────
    Order("commission", "Somebody wants a word with you privately",
          "Your standing is good enough that a power will put a commission to "
          "you — work that escalates, and pays properly at the end of it.",
          goes_to="port", weight=55),
    Order("contracts", "There is work on the board",
          "Postings at this port: cargo, bounties, surveys. Nothing is "
          "required, but standing is worth more than the fee.",
          goes_to="port", weight=30),
    Order("rumour", "There is word going round",
          "People at this port are talking about somewhere specific. Some of "
          "it is wrong; most of it is not.",
          goes_to="port", weight=35),

    # ── the long game ─────────────────────────────────────────────────────
    Order("research", "Nothing is on the bench",
          "Points are accruing unassigned. Pick a programme and they start "
          "being spent on it.",
          goes_to="tech", weight=50),
    Order("evidence", "The bench is short of material",
          "The programme is marking time for want of a particular kind of "
          "evidence. Surveys, landings, salvage and digs each feed a different "
          "sort of question.",
          goes_to="tech", weight=40),
    Order("survey", "Nothing here has been looked at properly",
          "A surveyed body tells you what is on it and feeds the bench. An "
          "unsurveyed one is a name and an orbit.",
          goes_to="system", weight=38),
    Order("land", "There is ground worth walking on",
          "A landing party brings back specimens, salvage and things nobody "
          "has catalogued. It also has to come home.",
          goes_to="system", weight=28),
    Order("colony", "You could put something down here",
          "A seed on the right body becomes a settlement that produces while "
          "you are elsewhere — and can be developed once it matures.",
          goes_to="system", weight=26),
    Order("works", "A colony is idle",
          "It has matured and is producing, and nothing further is being built "
          "there. Works change what a settlement is.",
          goes_to="empire", weight=36),
    Order("survey_sale", "You are carrying charts worth money",
          "A completely surveyed system sells once, to anybody with a survey "
          "office. Partial surveys are worth nothing.",
          goes_to="port", weight=32),

    # ── the sector ────────────────────────────────────────────────────────
    Order("venture", "The powers are moving",
          "Somebody is annexing, embargoing or courting somebody else. You can "
          "back it, work against it, or let it happen.",
          goes_to="diplomacy", weight=42),
    Order("bloom", "The Bloom is spreading",
          "It takes systems while you are doing other things. Burning it back "
          "needs armament, and the longer it is left the more it needs.",
          goes_to="map", weight=65, tint="warn"),
    Order("trade", "The hold is empty",
          "Buy where a thing is plentiful and sell where it is short. The "
          "register remembers what you saw at other ports.",
          goes_to="port", weight=20),
]

ORDERS_BY_ID = {o.id: o for o in ORDERS}

#: How many to show at once. More than this and it stops being advice.
SHOWN = 4
