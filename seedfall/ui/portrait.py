"""A face for everybody aboard, drawn from what the game already knows.

The crew had no picture. `sim/lifepath.py` knows what somebody did for twenty
years, `sim/person.py` knows where they are from and who raised them,
`sim/lifespan.py` knows how old they are and how far through their run,
`sim/loyalty.py` knows what they think of you and `sim/clinic.py` knows what
has been fitted into them — and the whole of it reached the screen as rows of
text under a name.

**Nothing here is authored and nothing here is stored.** A face is a reading
of the same officer id the rest of it is read from, through
`RNG(f"{seed}:face:{id}")`, so the same person has the same face in every
frame, on every screen and after a reload — the project's usual bargain,
pointed at a portrait.

**And it is a portrait of the record, not a decoration.** Everything in the
drawing is a fact you can find in words somewhere else on the same screen:
the lineage is the colour, the years are in the hair and the jaw, the career
is the collar, the homeworld is what is behind them, the mood is the mouth —
and what a clinic has fitted is *visible*, which is the point. Strain is a
number on the Crew screen and an argument on the Clinic tab; here it is a
person who is visibly part machine, which is the whole of what the Verge
minds about.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.rng import RNG
from ..data import treatments as treat_table
from . import theme

#: The skin a lineage wears, as `(light, shadow)`. Two tones and no gradient:
#: this game's pictures are flat and lit from one side, and a portrait that
#: airbrushed would sit oddly beside a hull.
SKIN = {
    "wet": (("#d8a882", "#a97a58"), ("#b9825f", "#8a5a3f"),
            ("#8d5f45", "#65402d"), ("#eec9a6", "#bd9a78")),
    "grafted": (("#c9a98f", "#8d7460"), ("#a78d78", "#6f5b4a")),
    "dry": (("#c2ced6", "#8b9aa5"), ("#aebbc6", "#798793")),
    "xeno": (("#b98fe0", "#7a5c96"), ("#9d79c4", "#5e4676")),
    "kith": (("#8fc7a6", "#5d8a72"), ("#a7d6ba", "#6f9c84")),
    # The three substrates that are not flesh, or are flesh to order.
    "frame": (("#9aa7ae", "#5f6b72"), ("#8e9ba6", "#565f68"),
              ("#a8b4ba", "#6b767d")),
    "mind": (("#b6c8d2", "#7d8f9c"), ("#c3d4dd", "#8899a6")),
    "vatborn": (("#d9b79a", "#a6866c"), ("#c7a68a", "#96795f"),
                ("#e4c8ae", "#b39a82")),
}
DEFAULT_SKIN = SKIN["wet"]

#: What is behind them, by where they grew up. A crew file photograph is
#: taken somewhere, and where it was taken is a fact about the person.
GROUNDS = {
    "belt": ("#141a20", "rock"),
    "ship": ("#101a18", "bulkhead"),
    "highport": ("#101c26", "windows"),
    "arcology": ("#161520", "windows"),
    "outpost": ("#191510", "rock"),
    "dome": ("#121c18", "bulkhead"),
    "water": ("#0f1b22", "plain"),
    "steppe": ("#1a1913", "plain"),
    "quarantine": ("#1b1414", "bulkhead"),
    "vacuum": ("#0a0d12", "plain"),
}
DEFAULT_GROUND = ("#0e1613", "plain")

#: Hair, in the order a portrait would notice it, and what grey does to it.
HAIR = ("#2a211c", "#3c2a1e", "#5a4632", "#1d1a1a", "#6b5a44", "#33302e")
GREY = "#b9c3c0"

#: The collar of the service that made them. Read off the career on their
#: record, so the picture and the service history cannot disagree.
COLLARS = {
    "charter": "#4fd6d0", "yards": "#e6ac6d", "hauler": "#8fb3d9",
    "orders": "#e2f0e8", "prospector": "#b98fe0", "picket": "#e0685f",
    "reach": "#54cf7c", "drifter": "#7c9689",
    "clinician": "#a7d6ba", "factor": "#d8c27a", "entertainer": "#e08fc0",
    "constable": "#5f8fe0", "magistrate": "#c0c8d6", "syndicate": "#8a6f5a",
}
DEFAULT_COLLAR = "#7c9689"

#: What a fitted treatment does to a face, by treatment id. Anything not
#: named here is inside somebody and does not show, which is itself a fact
#: worth being able to see: a palm deck is a scar and a cortex link is not.
SHOWS = {
    "optic_suite": "eye",
    "cortex_link": "temples",
    "subdermal": "plate",
    "muscle_weave": "neck",
    "reflex_lace": "spine",
    "vacuum_rig": "gills",
    "chop_job": "seam",
    "hand_deck": "scar",
    "limb_regrow": "scar",
    "skin_graft": "patch",
    "eye_grow": "eye",
    "heavy_frame": "heavy",
    "gene_tidy": "even",
    "bright_line": "even",
}

#: Where the light is, and how strong the rim is. One hard source over the
#: subject's left, the same as every hull in the game.
RIM = "#dff3ec"


@dataclass
class Face:
    """Everything a portrait needs, derived once."""

    skin: tuple = ("#d8a882", "#a97a58")
    hair: str = HAIR[0]
    grey: float = 0.0
    bald: float = 0.0
    #: 0 young, 1 at the end of the run.
    age: float = 0.4
    #: How wide the head is against the frame, and how long the jaw.
    width: float = 1.0
    jaw: float = 1.0
    brow: float = 0.0
    #: −1 unhappy, +1 content.
    mood: float = 0.0
    collar: str = DEFAULT_COLLAR
    ground: tuple = DEFAULT_GROUND
    #: What shows of what has been fitted.
    marks: tuple = ()
    strain: float = 0.0
    eyes: str = "#1b2420"
    tilt: float = 0.0
    #: Set for somebody who is not standing a watch any more.
    gone: bool = False
    #: Built rather than born: a frame or an instanced mind. Drawn with a
    #: visor and panel seams instead of eyes and hair, because a crew list
    #: that drew a machine as a person with grey skin was telling a lie the
    #: whole rest of this feature exists to stop telling.
    built: bool = False
    #: Which of `data/kindred.CLASSES` anybody at a gate sorts them into.
    kind: str = "born"
    note: str = ""
    extras: dict = field(default_factory=dict)


def of(game, officer) -> Face:
    """One person's face. Cheap, stable, and stored nowhere."""
    from ..sim import clinic as clinic_sim
    from ..sim import lifespan as lifespan_sim
    from ..sim import loyalty as loyalty_sim
    from ..sim import person as person_sim

    seed = getattr(game, "seed", "verge") if game is not None else "verge"
    rng = RNG(f"{seed}:face:{getattr(officer, 'id', 0)}")
    whole = person_sim.of(game, officer)
    lineage = lifespan_sim.lineage_of(officer, game)
    tones = SKIN.get(getattr(lineage, "id", "wet"), DEFAULT_SKIN)
    span = max(1.0, float(getattr(lineage, "span", 80)))
    years = lifespan_sim.age_of(officer, game)
    prime = max(1.0, float(getattr(lineage, "prime", 45)))

    from ..data import kindred as kin_table
    face = Face()
    face.kind = kin_table.class_of(getattr(lineage, "id", "wet"))
    face.built = face.kind in ("machine", "recorded")
    face.skin = rng.pick(list(tones))
    face.hair = rng.pick(list(HAIR))
    face.age = max(0.0, min(1.0, years / span))
    # Grey arrives around the prime and is most of the way in by the span.
    face.grey = max(0.0, min(1.0, (years - prime * 0.7) / max(1.0, span - prime * 0.7)))
    face.bald = rng.float(0.0, 1.0) * max(0.0, min(1.0, years / prime))
    # Wider than it looks: at ±12% every head in a crew was the same egg.
    face.width = rng.float(0.80, 1.22)
    face.jaw = rng.float(0.74, 1.26)
    face.brow = rng.float(-1.0, 1.0)
    face.tilt = rng.float(-0.05, 0.05)
    face.eyes = rng.pick(["#1b2420", "#3a5a4a", "#2d3f52", "#4a3a2a",
                          "#5a4a6a"])
    level = loyalty_sim.loyalty_of(officer)
    face.mood = max(-1.0, min(1.0, (level - 50.0) / 40.0))
    record = whole.record
    face.collar = COLLARS.get(record.career, DEFAULT_COLLAR)
    home = whole.home
    face.ground = GROUNDS.get(getattr(home, "id", ""), DEFAULT_GROUND)
    face.gone = bool(getattr(officer, "retired", False))
    marks = []
    for got in clinic_sim.fitted_to(game, officer):
        shown = SHOWS.get(got.id)
        if shown and shown not in marks:
            marks.append(shown)
    face.marks = tuple(marks)
    face.strain = clinic_sim.strain_of(game, officer)
    if face.built:
        face.bald = 1.0
        face.grey = 0.0
    face.note = _note(whole, years, face)
    return face


