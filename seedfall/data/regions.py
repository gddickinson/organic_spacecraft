"""The Far Reaches: three regions past the Verge's rim, and what each is like.

The Verge is forty-two stars in a seventy-light-year field, and the review's
play-test measured what that costs: once the reachable pocket is charted an
explorer's income stalls (+22k in two and a half years; another's purse peaked
on day 1,190 and fell), and the mid-game has nowhere new to go. The Weave has
always said its gates are older than anyone flying it. These are what they
were built to reach.

Each region sits behind a **deep anchor** — a dormant gate on the Verge's rim
that has to be relit (`sim/relight.py`) — and is generated only then, from its
own seed (`world/regions.py`), so a chronicle that never opens one pays
nothing and a save from before the Reaches can open one.

Pure data. The rules that read `RULES` live in `sim/regions.py`, one function
each, and every one of them is switched off by an efficacy check.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The Verge's own id. Every system without a region is in it.
VERGE = "verge"


@dataclass(frozen=True)
class RegionSpec:
    id: str
    name: str
    #: How many systems it grows, and the frame they are laid out in (ly).
    count: int
    w: float
    h: float
    #: Which rim of the Verge its deep anchor stands on: west, north or east.
    rim: str
    #: Spacing, as `world/galaxy` does it for the Verge: no star further than
    #: `max_lane` from its nearest neighbour, none nearer than `min_sep`.
    max_lane: float
    min_sep: float
    #: Every star is joined to every other by hops no longer than this. The
    #: relaxation above bounds each star's *nearest* neighbour, which leaves
    #: clusters with a gap between them: measured on the first draft, a
    #: Shoals entry could not reach either haven at 9.2 ly. Seven and a half
    #: is inside an opening hull's reach; the Hollow asks for a real drive.
    link: float
    #: (id, name, heat, tint, weight) — the Verge's `galaxy.STAR_CLASSES`
    #: shape. **Region tables, never that one**: adding a class to it, or
    #: reordering it, changes the Verge's draw sequence and every seed in
    #: every save grows a different sky.
    stars: tuple
    #: One line for the chart and the codex.
    character: str
    blurb: str


REGIONS: list[RegionSpec] = [
    RegionSpec(
        "shoals", "The Shoals", 12, 40.0, 30.0, "west", 5.4, 2.6, 7.5,
        (("M", "M-type red dwarf", 0.32, "#e07a5f", 30),
         ("K", "K-type orange", 0.52, "#e6ac6d", 22),
         ("F", "F-type white", 0.86, "#e8f0f5", 14),
         ("T", "T-Tauri young star", 0.64, "#f0a6c8", 26)),
        "An emission nebula: young stars in glowing gas.",
        "The gas that lights the Shoals also blinds you in it. Sensors reach "
        "half as far, a survey reads less, and nobody's law reaches at all — "
        "only the Freehold havens, which tolerate what the Verge seizes. The "
        "nebula condenses into something the Concordat and the Dry Choir "
        "will pay very well for, and it is sold nowhere else."),
    RegionSpec(
        "hollow", "The Hollow", 10, 64.0, 46.0, "north", 11.0, 6.4, 12.0,
        (("M", "M-type red dwarf", 0.32, "#e07a5f", 34),
         ("D", "white dwarf", 0.18, "#cfe6ff", 30),
         ("N", "neutron star", 0.10, "#9fd8ff", 12),
         ("X", "black hole", 0.05, "#6b4fa8", 6)),
        "A void, sparse and dark.",
        "Long lanes, few stars and fewer of them alive. Rogue worlds drift "
        "through with no sun at all: a grown hull's intima makes no air "
        "alongside one, and the tank is what you breathe. Something older "
        "than the Weave left its rings here, and nothing else — one derelict "
        "relay is the only quay in it."),
    RegionSpec(
        "cradle", "The Cradle", 14, 36.0, 28.0, "east", 5.0, 2.8, 7.5,
        (("O", "O-type blue giant", 1.25, "#9db4ff", 12),
         ("BG", "B-type blue giant", 1.10, "#aac6ff", 26),
         ("A", "A-type blue-white", 1.00, "#b8d8ff", 34),
         ("F", "F-type white", 0.86, "#e8f0f5", 28)),
        "A young, hot, dense cluster.",
        "Blue giants a few light years apart, and the radiation to go with "
        "them: the crew takes a dose every day aboard and the hull runs hot. "
        "Shielding and a melanised rind cut it. The ground is rich — the "
        "richest ore in the known sky — and nobody holds any of it yet."),
]

REGIONS_BY_ID = {r.id: r for r in REGIONS}


# ── the rules each region runs by ──────────────────────────────────────────

#: Per region, per key: what `sim/regions.rule` answers. A key a region does
#: not name reads as the Verge's value in `NEUTRAL`, so a new rule is one row
#: here and one reader, and a later wave (the Kith, phenomena) can add keys
#: without touching the rest.
RULES: dict[str, dict[str, float]] = {
    # Sensor reach and survey resolution through glowing gas. Halved reach is
    # the spec's number; 0.8 of the resolution is what moves a close pass on
    # an opening array (scan 0.55) from 0.55 to 0.44 — under the 0.5 a
    # second look needs to count as sharper (`planets.SHARPER_BY` on 0.45).
    "shoals": {"sensor": 0.5, "survey": 0.8, "lawless": 0.30,
               "claimable": 0.0},
    # A sunless body is dark: no light, no photosynthesis. See `DARK_BODY`.
    "hollow": {"claimable": 0.0},
    # Crew dose and extra hull heat, per day aboard. See `DOSE_*`, `HEAT_*`.
    "cradle": {"dose": 1.0, "heat": 1.0, "claimable": 0.0},
}

#: What every rule reads as where nothing says otherwise — the Verge.
NEUTRAL: dict[str, float] = {"sensor": 1.0, "survey": 1.0, "lawless": 0.0,
                             "dose": 0.0, "heat": 0.0, "claimable": 1.0}

#: Share of the Hollow's bodies that are rogues: sunless worlds drifting
#: through, no star-lit face at all. Marked after generation, from the body's
#: own identity, so the draw sequence is `make_body`'s and nothing else's.
ROGUE_SHARE = 0.35

#: Of those rogues, the share carrying a Precursor ruin — the one thing the
#: Hollow's makers left besides their rings. An anomaly, found by a survey
#: that can see one, and worth the reading: (id, name, tint, research, text).
RUIN_SHARE = 0.4
PRECURSOR_RUIN = (
    "precursor", "Precursor ruin", "xeno", 70,
    "Worked stone on a world with no sun, laid in the same lattice as the "
    "Hollow's rings. Whoever built them built here too, and left nothing "
    "else — no bodies, no writing, no second thing of any kind.")

#: Morale a Cradle day takes off an unshielded crew. Morale drifts back at
#: 8% of the gap a day (`crew.morale_tick`), so this settles about 0.19 below
#: where the crew would otherwise sit — measured, 0.72 to 0.53 over sixty
#: days on an opening NAVIS — which is felt, and survivable.
DOSE_MORALE = 0.015

#: What cuts the dose: `Stats.crew_guard` (Dsup chromatin, a wake cradle —
#: the fittings that already say they protect the crew) takes its own share
#: off, and a melanised rind takes this much of what is left.
DOSE_TECH = "melanin"
DOSE_TECH_CUT = 0.4

#: How hot the Cradle's light keeps a hull, as a share of its rated cap: the
#: radiators never get her below it while she is there. Felt as a hull that
#: starts every fight and every hard burn this far up the gauge, rather than
#: as damage in its own right — the cap is where cooking starts.
HEAT_SHARE = 0.45


# ── the deep anchors, and relighting one ───────────────────────────────────

#: The research node that says what a deep anchor is doing. Tier 3, fed by
#: survey and specimen evidence (`data/inquiry.TECH_MIX`).
DEEP_TECH = "deepweave"

#: What a relight takes, paid at the anchor. At posted prices the materials
#: are most of the bill, so the credits are the smaller part: labour.
#:
#: **Less than the spec's example (60 t magnetite, 8 t xenolith), measured.**
#: A scripted trading captain who researches toward Deep Weave has the tech by
#: day 218-379 and the anchor read by day 163-710; the purse is the slow part.
#: With the example bill and 60,000 credits on top — about 126,000 at base
#: prices — no run of eight got there in three years, and the one that had
#: every tonne aboard by day 960 never again held the credits. This bill is
#: about 50,000 at base prices.
RELIGHT_CREDITS = 10_000.0
RELIGHT_GOODS = {"magnetite": 40, "alloy": 40, "xenolith": 5}
RELIGHT_DAYS = 30

#: A deep anchor has to be *read* before anybody can relight it: a deep
#: survey (`data/surveys` "deep") of a body in its system.
READ_METHOD = "deep"

#: How the region's own rings are laid in the Hollow: this many lit links
#: between its most distant systems, toll-free, older than the Weave.
HOLLOW_RINGS = 3

#: Names for the deep anchors, by region.
ANCHOR_NAMES = {"shoals": "the Shoal Gate", "hollow": "the Hollow Gate",
                "cradle": "the Cradle Gate"}


# ── nebular condensate ─────────────────────────────────────────────────────

CONDENSATE = "condensate"

#: How abundant it is at a Shoals market, before the usual supply draw: a
#: glut, which is what makes it cheap where it is made.
NATIVE_GLUT = 1.9

#: The Verge powers that buy it, and the supply they are left at: short, and
#: permanently so, which is what makes it dear where it is wanted. Added to
#: their markets when the Shoals open, from a seed of its own.
#:
#: Measured with a scripted captain who relights the Shoals from a day-500
#: purse of 60,000 and runs condensate for a year: at 0.34 / 0.38 the run
#: cleared 285-835 a day (payback 63-183 days) where the same captain's Verge
#: trade lost 38-143 a day — a trip was worth 40,000, most of a mid-game
#: purse. Eased so a trip is a windfall rather than the economy.
CONDENSATE_BUYERS = {"concordat": 0.42, "sanhedrin": 0.46}

#: Names for what stands in the Reaches.
HAVEN_NAME = "Freehold haven"
RELAY_NAME = "Derelict relay"
