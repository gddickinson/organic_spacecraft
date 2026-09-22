"""Renown: the career ladder — ranks, their perks, and the career milestones.

The play-test's sharpest finding was that twenty honest three-year careers
reached no ending, and nothing rewarded being a third of the way to one. A
milestone is a thing a captain has done that the game can *read*: a count, a
flag, a record the rules already keep. Each is worth renown; renown climbs
the ranks; every rank carries a perk that some system reads at one line.

**A milestone is data.** `fact` names a number `sim/renown_facts` computes
from state that already exists, and the milestone fires the first day that
number reaches `at` (every `also` pair must hold too). It is never granted
twice. The ending tracks — three steps on each of the ten endings — are in
`data/milestone_tracks.py`, shaped the same way.

How to add one (the Kith, phenomena and officer arcs land this way after the
merge — their facts are already read, through `progress(game)` behind an
import guard, as `"<module>:<key>"`):

    M("kith_contact", "First words with the Kith", 40, "kith:contact", 1,
      "kith", "Something in the Cradle answered in signs."),

A reward names who pays for it (`payer`, a power's purse — nothing is
conjured) and is priced by `sim/renown.reward_terms`, which is the one door
the Voyage screen, the moment and the act all read.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Reward:
    """What a milestone pays. Every credit comes out of `payer`'s purse."""
    credits: int = 0
    payer: str = ""
    #: power -> standing delta; "*" means each of the four powers.
    standing: dict = field(default_factory=dict)
    #: Points into the bench's current project (`research.grant`).
    research: int = 0
    #: A name the captain carries from then on (memoir, Hall, Voyage).
    title: str = ""


@dataclass(frozen=True)
class Milestone:
    id: str
    name: str
    renown: int
    fact: str
    at: float
    topic: str
    text: str
    reward: Reward | None = None
    #: Further (fact, at) pairs that must hold as well.
    also: tuple = ()
    #: For the ending tracks: which ending, and which step (1-3).
    track: str = ""
    step: int = 0
    #: What feeds it, said on the ladder and by counsel.
    feeds: str = ""
    #: The screen that does it (`data/screens` id), for "take me there".
    screen: str = ""


def M(mid, name, renown, fact, at, topic, text, reward=None, also=(),
      feeds="", screen=""):
    return Milestone(mid, name, renown, fact, at, topic, text, reward,
                     tuple(also), "", 0, feeds, screen)


#: (id, name, renown needed). A rank is held for good once reached.
#:
#: Measured on the careful captain (`tests/careful_captain.py`), seeds s1-s5
#: over five years: the first milestone on day 1 on every seed, Captain on
#: days 45-76, Commodore on days 447-686, Admiral of the Verge on two seeds
#: (days 781 and 1,825), Legend on none — as it should be, rare. At 100 for
#: Captain the same careers took 88-120 days; the spec asks about 90.
RANKS = (
    ("master", "Master", 0),
    ("captain", "Captain", 80),
    ("commodore", "Commodore", 250),
    ("admiral", "Admiral of the Verge", 550),
    ("legend", "Legend", 1000),
)
RANKS_BY_ID = {rid: (rid, name, need) for rid, name, need in RANKS}

#: Each perk is a key, read at exactly one line by the system it names
#: (`sim/renown.perk`), and switched off by `efficacy` in the suite.
PERKS = {
    "berth": ("captain", "Priority berthing",
              "A full quay holds a berth for you: the harbourmaster moves a "
              "trader along."),
    "charter": ("captain", "The charter fee waived",
                "A trading house is chartered for nothing — the issuing "
                "power forgoes its fee for a captain of standing."),
    "recruits": ("commodore", "Better recruits",
                 "Every hand looking for a berth is a level better: word of "
                 "your name reaches the quays before you do."),
    "floor": ("admiral", "A floor under your standing",
              "No power's standing with you falls below Neutral. You may be "
              "disliked; you are not dismissed."),
    "table": ("admiral", "A motion of your own",
              "Once a year the Assembly tables a resolution you name."),
    "name": ("legend", "Your name on the chart",
             "A system you choose is renamed for your ship, for good."),
}

