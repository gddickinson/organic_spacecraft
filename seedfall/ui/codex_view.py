"""The codex — the fleet class reference, the powers, and the vocabulary.

Everything here is drawn from the GESTALT documents this game sits inside.
"""

from __future__ import annotations

from ..core.util import duration, mass, num
from ..data.chassis import (CHASSIS, FAMILY_LABEL, FAMILY_NOTE,
                            FAMILY_ORDER, FAMILY_TINT, by_family)
from ..data.colonies import COLONIES
from ..data.factions import FACTIONS, standing
from ..data.part_types import SLOT_LABEL, SLOT_ORDER
from ..data.parts import PARTS
from ..data.robots import (DUTIES, ROBOTS, autonomy_name, autonomy_note,
                           autonomy_tint, by_family as robots_by_family,
                           with_duty)
from ..data.inquiry import EVIDENCE_BY_ID
from ..data.berths3d import BERTHS
from ..data.lore import GLOSSARY, INTRO
from ..data.starclasses import STAR_CLASSES
from ..data.xenotech import CULTURES, XENOTECH
from ..data import works3d
from ..data.worlds3d import WORLD_PAINTS
from ..sim import notes as notes_sim
from ..sim.traffic import ERRANDS
from .thumb3d import Thumb
from .widgets import (Card, Panel, Pill, TabBar, View, label, note, spacer)

#: A line each for the things the sky draws. Kept here rather than in `data/`
#: because these describe the *picture* — what a captain is looking at — while
#: `worlds3d` and `berths3d` describe how to draw it.
WORLD_BLURB = {
    "rocky": "Dust, ice at the poles, and whatever the seams hold.",
    "ocean": "Water enough to matter, and green where it meets land.",
    "ice": "Cap to cap. What is under it is somebody's problem.",
    "moon": "Grey rock and dark maria. Cheap to reach, thin to work.",
    "asteroid": "Not a world. A working, with an orbit.",
    "comet": "Volatiles on a long ellipse, and worth catching.",
    "gas": "Belts and zones, a storm that outlives captains, and no ground.",
}

BERTH_NAME = {"quay": "Outpost quay", "hub": "Fleet Hub",
              "holding": "Bonded holding", "gate": "Weave gate"}

BERTH_BLURB = {
    "quay": "A can, a mast and one arm. The humblest thing anybody calls a port.",
    "hub": "Two habitation rings on a spine. Somewhere a fleet lives.",
    "holding": "Tanks in a frame. Cargo waits here; nobody does.",
    "gate": "Older than the Charter, and nobody has built another.",
}