def _note(whole, years: float, face: Face) -> str:
    """One line a screen can put under the picture."""
    from ..data import kindred as kin_table
    record = whole.record
    said = (f"{kin_table.CLASS_NAME.get(face.kind, face.kind)} · "
            f"{record.career_name} · {years:.0f} years")
    if face.marks:
        said += f" · {len(face.marks)} fitted and showing"
    return said


def strain_tint(strain: float) -> str:
    """What a strained person's rim light looks like."""
    if strain >= 3.0:
        return theme.tint("warn")
    if strain >= 1.0:
        return theme.tint("lumen")
    return RIM


def worst_mark(face: Face) -> str:
    """The one fitting a caption would mention first."""
    for want in ("seam", "eye", "temples", "plate", "gills", "neck"):
        if want in face.marks:
            return want
    return face.marks[0] if face.marks else ""


def named(mark: str) -> str:
    """What a mark is, in the words a crew list uses."""
    return {
        "eye": "an optic",
        "temples": "temple ports",
        "plate": "subdermal plate",
        "neck": "a weave at the shoulders",
        "spine": "a lace along the spine",
        "gills": "vacuum ports at the throat",
        "seam": "a seam somebody did in an afternoon",
        "scar": "a scar",
        "patch": "grafted skin",
        "heavy": "a heavy-worlder frame",
        "even": "a face nobody had to make",
    }.get(mark, mark)


def treatments_showing(game, officer) -> list:
    """The fitted work that is visible on somebody, as treatments."""
    from ..sim import clinic as clinic_sim
    return [t for t in clinic_sim.fitted_to(game, officer)
            if t.id in SHOWS and t.id in treat_table.TREATMENT_BY_ID]
