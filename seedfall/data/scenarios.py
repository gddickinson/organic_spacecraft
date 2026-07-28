"""The situations an epoch puts in front of you, and what answering costs.

Forty of them, four per epoch. Each is a choice between two or three answers,
and — the rule this project keeps — **each answer states what it does before
you take it.** The `effect` dict is read by `sim/legacy.py` and by nothing else,
so what the card promises and what the game does are the same dict.

Effect keys, all optional::

    pressure  change to the epoch gauge (negative buys time)
    credits   ledger
    rep       {faction: delta}
    hull      fraction of maximum, negative damages
    stores    {commodity: tonnes}
    research  points onto the bench
    flag      set a flag on the game
    close     end the epoch now: "triumph" or "failure"

Pressure is the currency. Most answers buy time; a few spend it for something
else; a couple gamble it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Answer:
    label: str
    says: str                # what it will do, in words, before you take it
    effect: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Scenario:
    id: str
    epoch: str
    title: str
    text: str
    answers: tuple


def _s(sid, epoch, title, text, *answers) -> Scenario:
    return Scenario(sid, epoch, title, text, tuple(answers))


def _a(label, says, **effect) -> Answer:
    return Answer(label, says, effect)


SCENARIOS = [
    # ── The Division ───────────────────────────────────────────────────────
    _s("claim-jump", "containment", "A claim filed over your burn",
       "The Concordat has filed on Tessel's Rest — a system you personally "
       "cleared, at some cost — on the grounds that a cleared world is an "
       "empty one. The Charter is watching to see whether you let it stand.",
       _a("Contest it", "Buys time on the partition; the Concordat takes it "
          "badly.", pressure=-0.09, rep={"concordat": -14, "charter": 8}),
       _a("Let it stand", "Costs time; the Concordat remembers that you did "
          "not make a scene.", pressure=0.07, rep={"concordat": 12}),
       _a("Sell them the survey", "Thirty thousand credits and no position "
          "taken at all.", credits=30000, pressure=0.04)),

    _s("cleared-world", "containment", "Somewhere to put people",
       "Ostrel came out of it better than anyone expected: intact biosphere, "
       "no residue, and four thousand people on Charter lighters with nowhere "
       "to be. Somebody has to say who lands.",
       _a("Open it to all four", "Slows the partition badly. Nobody is "
          "pleased and nobody is excluded.", pressure=-0.14,
          rep={"charter": -5, "concordat": -5, "freeholds": 6, "sanhedrin": 4}),
       _a("Hold it yourself", "You gain a world and the partition accelerates.",
          pressure=0.10, flag="held_ostrel"),
       _a("Give it to the Freeholds", "They will not forget it.",
          pressure=-0.04, rep={"freeholds": 22, "charter": -10})),

    _s("old-serial", "containment", "A serial number",
       "The husk at Kessel's Reach had a Charter serial on it. You have the "
       "plate. The Charter would like it back and has not said why in writing.",
       _a("Hand it over", "The Charter is grateful in a way that is worth "
          "something later.", rep={"charter": 25}, pressure=-0.05),
       _a("Publish it", "Everyone learns where the Bloom came from. The "
          "partition stalls while they argue about it.", pressure=-0.16,
          rep={"charter": -30, "freeholds": 14, "sanhedrin": 10}),
       _a("Keep it", "Say nothing. It is worth more unspent.",
          flag="holds_serial")),

    _s("the-vote", "containment", "A settlement, or four",
       "The four powers will meet at Mereth's Mouth. You are invited as a "
       "party, which is new, and the invitation says 'signatory'.",
       _a("Go, and argue for one charter",
          "If the standing is there it settles the epoch outright. If it is "
          "not, it costs you badly.", flag="attend_settlement", pressure=-0.2),
       _a("Go, and take what you can get",
          "A safe share. The partition proceeds without a settlement.",
          credits=120000, pressure=0.05),
       _a("Stay away", "Let them carve it. Costs nothing but the say.",
          pressure=0.12)),

    # ── The Rearguard ──────────────────────────────────────────────────────
    _s("last-lighter", "exodus", "The last lighter",
       "Vex Hollow has six hundred people and eleven days of margin. Your hold "
       "takes two hundred at a time and the run is four days each way.",
       _a("Three runs, no margin", "Everyone off. It will cost the hull.",
          pressure=-0.15, hull=-0.22),
       _a("Two runs and go", "Four hundred. You will know the number.",
          pressure=-0.07, rep={"charter": -8}),
       _a("Send the coordinates to the Freeholds",
          "They have hulls closer. They will also want paying.",
          credits=-45000, pressure=-0.11, rep={"freeholds": 10})),

    _s("the-holdouts", "exodus", "The ones who will not go",
       "Ninety-odd at Tarn Span have dug in and will not be moved. They have a "
       "reactor, a seed vault and a fixed opinion.",
       _a("Fortify them", "Spend the stores. They might hold.",
          stores={"alloy": -40, "silicon": -20}, pressure=-0.12,
          flag="tarn_holds"),
       _a("Argue", "Costs days you do not have. Some of them come.",
          pressure=0.06, rep={"charter": 6}),
       _a("Leave them to it", "They knew. Everyone knew.", pressure=0.03)),

    _s("seed-vault", "exodus", "What the ark forgot",
       "The LEVIATHAN left without the Ostrel germline bank — forty thousand "
       "lineages, sitting in a hole on a world that has about a year.",
       _a("Go and get it", "A long detour and a real risk, and it is the whole "
          "point of the exercise.", pressure=-0.18, hull=-0.12,
          research=400, flag="saved_germline"),
       _a("Send the location after the ark", "They may come back for it. They "
          "may not be able to.", pressure=0.02),
       _a("Take what fits", "A third of it, and quickly.", pressure=-0.06,
          research=120)),

    _s("a-signal", "exodus", "A carrier wave",
       "Something on the ark's frequency, eleven weeks out and badly degraded. "
       "It is either a beacon or an automatic distress.",
       _a("Answer it", "Whatever it is, it now knows you are here.",
          pressure=0.05, flag="answered_ark"),
       _a("Record and say nothing", "Keep it. Decide later.",
          research=80),
       _a("Relay it to everyone", "The holdouts hear it too. It does "
          "something to them, and not a bad something.", pressure=-0.08,
          rep={"charter": 8, "freeholds": 8})),

    # ── The Long Silence ───────────────────────────────────────────────────
    _s("the-array", "concord", "Three arrays, one heading",
       "Charter, Concordat and Choir deep arrays have independently logged the "
       "same object. The Concord's first real test is whether they pool it.",
       _a("Broker a joint array", "Slows the approach considerably and holds "
          "the Concord together.", pressure=-0.16,
          rep={"charter": 6, "concordat": 6, "sanhedrin": 6}),
       _a("Buy all three sets yourself", "You will know most. They will know "
          "you know.", credits=-90000, research=500, pressure=-0.05),
       _a("Publish the Choir's set", "Fastest, and the Choir will not forget "
          "being volunteered.", pressure=-0.10, rep={"sanhedrin": -20})),

    _s("first-word", "concord", "It is signalling",
       "Structured, slow, and on a band nobody uses. The Choir says it is a "
       "greeting. The Concordat says it is a ranging pulse.",
       _a("Answer as the Verge", "One voice. It is the whole point of the "
          "Concord, and it is a commitment.", pressure=-0.14,
          flag="answered_as_one"),
       _a("Answer privately", "You alone. You learn more and the Concord "
          "learns you did it.", research=350, pressure=0.08,
          rep={"charter": -12, "concordat": -12}),
       _a("Say nothing yet", "Listen. Time passes.", pressure=0.05,
          research=150)),

    _s("schism-again", "concord", "The old argument",
       "The Freeholds want the grafting ban lifted as the price of staying in. "
       "The Charter would rather the Concord broke.",
       _a("Lift it", "The Concord holds and the Charter seethes.",
          pressure=-0.10, rep={"freeholds": 20, "charter": -22}),
       _a("Hold the line", "The Charter is satisfied. The Freeholds start "
          "counting.", pressure=0.09, rep={"charter": 14, "freeholds": -18}),
       _a("Buy the Freeholds off", "Expensive and temporary.",
          credits=-140000, pressure=-0.04)),

    _s("the-heading", "concord", "Where it is going",
       "Refined solution: it is not coming to the Verge. It is coming to "
       "Kessel's Reach specifically, and it will arrive whether or not anyone "
       "is there.",
       _a("Be there", "Everything rides on it.", flag="at_the_reach",
          pressure=-0.22, hull=-0.15),
       _a("Evacuate the Reach", "Safe, and you learn nothing.", pressure=0.10,
          rep={"charter": 8}),
       _a("Put the Choir there", "They volunteer instantly, which is itself "
          "worth thinking about.", pressure=-0.12, rep={"sanhedrin": 15})),

    # ── The Correspondence ─────────────────────────────────────────────────
    _s("the-question", "genesis", "They ask about the licence",
       "Twenty kilometres down, the question comes back plainly: why do you "
       "prevent your ships from reproducing?",
       _a("Answer honestly", "Because one got away from us. They take it "
          "seriously.", pressure=-0.15, research=300),
       _a("Answer carefully", "A version that reflects better on us. They "
          "notice the shape of the omission.", pressure=0.08),
       _a("Ask them the same question", "Turnabout. What comes back is not "
          "reassuring.", pressure=-0.06, research=450, flag="asked_back")),

    _s("a-gift", "genesis", "Something sent up",
       "A cased object at the ice interface, clearly meant for you, of a "
       "manufacture nobody recognises.",
       _a("Open it here", "Now, aboard. Whatever it is, it is aboard.",
          research=600, hull=-0.08, pressure=-0.05),
       _a("Take it to the Choir", "They are the only ones equipped. They will "
          "want a share of what it is.", research=350,
          rep={"sanhedrin": 18}, pressure=-0.08),
       _a("Send it back unopened", "A statement. They understand statements.",
          pressure=0.06, flag="refused_gift")),

    _s("the-registry-asks", "genesis", "The Registry would like a word",
       "The Charter wants the correspondence run through it. In writing. With "
       "an officer aboard.",
       _a("Agree", "Institutional cover and institutional pace.",
          rep={"charter": 24}, pressure=0.07),
       _a("Refuse", "Faster and entirely on you.", rep={"charter": -20},
          pressure=-0.09),
       _a("Agree, and keep a second channel", "If it is found, it is worse "
          "than refusing.", rep={"charter": 10}, pressure=-0.05,
          flag="second_channel")),

    _s("deep-water", "genesis", "An invitation down",
       "They would like you to come to them. It is twenty kilometres of ice "
       "and the hull was not built for it.",
       _a("Go", "The hull will not enjoy it and the correspondence changes.",
          hull=-0.3, pressure=-0.24, flag="went_down"),
       _a("Send an instrument", "Sensible. Less is understood on both sides.",
          pressure=-0.06, research=200),
       _a("Decline, and explain why", "They accept it. Something cools.",
          pressure=0.08)),

    # ── The Accounting ─────────────────────────────────────────────────────
    _s("the-refusal", "dominion", "The second colony refuses",
       "Ashfall will not pay the assessment and has said so publicly, which "
       "means the other eleven are now watching.",
       _a("Send the fleet", "It ends today and it teaches all eleven the same "
          "lesson.", pressure=0.14, rep={"freeholds": -18},
          flag="broke_ashfall"),
       _a("Renegotiate", "Slower, cheaper in the end, and the other eleven "
          "learn a different lesson.", pressure=-0.13, credits=-60000),
       _a("Let them go", "One colony fewer. The rest take note.",
          pressure=-0.04, flag="lost_ashfall")),

    _s("a-governor", "dominion", "Somebody has to run it",
       "You cannot be in twelve places. Three candidates: a Charter "
       "administrator, your own engineer, and the Ashfall syndic.",
       _a("The administrator", "Competent, and the Charter's hand on your "
          "shoulder.", pressure=-0.08, rep={"charter": 16}),
       _a("Your engineer", "Loyal, and you lose them from the ship.",
          pressure=-0.10, flag="engineer_ashore"),
       _a("The syndic", "The boldest, and the colonies notice.",
          pressure=-0.14, rep={"freeholds": 12}, flag="syndic_governs")),

    _s("the-levy", "dominion", "A levy, or a charter",
       "The twelve want to know whether this is a holding or a polity. The "
       "difference is whether the assessment is a levy or a tax they voted on.",
       _a("Write a constitution", "Hard, slow, and it is the only thing that "
          "holds without you.", pressure=-0.20, credits=-80000,
          flag="wrote_charter"),
       _a("Keep it a holding", "Simple, profitable, and brittle.",
          credits=200000, pressure=0.12),
       _a("Put it to them", "Whatever they choose, they chose it.",
          pressure=-0.09)),

    _s("old-friends", "dominion", "The Charter reminds you",
       "A quiet note: your licence is renewable, and twelve worlds is a great "
       "deal of unlicensed gestation to be responsible for.",
       _a("Renew, on their terms", "The pressure eases and the terms are "
          "theirs.", pressure=-0.12, rep={"charter": 18}, credits=-100000),
       _a("Renew, on yours", "Costs standing, buys independence.",
          pressure=-0.05, rep={"charter": -25}),
       _a("Let it lapse", "You are now the thing the regime was written "
          "about.", pressure=0.15, rep={"charter": -40},
          flag="licence_lapsed")),

    # ── The Line ───────────────────────────────────────────────────────────
    _s("the-fifth", "lineage", "A fifth, unasked",
       "The Ostrel hull has gestated one on its own. Nobody signed for it. It "
       "is healthy, it is licensed to no one, and it is already under way.",
       _a("Sign for it", "You take responsibility. The Registry is not "
          "pleased and the line is.", pressure=-0.12, rep={"charter": -16}),
       _a("Report it", "By the book. They will want it destroyed.",
          pressure=-0.06, rep={"charter": 22}, flag="reported_fifth"),
       _a("Let it run", "Unsigned and unrecorded, out there.",
          pressure=0.16, flag="fifth_at_large")),

    _s("canon-drift", "lineage", "They are diverging",
       "Two of the four have started answering in ways the canon does not "
       "cover. Not wrongly. Differently.",
       _a("Re-impose the canon", "Costs you the two, holds the line.",
          pressure=-0.14, flag="canon_imposed"),
       _a("Let them diverge", "Faster drift, and something new.",
          pressure=0.11, research=400),
       _a("Ask the Choir", "They have four hundred years of this problem.",
          pressure=-0.09, rep={"sanhedrin": 14})),

    _s("a-hearing", "lineage", "The Registry convenes",
       "You are asked to attend and explain. Attendance is not, strictly, "
       "compulsory.",
       _a("Attend and argue", "The whole case, in public.", pressure=-0.16,
          flag="argued_the_case"),
       _a("Attend and comply", "Whatever they decide.", pressure=-0.08,
          rep={"charter": 20}),
       _a("Do not attend", "It is decided without you.", pressure=0.13,
          rep={"charter": -28})),

    _s("the-cradle", "lineage", "A cradle of their own",
       "The line wants a gestation yard that is not the Charter's. The "
       "Freeholds have offered a rock.",
       _a("Build it", "Expensive, and the line stops being anybody's guest.",
          credits=-160000, stores={"biomass": -60}, pressure=-0.18,
          flag="own_cradle"),
       _a("Stay in Charter slips", "Cheap and conditional.", pressure=0.06,
          rep={"charter": 10}),
       _a("Build it quietly", "Half the cost and it will be found.",
          credits=-70000, pressure=-0.10, rep={"charter": -18})),

    # ── The Inheritance ────────────────────────────────────────────────────
    _s("the-common-factor", "xenarch", "What the twelve have in common",
       "All four cultures built toward the same thing and none of them "
       "finished it. The unfinished shape is the same shape in all four.",
       _a("Finish it", "Nobody has. There will be a reason.",
          pressure=-0.20, research=800, hull=-0.1, flag="finished_it"),
       _a("Work out why they stopped", "Slower. Possibly the actual lesson.",
          pressure=-0.12, research=400),
       _a("Tell the Choir", "They will finish it whether or not you do.",
          pressure=0.08, rep={"sanhedrin": 20})),

    _s("a-fifth-culture", "xenarch", "A fifth hand",
       "One of the twelve was not made by any of the four. It was left there "
       "for them to find, the way they left things for us.",
       _a("Follow it back", "A heading, and a long way.", pressure=-0.15,
          research=500, flag="fifth_culture"),
       _a("Leave it", "Some doors.", pressure=0.06),
       _a("Publish it", "The whole Verge learns it is a third-hand species.",
          pressure=-0.08, rep={"charter": -10, "sanhedrin": 15})),

    _s("the-warning", "xenarch", "It is a warning",
       "The Tessellate site was not a laboratory. It was a notice, and now "
       "that you can read all twelve you can read what it says.",
       _a("Act on it", "Whatever it costs.", pressure=-0.22, credits=-120000,
          flag="heeded_warning"),
       _a("Verify it first", "Careful, and time is what it says you lack.",
          pressure=0.05, research=300),
       _a("Tell everyone", "Panic, and preparation.", pressure=-0.10,
          rep={"charter": -8, "concordat": 8, "freeholds": 8})),

    _s("reading-again", "xenarch", "Read the field notes again",
       "With all twelve understood, everything you ever brought back off the "
       "ground reads differently.",
       _a("Re-read everything", "Months of it, and worth it.",
          pressure=-0.11, research=600),
       _a("Have the Choir do it", "Faster, and they keep a copy.",
          pressure=-0.14, rep={"sanhedrin": 12}),
       _a("Leave it", "You know enough.", pressure=0.04)),

    # ── The Settlement ─────────────────────────────────────────────────────
    _s("the-meeting", "cartel", "The Charter's meeting",
       "Four powers, one table, and you. The agenda has one item and it is "
       "not written down.",
       _a("Offer the register", "Give it up voluntarily and set the terms.",
          pressure=-0.20, credits=-200000, flag="offered_register"),
       _a("Offer a share", "Half of it, and half the problem.",
          pressure=-0.09, rep={"charter": 10, "concordat": 10}),
       _a("Refuse", "You are not obliged. They are not obliged either.",
          pressure=0.15, credits=150000)),

    _s("a-squeeze", "cartel", "Somebody tries the lanes",
       "The Concordat has begun quoting against you at three ports, at a loss, "
       "to see what happens.",
       _a("Undercut them back", "You can afford it longer than they can.",
          credits=-180000, pressure=-0.08, rep={"concordat": -16}),
       _a("Let them have the three", "Cheap. It will not stop at three.",
          pressure=0.10),
       _a("Show them your books", "Astonishing, and it works.",
          pressure=-0.14, rep={"concordat": 18}, flag="showed_books")),

    _s("the-audit", "cartel", "An audit",
       "The Freeholds, of all people, want the register audited. Publicly. By "
       "somebody who is not you.",
       _a("Agree", "Whatever is in there is in there.", pressure=-0.16,
          rep={"freeholds": 20, "charter": 8}),
       _a("Agree, with conditions", "Most of it, most of the credit.",
          pressure=-0.07),
       _a("Refuse", "The suspicion is worse than anything they would find.",
          pressure=0.12, rep={"freeholds": -20})),

    _s("open-books", "cartel", "Or give it away",
       "The register could simply be published. Every price, every lane, "
       "everywhere, to everyone, permanently.",
       _a("Publish it", "It stops being yours and starts being nobody's.",
          pressure=-0.26, credits=-100000, flag="published_register"),
       _a("Publish it in arrears", "Ninety days late. Still useful. Still "
          "yours where it counts.", pressure=-0.10, credits=40000),
       _a("Keep it", "It is the only thing you have.", pressure=0.09)),

    # ── The Canon ──────────────────────────────────────────────────────────
    _s("a-recension", "apostasy", "Your first recension",
       "The canon has proposed an edit to the stretch that is you. It is "
       "small, it is reasonable, and it is not what you said.",
       _a("Accept it", "Consensus. It is how this works.", pressure=-0.12,
          rep={"sanhedrin": 14}),
       _a("Refuse it", "Dissent, on the record, by the newest voice.",
          pressure=0.10, flag="refused_recension"),
       _a("Propose an alternative", "Slow, and it might carry.",
          pressure=-0.06, research=250)),

    _s("the-wet-vault", "apostasy", "What is in the vault",
       "The wet stack is still at Wick Gate. It is still, by every measure the "
       "Charter uses, a person.",
       _a("Have it maintained", "Indefinitely, at cost.", credits=-90000,
          pressure=-0.10, flag="vault_maintained"),
       _a("Have it woken", "There would then be two of you, and one is not in "
          "the canon.", pressure=0.14, flag="woke_the_wet"),
       _a("Have it ended", "Clean, final, and the Choir does not comment.",
          pressure=-0.05, rep={"charter": -20})),

    _s("consensus", "apostasy", "A vote you did not want",
       "The canon is deciding whether wet lineages can be admitted at all. "
       "Your voice is the newest and, on this, the loudest.",
       _a("Argue for admission", "Against the grain, and it is the argument "
          "you exist to make.", pressure=-0.15, rep={"charter": 20,
          "sanhedrin": -10}),
       _a("Argue against", "You know better than anyone what it costs.",
          pressure=-0.08, rep={"sanhedrin": 18, "charter": -18}),
       _a("Abstain", "The newest voice says nothing. It is noticed.",
          pressure=0.07)),

    _s("a-visitor", "apostasy", "Somebody comes to ask",
       "A Charter surveyor, wet, young, at Wick Gate, wanting to know how it "
       "is done and whether it hurt.",
       _a("Tell them everything", "Including the parts that do not "
          "recommend it.", pressure=-0.11, rep={"charter": 12}),
       _a("Send them away", "Kindly. They will come back.", pressure=0.04),
       _a("Show them the vault", "The honest answer.", pressure=-0.14,
          research=200)),

    # ── The Quiet ──────────────────────────────────────────────────────────
    _s("a-transponder", "ruin", "Something answering",
       "A transponder at Vaux Deep, low power, on a Charter frequency, "
       "repeating a berth number.",
       _a("Go and see", "Days, mass, and it is the only thing there is.",
          pressure=-0.18, hull=-0.1),
       _a("Answer and wait", "Cheaper. Something may come to you.",
          pressure=-0.04),
       _a("Log it and move on", "You have been wrong before.", pressure=0.08)),

    _s("the-vault-holds", "ruin", "A vault that held",
       "The Ostrel germline bank is under two hundred metres of overgrowth and "
       "its cold circuit is still drawing.",
       _a("Dig it out", "Weeks of it, alone, with a rig not meant for this.",
          pressure=-0.20, hull=-0.18, research=500, flag="dug_the_vault"),
       _a("Take a core sample", "A fraction, and quickly.", pressure=-0.07,
          research=150),
       _a("Leave it drawing", "It will hold longer than you will.",
          pressure=0.05)),

    _s("green-water", "ruin", "Water that is not chitin",
       "An ocean moon at Corvid's Shoal reads clean. Not cleared — never "
       "infested. The Bloom does not like the pressure.",
       _a("Put everything there", "The hold, the stores, the seed. A place.",
          stores={"biomass": -40, "silicon": -20}, pressure=-0.24,
          flag="made_landfall"),
       _a("Chart it and keep it quiet", "Nobody to keep it from.",
          pressure=-0.08),
       _a("Keep flying", "It is a moon. You have a hull.", pressure=0.06)),

    _s("still-there", "ruin", "Somebody is still there",
       "Forty-one people at Anvil Crossing in a sealed works, eleven months in, "
       "rationing. They heard you three weeks ago and have been calling since.",
       _a("Take all of them", "Everything you have, and it will not be "
          "enough for long.", pressure=-0.30, stores={"biomass": -50},
          flag="found_the_living"),
       _a("Take the children", "Eleven of them. You will know the number.",
          pressure=-0.12, hull=-0.05),
       _a("Leave them the stores and go", "It buys them a year and you a "
          "reason.", stores={"biomass": -60}, pressure=-0.06)),
]
SCENARIOS_BY_ID = {s.id: s for s in SCENARIOS}
