"""The tutorial, as a sequence of things to actually do.

Not a wall of text and not a script that assumes you complied. Each lesson
names one thing, and `sim/tutorial.py` watches the game until that thing has
genuinely happened — measured against a mark taken when the lesson opened, so
"survey a body" means one more than you had, not "a body is surveyed".

Each lesson carries what to do, where to do it, and — the part a tutorial
usually skips — **what just happened and why it matters**, shown after rather
than before, when there is something to point at.

Every `watch` here must have a matching watcher in `sim/tutorial.py`, and a
check fails if one does not.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    ask: str                 # the thing to do
    screen: str              # where it is done
    watch: str               # which watcher decides it has happened
    then: str                # what just happened, and why it matters
    skip_if: str = ""        # a watcher that means this is already true


LESSONS = [
    Lesson("survey", "Look at something",
           "Open the System screen and survey one of the bodies here.",
           "system", "surveyed_one",
           "That is the loop the whole game hangs off. A survey tells you what "
           "is on a body — ore, ice, biomes, lifeforms, anomalies, sometimes a "
           "buried alien site — and it puts evidence on the research bench at "
           "the same time. Surveying every body in a system completes a chart, "
           "which is a thing you can sell."),

    Lesson("port", "Find out what things are worth",
           "Open the Port screen. You do not have to buy anything yet.",
           "port", "saw_market",
           "Prices drift daily toward each port's own equilibrium, so a "
           "profitable run stays profitable for a while and then quietly stops "
           "being. Every price you look at is written into your register, and "
           "the freight desk on that screen ranks runs using it — by what the "
           "voyage clears, not by the spread."),

    Lesson("sell", "Sell what you have learned",
           "Sell your survey data at the port. It is the first money most "
           "captains make.",
           "port", "sold_something",
           "Survey data is a commodity like any other and it regenerates every "
           "time you look at something new. A completed chart is worth more "
           "than the sum of its bodies, and different powers pay for different "
           "things — the Codex says which."),

    Lesson("fuel", "Buy reaction mass",
           "Buy volatiles at the port. Sixty tonnes is a comfortable tank.",
           "port", "bought_fuel",
           "Volatiles are reaction mass. You can also cut them out of ice with "
           "the mining rig, anywhere, for free but slowly — which is why an "
           "empty tank is never the end of a chronicle, only a delay."),

    Lesson("helm", "Go somewhere",
           "Open the Helm and fly to another body, or jump from the Sector "
           "chart to another star.",
           "helm", "moved",
           "A jump drops you at the system edge, not alongside anything, and "
           "bodies keep moving on their orbits while you fly. Four burn "
           "profiles trade reaction mass against days, and coasting is always "
           "free. A hard burn arrives hot, and over the cap the hull cooks."),

    Lesson("work", "Take on some work",
           "Accept a contract from the board on the Port screen.",
           "port", "took_contract",
           "Contracts complete the moment their terms are met rather than when "
           "you remember to hand them in. Taking a power's work is a position, "
           "not an errand: finishing it costs you standing with everyone that "
           "power is at odds with, in proportion to how bad the rift is."),

    Lesson("ship", "Look at what you are flying",
           "Open the Ship screen and switch to the Plans tab.",
           "ship", "saw_plans",
           "The model is the fitted list — refit and it changes. Click any "
           "piece to read it. The hull has six layers and damage lands "
           "outermost first; the one marked critical is the pressure vessel, "
           "and below it there is only crew."),

    Lesson("powers", "See who is who",
           "Open the Diplomacy screen.",
           "diplomacy", "saw_diplomacy",
           "Two axes, not one: your standing with each power, and how the "
           "powers regard each other. Tribute and relief move the first; only "
           "brokering moves the second, and brokering needs both parties to "
           "think well of you already. Every overture says what it will move "
           "before you commit."),
]
LESSONS_BY_ID = {lesson.id: lesson for lesson in LESSONS}

#: What the bar says when there is nothing left to teach.
DONE = ("That is the whole of it. Everything else the game does is explained "
        "on the screen that does it, and the Help screen has the rest — press "
        "the Help key from anywhere and it opens at wherever you are.")
