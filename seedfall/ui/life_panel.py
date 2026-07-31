"""The life catalogue, grouped by what it runs on.

`Lifeform.metabolism` was declared as the identity behind the two strings the
survey screens print, and `test_declared` excused it on the grounds that "a
catalogue that groups by metabolism is wanted". This is that catalogue.

Everything comes from `sim/biology.catalogue`, which walks the sector for
organisms you have actually catalogued and groups them — so a column here is
proof of where you have been rather than a list of what exists. The deepest
column reads first, and each says whether anybody aboard can explain it.
"""

from __future__ import annotations

from ..data import life3d
from ..sim import biology
from .thumb3d import Thumb
from .widgets import Panel, label, mono_label, note, spacer

#: How many of a group's organisms get a portrait before the rest are a
#: count. The same six the register already lists by name — a catalogue is
#: read, and a wall of two hundred thumbnails is not reading.
DRAWN = 6

#: How wide a portrait may be here. These stack down a panel rather than
#: sitting in a card grid, so without a cap each is a full-width black band
#: with a small animal in the middle.
PORTRAIT_W = 190


def build(game) -> Panel:
    groups = biology.catalogue(game)
    told = biology.summary(game)
    p = Panel("Life catalogue")
    p.add(note("What you have catalogued, by biochemistry. A specimen nobody "
               "aboard can read still goes in the register and still counts — "
               "it is worth more once the bench can say what it is doing, "
               "which is a reason to come back rather than a reason not to "
               "land."))
    p.add_row("Organisms catalogued",
              f"{told['found']} across {told['kinds']} of {told['of']} "
              "biochemistries",
              "chloro" if told["found"] else "dim")
    if told["found"]:
        p.add_row("Legible to the bench",
                  f"{told['read']} read · {told['blind']} not",
                  "warn" if told["blind"] else "chloro")

    if not groups:
        p.add(spacer(3))
        p.add(note("Nothing catalogued yet. A close pass finds what moves; a "
                   "deep survey reaches what is buried."))
        return p

    for row in groups:
        p.add(spacer(4))
        p.add(label(f"{row['name']} — {len(row['rows'])} catalogued", "h3",
                    "chloro" if row["understood"] else ""))
        p.add(note(row["note"].capitalize() + "."))
        tech = row["tech"]
        if row["understood"]:
            p.add_row("The bench reads it",
                      tech.name if tech else "yes", "chloro")
        elif tech is not None:
            p.add_row("Would take", f"{tech.name} · {tech.cost:,} points",
                      "warn")
        p.add_row("Worth per specimen",
                  f"×{row['multiplier']:.2f} of the base")
        for found in row["rows"][:DRAWN]:
            life = found["lifeform"]
            # The body plan is the picture, the biochemistry the colour and a
            # trait a feature you can see — all three off this organism's own
            # record. See `data/life3d.py`.
            p.add(Thumb("life", life, height=84, width=PORTRAIT_W))
            p.add(mono_label(f"{life.name} — "
                             f"{found['body'].name}, {found['system'].name}"))
            # Which traits the picture shows, and which it cannot. Some are
            # real and invisible — you cannot see repaired chromatin from a
            # lander — and saying so is better than implying the portrait is
            # the whole organism.
            shown = set(life3d.for_lifeform(life).marks)
            seen = [t[1] for t in (life.traits or []) if t[0] in shown]
            unseen = [t[1] for t in (life.traits or []) if t[0] not in shown]
            if seen:
                p.add(note(", ".join(seen).capitalize() + " — drawn."))
            if unseen:
                p.add(note(", ".join(unseen).capitalize()
                           + " — real, and nothing a portrait can show."))
        if len(row["rows"]) > DRAWN:
            p.add(note(f"and {len(row['rows']) - DRAWN} more."))
    return p
