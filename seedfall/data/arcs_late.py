"""Officer arcs, the second six: the cartographer to the heir.

Split out of `data/arcs.py` at the length rule; the shapes are
`data/arc_types.py` and the registry is `arcs.ARCS`. Two of these stories
end past the rim (the cartographer's in the Hollow, the pilgrim's in the
Cradle): a beat whose place is in an unopened region waits without lapsing,
and says what would open the way.
"""

from __future__ import annotations

from .arc_types import Arc, Beat, choice

CARTOGRAPHER = Arc(
    "cartographer", "The cartographer",
    "An unfinished chart of a lost route.",
    (
        Beat("date", "", "An unfinished chart",
             "I've a chart my teacher never finished. A route nobody flies "
             "now. The first leg is easy. The rest is a question.",
             "has an unfinished chart",
             (choice("fly", "Say we will fly its legs",
                     "Then I'll plot them tonight.", loyalty=4),
              choice("sell", "Sell it to a Yards broker",
                     "She'd have hated that. So do I.", credits=800,
                     purse="concordat", loyalty=-6))),
        Beat("place", "anchor:hollow", "The dark gate",
             "The chart ends at {place}, at the dark gate. The last line "
             "points through it — into the Hollow. I want to see where.",
             "wants to go to {place}, where the chart ends",
             (choice("survey", "Stand off the gate with them a while",
                     "Someone has to open that door. When it's open, I'm "
                     "first through.", loyalty=6),
              choice("story", "Say the Hollow is a story",
                     "Stories end somewhere too.", loyalty=-4))),
        Beat("place", "region:hollow", "Where the chart points",
             "We're through. {place}. The chart's right — all of it. Let me "
             "finish it, for you and for whoever flies after.",
             "wants to fly the chart's last leg, into the Hollow",
             (choice("finish", "Let them finish the chart",
                     "Every leg. You'll never plot a jump the same.",
                     loyalty=8, signature=True),
              choice("sell", "Sell the finished chart to the Yards",
                     "Somebody else's name on it, then.", credits=3000,
                     purse="concordat", loyalty=-6))),
    ),
    "dead_reckoning")

PILGRIM = Arc(
    "pilgrim", "The pilgrim",
    "They want to see the Cradle's stars.",
    (
        Beat("date", "", "The Cradle's stars",
             "Where I was raised they said the first stars were in the "
             "Cradle, past the rim. I'd like to see them before I can't. "
             "It's a small thing to want.",
             "wants to see the Cradle's stars",
             (choice("promise", "Promise them the Cradle",
                     "I'll remember you said it.", loyalty=5),
              choice("wall", "Say the rim is a wall",
                     "Walls have gates.", loyalty=-4))),
        Beat("place", "anchor:cradle", "The gate",
             "{place}. The gate's dark. I can feel it anyway. Can we stay a "
             "day?",
             "wants to see the Cradle's gate at {place}",
             (choice("stay", "Stay a day with them",
                     "Thank you. I heard something. I think.", loyalty=6),
              choice("go", "Move on", "Aye. Another time.", loyalty=-3))),
        Beat("place", "region:cradle", "The song",
             "{place}. {song} Let me learn it.",
             "wants to go into the Cradle",
             (choice("listen", "Let them learn it",
                     "I think it's a greeting. I'll learn to answer.",
                     loyalty=8, signature=True),
              choice("record", "Record it for the Charter",
                     "They'll file it. It isn't a file.", credits=2000,
                     purse="charter", loyalty=-5))),
    ),
    "light_tongued")

WIDOW = Arc(
    "widow", "The widow",
    "Their partner died on a hull like this one.",
    (
        Beat("date", "", "A name on a hull",
             "My partner died on a {hull}. Same class as ours. I didn't sign "
             "on because of it, and I didn't sign on in spite of it. I know "
             "where the wreck is.",
             "lost a partner on a hull like this one",
             (choice("ask", "Ask where",
                     "I'll give the navigator the numbers.", loyalty=5),
              choice("past", "Say the past stays past",
                     "It doesn't. But all right.", loyalty=-5))),
        Beat("place", "wreck", "The wreck",
             "{place}. She's here. The hull's cold. I'd like to go across.",
             "wants to go to the wreck at {place}",
             (choice("across", "Take them across in a boat",
                     "Thank you. I'll be a while.",
                     cargo=(("volatiles", -5),), loyalty=6),
              choice("look", "Look from here",
                     "From here, then. It's enough.", loyalty=2))),
        Beat("loyalty", "", "Bury or salvage",
             "I've been thinking about the wreck. We can bury her properly — "
             "a slow burn into the star. Or we take what's good off her. "
             "She'd have said take it. I don't know what I say.",
             "will decide about the wreck once they trust you",
             (choice("bury", "Bury them properly",
                     "The bridge came. All of them. I'll remember that "
                     "when it's bad.", loyalty=8, bridge=2, signature=True),
              choice("salvage", "Salvage the wreck",
                     "She'd have said take it. She'd have been right. I "
                     "still mind.", cargo=(("alloy", 30),), loyalty=-6))),
    ),
    "remembered")

