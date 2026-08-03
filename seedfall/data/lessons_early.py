"""The first five chapters: finding your way, flying, money, science, distance.

Each lesson names one thing to do and, after it is done, says what just
happened and why it matters — the explanation comes *after*, when there is
something to point at. `sim/tutorial_watch.py` holds the watcher that decides
each one, from the state of the chronicle rather than from a claim.
"""

from __future__ import annotations

from .lesson_types import Lesson

EARLY = [
    # ── I. First light ────────────────────────────────────────────────────
    Lesson("map", "Look at where you are",
           "Open the Sector chart. This is the whole Verge; you are the "
           "marked star.",
           "map", "saw_map",
           "Stars you have not visited show only what your instruments can "
           "make out from here. Lanes are what a jump can cross, and the "
           "chart will not offer one your drive cannot make — so the wall "
           "you see is a real wall, not a decoration. Every screen has a "
           "keyboard shortcut, listed under Help.",
           chapter="first-light", skip_if="have_played"),

    Lesson("ship", "Meet your ship",
           "Open the Ship screen and read the layer stack, the fittings and "
           "the hold.",
           "ship", "saw_ship",
           "A hull is six layers deep and damage eats them from the outside "
           "in, so a breach is a specific thing rather than a number going "
           "down. What is fitted decides what she can do — jump range, "
           "sensors, cargo, guns — and every fitting costs mass, which costs "
           "acceleration. There is no best ship, only a ship set up for the "
           "work you mean to do.",
           chapter="first-light", skip_if="have_played"),

    Lesson("manual", "Find the manual",
           "Open Help. The manual is written for a captain, not for a "
           "programmer, and it knows which screen you came from.",
           "help", "saw_manual",
           "Anything countable in the manual is counted when you read it, so "
           "it cannot go stale. Press Help from any screen and it opens at "
           "that screen's page. The Academy tab beside it lists every course "
           "in this tutorial, so you can come back and take one again.",
           chapter="first-light", skip_if="have_played"),

    # ── II. The wheel ─────────────────────────────────────────────────────
    Lesson("conn", "Take the ship's wheel",
           "Open the Pilot screen, press Run clock, and fly her for five "
           "minutes — hold a thruster button, or the W/A/S/D and R/F keys.",
           "pilot", "flew_conn",
           "That was the conn. A held thruster burns for as long as you hold "
           "it, so speed builds rather than jumping; the clock runs at a "
           "minute a beat, and the Time button compresses it. Everything you "
           "burn and every minute you fly is billed as it happens. The same "
           "flight shows in the Conn window, the Flight controls and the "
           "Approach view — they are five windows onto one ship.",
           chapter="the-wheel"),

    Lesson("autopilot", "Hand her to the computer",
           "Arm an autopilot mode — Hold station or Brake to zero will do — "
           "and let it fly a beat.",
           "pilot", "computer_flew",
           "One computer flies every automatic manoeuvre: hold station, "
           "brake to zero, close and berth, make orbit, move away, and run "
           "for a mark you have laid a course on. It is the same bar on "
           "every flying screen, and Manual always takes her back. You never "
           "have to fight it for the controls — a held thruster outranks it "
           "for as long as your hand is down.",
           chapter="the-wheel"),

    Lesson("berth", "Get alongside something",
           "Take the conn on a quay and let the computer close and berth — "
           "or fly her in by hand if you would rather.",
           "pilot", "berthed",
           "Alongside is a *place*: a named berth on the structure, at "
           "walking pace. Arrive fast and it is a collision, and both hulls "
           "pay. A structure that has cleared you will send boats out to "
           "walk you in for nothing, which is what being welcome is worth. "
           "Once you are alongside, the Port screen is open to you.",
           chapter="the-wheel", skip_if="have_berthed"),

    # ── III. Bread and salt ───────────────────────────────────────────────
    Lesson("port", "Find out what things are worth",
           "Open the Port screen. You do not have to buy anything yet.",
           "port", "saw_market",
           "Prices drift daily toward each port's own equilibrium, so a "
           "profitable run stays profitable for a while and then quietly "
           "stops being. Every price you look at is written into your "
           "register, and the freight desk ranks runs using it — by what the "
           "voyage clears, not by the spread.",
           chapter="bread-and-salt", skip_if="have_prices"),

    Lesson("sell", "Sell what you have learned",
           "Sell your survey data at the port. It is the first money most "
           "captains make.",
           "port", "sold_something",
           "Survey data is a commodity like any other and it regenerates "
           "every time you look at something new. A completed chart is worth "
           "more than the sum of its bodies, and different powers pay for "
           "different things — the Codex says which.",
           chapter="bread-and-salt"),

    Lesson("fuel", "Buy reaction mass",
           "Buy volatiles at the port. Sixty tonnes is a comfortable tank.",
           "port", "bought_fuel",
           "Volatiles are reaction mass. You can also cut them out of ice "
           "with the mining rig, anywhere, for free but slowly — which is "
           "why an empty tank is never the end of a chronicle, only a delay.",
           chapter="bread-and-salt"),

    # ── IV. Looking closely ───────────────────────────────────────────────
    Lesson("survey", "Look at something properly",
           "Open the System screen and survey one of the bodies here.",
           "system", "surveyed_one",
           "That is the loop the whole game hangs off. There are four ways "
           "to look and they are not a ladder: a long-range sweep is free "
           "and sees only resources, a close pass costs reaction mass and "
           "sees life, a probe swarm needs dronework, and a deep survey sees "
           "what is buried. Each says what it is blind to before you commit.",
           chapter="looking-closely", skip_if="have_surveyed"),

    Lesson("research", "Put the bench to work",
           "Open Research and choose a project from the tree.",
           "tech", "set_project",
           "Research runs on ship time, so it keeps going while you fly, and "
           "surveys feed it: what you look at becomes evidence on the bench. "
           "The tree is fifty-eight nodes across ten branches, and nothing "
           "in it is required — it is a set of doors, not a track.",
           chapter="looking-closely"),

    Lesson("unlock", "Finish something",
           "Let a project run to completion. Time passes while you do other "
           "work, so go and do some.",
           "tech", "unlocked_tech",
           "A finished technology changes what the shipyard will build, what "
           "colonies you may plant, and what the survey can see. Alien "
           "technology is a separate progression: it cannot be reasoned out, "
           "only understood by digging it up, taking it apart, or buying "
           "somebody's field notes.",
           chapter="looking-closely"),

    # ── V. The long crossing ──────────────────────────────────────────────
    Lesson("helm", "Go somewhere",
           "Open the Helm and set course for another body in this system.",
           "helm", "moved",
           "Bodies move on real orbits while you fly, so the helm aims at "
           "where the target will be. Four burn profiles trade reaction mass "
           "against days and coasting is always free — which is what stops "
           "an empty tank from becoming a dead end. A hard burn arrives hot, "
           "and a hot hull is a worse thing to burn again in.",
           chapter="the-long-crossing", skip_if="have_travelled"),

    Lesson("watch", "Stand a watch",
           "Fly a crossing watch by watch from the Transit screen rather "
           "than skipping to the far end.",
           "transit", "stood_watch",
           "A crossing is a sequence of watches, and things come up on them: "
           "a fault, a sighting, a choice about how hard to push. Every "
           "option costs one of three things — days, reaction mass, or "
           "hull — and the screen says which before you choose. You can cut "
           "a burn and turn back at any watch; what is spent is spent.",
           chapter="the-long-crossing"),

    Lesson("jump", "Cross to another star",
           "Open the Sector chart and jump to a system you have not been to.",
           "map", "jumped",
           "A jump drops you at the system edge, not alongside anything, so "
           "arriving is the start of a journey rather than the end of one. "
           "How hard you fly the jump is a choice on two clocks: the "
           "Verge's, which every market and deadline runs on, and the "
           "ship's, which is what your crew actually live through.",
           chapter="the-long-crossing"),
]
