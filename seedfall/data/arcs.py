"""Officer arcs: twelve stories, three beats each, and what finishing one buys.

Officers had convictions, loyalty, lineages and minds, and nothing they
wanted was ever *about them* — a veteran of ten years read like a new hire
with the same numbers. An arc is one thing an officer wants, told in three
beats that arrive as despatches (`sim/comms`) in their own voice. Each beat
is set off by a place, a date, their loyalty or something the ship does,
offers two or three costed answers, and lapses if nobody answers. The last
beat, well resolved, leaves a **signature**: a named ability stronger than a
trait and bound to the story.

The first six stories are here; the other six are in `data/arcs_late.py`
(split at the length rule). The rules are `sim/arcs.py`. To add a story:
write an `Arc` with three `Beat`s, give its `Signature` an effect key, and
read that key at one point in the game — `tests/test_arcs` fails a signature
that moves nothing.
"""

from __future__ import annotations

from .arc_types import Arc, Beat, Signature, choice

# ── the calendar ───────────────────────────────────────────────────────────

#: No story starts before this day: a new captain has a ship to learn, and an
#: officer who opens with their dead brother on day three is noise.
QUIET_DAYS = 45

#: Days between one beat and the next arming, drawn per officer and beat from
#: their own key. Fifty to a hundred and twenty: with a place to fly to in
#: between, an engaged captain finishes a story in roughly a year and a half,
#: which is what "an officer who stays three years usually sees theirs out"
#: needs with room for a detour.
GAP_MIN = 50
GAP_MAX = 120

#: How long a despatch waits for an answer before the beat lapses.
ANSWER_DAYS = 60

#: How long a beat waits for its trigger once it is armed, by kind. A date
#: beat needs none: it arrives when it arms.
PLACE_DAYS = 300
EVENT_DAYS = 365
LOYALTY_DAYS = 240

#: The loyalty a *loyalty* beat waits for. A bridge paid on time settles in
#: the eighties — 1.5 a payday against the drift's pull toward 63
#: (`loyalty.drift`); measured on three idle seeds, 88-89 over three years —
#: and signs on at 62 ± 8. So 75 comes to an officer who has been treated
#: decently for most of a year, and not to one whose earlier beats lapsed.
LOYAL_AT = 75.0

#: What a lapsed beat costs the officer, first, second and last. The last is
#: the one that can end a career: from "Restless" it goes below the walkout
#: line (`convictions.WALKOUT`, 12), and `loyalty.tick` — the one path by
#: which anybody leaves the ship — does the rest.
LAPSE_FIRST = 4.0
LAPSE_SECOND = 6.0
LAPSE_LAST = 14.0

#: The timed race's clock: from the day it arms to crossing the line. Two or
#: three jumps at a standard drive is 20-40 days (`galaxy.transit_days`), so
#: forty-five is a race, not a formality.
RACE_DAYS = 45

#: The tutorial's chapters before this one are quiet: the curriculum is
#: teaching a captain to fly, and a story would interrupt the lesson.
QUIET_CHAPTER = "rock-and-ice"

# ── the signatures' numbers ────────────────────────────────────────────────
# Each is worth about a tier-2 fitting in its niche (those run ₡4,600-28,000,
# median ₡10,000) and nothing outside it, which the numbers below were sized
# against in the notes beside each.

#: Kessel-steady: a burn cuts 20% more mass.
BURN_LIFT = 0.20
#: Paid in full: Freeholds standing held at "Tolerated" (`factions.STANDINGS`).
FREEHOLD_FLOOR = 15.0
#: Second mind: one more try at the decoding bench, and survey quality.
DECODE_TRIES = 1
SCAN_LIFT = 0.08
#: Peer reviewed: a provisional result is confirmed this much faster.
CONFIRM_LIFT = 0.30
#: Drill: an unattended helm turns this much better.
DRILL_LIFT = 0.10
#: Green thumb: every holding's yield.
YIELD_LIFT = 0.08
#: Dead reckoning: light years on every jump.
JUMP_LIFT = 0.5
#: Light-tongued: comprehension of the Kith where they exist
#: (`arcs.comprehension`), and — the Kith or not — the comms bonus
#: `ship.stats` carries (a trait gives 0.04 diplomacy). `stats` has no game
#: to ask whether the Kith exist, so the comms half is always on.
TONGUE_LIFT = 0.25
DIPLOMACY_LIFT = 0.08
#: Remembered: the crew's morale never sinks below this. An unpaid crew
#: settles at 0.37 (`crew.morale_tick`), a breached one at 0.42.
MORALE_FLOOR = 0.45
#: Lucky: a failed ground attempt is rolled again this often.
REROLL = 0.25
#: Unafraid: xenolith and readings from studying a mass.
STUDY_LIFT = 0.30
#: Landed: a Station share, paid monthly out of the Freeholds' purse —
#: ₡9,000 over three years, a tier-2 fitting's worth. Given away instead, it
#: is the standing the heir's "give" answer states, once.
LANDED_MONTHLY = 250

