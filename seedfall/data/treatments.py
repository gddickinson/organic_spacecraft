"""What a concourse can do to a person: mend them, keep them, change them.

The game had nothing of this. A crew aged, shed levels to decline, took the
years a crossing costs them and went under on a long one, and there was
nowhere in the Verge that would do anything about any of it — no surgery, no
anagathics, no cold berth you could buy by the year, and nothing at all you
could have fitted.

Eight sorts of work, matching the `offers` tags a venue carries
(`data/venue_types.py`), so a door either does this kind of work or it does
not and no module has to know the venue tables:

- **care** — ordinary medicine. Clears the wear a hard stretch put on
  somebody before it costs them a level.
- **surgery** — the serious repairs, under. Buys back a level already shed.
- **graft** — cloned tissue, organs, limbs. A characteristic, restored.
- **years** — anagathics. Takes real years off a real age, which is the only
  thing in this game that moves a lifespan the right way. Ruinous, and the
  reason the Charter's officers are all so old and so rich.
- **ice** — cold storage by the year, for somebody who is not needed yet.
- **cyber** — fitted hardware. The best numbers in the file, and the only
  ones that charge **strain**: what it costs a person to be partly a machine
  among people who are not.
- **gene** — the germ line. Permanent, expensive, and illegal almost
  everywhere the Charter runs.
- **train** — a skill, taught properly, over weeks.

**Everything here is priced and gated exactly like `data/kit.py`**: a tech
level below which nobody can do it, a law level above which nobody will admit
to it, and ten per cent a level either way on the price. The difference is
that a thing in `kit.py` sits in a pocket and a thing in here is *in
somebody*, which is why every row has a risk and the good ones have a cost
that is not money.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The characteristics a treatment can move, from `sim/checks.py`. Kept as a
#: tuple here so the table can be checked without importing the sim.
SCORES = ("str", "dex", "end", "int", "edu", "soc")

#: The ceiling a treatment may lift a characteristic to. Traveller's own
#: scale runs to 15; anything past this is a different sort of story.
SCORE_CAP = 15

#: What strain is, and what it costs. Every point of it is a point off the
#: person's loyalty *and* their standing with everybody who has to look at
#: them — the Verge is four cultures and none of them is relaxed about this.
STRAIN_LOYALTY = 3.0

#: How long the ship is alongside, per day of work. A treatment's `days` is
#: the ship's calendar, not the patient's — which is the decision.
LONGEST = 90


@dataclass(frozen=True)
class Treatment:
    """One thing a clinic, a shop or a back room will do to somebody."""

    id: str
    name: str
    #: One of the `offers` tags: care, surgery, graft, years, ice, cyber,
    #: gene, train.
    kind: str
    cr: int
    tl: int
    #: The law level at or above which nobody licensed will do it. 0 means
    #: nobody minds.
    law: int = 0
    days: int = 1
    #: What it does. A characteristic map, a skill, levels of wear cleared,
    #: levels bought back, and years taken off an age.
    gives: dict = field(default_factory=dict)
    skill: str = ""
    heals: float = 0.0
    restores: int = 0
    years: float = 0.0
    #: What it costs that is not money.
    strain: float = 0.0
    #: The difficulty of the throw, from `sim/checks.DIFFICULTIES`. Empty
    #: means it cannot go wrong.
    risk: str = ""
    #: What goes wrong when it does.
    mishap: str = ""
    note: str = ""


TREATMENTS: tuple = (
    # ── care: the ordinary repairs ─────────────────────────────────────────
    Treatment("check_up", "A proper check-up", "care", 90, 6, days=2,
              heals=0.35,
              note="Somebody looks at them properly for the first time in "
                   "two years."),
    Treatment("convalescence", "A fortnight ashore, under care", "care", 400,
              7, days=14, heals=1.0,
              note="Rest, food, and nobody shouting. It works."),
    Treatment("nerve_tuning", "Nerve tuning", "care", 1_800, 10, days=5,
              heals=0.6, gives={"dex": 1}, risk="average",
              mishap="A week of tremors, and a point of dexterity gone.",
              note="The signal cleaned up where it has got noisy."),
    Treatment("marrow_wash", "A marrow wash", "care", 3_200, 11, days=9,
              heals=1.4, gives={"end": 1}, risk="routine",
              mishap="They are flat for a month and no better for it.",
              note="Everything that carries oxygen, replaced."),

    # ── surgery: buying back what decline took ─────────────────────────────
    Treatment("joint_rebuild", "A joint rebuild", "surgery", 6_000, 9,
              days=21, restores=1, risk="average",
              mishap="It sets badly. They are slower than before.",
              note="Hips, shoulders, knees. Everything a working life eats."),
    Treatment("spinal_lattice", "A spinal lattice", "surgery", 14_000, 11,
              days=30, restores=1, gives={"str": 1}, risk="difficult",
              mishap="Six weeks flat and a point of strength gone.",
              note="Laid along the bone. They stand up straight afterwards."),
    Treatment("neural_prune", "A neural prune", "surgery", 22_000, 12,
              days=24, restores=1, gives={"int": 1}, risk="difficult",
              mishap="They lose a fortnight, and are not sure which one.",
              note="What is not being used is taken out of the way."),

    # ── graft: tissue, organs, limbs ───────────────────────────────────────
    Treatment("skin_graft", "Cloned skin", "graft", 2_400, 9, days=10,
              heals=0.8, gives={"soc": 1},
              note="Burns, vacuum scarring, and what a hard vacuum does to "
                   "a face."),
    Treatment("organ_swap", "A cloned organ", "graft", 11_000, 10, days=18,
              gives={"end": 2}, risk="average",
              mishap="It is rejected. They are worse off than they started.",
              note="Grown from them, so nothing has to be suppressed."),
    Treatment("limb_regrow", "A limb, regrown", "graft", 18_000, 11, days=45,
              gives={"str": 1, "dex": 1}, risk="average",
              mishap="It comes in wrong and has to come off again.",
              note="Slower than a fitted one, and it is theirs."),
    Treatment("eye_grow", "Cloned eyes", "graft", 7_500, 10, days=12,
              gives={"int": 1}, skill="recon",
              note="Better than the ones they were born with, slightly."),

    # ── years ──────────────────────────────────────────────────────────────
    Treatment("anagathic_course", "A course of anagathics", "years",
              120_000, 12, days=30, years=4.0, risk="difficult",
              mishap="It does not take. The money is gone and so is the year.",
              note="Four years off, and a standing arrangement with a clinic "
                   "that will outlive most captains."),
    Treatment("anagathic_black", "Unlicensed anagathics", "years", 44_000,
              12, law=6, days=21, years=3.0, strain=0.5, risk="formidable",
              mishap="Something in it was wrong. They lose a point of "
                     "endurance and two years.",
              note="The same molecule, made by somebody with no licence to "
                   "lose."),
    Treatment("telomere_reset", "A telomere reset", "years", 260_000, 14,
              days=60, years=9.0, gives={"end": 1}, risk="difficult",
              mishap="A fortnight of fever and nothing to show for it.",
              note="The whole clock, wound back. Four clinics in the Verge "
                   "can do it and they all have a waiting list."),

    # ── ice ────────────────────────────────────────────────────────────────
    Treatment("cold_berth", "A cold berth, by the year", "ice", 3_000, 9,
              days=1, risk="routine",
              mishap="They do not come up well. A level, and a year of it.",
              note="Racked, logged, and not ageing. Somebody has to pay the "
                   "bill every year they are in it."),
    Treatment("vitrified_berth", "A vitrified berth", "ice", 9_000, 11,
              days=2,
              note="Sugar glass. Nothing happens to them at all, which is "
                   "the point and the price."),

    # ── cyber: the good numbers, and what they cost ────────────────────────
    Treatment("hand_deck", "A palm deck", "cyber", 8_000, 11, law=8, days=4,
              gives={"int": 1}, skill="computers", strain=0.5,
              note="A board under the skin of the forearm. Everybody can "
                   "tell."),
    Treatment("optic_suite", "An optic suite", "cyber", 12_000, 11, law=8,
              days=6, gives={"int": 1}, skill="recon", strain=1.0,
              risk="routine",
              mishap="The calibration never settles. Headaches, and a point "
                     "of intellect.",
              note="Spectra a person was not built to see. They stop "
                   "blinking as much."),
    Treatment("muscle_weave", "A muscle weave", "cyber", 16_000, 12, law=7,
              days=9, gives={"str": 2}, strain=1.5, risk="average",
              mishap="It knits wrong and has to be cut out. A point of "
                     "strength, gone.",
              note="Laid through the muscle. They are stronger than they "
                   "look and it shows in how people stand near them."),
    Treatment("reflex_lace", "A reflex lace", "cyber", 24_000, 12, law=6,
              days=11, gives={"dex": 2}, strain=2.0, risk="average",
              mishap="They twitch for a season and lose a point of "
                     "dexterity.",
              note="The spine, made faster than the mind that owns it."),
    Treatment("subdermal", "Subdermal plate", "cyber", 9_000, 11, law=6,
              days=7, gives={"end": 1}, strain=1.5,
              note="Under the skin, across the chest and forearms. It is "
                   "obvious at a handshake."),
    Treatment("vacuum_rig", "A vacuum rig", "cyber", 30_000, 13, law=9,
              days=14, gives={"end": 2}, skill="vacc_suit", strain=1.0,
              risk="difficult",
              mishap="The seals never take. A point of endurance and a "
                     "fortnight in a bed.",
              note="Sealed ports, a gill, and eight hours outside without a "
                   "suit."),
    Treatment("cortex_link", "A cortex link", "cyber", 48_000, 13, law=7,
              days=16, gives={"int": 2, "edu": 1}, skill="electronics",
              strain=2.5, risk="difficult",
              mishap="Something is burnt out. Two points of intellect and a "
                     "stammer.",
              note="They are never entirely alone again, and they say it is "
                   "worth it."),
    Treatment("chop_job", "A chop job", "cyber", 3_500, 11, law=5, days=3,
              gives={"str": 1, "dex": 1}, strain=3.0, risk="formidable",
              mishap="Infection, and a limb they will lose properly later.",
              note="Everything at once, in an afternoon, by somebody who "
                   "will not be here next month."),

    # ── gene ───────────────────────────────────────────────────────────────
    Treatment("gene_tidy", "A germ-line tidy", "gene", 65_000, 13, law=9,
              days=30, gives={"end": 1, "int": 1}, risk="difficult",
              mishap="Nothing takes, and a clinic somewhere has a file on "
                     "them now.",
              note="What they would have been, had anybody been careful."),
    Treatment("heavy_frame", "A heavy-worlder frame", "gene", 90_000, 14,
              law=8, days=45, gives={"str": 2, "end": 1}, strain=0.5,
              risk="difficult",
              mishap="The frame outgrows the heart. A point of endurance.",
              note="Bone and muscle rewritten for a gravity they will "
                   "probably never stand in."),
    Treatment("bright_line", "A bright line", "gene", 140_000, 14, law=10,
              days=60, gives={"int": 2, "edu": 2}, strain=1.0,
              risk="formidable",
              mishap="They are changed, and not in the direction anybody "
                     "paid for.",
              note="Illegal under every Charter statute and half the "
                   "Sanhedrin's doctrine."),

    # ── train ──────────────────────────────────────────────────────────────
    Treatment("short_course", "A short course", "train", 2_000, 7, days=21,
              note="Three weeks, a classroom, and an examination at the end."),
    Treatment("full_course", "A full course", "train", 9_000, 9, days=60,
              note="Two months of somebody's whole attention."),
    Treatment("wired_teach", "Wired instruction", "train", 26_000, 12, law=9,
              days=10, strain=0.5, risk="average",
              mishap="It does not stick, and they have a headache for a "
                     "month.",
              note="Laid in directly. It is not the same as knowing it, and "
                   "afterwards you cannot tell."),
)

TREATMENT_BY_ID = {t.id: t for t in TREATMENTS}
BY_KIND = {}
for _t in TREATMENTS:
    BY_KIND.setdefault(_t.kind, []).append(_t)
BY_KIND = {k: tuple(v) for k, v in BY_KIND.items()}


def legal_at(treatment: Treatment, law: int) -> bool:
    """Would anybody here admit to doing it?"""
    return treatment.law <= 0 or law < treatment.law


def done_at(treatment: Treatment, tech: int) -> bool:
    """Can this place actually do it? No grace: a clinic either has the
    machine or it does not, unlike a chandler who can order a suit in."""
    return treatment.tl <= tech


def price_at(treatment: Treatment, tech: int) -> int:
    """What it costs here. Cheap where it is routine, dear where it is not.

    The same ten per cent a level `data/kit.py` charges, for the same
    reason — and it is most of why a captain flies a sick officer to a
    Charter capital rather than to the nearest rock with a surgery.
    """
    if treatment.cr <= 0:
        return 0
    gap = tech - treatment.tl
    shift = max(0.34, min(3.0, 1.0 - gap * 0.10))
    return max(1, int(treatment.cr * shift))