GAMBLER = Arc(
    "gambler", "The gambler",
    "A marker at a Freehold card room, and a race.",
    (
        Beat("date", "", "A marker at a card room",
             "I owe a Freehold card room. Not much. The house takes coin or a "
             "favour, and the favour's a race.",
             "owes a Freehold card room",
             (choice("pay", "Pay the marker",
                     "Clean slate. Almost disappointing.", credits=-1500,
                     loyalty=4),
              choice("race", "Hear about the race",
                     "Now you're talking.", loyalty=3))),
        Beat("place", "freehold_port", "The bet",
             "{place}. The house is backing a run: a timed jump, their pick "
             "of finish. Win it and the marker's torn up, and then some. I'd "
             "stake my share.",
             "wants to place a bet at {place}",
             (choice("back", "Back them with a stake",
                     "Now we're a syndicate.", credits=-1000, loyalty=6),
              choice("watch", "Let them bet their own share",
                     "Fair. My share, my risk.", loyalty=2),
              choice("refuse", "No racing", "Fine. Dull, but fine.",
                     loyalty=-4))),
        Beat("place", "race", "Across the line",
             "Across the line at {place} with days in hand. {rival}The house "
             "pays. And I've noticed something: I'm lucky when you fly.",
             "is racing to {place} — the house's finish",
             (choice("luck", "Tell them to keep their luck close",
                     "Oh, I will. On the ground especially.", loyalty=6,
                     signature=True),
              choice("winnings", "Take the house's winnings",
                     "Coin, then. Coin's lucky too.", credits=3000,
                     purse="freeholds", loyalty=-2))),
    ),
    "lucky")

HERETIC = Arc(
    "heretic", "The heretic",
    "They think the Bloom is new life.",
    (
        Beat("date", "", "What the Bloom is",
             "I don't think the Bloom is a disease. I think it's the first "
             "new life anybody has seen, and we burn it because we're "
             "frightened. I'm not asking you to agree. I'm asking to look.",
             "thinks the Bloom should be understood",
             (choice("look", "Let them look",
                     "Thank you. Somebody has to.", loyalty=5,
                     rep=(("charter", -1),)),
              choice("fire", "Say it is a fire",
                     "Fires don't answer back.", loyalty=-6))),
        Beat("place", "bloom", "Alongside the mass",
             "{place}. It's right there. I need a week alongside and a "
             "sample hold. If it grows while we watch, it grows.",
             "wants to go to {place}, to study the mass",
             (choice("study", "Take readings with them",
                     "It's beautiful. Don't tell the Charter I said so.",
                     cargo=(("volatiles", -10),), loyalty=7,
                     rep=(("charter", -2),)),
              choice("burn", "Burn it instead",
                     "Then you didn't need me.", loyalty=-8,
                     rep=(("charter", 3),)))),
        Beat("place", "charter_capital", "The Charter notices",
             "The Charter has noticed. {seat}They'd like me to recant, here "
             "at {place}. Or you can speak for the work.",
             "has been summoned to {place}",
             (choice("speak", "Speak for the work",
                     "You said it out loud. I'll never be afraid of it "
                     "again.", loyalty=8, rep=(("charter", -6),),
                     signature=True),
              choice("recant", "Let them recant",
                     "I said the words. I didn't mean them.", loyalty=-8,
                     rep=(("charter", 4),)))),
    ),
    "unafraid")

HEIR = Arc(
    "heir", "The heir",
    "A share in a Freehold station, to be claimed.",
    (
        Beat("date", "", "A will to be read",
             "An aunt of mine held a share in a Freehold station. She's died. "
             "The will's to be read and I'm named in it. I'd have to be there.",
             "is named in a will",
             (choice("go", "Say we will get them there",
                     "She'd have liked you.", loyalty=5),
              choice("no", "Say the ship cannot detour",
                     "It's only money. And family.", loyalty=-4))),
        Beat("place", "freehold_port", "The reading",
             "{place}. The reading's today. The share is mine if I claim it. "
             "{seat}",
             "has a will read at {place}",
             (choice("attend", "Go in with them",
                     "You sat at the back. I saw.", loyalty=5,
                     rep=(("freeholds", 2),)),
              choice("wait", "Wait on the ship",
                     "It went fine. I'll tell you about it.", loyalty=1))),
        Beat("date", "", "Claim it, or give it away",
             "It's mine to keep or to give. Keep it, and the station pays a "
             "share every month for as long as I'm aboard. Give it to the "
             "station's crew, and every Freehold quay hears what this ship "
             "did.",
             "has a share to claim or give away",
             (choice("claim", "Claim the share",
                     "A landed officer. Don't tell my mother.", loyalty=6,
                     signature=True),
              choice("give", "Give it to the station's crew",
                     "They cried. So did I, a bit.", loyalty=4,
                     rep=(("freeholds", 20),), signature=True),
              choice("sell", "Sell it now",
                     "Quick money. Quick is a kind of money.", credits=3500,
                     purse="freeholds", loyalty=-3))),
    ),
    "landed")

LATE = [CARTOGRAPHER, PILGRIM, WIDOW, GAMBLER, HERETIC, HEIR]
