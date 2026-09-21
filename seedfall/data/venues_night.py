"""The evening: eating, drinking, watching, listening, and the other concourse.

What a crew does when the watch turns. Every door here takes money and gives
back something that is not money — morale, loyalty, standing, or a name worth
having — and the ones at the bottom of the file give back rather more than
that, at a price a captain should read twice.

**The vice tier is gated the other way round.** Everywhere else in this game
a better place needs a *higher* number: more people, a better port, a higher
tech level. A chop shop, a fight pit that does not stop and a fence who asks
nothing need a **low law level** — `most_law` — so they appear on the rocks
and the free ports and vanish the moment a captain puts in somewhere the
Charter actually runs. That is the cyberpunk bargain stated as a table: the
work you want is where the law is not, and the law is not where you would
want to live.
"""

from __future__ import annotations

from .venue_types import Venue

NIGHT: tuple = (
    # ── eating ─────────────────────────────────────────────────────────────
    Venue("mess", "The crews' mess", "eatery", 12, 1, 0,
          morale=0.02, rumour=0.25,
          note="Whatever the vats made. Everybody is here.",
          offers=("meal",)),
    Venue("noodle_stall", "A noodle stall", "eatery", 20, 1, 1,
          morale=0.03, rumour=0.30,
          note="Hot, fast, and the queue is where you hear things.",
          offers=("meal",)),
    Venue("chophouse", "A chophouse", "eatery", 90, 2, 3,
          morale=0.06, loyalty=1.0, rumour=0.20,
          note="Grown meat, and they do not apologise for it.",
          offers=("meal",)),
    Venue("garden_table", "A garden table", "eatery", 260, 3, 4,
          morale=0.09, loyalty=2.0, standing=0.1,
          note="Things that were grown in soil. On this world. Recently.",
          favours="steward", offers=("meal",)),
    Venue("orders_refectory", "The Orders' refectory", "eatery", 30, 2, 3,
          morale=0.04, loyalty=1.5, rumour=0.15,
          note="Plain, quiet, and nobody asks you anything.",
          favours="xenology", offers=("meal",)),
    Venue("captains_table", "The captains' table", "eatery", 600, 4, 5,
          morale=0.05, loyalty=1.0, standing=0.35, rumour=0.45,
          note="You are not paying for the food.", favours="diplomat",
          offers=("meal",)),
    Venue("vat_canteen", "The vat canteen", "eatery", 7, 1, 1,
          morale=0.01, rumour=0.20,
          note="Protein, texture, a number on the wall. It is food.",
          offers=("meal",)),
    Venue("kith_table", "A Kith table", "eatery", 40, 2, 2,
          morale=0.07, loyalty=2.0, standing=0.1,
          note="You will not know what half of it is. Eat it anyway.",
          favours="xenology", offers=("meal",)),

    # ── entertainments ─────────────────────────────────────────────────────
    Venue("dive", "A dockside dive", "entertainment", 25, 1, 0,
          morale=0.05, loyalty=1.0, rumour=0.40,
          note="Loud, cheap, and everybody has a hull to complain about.",
          favours="carouse"),
    Venue("gaming_floor", "The gaming floor", "entertainment", 120, 2, 3,
          morale=0.04, rumour=0.30,
          note="The odds are known and people play anyway.",
          favours="gambler"),
    Venue("observation", "The observation deck", "entertainment", 15, 2, 1,
          morale=0.06, loyalty=1.0,
          note="A window, and the system going about its business."),
    Venue("club", "A members' club", "entertainment", 450, 4, 5,
          morale=0.04, standing=0.40, rumour=0.35,
          note="The door is the point.", favours="persuade"),
    Venue("kith_gathering", "A Kith gathering", "entertainment", 0, 1, 1,
          morale=0.05, loyalty=1.5, standing=0.1,
          note="You are a guest. Behave like one.", favours="xenology"),
    Venue("sim_parlour", "A sim parlour", "entertainment", 65, 2, 3, tech=11,
          morale=0.07, loyalty=0.5,
          note="Four hours of being somebody with a better life.",
          favours="computers"),
    Venue("dance_hall", "A dance hall", "entertainment", 35, 2, 3,
          morale=0.06, loyalty=1.0, rumour=0.25,
          note="Loud enough that nobody has to talk about the crossing.",
          favours="carouse"),
    Venue("fight_pit", "The fight pit", "entertainment", 40, 1, 2, most_law=7,
          morale=0.04, loyalty=1.0, rumour=0.35,
          note="Nobody dies. Usually.", favours="athletics"),

    # ── the arts ───────────────────────────────────────────────────────────
    Venue("playhouse", "A playhouse", "arts", 80, 3, 4,
          morale=0.07, loyalty=1.0, standing=0.1,
          note="Four hours about somebody else's problems.", favours="art"),
    Venue("vault_concert", "A vault concert", "arts", 150, 3, 4,
          morale=0.09, loyalty=2.0, standing=0.15,
          note="Under the hab ring, where the acoustics are.", favours="art"),
    Venue("gallery", "A gallery", "arts", 20, 3, 4,
          morale=0.04, standing=0.15,
          note="Half of it is Verge work. A quarter of it is not human.",
          favours="art"),
    Venue("opera", "The opera house", "arts", 520, 4, 5,
          morale=0.08, loyalty=1.5, standing=0.40, rumour=0.35,
          note="Five hours, one interval, and everybody who matters.",
          favours="diplomat"),
    Venue("recital", "A recital room", "arts", 45, 2, 3,
          morale=0.05, loyalty=1.0,
          note="Twenty chairs and somebody very good.", favours="art"),
    Venue("archive_hall", "The archive hall", "arts", 12, 2, 3,
          morale=0.03, rumour=0.25,
          note="What this place remembers about itself.",
          favours="investigate", offers=("data",)),

    # ── houses and orders ──────────────────────────────────────────────────
    Venue("chapel", "A dock chapel", "temple", 0, 1, 0,
          morale=0.03, loyalty=1.0,
          note="Open at all hours, because the hours are when it is needed."),
    Venue("orders_house", "An Orders' house", "temple", 0, 2, 2,
          morale=0.04, loyalty=2.0, standing=0.10,
          note="Quiet, and somebody who will sit with a person.",
          favours="xenology", offers=("care",)),
    Venue("memorial", "The mariners' memorial", "temple", 0, 2, 2,
          morale=0.02, loyalty=1.5,
          note="Names, and the years beside them. Some of them you know."),

    # ── the other concourse ────────────────────────────────────────────────
    Venue("chop_shop", "A chop shop", "vice", 0, 1, 2, tech=11, most_law=5,
          note="They will fit anything to anybody. Once. In an afternoon.",
          favours="cybernetics", offers=("cyber", "graft", "surgery")),
    Venue("black_clinic", "A black clinic", "vice", 0, 2, 3, tech=12,
          most_law=5,
          note="Years, without the paperwork, and without the warranty.",
          favours="pharmacy", offers=("years", "cyber", "gene")),
    Venue("ice_house", "An ice house", "vice", 0, 1, 2, tech=10, most_law=4,
          note="Nobody asks who is in the rack, or who is paying.",
          favours="streetwise", offers=("ice",)),
    Venue("fence", "A fence", "vice", 0, 1, 1, most_law=6,
          rumour=0.45,
          note="Buys anything, at a third, and forgets your face.",
          favours="streetwise", offers=("fence", "shelf")),
    Venue("den", "A den", "vice", 30, 1, 1, most_law=6,
          morale=0.09, loyalty=-1.0, rumour=0.35,
          note="Everybody comes out of it happier and worse.",
          favours="carouse"),
    Venue("blood_pit", "The blood pit", "vice", 60, 1, 1, most_law=3,
          morale=0.05, rumour=0.40,
          note="It does not stop when somebody falls over.",
          favours="gun_combat"),
    Venue("hiring_stone", "The hiring stone", "vice", 0, 1, 1, most_law=6,
          rumour=0.30,
          note="Whoever is standing on it will go anywhere, for anything.",
          favours="streetwise", offers=("hire",)),
    Venue("smugglers_rest", "The smugglers' rest", "vice", 45, 1, 1,
          most_law=4, morale=0.06, loyalty=1.0, rumour=0.50,
          note="Everybody here knows a way in somewhere.",
          favours="deception", offers=("data",)),
)
