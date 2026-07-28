"""Who outlaws what, and how hard they look for it.

An unlicensed seed was already the most valuable thing in the commodity table
and already flagged illegal, and neither fact meant anything: the Freeholds
both sold it and bought it, so a hold full of it never had to cross anybody
else's space, and nobody ever looked in the hold.

The two halves are here. A power that outlaws a good has no posted price for
it and therefore a much better unposted one — that is the reason to carry it.
The same power boards you at the dock — that is the reason not to.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Regime:
    faction: str
    #: Commodity ids this power will seize.
    outlaws: tuple[str, ...]
    #: How hard they look, 0..1. Drives both inspection odds and the premium:
    #: a good is dear exactly where it is difficult.
    zeal: float
    #: What they call the offence, in a log line.
    writ: str
    #: Read out when they come aboard.
    notice: str
    #: Read out when the hold is clean.
    waved: str


REGIMES: list[Regime] = [
    Regime(
        "charter", ("wildseed",), 0.9,
        "carriage of unlicensed reproductive material",
        "A Charter cutter comes alongside before you are made fast, and the "
        "officer who steps through is carrying a sequencer rather than a "
        "sidearm. The licensing regime is the only thing the Charter has that "
        "the Bloom has not already made a fool of, and they know it.",
        "The sequencer finds nothing that is not on your manifest. The officer "
        "seems almost disappointed, and signs you in."),

    Regime(
        "concordat", ("wildseed",), 0.5,
        "carriage of self-replicating stock",
        "Yards security board you in the lock, unhurried and thorough. They "
        "have no licensing regime to protect and no particular feeling about "
        "the Charter's; they simply will not have a thing aboard their station "
        "that can make more of itself.",
        "They find nothing that grows and lose interest immediately."),

    Regime(
        "sanhedrin", (), 0.0,
        "", "", ""),

    Regime(
        "freeholds", (), 0.0,
        "", "", ""),
]

REGIMES_BY_FACTION = {r.faction: r for r in REGIMES}

#: What a seizure sounds like. Drawn when they find it.
SEIZURES: tuple[tuple[str, str], ...] = (
    ("The hold is opened",
     "It takes them four minutes. Whatever you were told about that "
     "compartment when you bought the hull, they had heard it first."),
    ("A sample is taken",
     "The officer runs one seed and does not bother running a second. The "
     "sequencer's verdict is a single unlit line, which is somehow worse than "
     "an alarm."),
    ("The manifest is compared",
     "Not to what is in the hold — to what you bought, where, and from whom. "
     "They had that before you were made fast."),
)

#: A run that gets through. Flavour, and a reminder the risk was real.
CLEARANCES: tuple[str, ...] = (
    "They look in three places and not the fourth.",
    "The officer is at the end of a double watch and it shows.",
    "Your standing is read off a screen before anyone reaches the lock, and "
    "the search stops being thorough at about that moment.",
    "Something at the far end of the station goes wrong at a convenient "
    "moment. You do not ask.",
)