class CodexView(View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "classes"

    def build(self) -> None:
        self.head("Codex",
                  "The class reference, the powers of the Verge, and the vocabulary.")
        tabs = TabBar([("classes", "Fleet classes"), ("colonies", "Colony classes"),
                       ("machines", "Machines"), ("fittings", "Fittings"),
                       ("sky", "The sky"), ("relics", "Relics"),
                       ("factions", "Powers"), ("life", "Life"),
                       ("notes", "Field notes"), ("glossary", "Glossary"),
                       ("about", "About")], self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        {"classes": self._classes, "colonies": self._colonies,
         "machines": self._machines, "fittings": self._fittings,
         "sky": self._sky, "relics": self._relics,
         "factions": self._factions, "life": self._life,
         "notes": self._notes, "glossary": self._glossary,
         "about": self._about}[self.tab]()

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.refresh()

    def _classes(self) -> None:
        known = self.game.research.unlocked
        self.col.addWidget(note(
            f"{len(CHASSIS)} hull classes across five technologies. A grown hull "
            "heals and eats phosphate; a fabricated one is welded in weeks and "
            "never mends; the other three each break that trade differently."))
        for family in FAMILY_ORDER:
            hulls = by_family(family)
            if not hulls:
                continue
            self.col.addWidget(spacer(6))
            self.col.addWidget(label(f"{FAMILY_LABEL[family]} — {len(hulls)}",
                                     "h3", FAMILY_TINT[family]))
            self.col.addWidget(note(FAMILY_NOTE[family]))
            self.grid([self._hull_card(c, known) for c in hulls], cols=2)

    def _hull_card(self, c, known) -> Card:
        have = not c.tech or c.tech in known
        card = Card(selectable=False)
        # The picture first. Thirty-five classes were listed here as text and
        # nothing else, on top of five hull silhouettes the sky had been
        # drawing for cycles — and the proportions come from this card's own
        # numbers, so the portrait and the specification cannot disagree.
        card.add(Thumb("hull", c, height=96))
        card.add(label(c.name, "h3", FAMILY_TINT[c.family] if have else "dim"))
        card.add(label(f"{c.binomial} · {c.tier}" if c.binomial else c.tier, "sub"))
        card.add(label(c.blurb, "", wrap=True))
        card.add(note(f"{c.role} · crew {num(c.crew)} · {mass(c.mass_t)} · "
                      f"hull {num(c.hull)} · hold {num(c.cargo)} t · "
                      f"jump {c.jump:g} ly · {duration(c.grow)} to build"))
        if not have:
            card.add(Pill(f"needs {c.tech}", "dim"))
        return card

    def _sky(self) -> None:
        """The worlds, the stars and the berths — drawn, not described.

        Everything on this tab has been in the sky for cycles and on no page a
        captain could sit and read. A codex that lists thirty-five hulls and
        says nothing about the nine kinds of star you fly under is half a
        catalogue.
        """
        self.col.addWidget(note(
            f"{len(WORLD_PAINTS)} kinds of world, {len(STAR_CLASSES)} classes "
            f"of star, {len(ERRANDS)} errands of traffic and {len(BERTHS)} "
            "sorts of berth. Drawn the way the windows draw them, so what is "
            "on this page is what is out there."))

        self.col.addWidget(spacer(6))
        self.col.addWidget(label("Worlds", "h3", "chloro"))
        self.col.addWidget(note(
            "Painted rather than built: a lit disc, its own latitudes, and "
            "ground texture at whatever scale you are looking from."))
        self.grid([self._sky_card("world", kind, kind.title(),
                                  WORLD_BLURB.get(kind, ""))
                   for kind in WORLD_PAINTS], cols=4)

        self.col.addWidget(spacer(8))
        self.col.addWidget(label("Stars", "h3", "osteo"))
        self.col.addWidget(note(
            "Nine classes, and the light every one of them throws is the light "
            "on your hull."))
        self.grid([self._sky_card("star", key, star.name, star.blurb)
                   for key, star in STAR_CLASSES.items()], cols=3)

        self.col.addWidget(spacer(8))
        self.col.addWidget(label("Traffic", "h3", "steel"))
        self.col.addWidget(note(
            "Other people's hulls, by what they are out here doing. At the "
            "range traffic is seen the outline is the whole of it — which is "
            "why an unmarked hull is worth knowing on sight."))
        self.grid([self._sky_card("ship", errand, ERRANDS[errand][0],
                                  ERRANDS[errand][1].capitalize() + ".")
                   for errand in ERRANDS], cols=3)

        self.col.addWidget(spacer(8))
        self.col.addWidget(label("Berths", "h3", "steel"))
        self.col.addWidget(note(
            "What you come alongside. A gate is not architecture — it is a "
            "ring somebody left."))
        self.grid([self._sky_card("berth", key, BERTH_NAME.get(key, key.title()),
                                  BERTH_BLURB.get(key, ""))
                   for key in BERTHS], cols=4)

    def _sky_card(self, kind: str, subject, name: str, blurb: str) -> Card:
        card = Card(selectable=False)
        card.add(Thumb(kind, subject, height=104))
        card.add(label(name, "h3"))
        if blurb:
            card.add(note(blurb))
        return card

    def _colonies(self) -> None:
        known = self.game.research.unlocked
        self.col.addWidget(note(
            f"{len(COLONIES)} station and colony classes. Plant one and walk "
            "away; it yields every day, wherever you happen to be. Every "
            "structure here is built out of its own entry — what it digs, "
            "what it distils, what it builds and how many people are aboard "
            "— so the picture and the specification cannot disagree."))
        cards = []
        for c in COLONIES:
            have = not c.tech or c.tech in known
            card = Card(selectable=False)
            # The picture first, as on a hull card. Nineteen classes were
            # listed here as text and nothing else, while the sky drew all
            # nineteen as the same four tanks in a frame.
            card.add(Thumb("work", c, height=96))
            card.add(label(c.name, "h3", FAMILY_TINT[c.family] if have else "dim"))
            card.add(label(c.binomial or "Fabricated", "sub"))
            card.add(label(c.blurb, "", wrap=True))
            # Every card is drawn level so the shapes can be compared, the way
            # the star cards are — so the one thing a level portrait cannot
            # say, the size, is said in words. A picket is 0.6 km across and
            # ARCA is five.
            card.add(note(f"Sites: {', '.join(c.sites)} · {duration(c.days)} gestation"
                          + (f" · holds {num(c.pop)}" if c.pop else "")
                          + f" · {works3d.size_km(c.id) * 2:,.1f} km across"))
            if not have:
                card.add(Pill(f"needs {c.tech}", "dim"))
            cards.append(card)
        self.grid(cards, cols=2)

    def _machines(self) -> None:
        """Hands that are not people, by what they can be left alone to do.

        The tab is organised by **autonomy** rather than by family, because
        that is the axis a captain actually chooses on: what a machine is
        rated at matters far less than how much of that rating survives the
        distance to wherever you are going to leave it. See `sim/robots.grip`.
        """
        known = self.game.research.unlocked
        self.col.addWidget(note(
            f"{len(ROBOTS)} classes of machine across the same five "
            "technologies the hulls are built in. Every one of them is rated "
            "on the same ladder real spacecraft are — teleoperated, "
            "preplanned, adaptive, goal-directed — and that rating, not the "
            "level on the card, is what decides where it is worth putting."))
        self.col.addWidget(spacer(4))
        self.col.addWidget(note("Duties: " + " · ".join(
            f"{label_}, {len(with_duty(duty))} classes"
            for duty, (label_, _blurb) in DUTIES.items())))

        for rung in (4, 3, 2, 1):
            classes = [r for r in ROBOTS if r.autonomy == rung]
            if not classes:
                continue
            self.col.addWidget(spacer(6))
            self.col.addWidget(label(
                f"{autonomy_name(rung)} — {len(classes)}", "h3",
                autonomy_tint(rung)))
            self.col.addWidget(note(autonomy_note(rung)))
            self.grid([self._machine_card(r, known) for r in classes], cols=2)

        self.col.addWidget(spacer(8))
        self.col.addWidget(label("By yard", "h3", "steel"))
        self.col.addWidget(note(" · ".join(
            f"{FAMILY_LABEL[family]} {len(robots_by_family(family))}"
            for family in FAMILY_ORDER if robots_by_family(family))))

    def _machine_card(self, r, known) -> Card:
        have = not r.tech or r.tech in known
        card = Card(selectable=False)
        # The picture first, as on a hull card and a colony card. The Machines
        # tab was the last catalogue page in the game that was pure text.
        card.add(Thumb("robot", r.id, height=96))
        card.add(label(r.name, "h3", FAMILY_TINT[r.family] if have else "dim"))
        card.add(label(f"{r.binomial} · {FAMILY_LABEL[r.family]}"
                       if r.binomial else FAMILY_LABEL[r.family], "sub"))
        card.add(label(r.blurb, "", wrap=True))
        does = [DUTIES[d][0] for d in r.duties if d in DUTIES]
        if r.stat:
            does.insert(0, f"stands {r.stat}")
        card.add(note(f"Level {r.level} · {mass(r.mass_t)} · "
                      + (", ".join(does) or "no posting")))
        card.add(note("Upkeep " + ", ".join(
            f"{amount:.3g} {key}" for key, amount in sorted(r.upkeep.items()))))
        if not have:
            card.add(Pill(f"needs {r.tech}", "dim"))
        return card

    def _fittings(self) -> None:
        """Everything that bolts to a hull, by the slot it goes in.

        The last page in the catalogue that was words only. A fitting's
        picture makes a narrower claim than a hull's — what kind of thing it
        is, whose yard built it, and roughly how much hull it eats — because
        eighteen defensive plates cannot be eighteen pictures and pretending
        otherwise would be a distinction drawn where none exists.
        """
        known = self.game.research.unlocked
        self.col.addWidget(note(
            f"{len(PARTS)} fittings across {len(SLOT_ORDER)} slots. The slot "
            "is the shape, the yard is the colour and the tonnage is the "
            "bulk — so a railgun does not look like a radiator, and a grown "
            "organ does not look like a Yards weld."))
        for slot in SLOT_ORDER:
            inslot = [p for p in PARTS if p.slot == slot]
            if not inslot:
                continue
            self.col.addWidget(spacer(6))
            self.col.addWidget(label(
                f"{SLOT_LABEL.get(slot, slot.title())} — {len(inslot)}", "h3"))
            self.grid([self._fitting_card(p, known)
                       for p in sorted(inslot, key=lambda p: p.mass)], cols=3)

    def _fitting_card(self, part, known) -> Card:
        have = not part.tech or part.tech in known
        card = Card(selectable=False)
        card.add(Thumb("part", part, height=88))
        card.add(label(part.name, "h3",
                       FAMILY_TINT.get(part.family, "") if have else "dim"))
        card.add(label(f"{mass(part.mass)} · "
                       + (FAMILY_LABEL[part.family]
                          if part.family in FAMILY_LABEL else "any yard"),
                       "sub"))
        card.add(label(part.blurb, "", wrap=True))
        if part.wpn is not None:
            card.add(Pill("weapon", "warn"))
        if part.ability is not None:
            card.add(Pill("ability", "lumen"))
        if not have:
            card.add(Pill(f"needs {part.tech}", "dim"))
        return card

    def _relics(self) -> None:
        """What four cultures that were not people left lying about.

        The last page in the catalogue that was words only, and the one that
        wanted a picture most: a captain could carry a Pressure Song for a
        whole chronicle and never see it. Grouped by **who made it**, because
        that is what the picture claims — three artefacts of one dead culture
        cannot be three silhouettes without inventing a distinction the cards
        do not make.
        """
        known = self.game.research.unlocked
        self.col.addWidget(note(
            f"{len(XENOTECH)} artefacts left by {len(CULTURES)} makers. The "
            "maker is the shape and the colour, how much there is to learn is "
            "the bulk, and a lit core means it does something to a ship "
            "rather than teaching you something."))
        for culture in CULTURES:
            theirs = [x for x in XENOTECH if x.culture == culture.id]
            if not theirs:
                continue
            self.col.addWidget(spacer(6))
            self.col.addWidget(label(
                f"{culture.name} — {len(theirs)}", "h3", culture.tint))
            self.col.addWidget(note(culture.blurb))
            self.grid([self._relic_card(x, known)
                       for x in sorted(theirs, key=lambda x: x.study)], cols=3)

    def _relic_card(self, relic, known) -> Card:
        card = Card(selectable=False)
        card.add(Thumb("relic", relic, height=96))
        card.add(label(relic.name, "h3",
                       "" if relic.id in known else "dim"))
        card.add(label(f"{relic.study} study", "sub"))
        card.add(label(relic.blurb, "", wrap=True))
        for stat, amount in sorted((relic.bonus or {}).items()):
            card.add(Pill(f"{stat} +{amount:.0%}", "lumen"))
        if not relic.bonus:
            card.add(Pill("teaches, not fits", "dim"))
        if relic.id not in known:
            card.add(Pill("unstudied", "dim"))
        return card

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

    def _life(self) -> None:
        from .life_panel import build as life_catalogue
        self.col.addWidget(life_catalogue(self.game))

    def _notes(self) -> None:
        """What landing parties brought back that was not cargo."""
        g = self.game
        summary = notes_sim.summary(g)
        p = Panel("Field notes")
        p.add_row("Recovered", f"{summary['held']} of {summary['total']}",
                  "chloro" if summary["held"] else "dim")
        if not summary["held"]:
            p.add(note("Nothing yet. Notes come off wrecks and old gardens, "
                       "and only if somebody goes down and reads the room."))
            self.col.addWidget(p)
            return
        p.add(note("Each one is evidence on the bench as well as a thing that "
                   "happened to somebody."))
        self.col.addWidget(p)

        for filed in sorted(notes_sim.held(g), key=lambda f: f.day):
            definition = filed.definition
            if definition is None:
                continue
            card = Panel(definition.title, "xeno")
            card.add(label(definition.text, "", wrap=True))
            card.add(spacer(3))
            card.add_row("Found on", f"{filed.body} · {filed.system}")
            card.add_row("Filed", f"day {filed.day}")
            card.add_row("Evidence", f"{definition.worth:g} · "
                                     f"{EVIDENCE_BY_ID[definition.evidence].name}",
                         EVIDENCE_BY_ID[definition.evidence].tint)
            self.col.addWidget(card)

    def _glossary(self) -> None:
        p = Panel()
        for term, definition in GLOSSARY:
            p.add(label(term, "h3"))
            p.add(note(definition))
            p.add(spacer(5))
        self.col.addWidget(p)

    def _commission(self) -> None:
        """Who this captain is. Read off `game.beginning`, which the opening set."""
        from ..data.beginnings import ORIGINS_BY_ID, POSTINGS_BY_ID, STOCKS_BY_ID
        chosen = getattr(self.game, "beginning", None)
        if chosen is None:
            return
        stock = STOCKS_BY_ID.get(chosen.stock)
        origin = ORIGINS_BY_ID.get(chosen.origin)
        posting = POSTINGS_BY_ID.get(chosen.posting)
        if not (stock and origin and posting):
            return
        panel = Panel("This commission")
        panel.add_row("Hull", chosen.name)
        panel.add_row("Stock", stock.name)
        panel.add_row("Origin", origin.name)
        panel.add_row("Posted from", posting.name)
        panel.add(note(origin.blurb))
        panel.add(note(stock.blurb))
        self.col.addWidget(panel)

    def _about(self) -> None:
        self._commission()
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
