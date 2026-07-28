"""The codex — the fleet class reference, the powers, and the vocabulary.

Everything here is drawn from the GESTALT documents this game sits inside.
"""

from __future__ import annotations

from ..core.util import duration, mass, num
from ..data.chassis import CHASSIS, FAMILY_LABEL, FAMILY_TINT
from ..data.colonies import COLONIES
from ..data.factions import FACTIONS, standing
from ..data.lore import GLOSSARY, INTRO
from .widgets import (Card, Panel, Pill, TabBar, View, label, note, spacer)


class CodexView(View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "classes"

    def build(self) -> None:
        self.head("Codex",
                  "The class reference, the powers of the Verge, and the vocabulary.")
        tabs = TabBar([("classes", "Fleet classes"), ("colonies", "Colony classes"),
                       ("factions", "Powers"), ("glossary", "Glossary"),
                       ("about", "About")], self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        {"classes": self._classes, "colonies": self._colonies,
         "factions": self._factions, "glossary": self._glossary,
         "about": self._about}[self.tab]()

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.refresh()

    def _classes(self) -> None:
        known = self.game.research.unlocked
        cards = []
        for c in CHASSIS:
            have = not c.tech or c.tech in known
            card = Card(selectable=False)
            card.add(label(c.name, "h3", FAMILY_TINT[c.family] if have else "dim"))
            card.add(Pill(FAMILY_LABEL[c.family], FAMILY_TINT[c.family]))
            card.add(label(f"{c.binomial} · {c.tier}" if c.binomial else c.tier, "sub"))
            card.add(label(c.blurb, "", wrap=True))
            card.add(note(f"{c.role} · crew {num(c.crew)} · {mass(c.mass_t)} · "
                          f"hull {num(c.hull)} · hold {num(c.cargo)} t · "
                          f"jump {c.jump:g} ly · {duration(c.grow)} to build"))
            if not have:
                card.add(Pill(f"needs {c.tech}", "dim"))
            cards.append(card)
        self.grid(cards, cols=2)

    def _colonies(self) -> None:
        known = self.game.research.unlocked
        cards = []
        for c in COLONIES:
            have = not c.tech or c.tech in known
            card = Card(selectable=False)
            card.add(label(c.name, "h3", FAMILY_TINT[c.family] if have else "dim"))
            card.add(label(c.binomial or "Fabricated", "sub"))
            card.add(label(c.blurb, "", wrap=True))
            card.add(note(f"Sites: {', '.join(c.sites)} · {duration(c.days)} gestation"
                          + (f" · holds {num(c.pop)}" if c.pop else "")))
            if not have:
                card.add(Pill(f"needs {c.tech}", "dim"))
            cards.append(card)
        self.grid(cards, cols=2)

    def _factions(self) -> None:
        g = self.game
        for f in FACTIONS:
            if f.hidden and not g.flags.get("contact_made"):
                continue
            rep = g.rep.get(f.id, 0)
            band, tint = standing(rep)
            p = Panel(f.name, f.tint)
            p.add(Pill(f"{band} · {round(rep)}", tint))
            if f.creed and f.creed != "—":
                p.add(label(f"“{f.creed}”", "sub"))
            p.add(label(f.blurb, "", wrap=True))
            p.add(note(f.doctrine))
            if f.buys:
                p.add(note(f"Buys: {', '.join(f.buys)}. "
                           f"Sells: {', '.join(f.sells) or '—'}."))
            self.col.addWidget(p)

    def _glossary(self) -> None:
        p = Panel()
        for term, definition in GLOSSARY:
            p.add(label(term, "h3"))
            p.add(note(definition))
            p.add(spacer(5))
        self.col.addWidget(p)

    def _about(self) -> None:
        p = Panel("About this chronicle")
        for para in INTRO:
            p.add(label(para, "", wrap=True))
        p.add(spacer(6))
        p.add(note(
            "SEEDFALL is built directly on the GESTALT design programme kept in this "
            "repository: the design dossier, the fleet class reference, the "
            "engineering and biology compendium, the cell atlas, the metabolism "
            "physiology, and the nervous-system study. The hull classes, the "
            "six-layer hull, the phosphorus bottleneck, the reproduction licence and "
            "the containment regime are all theirs."))
        p.add(note("The documents are a concept, not a build spec. So, emphatically, "
                   "is this."))
        self.col.addWidget(p)