#: Each effect key is read at one point in the game: burn `threat.cleanse`;
#: freehold_floor, morale_floor and landed `arcs.tick`; decode
#: `minigames.begin_decoding`; scan, jump and diplomacy `ship.stats`; confirm
#: `inquiry.confirm_cost`; drill `stations.helm_share`; yield
#: `works.crewed_yields`; tongue `arcs.comprehension`; reroll
#: `expedition.attempt` (quoted by `odds_for`); study `responses.study_value`.
SIGNATURES = {
    "kessel_steady": Signature(
        "kessel_steady", "Kessel-steady",
        f"Every Bloom burn cuts {BURN_LIFT:.0%} more while they hold a seat.",
        (("burn", BURN_LIFT),)),
    "paid_in_full": Signature(
        "paid_in_full", "Paid in full",
        "Freeholds standing never falls below Tolerated.",
        (("freehold_floor", FREEHOLD_FLOOR),)),
    "second_mind": Signature(
        "second_mind", "Second mind",
        f"One more try at every decoding, and survey quality "
        f"+{SCAN_LIFT:.2f}.",
        (("decode", DECODE_TRIES), ("scan", SCAN_LIFT))),
    "peer_reviewed": Signature(
        "peer_reviewed", "Peer reviewed",
        f"Provisional results confirm {CONFIRM_LIFT:.0%} faster.",
        (("confirm", CONFIRM_LIFT),)),
    "drill": Signature(
        "drill", "Drill",
        f"An unattended helm turns {DRILL_LIFT:.0%} better.",
        (("drill", DRILL_LIFT),)),
    "green_thumb": Signature(
        "green_thumb", "Green thumb",
        f"Every holding yields {YIELD_LIFT:.0%} more.",
        (("yield", YIELD_LIFT),)),
    "dead_reckoning": Signature(
        "dead_reckoning", "Dead reckoning",
        f"+{JUMP_LIFT:g} ly on every jump, and the Hollow charted free.",
        (("jump", JUMP_LIFT),)),
    "light_tongued": Signature(
        "light_tongued", "Light-tongued",
        f"Diplomacy +{DIPLOMACY_LIFT:.2f}, and Kith comprehension "
        f"+{TONGUE_LIFT:.0%} wherever there are Kith to understand.",
        (("tongue", TONGUE_LIFT), ("diplomacy", DIPLOMACY_LIFT))),
    "remembered": Signature(
        "remembered", "Remembered",
        f"The crew's morale never falls below {MORALE_FLOOR:.0%}.",
        (("morale_floor", MORALE_FLOOR),)),
    "lucky": Signature(
        "lucky", "Lucky",
        f"A failed ground attempt is rolled again {REROLL:.0%} of the time.",
        (("reroll", REROLL),)),
    "unafraid": Signature(
        "unafraid", "Unafraid",
        f"Studying a Bloom mass yields {STUDY_LIFT:.0%} more.",
        (("study", STUDY_LIFT),)),
    "landed": Signature(
        "landed", "Landed",
        f"A Station share: ₡{LANDED_MONTHLY} a month from the Freeholds' "
        "purse — or, given away, the Freeholds' regard, once.",
        (("landed", LANDED_MONTHLY),)),
}


# ── the stories, first six ─────────────────────────────────────────────────

