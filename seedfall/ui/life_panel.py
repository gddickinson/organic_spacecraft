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

from ..sim import biology
from .widgets import Panel, label, mono_label, note, spacer


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
        for found in row["rows"][:6]:
            p.add(mono_label(f"{found['lifeform'].name} — "
                             f"{found['body'].name}, {found['system'].name}"))
        if len(row["rows"]) > 6:
            p.add(note(f"and {len(row['rows']) - 6} more."))
    return p
