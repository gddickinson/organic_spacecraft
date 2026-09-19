"""The living sky: what a star does for a while, and what it is worth to watch.

The sky was static. Stars never changed, and once a system was surveyed there
was nothing to come back for — part of the mid-game stall the play-test
measured. The GESTALT documents make the space environment a design driver
(flares, radiation, micrometeoroids, thermal cycling); these are the events
that make it one here.

Six kinds. Each changes what a place is for a while, each is forecast before
it begins (most of them), and each is **observable science**: a new evidence
kind for the bench, and data the Charter and the Dry Choir buy.

Pure data. `sim/phenomena.py` schedules them from per-system, per-season keys
and holds the one door for each effect; every effect is switched off by a
check in `tests/test_phenomena.py` that sees its number move.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Kind:
    id: str
    name: str
    #: `theme.TINTS` key for the strip and the log; `colour` is the chart ring.
    tint: str
    colour: str
    glyph: str
    #: How long it lasts, in days, low and high.
    days: tuple
    #: Days of warning the observatory gives at a neutral forecaster (scan 0,
    #: no CHORUS Node). Better instruments stretch it (`LEAD_SCAN`).
    lead: int
    #: Share of the observatory's candidates that come true. A forecast states
    #: the confidence this implies for *your* forecaster (`sim/phenomena
    #: .confidence`) — so seventy per cent means seven in ten, measured.
    real: float
    #: What one observation yields at quality 1: phenomena evidence, and the
    #: data's worth in credits before its buyer and its rarity.
    evidence: float
    value: float
    #: Days an observation takes.
    watch: int
    #: Does it bring a body with it (`Body.transient_until`)?
    transient: bool
    effect: str
    blurb: str


FLARE = Kind(
    "flare", "Stellar flare", "warn", "#ffb454", "✶", (1, 5), 3, 0.70,
    18.0, 900.0, 2, False,
    "Hard light: a dose to any crew not in a body's shadow or at a berth. "
    "Sensors read further; despatches are slow.",
    "A dwarf star's magnetic field snaps and reconnects, and for a day or "
    "five it throws out more hard light than it has all year. Proxima does "
    "this; so does every red dwarf worth the name.")

COMET = Kind(
    "comet", "Comet passage", "lumen", "#9fd8ff", "☄", (60, 200), 45, 0.85,
    30.0, 2200.0, 4, True,
    "A comet in the inner system: ice-rich, mineable for volatiles and "
    "phosphate, and its volatiles glut the nearby quays.",
    "A dirty snowball off the outer cloud, falling sunward for the first "
    "time in ten thousand years. It will be gone again in a season or two, "
    "and so will everything on it nobody took.")

STORM = Kind(
    "storm", "Ion storm", "xeno", "#b48cff", "≈", (3, 15), 5, 0.60,
    24.0, 1600.0, 3, False,
    "Lanes into and out of the system are closed, and a survey reads less.",
    "A front of charged gas driven through the nebula. Nothing jumps through "
    "it and nothing reads clearly inside it; the Shoals get them every "
    "season, the Verge hardly ever.")

ROGUE = Kind(
    "rogue", "Rogue flyby", "steel", "#8fa3b8", "●", (30, 90), 30, 0.80,
    40.0, 3200.0, 4, True,
    "A sunless world passing through: a new survey target, sometimes a "
    "relic.",
    "A world with no star of its own, falling through the system on its way "
    "from nowhere to nowhere. The Hollow has more of them than anywhere.")

AURORA = Kind(
    "aurora", "Aurora season", "chloro", "#7ee0a0", "≋", (20, 60), 10, 0.75,
    14.0, 700.0, 3, False,
    "The giants and magnetised worlds light up: working them yields more, "
    "and a dive is safer.",
    "The star's wind sets the big fields ringing. The upper air is warm, "
    "calm and bright for weeks, and the harvest rigs love it.")

NOVA = Kind(
    "nova", "Nova", "bad", "#ff6b6b", "✹", (120, 300), 120, 1.0,
    120.0, 12000.0, 6, False,
    "A mounting dose for eight light years round, then the burst: the "
    "system is scoured and a remnant is left.",
    "One of the Cradle's giants is done. It brightens for months and then "
    "it goes, and the only people who will ever see it are the ones who "
    "were out here when it did.")

#: The five that recur, in the order a season's key draws them. **Append
#: only**: each kind draws the same numbers whether it happens or not, so a
#: new one at the end changes nothing the others do.
KINDS = (FLARE, COMET, STORM, ROGUE, AURORA)
KINDS_BY_ID = {k.id: k for k in (*KINDS, NOVA)}

#: Which the observe act prefers when several are live at once: the rarest.
PRIORITY = ("nova", "rogue", "comet", "storm", "flare", "aurora")


# ── the schedule ───────────────────────────────────────────────────────────

#: A season of the sky, in days. The key a system's sky is drawn from is
#: `f"{seed}:sky:{system}:{season}"`, so it is the same whoever looks.
SEASON_DAYS = 90

#: A comet or a rogue may begin only one season in three per system (offset
#: by the system's id), in that season's first `TRANSIENT_START` days. With
#: `COMET.days` at most 200 a passage is over before the next slot opens, so
#: a system never holds two transients and one leaving shifts no index.
TRANSIENT_SLOT = 3
TRANSIENT_START = 60

#: Chance per season that a star has a flare coming, by class — candidates,
#: of which `FLARE.real` come true. Dwarfs mostly (a young T-Tauri too), any
#: star sometimes; the corpses never.
FLARE_RATE = {"M": 0.55, "K": 0.35, "T": 0.45, "B": 0.20, "G": 0.12,
              "F": 0.08, "A": 0.05, "BG": 0.05, "O": 0.05}

#: Per open transient slot, for a system with an outer body (orbit ≥ 0.6).
#: At 0.30 five comets were passing the Verge at once and ten of its two dozen
#: quays sat under a volatiles glut all year — reaction mass cheap everywhere,
#: which is a new economy rather than an event. At 0.12, about two at once.
COMET_RATE = 0.12
OUTER_ORBIT = 0.6

#: Per season, by region: the Shoals mostly, the Verge rarely.
STORM_RATE = {"shoals": 0.50, "verge": 0.025}

#: Per open transient slot, by region; the Hollow more.
ROGUE_RATE = {"hollow": 0.60}
ROGUE_ELSEWHERE = 0.09

#: Per season, for a system with a gas giant or a magnetised world — a rocky,
#: ocean or ice world at least this big (Earth's dynamo is 6,371 km). Eased
#: from 0.25, at which the bots met a notable phenomenon within two jumps
#: every 21 days (median, 15 careers) — busier than the 20-40 asked for.
AURORA_RATE = 0.18
MAGNETISED_KM = 5000


# ── what each does ─────────────────────────────────────────────────────────

#: A flare's strength, low and high: dose units a day on an unsheltered,
#: unshielded crew (the Cradle's daily dose is 1.0).
FLARE_DOSE = (0.6, 1.4)

#: Morale one unit of flare dose takes. Mean flare 1.0 × 3 days × this is
#: about 2.4% — the spec's "1-3% of a hand, never a sudden death".
FLARE_MORALE = 0.008

#: How much further the array reads in a flaring system: hard light off
#: every hull and rock.
FLARE_SENSOR = 1.25

#: Days a flare adds to a despatch sent from or to a flaring system.
FLARE_COMMS_DAYS = 1.5

#: What an ion storm leaves of a survey's resolution.
STORM_SURVEY = 0.6

#: Working an aurora world: yield multiplier, and what is left of the risk.
AURORA_YIELD = 1.35
AURORA_RISK = 0.5

#: Reaction mass a day to keep station in a body's shadow while there is
#: something to hide from — the price of the lee.
LEE_FUEL = 0.4


# ── transient bodies ───────────────────────────────────────────────────────

#: A passing comet, ice-rich: grades (low, high) and radius in km. Richer in
#: phosphate than a resident comet (0-0.10), which is the point of chasing
#: one.
COMET_GRADES = {"volatiles": (0.85, 1.0), "phosphate": (0.30, 0.60),
                "ore": (0.05, 0.20), "biomass": (0.0, 0.0)}
COMET_KM = (3, 22)

#: Where it sits while it passes (0 hot, 1 cold): inside, rising and falling.
COMET_ORBIT = (0.25, 0.55)

#: A glut of volatiles at the nearest quays this near, while the comet lasts
#: — how deep a glut is `data/shocks.COMET_GLUT`'s, the market's own table.
#: Two ports, not every one in range: at seven and a half light years with no
#: cap, the five comets a season brings glutted most of the Verge's quays at
#: once, and the powers' purses moved with it (a Concordat treasury 45,500 →
#: 20,900 over two idle years on one seed).
COMET_GLUT_LY = 7.5
COMET_GLUT_PORTS = 2

#: A rogue: rock or ice, sunless, and sometimes carrying a relic.
ROGUE_KM = (600, 4200)
ROGUE_ORBIT = (0.35, 0.8)
ROGUE_RELIC = 0.30


# ── the nova ───────────────────────────────────────────────────────────────

#: Days after the Cradle opens before the chosen star starts to brighten, and
#: how long it brightens (`NOVA.days`) — so the burst is forecast at least 120
#: days ahead, twice the spec's floor.
NOVA_DELAY = (60, 240)

#: The mounting dose reaches this far, in light years, and peaks at this.
NOVA_RADIUS_LY = 8.0
NOVA_DOSE = 1.5

#: What the burst does to a hull still in the system: this share of every
#: layer, and this share of the crew. Survivable only by luck and armour.
NOVA_HULL = 0.55
NOVA_CREW = 0.30

#: Days after the burst its light can still be taken, from another system
#: within this many light years.
NOVA_WATCH_DAYS = 45
NOVA_WATCH_LY = 14.0

#: What the star becomes: `data/remnants.NEUTRON`.
NOVA_REMNANT = "N"

#: A burst observation's evidence and worth, against a brightening one.
BURST_SCALE = 2.0

#: What is left on the scoured worlds of what they held.
SCOURED = {"volatiles": 0.1, "biomass": 0.0, "phosphate": 0.5, "ore": 1.0}


# ── the forecast ───────────────────────────────────────────────────────────

#: Forecasts reach the ship for stars within this many jumps' range.
FORECAST_JUMPS = 2.0

#: How well the forecaster tells a real flare from a flicker: share of false
#: alarms it drops. From the array's scan and a CHORUS Node of yours.
DISC_BASE = 0.10
DISC_SCAN = 0.60
DISC_CHORUS = 0.20
DISC_CAP = 0.90

#: And how far ahead it sees: lead × (1 + scan × this + a node × that).
LEAD_SCAN = 1.0
LEAD_CHORUS = 0.5


# ── observing, and selling what was seen ───────────────────────────────────

#: An observation's quality from the array: base + scan × slope, clamped.
OBS_BASE = 0.5
OBS_SCAN = 0.8
OBS_RANGE = (0.4, 1.2)

#: Who buys sky data, and the premium on the first of a kind anybody of
#: yours has sold. The Choir pays a fortune for burst data taken from a safe
#: distance.
BUYERS = ("charter", "sanhedrin")
FIRST_OF_KIND = 1.5
CHOIR_BURST = 2.5

#: Standing a lot of sky data buys with the power that takes it, and the cap.
DATA_REP = 0.5
DATA_REP_CAP = 2.0


# ── the bench ──────────────────────────────────────────────────────────────

#: The technologies phenomena evidence speeds: the sensors, the radiation
#: shielding, and Deep Weave.
FEEDS = ("magnetite", "xenobiology", "deepweave", "melanin", "dsup",
         "deinococcus", "whipple")

#: The most it speeds them, fully supplied, and the share of a programme's
#: cost in phenomena evidence that full supply takes.
UPLIFT = 0.15
FEED_SHARE = 0.25


# ── words ──────────────────────────────────────────────────────────────────

OBSERVATORY = "Charter observatory"
FORECAST = ("The {who} at {here} forecasts {what} at {where} within {days} "
            "days, {conf}% confidence. {advice}")

#: One line of advice a forecast ends on — short, because a despatch is.
ADVICE = {"flare": "Find a berth, or a body's shadow.",
          "comet": "Ice worth cutting, while it lasts.",
          "storm": "Its lanes will close while it blows.",
          "rogue": "A new world to look at, briefly.",
          "aurora": "The giants will be worth working."}
NOVA_FORECAST = ("The {who} at {here} reports {star} at {where} brightening "
                 "past anything in the catalogue. It will burst in about "
                 "{days} days. Everything within {radius:g} light years is "
                 "taking a mounting dose until it does.")
