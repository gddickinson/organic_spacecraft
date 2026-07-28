"""What your officers believe, and what it costs you to ignore it.

An officer is not a stat block with a wage. Each one came from somewhere and
wants something, and the same act reads differently from three seats on the
same bridge: burning a Bloom system is a good day's work to a veteran of
Kessel's Reach and a lost archive to a xenologist. Convictions are how a crew
disagrees with you.

Deltas are applied to loyalty, which runs 0..100.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Loyalty every officer signs on with.
START = 62.0
FLOOR, CEILING = 0.0, 100.0

#: Below this an officer starts talking about leaving; below WALKOUT they go.
RESTLESS = 30.0
WALKOUT = 12.0


@dataclass(frozen=True)
class Conviction:
    id: str
    name: str
    blurb: str
    #: event id -> loyalty delta
    reacts: dict[str, float] = field(default_factory=dict)
    #: Standing with this faction pulls their loyalty along with it.
    aligned: str | None = None


CONVICTIONS: list[Conviction] = [
    Conviction(
        "licence", "Believes in the licence",
        "The registry exists for a reason and the reason is that people die "
        "without it. Keeps their paperwork in order and expects you to.",
        reacts={"treaty": 6, "parley": 4, "kill_licensed": -7,
                "denounce_charter": -8, "colony": 3},
        aligned="charter"),

    Conviction(
        "burner", "Wants the Bloom burned",
        "Was at Kessel's Reach, or lost somebody who was. Does not think the "
        "wild lineage is a research subject.",
        reacts={"bloom_kill": 8, "bloom_cleansed": 12, "bloom_spread": -5,
                "parley": -2, "xeno_study": -2}),

    Conviction(
        "xenophile", "Thinks it should be studied",
        "Every burned system is a library nobody read. Argues for the sample "
        "jar over the flamethrower, and is often right and never popular.",
        reacts={"xeno_study": 8, "xeno_incorporated": 10, "bloom_cleansed": -6,
                "first_contact": 12, "bloom_kill": -2}),

    Conviction(
        "free", "Freehold to the bone",
        "Nobody's licence, nobody's tariff. Would rather be shot at than "
        "inspected, and thinks a treaty is just a longer leash.",
        reacts={"treaty": -5, "denounce_charter": 7, "harbour": 6,
                "kill_licensed": 4, "colony": 2},
        aligned="freeholds"),

    Conviction(
        "builder", "Wants something left behind",
        "Ships wear out. A settlement with a slipway and a garrison is the "
        "only argument against entropy anybody has ever won.",
        reacts={"colony": 9, "work_done": 7, "colony_lost": -12,
                "harbour": 4}),

    Conviction(
        "purse", "In it for the money",
        "No speeches. Signed on for a wage and a share, and keeps a very clear "
        "account of both.",
        reacts={"payday": 6, "missed_pay": -9, "loot": 4, "trade_profit": 3}),

    Conviction(
        "shipmate", "Loyal to the hull, not the flag",
        "Cares what happens to the people on this ship and very little for "
        "anything beyond the airlock.",
        reacts={"consort_lost": -10, "breach": -6, "crew_death": -12,
                "repair": 4, "parley": 3}),
]

CONVICTIONS_BY_ID = {c.id: c for c in CONVICTIONS}

#: Events any officer feels, whatever they believe.
UNIVERSAL: dict[str, float] = {
    "missed_pay": -6.0,
    "payday": 1.5,
    "victory": 3.0,
    "defeat": -5.0,
    "breach": -2.0,
    "crew_death": -4.0,
    "shore_leave": 9.0,
    "bonus_paid": 7.0,
    "promoted": 5.0,
}

#: How loyalty reads at the rail, worst first. The edges are the same numbers
#: the mechanics turn on, so what the pill says is what the officer does:
#: below WALKOUT they are leaving, below RESTLESS they work at three quarters.
BANDS = [
    (0, "Mutinous", "bad"),
    (WALKOUT, "Restless", "warn"),
    (RESTLESS, "Steady", ""),
    (68, "Willing", "lumen"),
    (85, "Devoted", "chloro"),
]