LAST_SIGNAL = Arc(
    "last_signal", "The last signal",
    "A sibling's beacon, out of Bloom country.",
    (
        Beat("date", "", "A beacon on an old band",
             "There's a beacon on the band my family used. My brother's hull. "
             "It's coming out of Bloom country, and it's been coming a long "
             "time. I'm not asking for anything yet. I'm telling you I heard "
             "it.",
             "has heard a brother's beacon",
             (choice("log", "Log it, and plot it",
                     "You wrote it down. That counts.", loyalty=4),
              choice("ghost", "Tell them it is a ghost",
                     "Maybe. I'll keep listening anyway.", loyalty=-5))),
        Beat("place", "bloom", "Where the beacon is",
             "We're here. {place}. The beacon's under the growth, a day in. I "
             "can take a boat and search, or we burn a way in and be sure.",
             "wants to go to {place}, where the beacon is",
             (choice("search", "Send a boat to search",
                     "Quietly. Good. He'd hate a fuss.",
                     cargo=(("volatiles", -15),), loyalty=6),
              choice("burn", "Burn a way in",
                     "Loud. But we'll know.", rep=(("charter", 3),),
                     loyalty=4),
              choice("leave", "Mark it and go",
                     "He's waited this long.", loyalty=-4))),
        Beat("event", "burn", "What the beacon was",
             "The last burn opened it. It's his log, Captain. Not him. Two "
             "years of him, talking to nobody. I'd like to read it with "
             "someone. Or I can do it alone.",
             "is waiting on the next Bloom burn to finish the search",
             (choice("together", "Read it with them",
                     "He was steady. I can be. Put me on the guns when we "
                     "burn.", loyalty=8, signature=True),
              choice("alone", "Give them the night alone",
                     "Thank you. I'll be on watch in the morning.",
                     loyalty=5),
              choice("archive", "Sell the log to the Charter",
                     "You sold my brother.", credits=1200, purse="charter",
                     rep=(("charter", 2),), loyalty=-10))),
    ),
    "kessel_steady")

OLD_DEBTS = Arc(
    "old_debts", "Old debts",
    "A Freehold cartel calls in a debt.",
    (
        Beat("date", "", "A letter from a card room",
             "A Freehold cartel has my name on a slate from before I signed "
             "with you. They've called it in. They want it settled in "
             "person, at their house.",
             "owes a Freehold cartel",
             (choice("go", "Say we will see them",
                     "Good. I'd rather face it than run.", loyalty=3),
              choice("refuse", "Say it is not the ship's debt",
                     "It isn't. It's mine. Right.", loyalty=-3,
                     rep=(("freeholds", -2),)))),
        Beat("place", "freehold_capital", "The cartel's house",
             "{place}. They're on the quay. I can pay, you can hide me in the "
             "hold, or we tell them where they stand.",
             "has to settle a slate at {place}",
             (choice("pay", "Pay the slate", "Clean. I owe you, not them.",
                     credits=-3000, rep=(("freeholds", 3),), loyalty=8),
              choice("hide", "Hide them in the hold", "Close. Thanks.",
                     rep=(("freeholds", -5),), loyalty=4),
              choice("confront", "Face the cartel down",
                     "They'll remember that. So will I.",
                     rep=(("freeholds", -8),), loyalty=6, bridge=1))),
        Beat("date", "", "The cartel's answer",
             "The cartel's written back. They'll call it square, and they "
             "want a name on it — the ship's, or mine. If it's the ship's, "
             "every Freehold quay treats us as family. {after}",
             "is waiting on the cartel's answer",
             (choice("ship", "Put the ship's name to it",
                     "Paid in full. Nobody at a Freehold quay looks at us "
                     "sideways again.", rep=(("freeholds", 4),), loyalty=6,
                     signature=True),
              choice("theirs", "Let it be their own name",
                     "Just me, then. Fair.", loyalty=3),
              choice("cash", "Take the cartel's quiet money",
                     "So that's what I'm worth to you.", credits=1500,
                     purse="freeholds", loyalty=-6)),
             after=(("pay", "You paid, so they're polite about it."),
                    ("hide", "They know you hid me. They're amused."),
                    ("confront", "They respect a captain who stood there."),
                    ("", "Nobody went. They noticed.")))),
    "paid_in_full")

