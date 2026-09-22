"""Manual topics for what the 2026-09 innovations added to the game.

Split out of `data/help.py` when it reached five hundred lines. Same
`Topic` shape, appended to `help.TOPICS` in this order, so the manual reads
as one book."""

from __future__ import annotations

from .help_types import Topic

MORE_TOPICS = [
    Topic("sound", "What you hear", "",
          ("The ship is quiet on purpose. Every sound is made by the game "
           "itself the first time it runs — soft tones and filtered noise, "
           "nothing bright — and each one means something.",
           "The log chimes once per kind of news: two rising notes for good, "
           "one mid pulse for something uneasy, a low falling tone for bad. "
           "A burst of news chimes once, not once a line. A held thruster "
           "rumbles, higher with the throttle; the collision guard pings "
           "faster as contact nears, and double-pips once she cannot be "
           "stopped; two small bells mean a berth made fast.",
           "Under everything is the system you are in: a warm drone at a red "
           "dwarf, an open fifth at a bright star. And under that, the Bloom "
           "— a low swell that grows with what you have seen of it. You can "
           "hear it getting worse.",
           "Volume, effects and ambience are in Options; the speaker at the "
           "window's top right mutes everything with one press."),
          see=("saving",)),
    Topic("hunts", "Rivals, and the hunt", "law",
          ("Some of the hulls you meet will not forget you. A raider you ran "
           "from, a posted price, a Concordat captain you let go, the cartel "
           "you sold under, a Bloom hull you did not finish — each can rise "
           "as a rival with a name, a hull that keeps its holes, and a file "
           "on the Law screen's Hunts tab. Beaten, they go to the yard and "
           "come back a level stronger. Spared, they may stand beside you "
           "once, or turn on you.",
           "The board at a quay posts prices: rivals, and raiders where the "
           "law says raiders work. Taking the paper gives a fresh sighting; "
           "a sighting goes stale by the day. At the system, a search states "
           "its odds before a day is spent, and a find is a fight on your "
           "terms: you pick the band.",
           "Running dark — the transponder off, on the heading bar or the "
           "Ship screen — means fewer meetings and the first volley when a "
           "hunt finds its quarry. A quay does not like it, and a patrol "
           "that finds you dark writes it down."),
          see=("law", "fighting-well")),
    # Innovation 5: freight lines.
    Topic("house", "A trading house, and its freight lines", "empire",
          ("Every tonne you trade moves in your own hold with you sitting in "
           "it. A trading house is how trade scales: charter one at a Station "
           "or a Fleet Hub, put haulers of your own on lines, and hire a "
           "master for each. A line is two ports, a good, a rule for buying "
           "and one for selling, and a cadence.",
           "The lines trade through the real counters on the sector's clock. "
           "They pay the quay, they move the price, and a route worked too "
           "hard stops paying: a master will not sail a spread that has "
           "closed, and lines that wait are paid to wait. The forecast on the "
           "new-line dialog runs the market's own arithmetic, other lines on "
           "the route included, and states the risk as a chance of loss.",
           "Risk is the systems a route crosses: lawless space robs cargoes, "
           "the Bloom takes hulls, a war zone seizes cargoes. Insurance is a "
           "price for certainty, never a way to make money. Masters want "
           "paying on time; one who is not, or who loses a hull, walks.",
           "Money reaches the house only from a sale, from your purse, or "
           "from an underwriter on a claim; it reaches your purse only by a "
           "sweep or a withdrawal. The ledger says where every credit went."),
          facts=("house",), see=("money", "trade", "empire")),
    Topic("adaptation", "A hull that remembers", "ship",
          ("A grown hull is alive, and it changes with use. Every act that "
           "loads the body is recorded against the hull that did it: damage "
           "taken under fire, running over the heat cap, light-years crossed, "
           "days at a dim star or a blue-white one, tonnes mined, surveys "
           "that saw something new, ocean dives and hard-burn crossings. The "
           "Body tab on the Ship screen shows each channel filling toward its "
           "next threshold.",
           "Cross one and an adaptation emerges: a small, permanent change "
           "with a gain and a cost, both stated. Encourage it and it sets in "
           "sooner, for growth material out of the stores — the body is grown "
           "by eating the rock. Suppress it and it fades, and the channel is "
           "starved back so it does not come straight again. Do nothing and "
           "it sets in by itself; the organism does not wait for permission.",
           "A body has room for only so many, by its size, and a surgeon at a "
           "Fleet Hub's gestation bay can prune one back out for credits and "
           "days. Hybrids adapt more slowly and keep fewer; xeno hulls adapt "
           "faster and grow what they grow at random. Fabricated and "
           "synthetic hulls never adapt: metal does not remember."),
          facts=("body",), see=("ship",)),
    # ── the Far Reaches (`data/regions.py`) ────────────────────────────────
    Topic("reaches", "The Far Reaches", "map",
          ("The Verge is not all there is. Three regions lie past its rim, "
           "each behind a deep anchor — a Weave gate that answers nothing in "
           "the Verge because it was built to reach somewhere else. The "
           "chart has a tab for each: dark until its anchor is relit, then "
           "drawn in its own frame, because no drive crosses the rim and "
           "light years mean nothing between two regions.",
           "The Shoals are an emission nebula: sensors reach half as far "
           "and a survey reads less, nobody's law reaches at all, and the "
           "Freehold havens there sell nebular condensate — made nowhere "
           "else, and bought dear by the Concordat and the Dry Choir.",
           "The Hollow is a void of long lanes and dead stars. Rogue "
           "worlds drift through it with no sun at all, and a grown hull's "
           "intima makes no air alongside one: you breathe the tank. Its "
           "own rings, older than the Weave, cross it for nothing, and one "
           "derelict relay sells reaction mass.",
           "The Cradle is a young cluster of blue giants. The crew takes "
           "a dose every day aboard and the hull never cools below half its "
           "cap; shielding and a melanised rind cut the dose. The ore is the "
           "richest in the sky, and nobody holds any of it yet.",
           "The endings are about the Verge, and stay so. Growth that "
           "crosses a deep gate is ground lost past the rim, not a new "
           "condition on containment."),
          facts=("reaches",), see=("deep-gates", "weave", "map")),

    Topic("deep-gates", "Relighting a deep anchor", "system",
          ("A deep anchor is on the chart from the first day, dark, and it "
           "says where it goes. Relighting one is a project in three parts, "
           "and the System screen at the anchor states all three before "
           "any of them is spent.",
           "Read it: a deep survey of a body in the anchor's system, the "
           "one way of looking that reaches what is buried. Understand it: "
           "the Deep Weave technology, which the bench learns from survey "
           "and specimen evidence rather than from reading. Pay for it: "
           "credits and material, at the anchor, and a month of work.",
           "Then the region is there, and the gate is nobody's: no toll, "
           "either way, instantly. It is also a road for the Bloom, like "
           "any ring you wake — an infested anchor hands a share of its "
           "growth across every season, so opening a door next to "
           "something bad is a decision, not an upgrade."),
          facts=("reaches",), see=("reaches", "survey", "weave")),
    # Innovation 6: the Assembly (`sim/assembly`, the Diplomacy screen's tab).
    Topic("assembly", "The Assembly", "diplomacy",
          ("Every season the four powers sit at a capital in turn — the "
           "Charter's, the Yards', the Freeholds', the Choir's — and vote on "
           "two or three motions. The clerk publishes the order paper a month "
           "ahead, by despatch. A motion passes on three votes of four, or on "
           "two with the other two abstaining, and binds for half a year.",
           "Each power votes its interest, and the screen shows every part of "
           "it: its creed, pride in its own motion, a grievance against the "
           "sponsor, its agenda, its purse and the state of the sector. The "
           "forecast is the vote if nothing changes.",
           "You can move a vote before the sitting: petition a power (it "
           "costs standing with them), pay for the vote (credits, and the "
           "others remember it was bought), or leak the sponsor's papers (a "
           "chart or a field note on them, and they will know). Be in the "
           "seat's system on the day and you speak to all four at once.",
           "Powers that vote together come closer; a power voted down takes "
           "it out on whoever voted it down. Brokering motions everybody can "
           "live with is the one road that raises every pair at once — the "
           "honest road to the Concord. What passes is real: halved dues, a "
           "ceasefire, an embargo at the counter, a levy on salvage."),
          see=("diplomacy", "trade")),
    # Innovation 2: the Kith (`sim/kith`, the gathering panel at a port).
    Topic("kith", "The Kith", "port",
          ("The Cradle is not empty. The Kith live there: colonies of many "
           "bodies grown along one stem, speaking in light. You meet them the "
           "first time you enter the Cradle, and their gatherings are marked "
           "on the chart once you have been to one or been told the way.",
           "Everything you do with them is gated on the lexicon — signs in "
           "four domains, each understood from nothing to fluent. Listen at a "
           "gathering (a science officer and a good array help), work the "
           "recordings you make on the decoding bench, give gifts, and watch "
           "their stars: each teaches. Listening alone stops short of "
           "conversation.",
           "A gathering posts no prices and sells nothing. Offer a gift from "
           "the hold: it is answered in songglass, by what that gathering "
           "thinks of the good — prized, welcome, plain or an offence — and a "
           "little more generously than it was given. The surplus is owed; "
           "the next gift pays it first, and a debt left too long becomes an "
           "insult. You can ask first, and the answer can be misheard.",
           "Every act has a stated chance of being misread, which costs "
           "standing and sometimes starts a fight. Understand them well "
           "enough, and be trusted, and they will sing an accord: their "
           "hulls, grown at a gathering, and a pilot. Songglass sells well to "
           "the Charter and the Dry Choir; their grafts fit a grown hull."),
          facts=("kith",), see=("reaches", "trade")),
    # Innovation 8: officer arcs (`sim/arcs`, the Ship screen's Crew tab).
    Topic("arcs", "Your officers' stories", "ship",
          ("Everyone you sign on has something they want that is about "
           "them: a brother's beacon out of Bloom country, a cartel's slate, "
           "a garden, a race. Their story is three beats long, and the Ship "
           "screen's Crew tab says whose is whose and how far each has got.",
           "A beat arrives as a despatch in their voice. Some come on a "
           "date; some when the ship reaches a place they name; some when "
           "they trust you enough to say it; some after a fight, a burn or "
           "a new holding. Every answer says what it costs, what it may "
           "win and what they will think of you before you choose it.",
           "Nobody waits for ever. A beat left unanswered, or a place never "
           "flown to, lapses and costs their loyalty; a neglected last beat "
           "costs the most, and an officer already restless may leave over "
           "it. A place past a dark rim is different: they wait, and say "
           "what would open the way.",
           "A story finished well leaves a signature — an ability that "
           "officer alone has, stronger than a trait and bound to what "
           "happened: a steadier burn, a floor under a power's regard, a "
           "luckier hand on the ground. The Codex keeps the stories told."),
          see=("crew", "despatches")),
    # Innovation 9: renown and the Voyage (`sim/renown`, Holdings' tab).
    Topic("renown", "Renown, and the Voyage", "empire",
          ("The Registry of Captains keeps your record. Survey a body, sell "
           "a cargo you brought, finish a contract, open a line, see a "
           "rival dead: each is a milestone, read from what you have "
           "actually done, never granted twice. Each is worth renown, and "
           "renown climbs the ranks: Master, Captain, Commodore, Admiral of "
           "the Verge, Legend.",
           "Every rank carries something real. A Captain is found a berth at "
           "a full quay and pays no fee to charter a trading house; a "
           "Commodore's recruits come a level better; an Admiral's standing "
           "with the four powers never falls below Neutral, and the "
           "Assembly tables one motion a year in their name; a Legend's "
           "ship's name goes on a star.",
           "Each of the ten endings has three rungs on the way to it, and "
           "each rung pays toward the next — credits out of a named power's "
           "purse, standing, bench work or a title. The Voyage tab on "
           "Holdings draws them as ladders, with what feeds the next rung.",
           "The first officer's counsel on the Sector Chart names three next "
           "moves, each with its reason and a button that opens the screen "
           "it is made on. Dismiss it for a month; the Help menu brings it "
           "back. When the chronicle ends the career is written up as a "
           "memoir, on the Aftermath screen and in the Hall of Captains on "
           "the title, which a new chronicle never clears."),
          see=("assembly", "house")),
    # Innovation 7: the living sky (`sim/phenomena`, the System screen's
    # Sky strip, the chart's rings, the shelter mark on the Pilot and Helm).
    Topic("phenomena", "A living sky", "system",
          ("Stars do things for a while. A red dwarf flares for a day or "
           "five; a comet falls through a system for a season or two; an "
           "ion storm shuts a system's lanes; a sunless world drifts through; "
           "the giants light up with aurorae. The Charter observatory "
           "forecasts most of them on the despatch board, with a lead and a "
           "confidence — and the confidence is honest: seventy per cent comes "
           "true seven times in ten. Better sensors and a CHORUS Node of "
           "yours see further ahead and cry wolf less.",
           "A flare is a dose to a crew out in the light: some morale, never "
           "a death. Be at a berth, or keep to a body's shadow from the Helm "
           "(a little reaction mass a day), and the crew takes none of it. "
           "The Pilot and Helm say whether you are sheltered. A storm "
           "refuses a jump and says how long it has left; a comet can be "
           "mined for volatiles and rare phosphate until it leaves, and "
           "floods the nearby quays with volatiles while it passes.",
           "Everything in the sky is science. Observe it from the System "
           "screen — the strip says the days, the evidence and what the data "
           "would fetch before you commit — and sell what you saw to the "
           "Charter or the Dry Choir. Phenomena evidence speeds the sensor, "
           "shielding and Deep Weave programmes.",
           "Once the Cradle is open, one of its giants will go nova. It "
           "brightens for months first, and everything near it takes a "
           "mounting dose; the burst scours the system and leaves a neutron "
           "star. Watch it brightening, and watch the burst from a "
           "neighbouring star: the Choir pays a fortune for that."),
          see=("survey", "despatches", "research")),
    Topic("afoot", "Afoot: walking a deck", "afoot",
          ("The Afoot screen puts people on the deck of somewhere the hull "
           "already is: your own hull, the quay, a habitat drum, a holding, "
           "a settlement, one of the trade's stations or bases, and any "
           "dead hull adrift in the system. Choose where, who goes (up to "
           "four: the captain, the officers, walking machines), and whether "
           "to carry what the law here forbids.",
           "A berth has a size. A hull longer than the mouth of a bay or "
           "the span of the structure itself is refused and held off — a "
           "990 m LEVIATHAN is not tying up to a 400 m quay — and her "
           "people come across by boat instead. Where a structure keeps "
           "boats (anything big enough to crew them, a quay from level two, "
           "never a Weave gate), a hull that stops and waits is walked "
           "alongside for no reaction mass at all: free and slow against "
           "fast and expensive, and the captain chooses.",
           "Getting there is part of it. A chronicle starts made fast "
           "alongside its home quay, and the crew walks across. Anywhere "
           "else the hull is only in orbit near things until it comes "
           "alongside — the harbour's pilot brings her in, or you take the "
           "conn — and until then the crew has to cross: in the ship's boat "
           "(a hull with a crew of six or more carries one), on the place's "
           "own shuttle for a fare, or in suits on a line across a couple of "
           "kilometres of open space to something in orbit. Whoever breathes "
           "goes in a vacc suit; a lineage that does not, goes as it is. The "
           "Concourse and the start page both show every way and what it "
           "costs. Cargo and a yard's business still go by lighter.",
           "Every plan is drawn in the shape of what it is. A hull's decks "
           "are slices through its own silhouette — bridge forward, drives "
           "aft, each fitting at its own mount, berths for the whole crew, "
           "air, water, stores and a way off in a hurry — and refitting her "
           "changes them. A quay is its can, arm and mast; a Fleet Hub its "
           "spine, four berths and two rings; a drum is a town inside it; "
           "a dome is open ground under its shell; a settlement is sheds "
           "and streets, open to a sky you can breathe or sealed in tubes "
           "against one you cannot. Every door the Concourse lists is a room "
           "on the plan, under the same name, and a place with more doors "
           "than a deck holds has more decks: a Fleet Hub's rings are as "
           "many levels deep as its concourse needs.",
           "Every deck has a weight, shown beside its name. A hull and a "
           "quay are weightless; a ring is spun, and each of its levels is "
           "drawn unrolled — walk off one end and you come on at the other, "
           "the outermost level the heaviest; a drum's floor is a full "
           "gravity; the ground is its world's own. Weightless, anybody "
           "without Zero-G goes hand over hand at twice the cost of a step, "
           "shoots unbraced, and is set drifting by the kick of a gun; "
           "magnetic boots put that right, and the people who live aboard "
           "are at home in it. A heavy world slows everybody.",
           "Left-click a square to walk there, a person to talk to them, an "
           "enemy to shoot. Right-click goes up to whatever is there. Arrow "
           "keys step; Tab takes the next person in hand; Space ends the "
           "turn. In calm, a click walks the whole way and the others "
           "follow; once somebody hostile has seen you, it is turns: each "
           "person moves and does one thing, then everybody else does.",
           "Every roll is two dice against eight, and every button says its "
           "odds before you press it. A shot is Gun Combat plus DEX, the "
           "weapon's own bonus, the range and any cover; damage is the "
           "weapon's dice plus by how much it hit, less armour. At no "
           "stamina somebody is down and bleeding: first aid stops it, and "
           "a friend can carry them out. The captain always comes home. An "
           "officer left lying on a dead hull does not.",
           "A gun with Auto can fire a burst, which adds its Auto to the "
           "damage, or lay down suppressing fire: nobody is hit, but the "
           "target and anybody beside them are pinned for a round and shoot "
           "the worse for it. Grenades are thrown with Athletics and DEX and "
           "land a square off on a miss: a fragmentation grenade hurts "
           "everybody in its burst, friend or not, a stun grenade floors "
           "them, and smoke hangs for three rounds and blinds every line "
           "through it.",
           "Places have their troubles. Two officers whose convictions "
           "collide can be at it when you walk your decks; where the law is "
           "thin, hard cases want a toll and a drunk wants a fight; your own "
           "works can be failing, on strike or sabotaged, and setting them "
           "right by hand runs them sweeter for a month. At a Kith gathering "
           "they sing a phrase and wait for it back, and an elder may sing a "
           "whole domain's song of passage: both teach the lexicon.",
           "Staff stand behind their counters: talk to them to do business "
           "across the counter, take a room, sign on a hand or ask a favour "
           "of the harbourmaster. Constables walk the corridors in "
           "proportion to the law level. What anybody sees you do — take "
           "from a locker, break a lock, hit somebody who was not hitting "
           "you — is a charge when you leave.",
           "What is found comes home only if you walk out with it: kit to the "
           "captain's keeping, cargo to the hold, data to the bench, study "
           "to the xenology desk. Wounds are kept, and mend by the day, "
           "faster with a medic and a sickbay. Somebody left lying where "
           "people live is found and brought home; a stun wears off."),
          see=("crew", "law", "ground", "combat")),
    Topic("craft", "Small craft: the cradle and the cockpit", "ship",
          ("A hull of any size carries small craft in cradles on its flank, "
           "and a captain starts with one: a WASP, a grown single-seat "
           "interceptor, with a hatch through to the cradle deck so a pilot "
           "walks out to her in shirtsleeves. The Ship screen's Cradle tab "
           "is the flight line.",
           "Somebody has to be certified to fly one — a Pilot ticket, which "
           "the captain holds and so does the navigator, and nobody else "
           "takes her out. Whoever goes is off their station until she is "
           "back on the cradle.",
           "A sortie is a flight of her own, flown from the cockpit window: "
           "the stick, the main drive, the computer's three modes, and "
           "instruments for her hull, her tank, her speed and how far off "
           "the cradle she is. She burns her own reaction mass, not the "
           "ship's, and the cradle tops her up on recovery from the hold.",
           "What she is for: a firing run at a hull inside ten thousand "
           "kilometres — her guns against theirs, and what comes back comes "
           "back at a craft the size of a launch; an hour's looking at a "
           "body or a contact, which is survey data on the bench and a world "
           "properly on the chart; and a lift, since the craft on the cradle "
           "is the ship's boat when the crew has to get across to somewhere "
           "the hull is not made fast to.",
           "Classes: the WASP and the heavier SHRIKE are fighters, the MOTE "
           "is all array and tankage, and the DORY is a boat with three "
           "seats behind the pilot. A craft is never in the fleet, never "
           "jumps, and does its work inside one system."),
          see=("crew", "flying-well", "combat")),
    Topic("establishments", "Yards, hotels, wheels and dens", "concourse",
          ("Besides its quay, a system has whatever the trade has built "
           "round it: shipyards and hull nurseries, grand hotels and "
           "spacers' rests, pleasure palaces, surgical stations, spa "
           "stations, gaming wheels and free markets in orbit; mining and "
           "research bases, garrisons, farms, retreats and smugglers' dens "
           "on the ground. A system with a Fleet Hub has three or four; a "
           "quiet rock one at most.",
           "A station is a berth on the System chart: fly to it and go "
           "aboard, or hail it. A base stands on its world and keeps a pad in "
           "orbit over it, its landing field's berth: fly to it and go down. "
           "Each has its own doors, open there "
           "and nowhere else — the Grand's suites, the wheel's high table, "
           "a quiet surgeon who keeps no records — and of everybody else's "
           "only what its business is. A garrison keeps a hard law; a den "
           "keeps none.",
           "A shipyard lays down welded hulls and refits one alongside it, "
           "where the port has no slips of its own; a hull nursery grows "
           "grown ones, and refits them. Where a dead hull is adrift, "
           "breakers may have set up: a breakers' yard wakes a derelict "
           "REVENANT for a captain with the research and the xenolith — "
           "though nobody lays down an ANTIPHON but an array of your own. "
           "Every one of them can be walked, laid out as it is "
           "built: a hotel is a ring, a palace a drum, a market a can, a "
           "base sheds on the ground.",
           "Alongside a house, its Concourse offers a stake: a tenth of it, "
           "paid monthly out of the takings for as long as it trades, with "
           "the quarter's statement sent by despatch. Sold back, a stake "
           "fetches four-fifths of what it cost."),
          see=("afoot", "shipyard", "trade")),
]
