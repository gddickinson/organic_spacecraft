"""The ending tracks: three intermediate milestones on each of the ten endings.

The endings were all-or-nothing, and the honest progress bars sat at 0 of 12,
0 of 12 and 1-2 of 10 for three years. Each ending now has three steps an
honest career feeds on the way, each with a reward that pays toward the next
one — credits out of a named power's purse (never conjured), standing, bench
work or a title. Ruin's track is the quiet one: it records what was lost and
pays nothing.

Rows are `data/milestones.Milestone`s, read by the same machinery as the
career milestones (`sim/renown`), so a step fires once, on the day its fact
reaches `at`, and the Voyage screen draws it as a rung on its ladder.

**Why these rewards.** Measured on the careful captain (five seeds, five
years, before any reward): the purse stood at or under ₡16,000 at 20 of
23 year-ends — hands, wages and food eat an explorer's income — and the
Genesis path — 7,830 points of
research, a ₡18,000 melt head and a dive — was finished on one seed of five.
The early steps therefore pay toward the thing the next step needs: the
melt head's price for the Genesis step that makes it possible, a licence
grant for the first hulls a line needs, and so on.
"""

from __future__ import annotations

from .milestones import Milestone, Reward


def T(track, step, mid, name, renown, fact, at, text, reward=None, also=(),
      feeds="", screen=""):
    return Milestone(mid, name, renown, fact, at, "track", text, reward,
                     tuple(also), track, step, feeds, screen)


