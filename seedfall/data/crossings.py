"""How hard you fly an interstellar crossing, and what each way costs.

Every jump was the same jump: a distance, a fuel bill, a number of days, and
nothing to decide. The drive had one setting and time was time.

Time is not time. A crossing flown hard runs the hull's own clock slow against
the Verge's, and the game now keeps both — `Game.day` for the sector and
`Game.ship_day` for the people aboard. `dilation` here is how many sector days
pass for each day lived aboard.

That turns a jump into a three-cornered trade, and none of the corners is
free:

- **Reaction mass.** Going fast enough for the clocks to disagree is
  expensive, and the tank is the one resource that strands you.
- **Your crew's lives.** A wet crew has about fifty working years. Flown hard,
  a decade of crossings costs them eighteen months. Flown slow, it costs them
  a decade — and eats a decade of food.
- **Everything you would have got done.** Research, repair, cooling and the
  smelter all run on ship time. Skip four years of ageing and you skip four
  years of the bench with it. The Verge does not skip anything: contracts
  expire, markets move, colonies grow and powers fall out while you are not
  there to see it.

So a hard burn is not "better". It is a way of spending fuel and progress to
buy back your crew's remaining years, and a long coast is the reverse.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Crossing:
    id: str
    name: str
    blurb: str
    #: Multipliers on the standard quote.
    days: float
    fuel: float
    #: Sector days per day lived aboard. 1.0 means the clocks agree.
    dilation: float
    #: What the captain should understand before committing.
    gives: str
    costs: str


CROSSINGS = [
    Crossing(
        "coast", "Long coast",
        "Light on the tank and heavy on the calendar. The drive idles, the "
        "bench runs, and the crew has a great deal of time to think.",
        days=1.55, fuel=0.45, dilation=1.0,
        gives="Half the reaction mass, and every day of it counts on the "
              "bench and in the workshop.",
        costs="Half again as long, and the crew lives every hour of it — "
              "ageing, eating and getting bored."),

    Crossing(
        "steady", "Steady transit",
        "The crossing as it has always been flown. The clocks agree and "
        "nobody has to think about it.",
        days=1.0, fuel=1.0, dilation=1.0,
        gives="No surprises in either direction.",
        costs="Nothing you would not expect."),

    Crossing(
        "hard", "Hard burn",
        "Stand the drive up and hold it there. The Verge ages about four "
        "days for every one aboard, which the crew will notice and the "
        "calendar will not forgive.",
        days=0.8, fuel=2.6, dilation=4.0,
        gives="A quarter of the ageing and a quarter of the stores, and you "
              "arrive sooner by the sector's clock too.",
        costs="Two and a half times the reaction mass, and three quarters of "
              "your research, repairs and refining simply do not happen."),

    Crossing(
        "relativistic", "Relativistic run",
        "Everything the drive has. Aboard it is a fortnight; outside it is "
        "most of a season. Used for crossings a wet crew would not otherwise "
        "survive, and for arriving somewhere before the news does.",
        days=0.7, fuel=5.0, dilation=11.0,
        gives="A crossing that costs a wet crew almost nothing of their span "
              "— the only way some of them are flown at all.",
        costs="Five times the mass, and the hull arrives having done nothing "
              "for a season. Whatever the Verge did meanwhile, it did "
              "without you."),
]
CROSSINGS_BY_ID = {c.id: c for c in CROSSINGS}

#: What a jump does when nobody chose — exactly the behaviour that shipped,
#: because the whole suite is written against it.
DEFAULT = "steady"
