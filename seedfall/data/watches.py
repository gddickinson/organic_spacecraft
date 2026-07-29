"""What happens on the watches of a crossing.

Flying somewhere was: pick a destination, pay the reaction mass, watch the
calendar move, and occasionally read a line about something that had already
happened to you. The helm could plot an intercept and route around a star and
then had nothing to do for eleven days.

A crossing now runs in watches, and a watch can bring something that wants an
answer. Every option here costs one of the three things a transit has to spend
— time, reaction mass, or the hull — so there is no option that is simply best.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Option:
    id: str
    label: str
    blurb: str
    #: Tonnes of reaction mass, days added, hull damage, heat.
    fuel: float = 0.0
    days: int = 0
    damage: float = 0.0
    heat: float = 0.0
    #: Chance the choice goes badly anyway, and what it costs if it does.
    risk: float = 0.0
    risk_damage: float = 0.0
    #: Days lost if it goes badly. A risk that can only cost hull left the
    #: contact watch with a 45% chance of nothing at all.
    risk_days: int = 0
    risk_text: str = ""
    #: What it is worth if it comes off.
    salvage: dict = field(default_factory=dict)
    research: float = 0.0
    #: Ends the crossing early, back where you started.
    aborts: bool = False


@dataclass(frozen=True)
class Watch:
    id: str
    name: str
    tint: str
    text: str
    options: tuple[Option, ...]
    #: Relative frequency.
    weight: float = 1.0
    #: Only on a leg that passes near the star.
    hot_only: bool = False


WATCHES: list[Watch] = [
    Watch("debris", "Debris on the plot", "warn",
          "A stream of it, plotted late and moving fast enough that the closing "
          "speed does the damage rather than the mass. It is across the course "
          "for about four hours.",
          options=(
              Option("hold", "Hold the course",
                     "Present the epidermis and let it take what it takes.",
                     damage=14, risk=0.30, risk_damage=30,
                     risk_text="A fragment goes deeper than the epidermis."),
              Option("around", "Burn around it",
                     "Two hours of hard lateral and a day added to the leg.",
                     fuel=4, days=1),
              Option("slow", "Take the speed off",
                     "Arrive at it slowly enough that it is only dust.",
                     days=2),
          )),

    Watch("flutter", "Radiator flutter", "osteo",
          "A bloom lobe is not deploying cleanly and the hull is holding more "
          "heat every watch. It will not fix itself at this power setting.",
          options=(
              Option("press", "Press on and live with it",
                     "The mounts will be sluggish for a while afterwards.",
                     heat=22, risk=0.20, risk_damage=18,
                     risk_text="Something in the lobe lets go entirely."),
              Option("throttle", "Throttle back until it seats",
                     "Half power for a day and a half. It seats.",
                     days=2),
              Option("vent", "Vent the loop and refill",
                     "Reaction mass through the radiators. Wasteful and quick.",
                     fuel=6),
          )),

    Watch("hulk", "Something adrift", "steel",
          "A hull, cold, tumbling slowly, no beacon. It has been out here a "
          "long time and nobody has filed it.",
          options=(
              Option("board", "Put a party across",
                     "Three days, and whatever is left in it.",
                     days=3, salvage={"alloy": 22, "components": 6},
                     research=40, risk=0.18, risk_damage=12,
                     risk_text="Something aboard was still under pressure."),
              Option("beacon", "Strip the beacon and go",
                     "A day held alongside, and a transponder worth selling.",
                     days=1, salvage={"components": 3}, research=12),
              Option("log", "Log it and pass",
                     "Somebody else's problem, and somebody else's salvage.",
                     research=4),
          )),

    Watch("slug", "A bad slug of mass", "warn",
          "The reaction organ is passing something it does not like — a run of "
          "mass with too much silicate in it. The drive is knocking.",
          options=(
              Option("purge", "Purge the line",
                     "Dump the bad run overboard and lose what is in it.",
                     fuel=8),
              Option("run", "Run it through",
                     "It will clear eventually. Probably.",
                     risk=0.35, risk_damage=24,
                     risk_text="The knock becomes a crack in the throat."),
              Option("ease", "Ease the throttle until it clears",
                     "Slow, and it clears.", days=2),
          )),

    Watch("squall", "The star throws something", "warn",
          "A flare, and the leg is close enough in that the magnetosphere is "
          "not going to help. Suits are counting already.",
          hot_only=True,
          options=(
              Option("shelter", "Put the hull between it and the crew",
                     "Turn beam-on and hold. The epidermis takes the dose.",
                     damage=18, days=1),
              Option("run", "Burn out of it",
                     "Hard away from the star and back on course after.",
                     fuel=9, days=1),
              Option("ride", "Ride it out on course",
                     "Nobody wants this and it is the fastest way through.",
                     heat=16, risk=0.40, risk_damage=22,
                     risk_text="Two of the crew are in the medical bay for a "
                               "fortnight."),
          )),

    Watch("bloomlet", "The intima is fruiting", "chloro",
          "Somewhere in the long quiet of a coast the photosynthetic layer has "
          "decided conditions are excellent and started putting out bodies.",
          options=(
              Option("harvest", "Harvest it",
                     "Two days of careful work and a hold of good biomass.",
                     days=2, salvage={"biomass": 26}, research=18),
              Option("leave", "Leave it to reabsorb",
                     "It will take the mass back in a week and nobody loses.",
                     research=6),
          )),

    Watch("contact", "A hull on the same lane", "lumen",
          "Somebody else is running this leg, a little behind and closing. No "
          "transponder, which is not in itself unusual out here.",
          options=(
              Option("hail", "Hail them",
                     "Say who you are and see what comes back. They will know "
                     "who you are either way.",
                     research=8, risk=0.25, risk_damage=48,
                     risk_text="They knew the name, and they had been waiting "
                               "for it."),
              Option("dark", "Run dark and let them pass",
                     "Cold hull, no emissions, two days of drifting.",
                     days=2),
              Option("hold", "Hold course and see",
                     "They are probably nobody. Probably.",
                     risk=0.45, risk_damage=30, risk_days=3,
                     risk_text="They were not nobody. They come alongside, "
                               "take three days looking you over, and leave "
                               "a plate short."),
          )),
]

WATCHES_BY_ID = {w.id: w for w in WATCHES}

#: How many watches a crossing is divided into, by length in days.
def watches_for(days: int) -> int:
    if days <= 3:
        return 1
    if days <= 9:
        return 2
    if days <= 20:
        return 3
    return 4


#: Chance a given watch brings something.
EVENT_CHANCE = 0.55