TRACKS = [
    # ── Dominion: twelve colonies and a million citizens ──────────────────
    T("dominion", 1, "dom_1", "Three colonies online", 20, "colonies", 3,
      "Three colonies yielding. The Charter's colonial registry files you "
      "as a proprietor and pays the first grant.",
      Reward(credits=8_000, payer="charter"),
      feeds="colonies online", screen="empire"),
    T("dominion", 2, "dom_2", "Six colonies, a hundred thousand", 35,
      "colonies", 6, "Six colonies and a hundred thousand people.",
      Reward(credits=15_000, payer="charter"),
      also=(("citizens", 100_000),), feeds="colonies and citizens",
      screen="empire"),
    T("dominion", 3, "dom_3", "Nine colonies, four hundred thousand", 60,
      "colonies", 9, "Nine colonies, four hundred thousand citizens.",
      Reward(title="Proprietor of the Verge", standing={"charter": 5}),
      also=(("citizens", 400_000),), feeds="colonies and citizens",
      screen="empire"),
    # ── Concord: four powers Kin, six pairs at peace ──────────────────────
    T("concord", 1, "con_1", "A treaty signed", 20, "treaties", 1,
      "A treaty with your name on it. The other three noticed.",
      Reward(standing={"*": 3}), feeds="treaties signed",
      screen="diplomacy"),
    T("concord", 2, "con_2", "Three pairs at peace", 35, "peace", 3,
      "Three pairs of powers at peace, and you in every room it was made.",
      Reward(standing={"*": 5}), feeds="pairs of powers at peace",
      screen="diplomacy"),
    T("concord", 3, "con_3", "Trusted by all four", 60, "trusted", 4,
      "All four powers trust you. Nobody else in the Verge can say it.",
      Reward(title="Peacemaker"), feeds="powers at Trusted",
      screen="diplomacy"),
    # ── Containment: every Bloom system cleansed, the First Instar dead ────
    T("containment", 1, "cnt_1", "A system cleansed", 20, "cleansed", 1,
      "A Bloom-held system burned clean. The Charter pays for the "
      "ordnance, as the licence says it must.",
      Reward(credits=10_000, payer="charter"),
      feeds="systems cleansed", screen="system"),
    T("containment", 2, "cnt_2", "Five systems cleansed", 35, "cleansed", 5,
      "Five systems burned clean.", Reward(credits=20_000, payer="charter"),
      feeds="systems cleansed", screen="system"),
    T("containment", 3, "cnt_3", "The First Instar found", 60, "heart", 1,
      "Kessel's Reach, and the thing at the middle of it.",
      Reward(title="Warden of the Licence", standing={"charter": 8}),
      feeds="the heart found", screen="map"),
    # ── Xenarchy: all twelve alien technologies ───────────────────────────
    T("xenarch", 1, "xen_1", "Three technologies not ours", 20, "xenotech",
      3, "Three alien technologies incorporated.",
      Reward(research=300), feeds="xenotech incorporated", screen="tech"),
    T("xenarch", 2, "xen_2", "Six technologies not ours", 35, "xenotech", 6,
      "Six. The Dry Choir asks for a copy of your notes, and pays for it.",
      Reward(credits=12_000, payer="sanhedrin"),
      feeds="xenotech incorporated", screen="tech"),
    T("xenarch", 3, "xen_3", "Nine technologies not ours", 60, "xenotech", 9,
      "Nine of twelve.", Reward(title="Xenarch", research=600),
      feeds="xenotech incorporated", screen="tech"),
    # ── the Cartel: the register and a million and a half ─────────────────
    T("cartel", 1, "car_1", "Ten live quotes", 20, "quotes", 10,
      "Ten markets' prices, all still true. The Freeholds' factors buy "
      "your copy of the register.",
      Reward(credits=5_000, payer="freeholds"),
      feeds="live price quotes", screen="port"),
    T("cartel", 2, "car_2", "A third of the markets", 35, "quote_share",
      0.3, "A third of the Verge's markets priced and current.",
      Reward(credits=12_000, payer="concordat"),
      feeds="share of markets priced", screen="port"),
    T("cartel", 3, "car_3", "Half a million", 60, "credits", 500_000,
      "Half a million in the purse at once.",
      Reward(title="Factor of the Verge"), feeds="credits", screen="port"),
    # ── Lineage: four grown hulls, a year flying each ──────────────────────
    T("lineage", 1, "lin_1", "A hull of your own gestated", 20, "grown", 1,
      "A grown hull out of a cradle of yours, signed for. The Charter "
      "repays the licence fee it charged you.",
      Reward(credits=8_000, payer="charter"),
      feeds="grown hulls you launched", screen="yard"),
    T("lineage", 2, "lin_2", "Two of your line", 35, "grown", 2,
      "Two grown hulls of your line.",
      Reward(credits=15_000, payer="charter"),
      feeds="grown hulls you launched", screen="yard"),
    T("lineage", 3, "lin_3", "A NAVIS of your line", 60, "grown_big", 1,
      "A grown hull of NAVIS size or more, gestated by you.",
      Reward(title="Founder of a Line", standing={"charter": 5}),
      feeds="grown hulls of NAVIS size", screen="yard"),
    # ── Exodus: the LEVIATHAN ──────────────────────────────────────────────
    T("exodus", 1, "exo_1", "The ark understood", 20, "ark_known", 1,
      "Parallel growth fronts: the LEVIATHAN can be laid down.",
      Reward(credits=20_000, payer="freeholds"),
      feeds="Parallel Growth Fronts researched", screen="tech"),
    T("exodus", 2, "exo_2", "The keel laid", 35, "ark_laid", 1,
      "A LEVIATHAN in the cradle.", Reward(credits=40_000, payer="charter"),
      feeds="a LEVIATHAN laid down", screen="yard"),
    T("exodus", 3, "exo_3", "The ark half grown", 60, "ark_grown", 0.5,
      "The ark half grown.", Reward(title="Arkwright"),
      feeds="the ark's growth", screen="yard"),
    # ── Genesis: First Contact with the Abyssals ───────────────────────────
    T("genesis", 1, "gen_1", "Built for the pressure", 20, "knows_piezolyte",
      1, "Piezolyte physiology: a hull that can go under the ice. The "
      "Charter's programme pays toward the melt head.",
      Reward(credits=15_000, payer="charter"),
      feeds="Piezolyte Physiology researched", screen="tech"),
    T("genesis", 2, "gen_2", "Under the ice", 35, "dives", 1,
      "Twenty kilometres of ice, and an ocean under it. The dive's "
      "specimens go straight to the bench.", Reward(research=400),
      feeds="ice dives", screen="system"),
    T("genesis", 3, "gen_3", "Something answered", 60, "contact", 1,
      "Something under the ice answered, and kept answering. What it said "
      "is the start of a protocol.",
      Reward(research=600, title="Speaker to the Deep"),
      feeds="contact made", screen="system"),
    # ── Apostasy: a crewless synthetic hull, Kin with the Dry Choir ───────
    T("apostasy", 1, "apo_1", "The Choir trusts you", 20, "choir", 40,
      "The Dry Choir trusts you. They fund the silicon a crewless hull is "
      "made of.", Reward(credits=10_000, payer="sanhedrin"),
      feeds="standing with the Dry Choir", screen="diplomacy"),
    T("apostasy", 2, "apo_2", "A crewless hull flown", 35, "crewless", 1,
      "A synthetic hull with nobody aboard, and it flies.",
      Reward(standing={"sanhedrin": 8}), feeds="a crewless hull",
      screen="yard"),
    T("apostasy", 3, "apo_3", "Kin with the Choir", 60, "choir", 70,
      "The Choir calls you Kin.", Reward(title="Apostate"),
      feeds="standing with the Dry Choir", screen="diplomacy"),
    # ── Ruin: the quiet track. It pays nothing. ───────────────────────────
    T("ruin", 1, "rui_1", "A harbour lost", 0, "harbours_lost", 1,
      "A quay drowned. It will not be the last."),
    T("ruin", 2, "rui_2", "A quarter of the Verge", 0, "drowned", 0.25,
      "A quarter of the Verge is the Bloom's."),
    T("ruin", 3, "rui_3", "Half the Verge", 0, "drowned", 0.5,
      "Half the Verge. The rest is a matter of time."),
]

#: The technology at the end of each ending's road — what the first
#: officer's counsel researches toward on the track furthest along: the
#: protocol itself (Genesis), the hull the ending is flown in (Exodus,
#: Lineage's cheapest non-pod hull, Apostasy's cheapest synthetic), the
#: branch the rest hangs from (Xenarchy), the heaviest gun the Bloom has
#: not adapted to yet (Containment), and so on.
ROADS = {"genesis": "firstcontact", "exodus": "multifront",
         "lineage": "magnetite", "apostasy": "synthmind",
         "xenarch": "xenobiology", "containment": "fusionlance",
         "dominion": "multifront", "concord": "charter",
         "cartel": "xenopharma"}

#: A rung that is a technology: its road is walked first, so the bench
#: reaches the rung (and what it pays) before the rest of the ending's road.
#: Cheapest-first along the whole Genesis road left Piezolyte Physiology —
#: the melt head's, and so every dive's — to the last third of it.
RUNG_TECH = {"knows_piezolyte": "piezolyte", "ark_known": "multifront"}

#: The ending order the Voyage screen draws, which is `data/lore.VICTORIES`'.
TRACK_ORDER = ("containment", "exodus", "concord", "genesis", "dominion",
               "lineage", "xenarch", "cartel", "apostasy", "ruin")
