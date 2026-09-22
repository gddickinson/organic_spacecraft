"""The column beside the deck: the party, what they can do, who they can see.

Every button here is an act the sim offered — `afoot_acts.offer` for what a
person can do where they stand, `afoot_fight.terms` for a shot,
`afoot_talk.can_talk` for a word — and every one says its odds or why not
before it is pressed. The panels decide nothing; they call back into the
screen, which calls the sim.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..data import afoot_arms as arms
from ..data import kit as kit_table
from ..sim import afoot_acts, afoot_fight, afoot_fire, afoot_map, afoot_talk
from ..sim.afoot_state import party
from . import afoot_canvas
from .widgets import Bar, Panel, Pill, button, label, note

#: How many lines of the walk's own log the column keeps in view, and how
#: many of the newest sit at the top of it, above the fold.
LOG_LINES = 9
LATEST_LINES = 3

STATUS = {"up": "", "down": "down, bleeding", "stable": "down, stable",
          "dead": "dead", "gone": "gone"}


def gear(actor) -> str:
    """What somebody is carrying, as a line."""
    arm = arms.arm(actor.weapon)
    worn = kit_table.ITEM_BY_ID.get(actor.armour)
    return f"{arm.name}" + (f" · {worn.name.lower()}" if worn else "")


def party_strip(view, walk) -> Panel:
    """Everybody in the party: stamina, movement left, what they carry."""
    p = Panel("The party")
    for who in party(walk):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        picked = who.id == walk.selected
        mark = afoot_canvas.tokens(walk).get(who.id, "")
        b = button(f"{mark} · {who.name}" if mark else who.name,
                   lambda _=False, i=who.id: view.pick(i),
                   kind="primary" if picked else "flat",
                   enabled=who.status != "dead")
        b.setObjectName(f"afoot_member_{who.id}")
        h.addWidget(b)
        state = STATUS.get(who.status, who.status)
        if who.standing:
            state = (f"{max(0, who.hp)}/{who.hp_max}"
                     + (f" · {who.mp} to move" if walk.mode == "action"
                        else "") + (" · acted" if who.acted else "")
                     + (f" · {who.stance}" if who.stance else ""))
        h.addWidget(label(state, "note",
                          "warn" if not who.standing else ""))
        h.addStretch(1)
        p.add(row)
        share = max(0.0, who.hp) / max(1, who.hp_max)
        p.add(Bar(share, "chloro" if share > 0.5 else "osteo" if share > 0.25
                  else "warn", 4))
        p.add(label(gear(who), "note"))
    return p


def in_hand(view, walk, who) -> Panel:
    """What the person in hand can do from where they stand — or, while
    they are down, who could get to them."""
    if not who.standing:
        return _down(view, walk, who)
    p = Panel(f"{who.name} can")
    acts = afoot_acts.offer(game_of(view), walk, who)
    for on, heading in GROUPS:
        rows = [a for a in acts if a.on == on]
        if not rows:
            continue
        p.add(label(heading, "dim"))
        for act in rows:
            odds = (f" — {act.odds:.0%}" if act.odds is not None and act.ok
                    else "")
            b = button(act.label + odds,
                       lambda _=False, a=act: view.do_act(a),
                       kind="primary" if act.id == "leave" and act.ok else "",
                       enabled=act.ok, why=act.why, tip=act.blurb)
            b.setObjectName(f"afoot_act_{act.id}_{act.target}")
            p.add(b)
    if not acts:
        p.add(note("Nothing within reach to do."))
    return p


def _down(view, walk, who) -> Panel:
    """Somebody down, in hand: what has happened to them, and each of the
    party still standing, nearest first, to take in hand instead."""
    p = Panel(f"{who.name} is {STATUS.get(who.status, who.status)}", "warn")
    help_ = ("First aid stops the bleeding; anybody can carry them out."
             if who.status == "down" else
             "They will keep. Anybody can carry them out."
             if who.status == "stable" else "There is nothing to be done.")
    p.add(note(help_))
    mates = sorted((m for m in party(walk, standing=True)),
                   key=lambda m: (m.deck != who.deck, afoot_map.apart(walk, m, who)))
    for mate in mates:
        far = ("another deck" if mate.deck != who.deck else
               f"{afoot_map.apart(walk, mate, who)} squares "
               "away")
        b = button(f"Take {mate.name} in hand — {far}",
                   lambda _=False, i=mate.id: view.pick(i))
        b.setObjectName(f"afoot_hand_to_{mate.id}")
        p.add(b)
    if not mates:
        p.add(note("Nobody is left standing."))
    return p


#: How the acts are grouped, by what each is done to (`afoot_acts.Act.on`).
GROUPS = (("thing", "Within reach"), ("actor", "People"),
          ("self", "Themselves"))


def game_of(view):
    return view.game


def in_sight(view, walk, who) -> Panel:
    """Everybody the party can see: what they are, and a shot or a word."""
    p = Panel("In sight")
    game = game_of(view)
    seen = view.canvas.seen_now() if view.canvas is not None else set()
    people = [a for a in walk.actors if a.side == "npc"
              and a.deck == walk.viewing and (a.x, a.y) in seen
              and a.status not in ("gone",)]
    people.sort(key=lambda a: afoot_map.apart(walk, who, a))
    if not people:
        p.add(note("Nobody in sight."))
        return p
    for other in people[:8]:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(label(other.name, ""))
        mood = other.mood if other.standing else STATUS.get(other.status)
        h.addWidget(Pill(mood, {"hostile": "warn", "friendly": "chloro",
                                "wary": "osteo"}.get(other.mood, "dim")))
        h.addStretch(1)
        p.add(row)
        buttons, fire = [], []
        if other.standing or other.status in ("down", "stable"):
            shot = afoot_fight.terms(game, walk, who, other)
            lo, hi = afoot_fight.damage_range(who, other)
            text = (f"Attack — {shot['odds']:.0%}, {lo}–{hi}" if shot["ok"]
                    else "Attack")
            b = button(text, lambda _=False, i=other.id: view.attack(i),
                       kind="danger" if other.hostile else "",
                       enabled=shot["ok"] and not who.acted and who.standing,
                       why=shot["why"] or "Already acted this round.")
            b.setObjectName(f"afoot_attack_{other.id}")
            buttons.append(b)
            fire = _fire(view, game, walk, who, other, shot)
        if other.standing:
            ok, why = afoot_talk.can_talk(walk, who, other)
            b = button("Talk", lambda _=False, i=other.id: view.talk_to(i),
                       enabled=ok, why=why)
            b.setObjectName(f"afoot_talk_{other.id}")
            buttons.append(b)
        p.add_buttons(*buttons)
        # Rows of their own, so a carbine and a grenade in hand never push
        # the column wider than the window's narrowest.
        for row in fire:
            p.add_buttons(*row)
    return p


def _fire(view, game, walk, who, other, shot) -> list:
    """Rows of buttons: a burst and suppressing fire for a weapon with Auto,
    and a throw for every sort of grenade the person in hand is carrying."""
    out, auto = [], []
    arm = afoot_fight.weapon(who)
    free = shot["ok"] and not who.acted and who.standing
    if arm.auto:
        b = button(f"Burst — {shot['odds']:.0%}, +{arm.auto}" if shot["ok"]
                   else "Burst", lambda _=False, i=other.id: view.burst(i),
                   kind="danger" if other.hostile else "", enabled=free,
                   why=shot["why"] or "Already acted this round.",
                   tip=f"The {arm.name}'s Auto {arm.auto} added to the "
                       "damage.")
        b.setObjectName(f"afoot_burst_{other.id}")
        auto.append(b)
        b = button("Suppress", lambda _=False, i=other.id: view.suppress(i),
                   enabled=free, why=shot["why"] or "Already acted this round.",
                   tip="Nobody is hit; they and anybody beside them are "
                       "pinned for a round.")
        b.setObjectName(f"afoot_suppress_{other.id}")
        auto.append(b)
        out.append(auto)
    for gid in sorted(set(afoot_fire.grenades(who))):
        got = afoot_fire.terms(game, walk, who, other, gid)
        name = arms.GRENADE_BY_ID[gid].name
        b = button(f"Throw a {name} — {got['odds']:.0%}" if got["ok"]
                   else f"Throw a {name}",
                   lambda _=False, i=other.id, g=gid: view.throw(i, g),
                   kind="danger", enabled=got["ok"] and not who.acted,
                   why=got["why"] or "Already acted this round.")
        b.setObjectName(f"afoot_throw_{gid}_{other.id}")
        out.append([b])
    return out


def goals(walk):
    if not walk.goals:
        return None
    p = Panel("To do here")
    for _gid, words, done in walk.goals:
        p.add(label(("✓ " if done else "· ") + words, "note",
                    "chloro" if done else ""))
    return p


def latest(walk):
    """The newest lines of the walk's log, at the top of the column, where
    a shot or a hail is seen without scrolling for it."""
    rows = walk.log[-LATEST_LINES:]
    if not rows:
        return None
    box = QWidget()
    col = QVBoxLayout(box)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(2)
    for _round, text, kind in rows:
        col.addWidget(label(text, "note", kind, wrap=True))
    return box


def log(walk) -> Panel:
    p = Panel("What happened")
    for entry in walk.log[-LOG_LINES:]:
        _round, text, kind = entry
        p.add(label(text, "note", kind, wrap=True))
    return p


def controls(view, walk) -> QWidget:
    """End the round, or give up to the watch."""
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(7)
    end = button("End turn" if walk.mode == "action" else "Wait a moment",
                 view.end_turn, kind="primary",
                 tip="Everybody else acts; then a new round.")
    end.setObjectName("afoot_end_turn")
    h.addWidget(end)
    watch = [a for a in walk.actors if a.hostile
             and a.folk in ("constable", "customs")]
    if watch:
        give = button("Give yourselves up", view.surrender, kind="danger",
                      tip="Go quietly. What they saw is charged; what you "
                          "found stays behind.")
        give.setObjectName("afoot_give_up")
        h.addWidget(give)
    h.addStretch(1)
    return row
