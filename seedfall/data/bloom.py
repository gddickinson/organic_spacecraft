"""The Bloom's growth stages, its adaptations, and what waits at Kessel's Reach.

A lineage with its Hayflick counter cut out does not sit still and it does not
stay the same shape. It grows through instars, the way anything with a genome
does; it learns, in the only way an organism without a nervous system can learn,
by losing the lineages that did not survive what you did to them; and at the
centre of it there is the thing that germinated first.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Stage:
    id: int
    name: str
    tint: str
    #: burden (summed infestation across the sector) that triggers this stage
    threshold: float
    growth: float          # multiplier on per-tick growth
    spread: float          # multiplier on the chance to seed a clean system
    instars: int           # roaming masses it will keep in the field
    blurb: str
    herald: str            # what the log says when it arrives


STAGES: list[Stage] = [
    Stage(0, "Latent", "dim", 0.0, 1.00, 1.00, 0,
          "Rooted where it germinated, eating what it can reach. It has not yet "
          "done anything a Charter biologist would call surprising.",
          "The lineage at Kessel's Reach is holding at its original extent."),
    Stage(1, "Vegetative", "osteo", 4.0, 1.25, 1.35, 0,
          "Past the mass where a grown hull would have stopped. The growth "
          "collars are opening on their own schedule now.",
          "The Bloom has passed vegetative threshold. It is growing faster than "
          "the registry's worst curve."),
    Stage(2, "Motile", "warn", 9.0, 1.35, 1.55, 2,
          "It has stopped waiting. Masses the size of freighters are moving "
          "between systems under their own power, and they are not drifting.",
          "Motile instars sighted under way between systems. It is coming to "
          "us now."),
    Stage(3, "Adaptive", "warn", 15.0, 1.45, 1.70, 3,
          "Whatever killed the last one does not work as well on the next. "
          "There is no nervous system in it: the lineages that survived you "
          "are simply the ones still here.",
          "Tissue recovered from a burn shows resistance to the weapons that "
          "made it. It is learning by dying."),
    Stage(4, "Sovereign", "warn", 23.0, 1.55, 1.90, 5,
          "Coordinated across light-hours, with no signal anyone can find. It "
          "is taking ports now, and it is choosing which.",
          "It is coordinating. Nobody can find the signal and nobody doubts "
          "there is one."),
]

STAGES_BY_ID = {s.id: s for s in STAGES}

#: The stage the Bloom's own answering carries it to, indexed by how many
#: responses have fired (`sim/responses`). Burden was the only ladder, and
#: burden only climbs when nobody fights — measured over five seeds, stage 3
#: needed 3½–5½ *years* of total neglect, so adaptation, resistance and
#: hunting were dead content in any chronicle a captain actually played.
#: "harden" is the adaptation beat, so two answers carry it straight to
#: Adaptive; "hunt" is a Bloom that has your measure, which is Sovereign.
STAGE_BY_ANSWERS = (0, 1, 3, 3, 4)

#: Damage families the Bloom can build resistance to, keyed off the part that
#: dealt the damage. Vary your armament or watch it stop working.
RESIST_FAMILIES = ("grown", "fabricated", "synthetic", "xeno", "any")

#: How much resistance one family can reach, and how fast it accrues.
MAX_RESIST = 0.55
RESIST_PER_HIT = 0.0022
RESIST_DECAY = 0.00035        # per day, for families you have stopped using

#: The Heart — the original germination, still at Kessel's Reach.
HEART_HP = 2600.0
HEART_NAME = "The First Instar"
HEART_BLURB = (
    "Under eleven months of overgrowth there is a husk about two metres across "
    "with a Charter serial still legible on it. Everything in the Verge that "
    "carries this lineage came out of this. It is not defended, exactly. It is "
    "simply very large and very difficult to stop."
)

#: Log beats fired once each, when their condition is first met.
BEATS = {
    "first_colony_lost":
        "A colony has been taken. The tissue that took it is Charter-canonical "
        "down to the codon, which everyone aboard already knew and nobody had "
        "yet had to look at.",
    "first_port_threatened":
        "A port is inside the growth margin. The harbourmaster's last message "
        "asked whether the licence regime had any provision for this.",
    "heart_located":
        "The survey resolves it: under the overgrowth at Kessel's Reach there "
        "is a husk with a serial number. Everything out here came from that.",
    "adaptation_noticed":
        "The physician has been comparing burn samples. Whatever you have been "
        "using most, it is working less well than it did.",
    "half_the_verge":
        "Half the systems on the chart carry it now. The Charter has stopped "
        "issuing guidance and started issuing evacuation orders.",
}
