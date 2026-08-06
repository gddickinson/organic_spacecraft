"""The manual: what each screen is for, and how the systems reach each other.

Written prose where prose is right, and **generated facts where facts would go
stale**. A manual that says "thirty-five hulls" is wrong the day somebody adds
one, so anything countable is counted at read time from the table it lives in.
`sim/manual.py` does the counting; this holds the words and says which screen
each topic belongs to.

Topics are ordered the way a new captain meets them, not alphabetically.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    screen: str              # which view this is about, "" for general
    body: tuple              # paragraphs
    #: Generated lines, by id, resolved in `sim/manual.py`.
    facts: tuple = ()
    see: tuple = ()          # other topic ids


TOPICS = [
    Topic("first", "The first thing to do", "",
          ("Nobody will tell you what to do about the Bloom, because nobody "
           "knows. There is no track here, only things worth doing.",
           "The reliable opening: survey the bodies in the system you start "
           "in, take the survey data to the port and sell it, buy reaction "
           "mass, and move on. That pays for itself from day one and it is "
           "how you learn what a system looks like.",
           "Every ending is open from turn one and none is locked behind "
           "another. You do not have to choose now."),
          facts=("endings", "starting_kit"), see=("survey", "trade")),

    Topic("moving", "Getting anywhere is a decision", "helm",
          ("A jump drops you at the edge of a system, not alongside anything. "
           "Bodies sit on real orbits and keep moving while you fly, so the "
           "helm aims at where a thing will be rather than where it is.",
           "Four burn profiles trade reaction mass against days. Coasting is "
           "always free — that is deliberate, and it is what stops an empty "
           "tank from becoming a dead chronicle.",
           "A hard burn arrives hot. Heat sheds on the clock, but above the "
           "cap the radiators stop keeping up and the hull cooks, so burning "
           "hard repeatedly costs real integrity. The panel says what you "
           "will arrive at before you commit."),
          facts=("burns", "reach"), see=("map", "instruments")),

    Topic("law", "Four powers, four laws, and none of them universal", "law",
          ("There is no law of the Verge. There are four powers, each with "
           "its own, and each is only as long as that power's arm. An act "
           "offends nobody who could not see it — and a power sees a system "
           "through its quay, its register, its hulls on station, or a "
           "friend who has one of those. Working where a power holds nothing "
           "is not innocence. It is being unobserved, and it is allowed to "
           "feel different.",
           "Being seen is not being charged. A witnessed act sits on the "
           "file until that power sweeps it, which happens about monthly — "
           "so there is a window in which leaving is a plan. Left long "
           "enough unfiled, most things age out. Destroying a hull and "
           "germinating without a licence never do.",
           "The four forums are deliberately not comparable. The Charter "
           "fields no armed vessel and never will: its law is paperwork, and "
           "its whole armoury is the word no — no clearance, no licence, no "
           "gate. The Concordat thinks in property and has hulls to collect "
           "it with. The Freeholds have no forum at all; a claim becomes a "
           "price on your hull, posted openly and sold to whoever fancies "
           "the work. The Dry Choir holds no hearing, because there is "
           "nowhere to stand and nothing is audible to you — what comes out "
           "is anathema, and their network simply stops answering.",
           "Every forum decides in your absence. Not turning up multiplies "
           "the assessment, makes them reach for a heavier instrument, and "
           "is itself an offence that never prescribes. Answer, admit, or "
           "settle before the day — the screen states the whole price of "
           "each before you choose.",
           "There is always a way out. Pay the judgment and whatever it "
           "bought them lifts itself. Buy the paper back off whoever holds "
           "it. Ask a harbourmaster who is fond of you to lose the file, "
           "which costs money and most of what they think of you. Or sign a "
           "treaty: an amnesty is a clause, and it is why a captain deep in "
           "trouble with one power may suddenly want very badly to be "
           "friends with it."),
          facts=("powers",), see=("diplomacy", "trade")),

    Topic("despatches", "Despatches, and why word arrives old", "despatches",
          ("A courier is not a radio. Word moves through the sector the way "
           "everything else does: instantly within a system, in hours where "
           "the Weave is lit, aboard ordinary hulls where it is not — about "
           "eleven days a light year — and at the speed of light where no "
           "hull can reach at all. A bulletin from the far side of the "
           "Verge is a history lesson by the time it is in your hand, and "
           "the board says how old each one is.",
           "Some despatches ask a question. Those stay on the board until "
           "you answer them; nothing forces you, and nothing stops the "
           "clock — but a power that wrote to you remembers whether you "
           "wrote back. Plain bulletins can simply be noted, and any left "
           "unread for a year are swept out with the rest of the litter.",
           "The Chronicle tab is the ship's own log, all of it — the "
           "sidebar shows the last sixty lines; every line the ship has "
           "kept is here, and can be sifted by kind."),
          see=("weave", "diplomacy")),

    Topic("map", "The chart, and what you can actually reach", "map",
          ("The dashed ring is one jump. The question that matters is what "
           "you can get to at all, by hopping — and often the answer is not "
           "everything. Stars struck through are behind a gap no amount of "
           "hopping closes.",
           "Opening the rest means a better drive. The chart says which one "
           "and how much it would open."),
          facts=("reach",), see=("moving", "shipyard")),

    Topic("survey", "Surveying, and why it pays", "system",
          ("Surveying a body tells you what is on it — biomes, lifeforms, "
           "anomalies, buried alien sites — and feeds the research bench.",
           "A chart is the record of a *completed* survey: every body in the "
           "system. It is priced on what is in the system rather than on how "
           "many rocks it has, and different powers pay for different things."),
          facts=("survey_pay",), see=("research", "trade")),

    Topic("trade", "Trade, and the freight desk", "port",
          ("Prices drift daily toward each port's own equilibrium, so a "
           "profitable run stays profitable for a while and then quietly "
           "stops being.",
           "Within a starting jump only about one lane in twenty is worth "
           "flying. The freight desk draws on two honest sources — your own "
           "register of prices you wrote down, and the harbourmaster, who "
           "will name his own power's ports but not quote you their board. It "
           "ranks runs by what the voyage clears, not by the spread.",
           "One good in the table is contraband: worth more exactly where it "
           "is forbidden, and the power that forbids it opens your hold at "
           "the dock."),
          facts=("goods",), see=("contracts", "customs")),

    Topic("customs", "Contraband, and the people who look for it", "port",
          ("One good in the table is outlawed by somebody, and it is worth "
           "more exactly where it is forbidden. That is the whole trade: the "
           "power that bans it is the power that pays.",
           "The unposted market is reached from the port screen and it is not "
           "hidden from anybody. Approaching cleanly, standing well and a "
           "concealed hold each take a share off the odds of being searched; "
           "none of them retires the risk.",
           "Being caught costs the cargo, a fine, standing, and — the part "
           "that lasts — scrutiny, which is that power's memory of what you "
           "have been carrying. It decays, slowly."),
          facts=("goods",), see=("trade", "diplomacy")),

    Topic("contracts", "Work worth taking", "port",
          ("Contracts are posted per port and scaled by distance, checked on "
           "the clock, and complete the moment their terms are met.",
           "Taking a power's work is a position, not an errand: finishing it "
           "costs you standing with everyone that power is at odds with, in "
           "proportion to how bad the rift actually is."),
          facts=("contract_kinds",), see=("diplomacy",)),

    Topic("research", "The bench", "tech",
          ("A programme is fed by evidence in four kinds, and the four come "
           "from four different parts of the job — a propulsion programme "
           "cannot be fed by botany.",
           "Four ways to run one: carefully, on parallel tracks, pushed, or "
           "reverse-engineered from somebody else's work. Pushing is fastest "
           "and risks setbacks."),
          facts=("tech_tree",), see=("xeno",)),

    # `screen` must name a view the window actually holds — "xeno" once sat
    # here, and the manual's "go to" button bricked the whole window on it.
    Topic("xeno", "Alien technology", "codex",
          ("Four cultures left twelve technologies scattered as buried sites. "
           "None can be derived. Understanding accumulates from excavating a "
           "site, taking relics apart, buying field notes, and seizing them "
           "off a hull you destroy.",
           "At full understanding a technology is *incorporated* — it never "
           "appears in the research tree, because you could not have worked "
           "it out."),
          facts=("xenotech",), see=("research", "ground")),

    Topic("ground", "There is a game on the ground", "",
          ("Landing a party opens a zone revealed one tile at a time. Moving "
           "costs days of supply; known ground is cheap to re-cross, which is "
           "what makes coming home survivable.",
           "Every feature is a choice, and each states its odds, the officer "
           "who would take it, the prize, and what a failure risks. Nothing "
           "is banked until the party is back on the lander."),
          facts=(), see=("crew", "xeno")),

    Topic("combat", "Combat is positional", "",
          ("Ships carry a heading and a speed on a real plane. The range band "
           "is derived from an actual separation rather than stored, so "
           "closing is a manoeuvre rather than a menu pick. Every mount has a "
           "firing arc and will refuse to fire outside it.",
           "Each turn you take one station personally — Helm, Gunnery or "
           "Engineering — and your officers hold the other two at their own "
           "level, which is competent and worse than you. The bridge says "
           "what taking each seat is worth given who you have."),
          facts=(), see=("crew", "ship")),

    Topic("crew", "Crew, and why the stations matter", "port",
          ("Six stations. An officer's level decides the odds on anything "
           "resolved against their stat, on the ground and in a fight.",
           "It is not a nicety: every ground option that pays a field note "
           "wants comms or medicine, and the opening crew is science, nav and "
           "engineering. A captain who never visits the berths is offered "
           "notes they cannot take."),
          facts=("stations",), see=("ground", "combat")),

    Topic("ship", "The hull, and what grafts to it", "ship",
          ("Five families, and which parts graft to which frame is a rule: a "
           "grown hull refuses a fusion lance, a Yards hull refuses an "
           "intima, a hybrid takes either.",
           "Fitted mass is not free — a full hold slows you — and power "
           "discipline is real: draw more than you generate and everything "
           "sags.",
           "The Plans tab draws the ship as fitted. Click any piece to read "
           "it."),
          facts=("hulls", "layers"), see=("shipyard", "instruments")),

    Topic("shipyard", "Refitting and building", "yard",
          ("The yard shows the ship you *would* have beside the one you do, "
           "and the bill for the difference. Removed parts sell back at half.",
           "You hold the technology for everything already bolted to your "
           "hull, so anything you remove can be put back."),
          facts=(), see=("ship", "map")),

    Topic("empire", "Colonies", "empire",
          ("Plant one and walk away; it yields every day, wherever you are. "
           "The seed dialog says what will grow — yield, upkeep, effects and "
           "a rough payback.",
           "Territory is contested in both directions. Planting inside a "
           "power's declared space costs standing, and a power will annex a "
           "system you hold in, which is a question rather than a news item."),
          facts=("colony_classes",), see=("diplomacy",)),

    Topic("diplomacy", "Two axes, not one", "diplomacy",
          ("Your standing with each power, and how the powers regard each "
           "other — a matrix that starts hostile in most pairs.",
           "Tribute, intelligence and relief move the first. Only brokering "
           "moves the second, and brokering requires both parties to think "
           "well of you already. Every overture states what it will move "
           "before you commit."),
          facts=("powers",), see=("contracts", "empire")),

    Topic("detection", "What you can see, and what can hide", "pilot",
          ("Your sensor rating is a range in kilometres, and everything is "
           "measured against a hull that is transponding, warm and lit. "
           "Worlds, stars and quays you always see — a planet is enormous "
           "and a quay squawks because being found is what it is for.",
           "A hull is the question. Dropping the transponder and going cold "
           "costs nothing and takes about three quarters of the range off "
           "anyone looking, which is why every raider does it. A shroud "
           "costs power and mass. A cloak is alien work, and a hull that has "
           "one is inside your gun range before your board admits it exists.",
           "A contact at the edge of your envelope is a smear, and the "
           "collision guard reads a poor fix pessimistically — it inflates a "
           "closing rate it cannot trust, so a cheap array warns you early "
           "and vaguely rather than late and precisely. The panel says "
           "'estimated' when that is what it is doing.",
           "The number that decides whether any of this matters is not the "
           "range but your stopping distance. Anything you see with less "
           "room than that is something you cannot do anything about — so a "
           "cloak beats your brakes long before it beats your eyes, and "
           "flying fast through busy traffic in a cheap hull is a real risk "
           "rather than a free one."),
          facts=("detection",), see=("instruments", "moving", "shipyard")),

    Topic("weave", "The Weave, and how to ride one", "map",
          ("A Weave anchor is a ring somebody else built, standing off a "
           "body in a system like a quay does. Two anchors that are both "
           "*lit* and joined to each other make a ring you can transit — "
           "and a transit is instant. It is the only thing in the Verge "
           "that costs no days at all; what it costs is a toll.",
           "**You do not fly to it to use it.** Flying alongside an anchor "
           "shows you what it is and nothing else, because a ring is ridden "
           "from the sector chart: the Weave panel there lists every "
           "destination a lit ring runs to from the system you are standing "
           "in, with the light years it saves and what the toll comes to, "
           "and a Step button for each.",
           "Most anchors start dark, and a dark one runs nothing. Waking an "
           "ancient anchor needs the Weavecraft technology before anything "
           "else — the metallurgy and the fold physics both — and then "
           "material and a stretch of days. You can also lay an anchor of "
           "your own where there is a lit ring near enough to hang one off, "
           "which is how the network becomes yours rather than theirs.",
           "The price of the network is on the same card as its use, and "
           "deliberately: growth crosses a lit ring exactly as easily as "
           "you do. Waking an anchor next to something infested opens a "
           "road for the Bloom as well as for your cargo."),
          facts=("weave",), see=("moving", "map")),

    Topic("instruments", "The instrument windows", "",
          ("Six pop-out windows — power, heat, integrity, hold, crew and a "
           "scope — that stay on top and re-read the live game. They are "
           "windows rather than a tab because the point is watching heat "
           "while you fly."),
          facts=("instruments",), see=("ship", "moving")),

    Topic("endings", "Endings, and what comes after", "legacy",
          ("Every ending is open from turn one and none is locked behind "
           "another.",
           "An ending is a turn in the sector's history rather than a stop. "
           "Taking one rewrites the world and opens an epoch with its own "
           "pressure and its own situations, and an epoch can close well or "
           "badly and be followed by another."),
          facts=("endings",), see=("first",)),

    # ── playing it well ───────────────────────────────────────────────────
    #
    # The manual above says what each system *is*. These four say what to do
    # with them, which is a different question and the one a new captain
    # actually has. The Academy tab beside this one walks the same ground
    # with your hands on the controls; this is the reading.

    Topic("first-hour", "Your first hour, in order", "",
          ("Survey the bodies where you start — the sweep is free and it "
           "costs three days. Take the data to the port and sell it. Buy "
           "volatiles until the tank is comfortable, sixty tonnes or so. "
           "Look at the contract board before you leave: work that pays for "
           "a journey you were making anyway is the cheapest money there is.",
           "Then pick a direction and go. Nothing in the Verge is on a "
           "timer that punishes exploring, and the second system you see "
           "teaches you more than the first one twice.",
           "If you do only one thing well in the first hour, make it "
           "surveying. It pays, it feeds the research bench, and it is how "
           "you learn to read a system at a glance."),
          see=("survey", "trade", "first")),

    Topic("money", "Making money, and what it is for", "port",
          ("Three reliable trades, roughly in the order they open to you: "
           "survey data, which regenerates every time you look at something "
           "new; freight, which the desk ranks by what the voyage clears "
           "rather than by the spread; and mining, which is slow, free, and "
           "never runs out.",
           "Buying low and selling high works, but prices drift toward each "
           "port's own equilibrium — so a run stays profitable for a while "
           "and then quietly stops being. Your register remembers what you "
           "saw and where; check it before you commit a hold.",
           "Money is for three things: reaction mass, a better hull, and "
           "holdings. Holdings are the only one that pays you back while you "
           "are somewhere else, and a badly chosen one loses money for years "
           "before it turns."),
          see=("trade", "contracts", "empire")),

    Topic("flying-well", "Flying her well", "pilot",
          ("Hold a thruster rather than tapping it: a held burn builds speed "
           "for as long as your hand is down, and the plumes on the diagram "
           "show exactly what is firing. The clock runs at a minute a beat, "
           "and the Time button compresses it when a run is long.",
           "Watch two numbers on an approach: the closing rate, and the rate "
           "you are *allowed*. The second is what the computer holds to, and "
           "flying inside it is the whole of a clean berthing. Alongside "
           "means at a berth, slowly — arrive fast and both hulls pay.",
           "The computer will do any of it: hold station, brake to zero, "
           "close and berth, make orbit, move away, or run for a mark. It is "
           "the same bar on every flying screen and Manual always takes her "
           "back — and a held thruster outranks it while your hand is down. "
           "Use it for the long dull parts and fly the interesting ones."),
          see=("moving", "instruments", "ship")),

    Topic("fighting-well", "Fighting, and not fighting", "battle",
          ("The band a fight opens at is the range you flew to, so the "
           "flying decides the fight before a shot. Close if your guns are "
           "short-ranged; stay out if they are not. Every mount has an arc, "
           "and turning to bring one to bear is a real decision.",
           "You sit in one seat a turn. Directed gunnery shoots markedly "
           "better than automatic, engineering routes power and patches the "
           "outermost breach, and the helm decides what will bear next turn "
           "— so the seat you take is the thing you are best at that turn.",
           "Heat is the ceiling on everything: guns make it, and a hull over "
           "its cap cooks. And you do not have to fight. Breaking off and "
           "talking has real odds, which the screen states before you try; a "
           "weaponless hull can win on resolve alone."),
          see=("combat", "crew", "ship")),

    Topic("saving", "Saving, keys and the rest", "",
          ("The chronicle saves itself whenever the calendar moves. There is "
           "one save; there is no scumming a bad roll.",
           "Anything you can be in the middle of — a crossing, an approach, a "
           "decoding exchange, an open trench, a power waiting on an answer — "
           "survives a save and is still waiting when you come back."),
          facts=("keys",), see=()),
]
TOPICS_BY_ID = {t.id: t for t in TOPICS}
