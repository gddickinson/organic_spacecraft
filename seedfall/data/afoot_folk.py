"""The people on a deck who are not yours: who they are, what they carry, how they act.

A concourse was a board of doors, and nobody stood behind any of them. These
are the somebodies: the keeper behind the chandler's counter, the clerk at
the bank, the constable the law level puts on the promenade, the fence the
law level *lets* be there, the dockhands, the drunks, the struck crew of a
hull that has just surrendered to you, and the things in the dark of a
derelict that are no longer anybody.

Every archetype is a small Traveller character: six scores (STR DEX END INT
EDU SOC, in that order), a handful of skills, what they carry, how they feel
about a stranger (`mood`), and how they behave (`ways`):

- `keep` — stand at their post and serve;
- `wander` — drift about the room they were put in;
- `patrol` — walk the corridors and look at people;
- `guard` — hold a place, and answer anybody who comes at it;
- `hunt` — come looking;
- `still` — does not move at all (a node, a sentry).

`topics` is what a person can be talked to about (`sim/afoot_talk.py`).
`lines` is what they say, by mood, in the game's own voice. A named person —
a harbourmaster, one of your officers, the master of a struck hull — speaks
through `sim/voice.py` instead, and remembers you.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Folk:
    """One sort of person, or thing, on a deck."""

    id: str
    name: str
    #: STR DEX END INT EDU SOC, before the dice move them a point or two.
    stats: tuple
    skills: dict = field(default_factory=dict)
    weapon: str = ""
    armour: str = ""
    mood: str = "neutral"
    ways: str = "wander"
    #: How far they can see, in squares.
    sight: int = 10
    #: Added to a nerve throw. A constable stands; a patron does not.
    brave: int = 0
    #: person | machine | bloom | kith — what can be said to it, and what
    #: it does when it goes down.
    kind: str = "person"
    topics: tuple = ()
    lines: dict = field(default_factory=dict)
    #: The persona a named one speaks with (`data/personas.py`).
    persona: str = "plain"


#: The ladder a disposition moves on, worst first. Talking moves somebody
#: along it one rung at a time; a crime moves the watch to the bottom.
MOODS = ("hostile", "wary", "neutral", "friendly")

#: The two states off the ladder: they have given up, or they have gone.
BROKEN = ("surrendered", "fled")

_CIVIL = ("greet", "place", "word", "persuade", "bribe")
_STAFF = ("greet", "business", "place", "word")

FOLK: tuple = (
    # ── a concourse ───────────────────────────────────────────────────────
    Folk("patron", "Patron", (7, 7, 7, 7, 7, 7),
         {"carouse": 1, "streetwise": 0}, ways="wander", topics=_CIVIL,
         lines={"greet": ("Busy tonight.", "You off the hull at the end?",
                          "Mind the step, it catches everybody."),
                "cold": ("Find your own table.", "Not interested."),
                "warm": ("Sit down, sit down.", "Buy you one?")}),
    Folk("resident", "Resident", (7, 7, 7, 7, 7, 6),
         {"streetwise": 1}, ways="wander", topics=_CIVIL,
         lines={"greet": ("You are not from this ring.",
                          "Visitors are down at the hub, mostly."),
                "cold": ("We do not get many of you here, and that is fine.",),
                "warm": ("Welcome, then. Watch the lifts; they stick.",)}),
    Folk("dockhand", "Dockhand", (9, 7, 9, 6, 5, 5),
         {"athletics": 1, "vacc_suit": 1, "streetwise": 1}, ways="wander",
         topics=_CIVIL, lines={
             "greet": ("Clear the lane, the loader's coming through.",
                       "Yours, the one at twelve? Pretty thing."),
             "cold": ("Crews. Always in the way.",),
             "warm": ("If you want it moved quiet, ask for Sal.",)}),
    Folk("worker", "Worker", (8, 7, 8, 6, 6, 5),
         {"mechanic": 1, "trade": 1}, ways="wander", topics=_CIVIL,
         lines={"greet": ("Shift change in an hour.", "Mind the line."),
                "cold": ("Management's upstairs.",),
                "warm": ("Good to see somebody from outside.",)}),
    Folk("keeper", "Keeper", (7, 7, 7, 8, 7, 7),
         {"broker": 1, "steward": 1, "persuade": 1}, ways="keep",
         topics=_STAFF, lines={
             "greet": ("What can I do for you?", "Help you?",
                       "Everything's priced. Nothing's a bargain."),
             "cold": ("Cash first.", "I know your sort."),
             "warm": ("For you, I'll see what's out the back.",)}),
    Folk("clinician", "Clinician", (6, 8, 7, 9, 10, 7),
         {"medic": 2, "sciences": 1, "cybernetics": 1}, ways="keep",
         topics=_STAFF + ("patch",), lines={
             "greet": ("Who is hurt?", "Take a seat. What is it?"),
             "cold": ("We treat anybody who pays.",),
             "warm": ("Sit. Let me look at that properly.",)}),
    Folk("clerk", "Clerk", (6, 7, 6, 8, 9, 7),
         {"admin": 2, "law": 1}, ways="keep", topics=_STAFF, lines={
             "greet": ("Next.", "Forms are on the left.",
                       "Name, hull, business."),
             "cold": ("The office is closing.",),
             "warm": ("I can move you up the list.",)}),
    Folk("agent", "Hiring agent", (7, 7, 7, 8, 8, 7),
         {"admin": 1, "persuade": 2, "streetwise": 1}, ways="keep",
         topics=_STAFF + ("hire",), lines={
             "greet": ("Looking for hands, or looking for a berth?",
                       "I've got people on the board who'd walk "
                       "through a bulkhead for steady pay."),
             "cold": ("The good ones won't sign for you.",),
             "warm": ("I kept a name back for you.",)}),
    Folk("informant", "Informant", (6, 8, 6, 8, 7, 5),
         {"streetwise": 2, "deception": 1, "investigate": 1}, ways="keep",
         topics=("greet", "word", "place", "bribe", "business"), lines={
             "greet": ("You look like somebody who wants to know things.",),
             "cold": ("I don't know you.",),
             "warm": ("For you, a discount on the truth.",)}),
    Folk("fence", "Fence", (7, 8, 7, 8, 7, 5),
         {"streetwise": 2, "broker": 2, "deception": 1}, weapon="snub_pistol",
         ways="keep", brave=1,
         topics=("greet", "business", "word", "persuade", "bribe"), lines={
             "greet": ("Whatever it is, I've seen worse.",
                       "No names. What have you got?"),
             "cold": ("Not here. Not you.",),
             "warm": ("Friend. What do you need moved?",)}),
    Folk("pickpocket", "Loiterer", (6, 10, 7, 7, 5, 4),
         {"stealth": 2, "streetwise": 2, "deception": 1}, weapon="blade",
         ways="wander", topics=_CIVIL, lines={
             "greet": ("Sorry — didn't see you there.",),
             "cold": ("Hands off, I haven't done anything.",)}),
    Folk("thug", "Hard case", (9, 7, 9, 6, 5, 4),
         {"gun_combat": 1, "athletics": 1, "streetwise": 1},
         weapon="cutlass", armour="jack", mood="wary", ways="wander",
         brave=1, topics=("greet", "persuade", "bribe"), lines={
             "greet": ("You lost?", "This is a private room."),
             "cold": ("Walk away while you can.",),
             "hostile": ("Wrong door, spacer.",),
             "warm": ("No trouble from us.",)}),
    Folk("bravo", "Hunter", (9, 9, 9, 8, 7, 6),
         {"gun_combat": 2, "recon": 1, "stealth": 1, "tactics": 1},
         weapon="laser_pistol", armour="mesh", mood="hostile", ways="hunt",
         brave=2, topics=("greet", "persuade", "bribe"), lines={
             "greet": ("There's paper on you.",),
             "hostile": ("Nothing personal. The paper says alive, mostly.",)}),
    # ── the law and the quay ──────────────────────────────────────────────
    Folk("constable", "Constable", (8, 8, 8, 7, 7, 7),
         {"gun_combat": 1, "law": 1, "recon": 1, "persuade": 1},
         weapon="stunner", armour="flak", mood="neutral", ways="patrol",
         brave=2, topics=("greet", "place", "papers", "persuade"), lines={
             "greet": ("Move along.", "Keep it tidy, Captain.",
                       "Any trouble, you come to us."),
             "cold": ("I'm watching you.", "One step wrong."),
             "hostile": ("Down on the deck! Now!",),
             "warm": ("Good to see a crew that behaves.",)}),
    Folk("customs", "Customs officer", (7, 8, 7, 8, 8, 7),
         {"admin": 2, "investigate": 2, "law": 1}, weapon="stunner",
         armour="mesh", ways="keep", brave=1,
         topics=("greet", "papers", "persuade", "bribe", "place"), lines={
             "greet": ("Anything to declare?", "Manifest, please."),
             "cold": ("Open the cases.",),
             "warm": ("Go on through.",)}),
    Folk("overseer", "Overseer", (7, 7, 7, 8, 8, 7),
         {"admin": 2, "leadership": 1, "mechanic": 1}, ways="keep",
         brave=1, topics=_STAFF, lines={
             "greet": ("Numbers are on the board.", "Shift's running."),
             "cold": ("We're behind, and I know it.",),
             "warm": ("Good of you to come down yourself.",)}),
    # ── your own hull ─────────────────────────────────────────────────────
    Folk("officer", "Officer", (7, 7, 7, 7, 7, 7), ways="keep",
         mood="friendly", brave=2, persona="officer",
         topics=("greet", "word", "report", "story", "join"), lines={
             "greet": ("Captain.", "Captain — all quiet at my station.",
                       "Didn't hear you come in, Captain.",
                       "Captain. Something I can do?"),
             "warm": ("Good to see you down here, Captain.",
                      "Captain. I was hoping you'd come by.",
                      "It means something, you walking the decks."),
             "cold": ("Captain.", "If you've a minute, I've a complaint.",
                      "Sir.")}),
    Folk("hand", "Hand", (8, 7, 8, 6, 6, 5),
         {"mechanic": 1, "vacc_suit": 1, "steward": 0}, ways="wander",
         mood="friendly", brave=1, topics=("greet", "word"), lines={
             "greet": ("Captain.", "All quiet, Captain.",
                       "Mind the hatch, it sticks."),
             "warm": ("Good to see you down here, Captain.",)}),
    Folk("stowaway", "Stowaway", (6, 9, 7, 7, 6, 4),
         {"stealth": 2, "streetwise": 1, "athletics": 1}, mood="wary",
         ways="wander", topics=("greet", "persuade", "enlist"), lines={
             "greet": ("Please. I only needed off that rock.",),
             "cold": ("I'm not going back. I'm not.",),
             "warm": ("I can work. Anything. Ask anybody.",)}),
    Folk("harbourmaster", "Harbourmaster", (7, 7, 7, 9, 9, 9),
         {"admin": 3, "law": 2, "persuade": 1}, ways="keep", brave=2,
         persona="harbourmaster",
         topics=("greet", "favour", "place", "word"), lines={
             "greet": ("Captain.",)}),
    # ── a struck hull, a raider's deck, a derelict ────────────────────────
    Folk("holdout", "Holdout", (8, 8, 8, 7, 6, 5),
         {"gun_combat": 1, "vacc_suit": 1, "tactics": 0}, weapon="autopistol",
         armour="jack", mood="hostile", ways="guard", brave=0,
         topics=("greet", "persuade"), persona="raider", lines={
             "hostile": ("She's struck, not taken!",
                         "Come and get it, then."),
             "surrendered": ("All right! All right. Don't.",)}),
    Folk("prisoner", "Struck crew", (7, 7, 7, 7, 6, 5),
         {"vacc_suit": 1, "mechanic": 1}, mood="surrendered", ways="keep",
         topics=("greet", "question", "enlist", "persuade"),
         persona="captain", lines={
             "surrendered": ("We struck. We're done.",
                             "Tell me you're not the sort who spaces people.")}),
    Folk("raider", "Raider", (9, 8, 9, 7, 6, 5),
         {"gun_combat": 1, "vacc_suit": 1, "athletics": 1},
         weapon="shotgun", armour="mesh", mood="hostile", ways="guard",
         brave=1, topics=("greet", "persuade", "bribe"), persona="raider",
         lines={"hostile": ("Salvage rights, friend. Ours.",
                            "Wrong wreck."),
                "surrendered": ("Take it. Take all of it.",)}),
    Folk("scavenger", "Scavenger", (8, 8, 8, 7, 6, 5),
         {"mechanic": 1, "vacc_suit": 2, "gun_combat": 0},
         weapon="cutting_torch", armour="vacc_suit", mood="wary",
         ways="wander", topics=("greet", "persuade", "bribe", "word"),
         lines={"greet": ("We were here first.",),
                "cold": ("Find your own wreck.",),
                "warm": ("Split it, then. There's plenty.",)}),
    # ── machines ──────────────────────────────────────────────────────────
    Folk("frame", "Work frame", (12, 6, 12, 4, 4, 0),
         {"mechanic": 1}, weapon="npc_manipulator", ways="wander",
         sight=8, brave=4, kind="machine", topics=("greet",),
         lines={"greet": ("Work order acknowledged.",)}),
    Folk("sentry", "Sentry", (8, 7, 8, 4, 0, 0),
         {"gun_combat": 1, "recon": 2}, weapon="npc_sentry",
         mood="hostile", ways="still", sight=12, brave=6, kind="machine"),
    # ── the Bloom ─────────────────────────────────────────────────────────
    Folk("thrall", "Thrall", (9, 6, 11, 2, 0, 0),
         {"athletics": 1}, weapon="npc_claws", mood="hostile", ways="hunt",
         sight=8, brave=6, kind="bloom",
         lines={"hostile": ("It turns towards the light you are carrying.",)}),
    Folk("creeper", "Creeper", (6, 5, 8, 1, 0, 0),
         {"athletics": 0}, weapon="npc_lash", mood="hostile", ways="guard",
         sight=5, brave=6, kind="bloom"),
    # ── the Kith ──────────────────────────────────────────────────────────
    Folk("kith", "Kith", (6, 9, 8, 9, 6, 8),
         {"athletics": 1, "art": 2}, weapon="npc_singer", mood="neutral",
         ways="wander", kind="kith", topics=("greet", "sing"),
         lines={"greet": ("A chord, rising, and a colour you have no "
                          "word for.",)}),
    Folk("kith_elder", "Kith elder", (6, 7, 9, 11, 8, 11),
         {"art": 3, "diplomat": 2}, weapon="npc_singer", mood="neutral",
         ways="keep", kind="kith", topics=("greet", "sing", "gift"),
         lines={"greet": ("A long, falling phrase. It is waiting for you.",)}),
)
FOLK_BY_ID = {f.id: f for f in FOLK}

#: Every topic a person can be asked about. `sim/afoot_talk` has one door
#: per id and `tests/test_afoot` holds the two lists together.
TOPICS = {
    "greet": "Pass the time of day",
    "place": "Ask about this place",
    "word": "Ask what the word is",
    "persuade": "Talk them round",
    "bribe": "Make it worth their while",
    "business": "Do business",
    "hire": "Look at the board",
    "patch": "Have somebody seen to",
    "papers": "Show your papers",
    "favour": "Ask a favour",
    "question": "Ask about the hull",
    "enlist": "Offer a berth",
    "sing": "Answer in the lexicon",
    "gift": "Offer a gift",
    "report": "Ask how the ship is",
    "story": "Ask what is on their mind",
    "join": "Take them along",
    "tie": "Settle it with them",
}
