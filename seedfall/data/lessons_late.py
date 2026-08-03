"""The last five chapters: working a system, fighting, holdings, powers, career.

The second half of the curriculum. See `lessons_early.py` for the shape of a
lesson and `sim/tutorial_watch.py` for the watchers that decide them.
"""

from __future__ import annotations

from .lesson_types import Lesson

LATE = [
    # ── VI. Rock and ice ──────────────────────────────────────────────────
    Lesson("mine", "Work a seam",
           "Open the System screen, pick a surveyed body and run an "
           "extraction.",
           "system", "mined",
           "Seams have depth and they wear out, so a body is a place you "
           "come back to rather than a button you hold. Ice is reaction mass "
           "for free if you have the days; ore and alloy are what a yard "
           "wants. The rig stops itself when the hold is full rather than "
           "quietly wasting the work.",
           chapter="rock-and-ice"),

    Lesson("dig", "Open a trench",
           "Find a body with a buried site and open a dig on it. A deep "
           "survey is what finds them.",
           "system", "dug",
           "A dig is four strata worked one at a time, and everything is "
           "banked as you go — so a trench abandoned half way is not a "
           "wasted season. What comes up is alien, and it is the only way "
           "into technology nobody could have reasoned out.",
           chapter="rock-and-ice"),

    Lesson("land", "Put people on the ground",
           "Land a party on a surveyed body that has a surface.",
           "system", "landed",
           "The ground is its own game: a fogged map revealed a tile at a "
           "time, days of supply spent on every step, hazards that your "
           "officers' skills answer. Nothing is banked until the party is "
           "back on the lander — and known ground is cheap to re-cross, "
           "which is what makes coming home survivable.",
           chapter="rock-and-ice"),

    # ── VII. Iron ─────────────────────────────────────────────────────────
    Lesson("mark", "Name an enemy",
           "From the Pilot screen, mark a hull hostile. It costs nothing and "
           "tells nobody.",
           "pilot", "marked_hostile",
           "A mark is yours: every chart, board and summary in the game "
           "reads the same list, so what you have decided about a hull "
           "follows it around. It does not start a fight. Nothing in this "
           "game makes you fight — a weaponless hull can win an engagement "
           "on resolve alone, and talking your way out is a real option "
           "with real odds.",
           chapter="iron"),

    Lesson("fight", "Take her into a fight",
           "Open fire on a hull you have marked, from the Pilot screen's "
           "fire control.",
           "pilot", "fought",
           "The band a fight opens at is the range you flew to, so closing "
           "is a manoeuvre rather than a menu pick, and every mount has an "
           "arc that must bear. You sit in one seat a turn — helm, gunnery "
           "or engineering — and your officers hold the others at their own "
           "level. Heat is the ceiling on everything: guns make it, and a "
           "hull over its cap cooks.",
           chapter="iron"),

    # ── VIII. Roots ───────────────────────────────────────────────────────
    Lesson("plant", "Plant something that lasts",
           "Found a colony on a surveyed body from the System screen. You "
           "will need a seed bay fitted and the stores to fill it.",
           "system", "planted",
           "A holding is the only thing in the game that pays you while you "
           "are somewhere else. Each class grants something specific — "
           "sensor reach, fabrication, a berth, a place the picket mesh "
           "reports from — and the grants are read by the systems they name "
           "rather than being flavour.",
           chapter="roots"),

    Lesson("empire", "Read your own account",
           "Open the Empire screen and look at what your holdings yield and "
           "cost.",
           "empire", "saw_empire",
           "Upkeep is real and a badly chosen holding loses money for years "
           "before it pays. The same screen tracks the five victory "
           "conditions, all of which are open from turn one and none of "
           "which is required. The Bloom is on it too: it is an antagonist "
           "with stages, not a timer.",
           chapter="roots"),

    # ── IX. Powers ────────────────────────────────────────────────────────
    Lesson("diplomacy", "Meet the powers",
           "Open Diplomacy and read the relations matrix.",
           "diplomacy", "saw_diplomacy",
           "Two axes, not one: what each power thinks of you, and what they "
           "think of each other. Tribute, intelligence and relief move the "
           "first; only brokering moves the second, and brokering needs both "
           "parties to think well of you already. Serving one power costs "
           "you with its enemies, and the game says how much before you "
           "commit.",
           chapter="powers"),

    Lesson("court", "Make a friend",
           "Improve your standing with a power — an overture from the "
           "Diplomacy screen will do it.",
           "diplomacy", "courted",
           "Standing buys real things: patience from harbourmasters, cheaper "
           "berthing, charts of their space, and eventually treaties. It "
           "also decays, and gifts show diminishing returns, so goodwill is "
           "a garden rather than a purchase.",
           chapter="powers"),

    # ── X. The long game ──────────────────────────────────────────────────
    Lesson("yard", "Visit a yard",
           "Open the Shipyard. You do not have to build anything.",
           "yard", "saw_yard",
           "A hull is opened only where there is a yard to open it. Here you "
           "design from the parts you have unlocked, cost it, and queue it — "
           "and the designer refuses what the frame will not take: a grown "
           "hull will not carry a fusion lance, a Yards hull will not carry "
           "an intima.",
           chapter="the-long-game"),

    Lesson("plans", "Look at her as she is",
           "Open the Ship screen's Plans tab and look at the drawing.",
           "ship", "saw_plans",
           "The drawing is the ship: the fittings you chose, the hold as it "
           "stands, the berths, and the blight where she is hurt. A hull "
           "that has been in a fight looks like one.",
           chapter="the-long-game"),

    Lesson("refit", "Change something",
           "Fit or strip a part at a yard — even a small one.",
           "yard", "refitted",
           "Every part costs mass, and mass costs acceleration, which is a "
           "trade you feel at the conn. Grown hulls heal and eat phosphate; "
           "fabricated hulls never mend but are welded in weeks. There are "
           "five families and thirty-five hulls, and the grown fleet is "
           "deliberately only one option.",
           chapter="the-long-game"),

    Lesson("work", "Take on some work",
           "Accept a contract from the board on the Port screen.",
           "port", "took_contract",
           "Contracts are optional work with deadlines, checked on the clock "
           "and completed the moment their terms are met rather than when "
           "you remember to hand them in. Commissions are the escalating "
           "kind: they open doors and close others.",
           chapter="the-long-game", skip_if="have_worked"),

    Lesson("codex", "Read the record",
           "Open the Codex — the class reference, the powers, and the "
           "glossary.",
           "codex", "saw_codex",
           "That is the whole tutorial. What is left is the game: five "
           "endings open from turn one, a sector that keeps moving whether "
           "you are watching or not, and a Bloom that is somebody's "
           "containment failure with a Charter serial still on it. The "
           "Academy tab under Help will take you through any course again.",
           chapter="the-long-game"),
]