DEFECTOR = Arc(
    "defector", "The defector",
    "A Dry Choir recording wants asylum aboard.",
    (
        Beat("date", "", "A recording asks for asylum",
             "There's a Dry Choir recording on a drive in my locker. It "
             "walked out of the canon, and it wants asylum. I said I'd ask. "
             "It takes up less room than a sandwich.",
             "is keeping a runaway recording",
             (choice("aboard", "Take it aboard",
                     "It said thank you. Twice. In different voices.",
                     loyalty=5, rep=(("sanhedrin", -3),)),
              choice("return", "Give it back to the Choir",
                     "I'll carry it to them myself. Don't ask me to like it.",
                     loyalty=-6, rep=(("sanhedrin", 3),)))),
        Beat("place", "choir_port", "The Choir is looking",
             "The Choir is at {place}, and they're looking for it. Customs "
             "will ask. I can scrub the drive's header, or we pay the "
             "inspector, or we hand it over.",
             "has to get a recording past the Choir at {place}",
             (choice("scrub", "Scrub the drive's header",
                     "Done. The bridge is uneasy. So am I.", loyalty=4,
                     bridge=-1, rep=(("sanhedrin", -3),)),
              choice("bribe", "Pay the inspector",
                     "Money well spent. It thinks so too.", credits=-2000,
                     loyalty=6),
              choice("hand", "Hand it over",
                     "It didn't argue. That was the worst part.", loyalty=-8,
                     rep=(("sanhedrin", 5),)))),
        Beat("loyalty", "", "It offers what it knows",
             "It trusts you now, because I do. It's offering to sit at the "
             "bench with me — it knows how the Choir reads a signal. Or it'll "
             "sell what it knows to the Yards and go.",
             "will say more once they trust you",
             (choice("bench", "Give it a seat at the bench",
                     "Two of us reading now. You'll see the difference.",
                     loyalty=6, signature=True),
              choice("sell", "Let the Yards buy it",
                     "It's gone, then. It left a note.", credits=4000,
                     purse="concordat", rep=(("concordat", 3),
                                             ("sanhedrin", -5)),
                     loyalty=-4))),
    ),
    "second_mind")

SCIENTIST = Arc(
    "scientist", "The disgraced scientist",
    "A Charter inquiry into their old work.",
    (
        Beat("date", "", "A Charter summons",
             "The Charter's opened an inquiry into my old work — the assays "
             "from before I came aboard. They say I faked the controls. I "
             "didn't. They want me in front of a board.",
             "is under a Charter inquiry",
             (choice("back", "Say the ship stands behind them",
                     "I didn't expect that. Thank you.", loyalty=5),
              choice("distance", "Keep the ship out of it",
                     "Understood. I'll go alone.", loyalty=-4,
                     rep=(("charter", 1),)))),
        Beat("place", "charter_capital", "The board sits",
             "{place}. The board sits tomorrow. I can defend it, recant and "
             "keep my name off the registry, or publish everything and let "
             "them try to stop it.",
             "has to answer the board at {place}",
             (choice("defend", "Pay counsel and defend it",
                     "We'll make them read it properly.", credits=-1500,
                     loyalty=6),
              choice("recant", "Let them recant",
                     "Fine. It's only the truth.", loyalty=-8,
                     rep=(("charter", 4),)),
              choice("publish", "Publish everything",
                     "Now they'll have to read it.", loyalty=8,
                     rep=(("charter", -6),)))),
        Beat("date", "", "The finding",
             "The finding's in. {after} Either way I'd like to keep working, "
             "and I'd like my name on it.",
             "is waiting on the board's finding",
             (choice("sign", "Put their name on the bench's work",
                     "Then let's check everything twice, and fast.",
                     loyalty=6, rep=(("charter", -2),), signature=True),
              choice("quiet", "Keep their name quiet",
                     "Safer. I know.", loyalty=-3, rep=(("charter", 2),))),
             after=(("defend", "Somebody replicated the assays. Vindicated."),
                    ("publish", "Vindicated, loudly. They hate it."),
                    ("recant", "They replicated it after I'd recanted. "
                               "Ruined for nothing."),
                    ("", "Nobody spoke for me, so it didn't matter.")))),
    "peer_reviewed")