#: The standing the "floor" perk holds each power at: the Neutral band's
#: floor (`data/factions.STANDINGS`).
STANDING_FLOOR = -8.0
#: Recruit levels the "recruits" perk adds.
RECRUIT_FLOOR = 1
#: Days between motions the "table" perk lets you name.
TABLE_EVERY = 365

#: The career milestones. Renown is roughly how rare the thing is on an
#: honest career: day-one acts 10, a season's work 15-25, a year's 30-60.
CAREER = [
    # ── looking ────────────────────────────────────────────────────────────
    M("underway", "Under way", 10, "visited", 2, "survey",
      "The first jump: a second star under your keel.", screen="map",
      feeds="systems visited"),
    M("first_look", "First look", 10, "surveyed", 1, "survey",
      "The first survey is on the bench. Every chart starts as one body.",
      screen="system", feeds="survey a body"),
    M("surveyor", "Surveyor", 15, "surveyed", 25, "survey",
      "Twenty-five bodies on the register in your hand.", screen="system",
      feeds="bodies surveyed"),
    M("cartographer", "Cartographer", 25, "surveyed", 100, "survey",
      "A hundred bodies. The Registry cites your charts by name now.",
      screen="system", feeds="bodies surveyed"),
    M("first_chart", "A system charted", 10, "charted", 1, "survey",
      "One system known end to end — every body in it looked at.",
      screen="system", feeds="systems fully charted"),
    M("charts_10", "Ten systems charted", 20, "charted", 10, "survey",
      "Ten systems charted whole.", screen="system",
      feeds="systems fully charted"),
    M("chart_sold", "A chart sold", 10, "charts_sold", 1, "survey",
      "A power paid for a whole system's chart.", screen="port",
      feeds="charts sold"),
    M("wanderer", "Five stars", 10, "visited", 5, "survey",
      "Five systems under your keel.", screen="map", feeds="systems visited"),
    M("far_wanderer", "Twenty stars", 20, "visited", 20, "survey",
      "Twenty systems. Half the Verge has seen your transponder.",
      screen="map", feeds="systems visited"),
    M("every_star", "Thirty-five stars", 35, "visited", 35, "survey",
      "Thirty-five systems. There are harbourmasters who have seen less.",
      screen="map", feeds="systems visited"),
    M("first_life", "Something alive", 10, "lifeforms", 1, "survey",
      "The first organism catalogued under your name.", screen="system",
      feeds="organisms catalogued"),
    M("naturalist", "Naturalist", 20, "lifeforms", 15, "survey",
      "Fifteen organisms catalogued.", screen="system",
      feeds="organisms catalogued"),
    M("anomaly", "Something odd", 15, "anomalies", 1, "survey",
      "An anomaly on the register: something that should not be there.",
      screen="system", feeds="anomalies found"),
    M("landfall", "Landfall", 15, "landed", 1, "survey",
      "A party on the ground and back aboard.", screen="system",
      feeds="a landing"),
    M("first_dig", "Into the strata", 15, "dug", 1, "survey",
      "A trench opened and read.", screen="system", feeds="a dig"),
    M("first_rock", "Eating rock", 10, "mined", 1, "survey",
      "The mining root went in and came out full.", screen="system",
      feeds="an extraction"),
    # ── money ──────────────────────────────────────────────────────────────
    M("first_sale", "Something sold", 10, "sales", 1, "trade",
      "A cargo you brought sold at a counter.", screen="port",
      feeds="cargoes sold where they were not bought"),
    M("survey_sold", "Data sold", 10, "survey_sales", 1, "trade",
      "Survey sets handed in and paid for.", screen="port",
      feeds="survey data sold"),
    M("prices_3", "Prices in hand", 10, "quotes", 3, "trade",
      "Three markets' prices on the register and still good.",
      screen="port", feeds="live price quotes"),
    M("contract_taken", "Work taken", 10, "taken", 1, "trade",
      "A contract off a board and in your book.", screen="port",
      feeds="contracts taken"),
    M("contract_1", "Work done", 15, "contracts", 1, "trade",
      "A contract finished and paid.", screen="port",
      feeds="contracts completed"),
    M("contracts_10", "A name on the boards", 25, "contracts", 10, "trade",
      "Ten contracts finished. The boards post work with you in mind.",
      screen="port", feeds="contracts completed"),
    M("commission", "A commission", 25, "commissions", 1, "trade",
      "A commission carried to its end.", screen="port",
      feeds="commissions completed"),
    M("purse_50k", "Solvent", 20, "credits", 50_000, "trade",
      "Fifty thousand in the purse at once.", screen="port",
      feeds="credits"),
    M("purse_150k", "Well found", 30, "credits", 150_000, "trade",
      "A hundred and fifty thousand. You could buy a hull outright.",
      screen="port", feeds="credits"),
    # ── the bench ──────────────────────────────────────────────────────────
    M("first_tech", "Something learned", 10, "techs", 1, "research",
      "The first technology of your own.", screen="tech",
      feeds="technologies learned"),
    M("techs_10", "Ten technologies", 20, "techs", 10, "research",
      "Ten technologies worked out aboard.", screen="tech",
      feeds="technologies learned"),
    M("techs_25", "Twenty-five technologies", 30, "techs", 25, "research",
      "Twenty-five. The tree has more of your hand in it than anybody's.",
      screen="tech", feeds="technologies learned"),
    M("tier_4", "The fourth tier", 25, "tier", 4, "research",
      "A fourth-tier technology — the far end of a branch.", screen="tech",
      feeds="the highest tier known"),
    M("first_xeno", "Not ours", 25, "xenotech", 1, "research",
      "An alien technology incorporated, not derived.", screen="tech",
      feeds="xenotech incorporated"),
    # ── holdings ───────────────────────────────────────────────────────────
    M("first_colony", "Something growing", 25, "colonies", 1, "colonies",
      "A colony online and yielding.", screen="empire",
      feeds="colonies online"),
    M("first_work", "Something built", 15, "works", 1, "colonies",
      "A colony works finished.", screen="empire", feeds="works finished"),
    M("citizens_10k", "Ten thousand", 20, "citizens", 10_000, "colonies",
      "Ten thousand people live where you planted.", screen="empire",
      feeds="citizens"),
    M("second_hull", "A second hull", 15, "fleet", 2, "colonies",
      "Two hulls in the fleet.", screen="yard", feeds="hulls in the fleet"),
    # ── fighting ───────────────────────────────────────────────────────────
    M("first_fight", "Under fire", 10, "fights", 1, "combat",
      "An engagement fought and lived through.", feeds="engagements"),
    M("first_win", "The other hull broke first", 15, "victories", 1,
      "combat", "An enemy destroyed or made to strike.",
      feeds="engagements won"),
    M("talked_down", "Talked down", 10, "talked_down", 1, "combat",
      "A fight ended by a hail rather than a salvo.",
      feeds="engagements ended by parley"),
    M("hunted", "A name that hates you", 10, "rivals", 1, "rivals",
      "A rival has risen with your name in their mouth.", screen="law",
      feeds="rivals risen"),
    M("bounty_1", "Paper paid", 20, "bounties", 1, "rivals",
      "A bounty collected.", screen="law", feeds="bounties collected"),
    M("rival_down", "Nemesis destroyed", 40, "rivals_dead", 1, "rivals",
      "A rival is dead. The despatches have stopped arriving.",
      screen="law", feeds="rivals destroyed"),
    M("rival_ally", "An enemy spared", 30, "rivals_allied", 1, "rivals",
      "A rival you could have killed sails with you now.", screen="law",
      feeds="rivals turned"),
    M("trophy", "A trophy", 15, "trophies", 1, "rivals",
      "Something taken off a rival's hull.", screen="law",
      feeds="trophies taken"),
    M("bloom_fought", "Against the Bloom", 20, "bloom_fought", 1, "combat",
      "You burned Bloom growth with your own guns.", screen="system",
      feeds="Bloom masses fought"),
    # ── the law ────────────────────────────────────────────────────────────
    M("clean_year", "A clean year", 15, "clean_days", 365, "law",
      "A year without a charge filed against you.", screen="law",
      feeds="days since the last charge"),
    M("debt_settled", "Square with the law", 10, "debts_settled", 1, "law",
      "A judgment debt paid off in full.", screen="law",
      feeds="debts settled"),
    # ── the powers ─────────────────────────────────────────────────────────
    # Counted over the four, because a captain starts Trusted by the power
    # that posted them: one is where every chronicle begins.
    M("tolerated", "Tolerated twice", 10, "tolerated", 2, "diplomacy",
      "A second power tolerates you. It is a start.", screen="diplomacy",
      feeds="powers at Tolerated or better"),
    M("trusted", "Trusted twice", 25, "trusted", 2, "diplomacy",
      "A second power trusts you with its business.", screen="diplomacy",
      feeds="powers at Trusted"),
    M("three_trusted", "Trusted three times over", 35, "trusted", 3,
      "diplomacy", "Three powers trust you. They will want to know why.",
      screen="diplomacy", feeds="powers at Trusted"),
    # ── the Weave and the Reaches ──────────────────────────────────────────
    M("gate_transit", "Through the Weave", 10, "transits", 1, "reaches",
      "Through an ancient gate and out the other side.", screen="map",
      feeds="gate transits"),
    M("gate_woken", "A gate woken", 30, "woken", 1, "reaches",
      "An ancient anchor woken by your hand.", screen="system",
      feeds="anchors woken"),
    M("anchor_read", "A deep anchor read", 20, "anchors_read", 1, "reaches",
      "A deep anchor on the rim, read by a deep survey.", screen="system",
      feeds="deep anchors read"),
    M("region_open", "Past the rim", 50, "regions", 1, "reaches",
      "A deep gate relit. There are stars beyond the Verge again.",
      screen="system", feeds="regions opened"),
    M("regions_all", "Every Reach", 60, "regions", 3, "reaches",
      "All three Reaches open. The Verge is not the edge of anything now.",
      screen="system", feeds="regions opened"),
    # ── freight lines ──────────────────────────────────────────────────────
    M("house", "A trading house", 20, "house", 1, "lines",
      "A house chartered in your name.", screen="empire",
      feeds="a charter"),
    M("line_opened", "A line of your own", 20, "lines", 1, "lines",
      "A hauler of yours on a line, with a master aboard.",
      screen="empire", feeds="lines opened"),
    M("line_trips", "Regular service", 25, "trips", 5, "lines",
      "Five round trips completed on your lines.", screen="empire",
      feeds="line trips completed"),
    # ── the Assembly ───────────────────────────────────────────────────────
    M("assembly_seen", "In the gallery", 15, "sittings", 1, "assembly",
      "Present at a sitting of the Assembly.", screen="diplomacy",
      feeds="sittings attended"),
    M("motion_won", "The House divides your way", 25, "motions_won", 1,
      "assembly", "A motion went the way you stood.", screen="diplomacy",
      feeds="motions carried your way"),
    M("motions_won_5", "A voice in the chamber", 35, "motions_won", 5,
      "assembly", "Five motions your way. The clerks know your ship.",
      screen="diplomacy", feeds="motions carried your way"),
    # ── the living hull ────────────────────────────────────────────────────
    M("adapted", "The hull remembers", 15, "adaptations", 1, "body",
      "An adaptation has set in: the hull is not the hull you launched.",
      screen="ship", feeds="adaptations set in"),
    M("adapted_3", "A body of its own", 20, "adaptations", 3, "body",
      "Three adaptations set in.", screen="ship",
      feeds="adaptations set in"),
    # ── the people ─────────────────────────────────────────────────────────
    M("veteran", "A veteran aboard", 15, "officer_level", 6, "crew",
      "An officer of the sixth level — as far as the work itself teaches.",
      screen="ship", feeds="the best officer's level"),
    M("full_bridge", "Every station manned", 15, "stations", 5, "crew",
      "Five stations with an officer at each.", screen="port",
      feeds="officers on the bridge"),
    # ── a life ─────────────────────────────────────────────────────────────
    M("year_1", "A year out", 15, "days", 365, "career",
      "A year in command, and still flying.", feeds="days in command"),
    M("year_3", "Three years out", 25, "days", 1095, "career",
      "Three years. Most captains who start do not see this.",
      feeds="days in command"),
    M("year_5", "Five years out", 35, "days", 1825, "career",
      "Five years in command.", feeds="days in command"),
    # ── the Kith (`sim/kith.progress`) ─────────────────────────────────────
    M("kith_contact", "First words with the Kith", 40, "kith:met", 1,
      "kith", "Something in the Cradle answered in signs.",
      screen="port", feeds="contact made in the Cradle"),
    M("kith_gifts", "Gift for gift", 25, "kith:exchanges", 10, "kith",
      "Ten gifts given and answered.", screen="port",
      feeds="gifts the Kith have answered"),
    M("kith_accord", "An accord sung", 50, "kith:accord", 1, "kith",
      "The Kith sang an accord with your ship.", screen="port",
      feeds="an accord with a gathering"),
    # ── the living sky (`sim/phenomena.progress`) ──────────────────────────
    M("sky_watched", "Eyes on the sky", 15, "phenomena:observed", 1,
      "survey", "Watched a phenomenon through and kept the data.",
      screen="system", feeds="phenomena observed"),
    M("sky_kinds", "A natural historian of the sky", 30,
      "phenomena:kinds_seen", 4, "survey",
      "Four kinds of phenomenon observed.", screen="system",
      feeds="kinds of phenomenon observed"),
    # ── the crew's own stories (`sim/arcs.progress`) ───────────────────────
    M("arc_beats", "Listening to the bridge", 15, "arcs:beats_done", 3,
      "crew", "Three of the crew's own stories answered.", screen="ship",
      feeds="arc beats answered"),
    M("arc_done", "A story finished", 25, "arcs:finished", 1, "crew",
      "An officer's story came to its end, and left a mark on them.",
      screen="ship", feeds="arcs finished with a signature"),
    M("arc_done_3", "A crew with histories", 35, "arcs:finished", 3,
      "crew", "Three officers' stories finished.", screen="ship",
      feeds="arcs finished with a signature"),
    # ── on foot (`sim/afoot`) ─────────────────────────────────────────────
    M("afoot_first", "Boots on the deck", 10, "afoot:walks", 1, "afoot",
      "A party walked a deck and came home.", screen="afoot",
      feeds="walks come home from"),
    M("afoot_boarded", "Boarded and decided", 20, "afoot:boarded", 1,
      "afoot", "A struck hull boarded, and taken or stripped from her own "
      "deck.", screen="afoot", feeds="prizes decided aboard"),
    M("afoot_cleared", "A dead hull cleared", 20, "afoot:cleared", 1,
      "afoot", "Whoever a wreck's end left aboard, put down or run off.",
      screen="afoot", feeds="wrecks cleared"),
    M("afoot_nest", "Burned out by hand", 20, "afoot:nests", 1, "afoot",
      "A Bloom nest burned out with a party standing in it.",
      screen="afoot", feeds="nests burned"),
    M("afoot_kinds", "Everywhere on foot", 30, "afoot:kinds", 6, "afoot",
      "Six kinds of place walked: hulls and quays, drums and dens, the "
      "dead and the struck.", screen="afoot", feeds="kinds of place walked"),
]

TOPICS = {
    "survey": "Looking", "trade": "Money", "research": "The bench",
    "colonies": "Holdings", "combat": "Fighting", "rivals": "Rivals",
    "law": "The law", "diplomacy": "The powers", "reaches": "The Weave",
    "lines": "Freight lines", "assembly": "The Assembly",
    "body": "The living hull", "crew": "The people", "career": "A life",
    "kith": "The Kith", "afoot": "On foot",
    "track": "Endings",
}