DESERTER = Arc(
    "deserter", "The deserter",
    "A Yards warrant, and an old unit.",
    (
        Beat("date", "", "A Yards warrant",
             "There's a Yards warrant with my name on it. I walked off a "
             "picket when they told me to fire on a Freehold hauler. I'd do "
             "it again. They'll come asking.",
             "is wanted by the Yards",
             (choice("shield", "Say they serve on this ship now",
                     "Then I'll serve it properly.", loyalty=5,
                     rep=(("concordat", -2),)),
              choice("doubt", "Ask for the whole story first",
                     "Fair. It's a long one.", loyalty=-1))),
        Beat("place", "yards_port", "The provost's quay",
             "{place}. Their provost is on the quay. I can surrender and take "
             "the hearing, you can say I'm yours and let them try, or we pay "
             "the fine and walk.",
             "has a Yards provost to face at {place}",
             (choice("fine", "Pay the fine", "Bought and done. Thank you.",
                     credits=-2500, loyalty=5, rep=(("concordat", 1),)),
              choice("yours", "Say they are yours",
                     "They heard you. Everyone did.", loyalty=9,
                     rep=(("concordat", -8),)),
              choice("surrender", "Let them take the hearing",
                     "I'll be back. Probably.", loyalty=-10,
                     rep=(("concordat", 4),)))),
        Beat("event", "fight", "The old unit",
             "That fight — somebody flying like my old unit. {rival}They "
             "taught me to hold a helm with nobody in the chair. Let me teach "
             "the ship.",
             "is waiting for the next fight to show you something",
             (choice("teach", "Let them drill the helm",
                     "Watch the helm next time you're on the guns.",
                     loyalty=6, signature=True),
              choice("rest", "Tell them to stand down",
                     "Aye. Standing down.", loyalty=-3))),
    ),
    "drill")

GROWER = Arc(
    "grower", "The grower",
    "Seed for a garden, carried a long way.",
    (
        Beat("date", "", "Seed in a pocket",
             "I've carried seed since the yards at home. A garden — not a "
             "colony, a garden. I'd like to put it on a moon somewhere it can "
             "watch a star come up.",
             "wants to plant a garden on a moon",
             (choice("yes", "Promise them a moon",
                     "I'll hold you to it.", loyalty=4),
              choice("cargo", "Say seed is cargo",
                     "Then I'll keep it in my pocket.", loyalty=-5))),
        Beat("place", "moon", "The moon",
             "{place} has a moon that'll take it. Forty tonnes of biomass for "
             "a bed, or I plant it thin and hope.",
             "wants to go to {place}, to plant on its moon",
             (choice("bed", "Give them a bed of biomass",
                     "It'll take. You'll see it green from orbit.",
                     cargo=(("biomass", -40),), loyalty=7),
              choice("thin", "Let them plant it thin",
                     "Thin is still planted.", loyalty=3),
              choice("later", "Not here",
                     "Somewhere else, then. Somewhere.", loyalty=-4))),
        Beat("event", "colony", "It blooms",
             "Word came with the new holding. {after} I know how to make "
             "ground give, Captain. Let me walk the holdings.",
             "is waiting for the ship to found a holding",
             (choice("walk", "Put them to walk the holdings",
                     "Every one of them, twice a year.", loyalty=5,
                     signature=True),
              choice("keep", "Keep them aboard",
                     "Aye. I'll keep the seed.", loyalty=-2)),
             after=(("bed", "The garden took. It's green from orbit."),
                    ("thin", "Half of it took. Half is enough."),
                    ("later", "I never planted it. The seed kept."),
                    ("", "The seed kept, in my pocket.")))),
    "green_thumb")


# The other six, and the registry. `arcs_late` needs only the shapes, and a
# story names its signature by id, so neither module imports the other's
# tables.
from .arcs_late import LATE  # noqa: E402

ARCS = [LAST_SIGNAL, OLD_DEBTS, DEFECTOR, SCIENTIST, DESERTER, GROWER, *LATE]
ARCS_BY_ID = {a.id: a for a in ARCS}
