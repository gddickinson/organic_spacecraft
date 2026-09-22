"""The column beside the deck: the party, what they can do, who they can see.

Every button here is an act the sim offered — `afoot_acts.offer` for what a
person can do where they stand, `afoot_fight.terms` for a shot,
`afoot_talk.can_talk` for a word — and every one says its odds or why not
before it is pressed. The panels decide nothing; they call back into the
screen, which calls the sim.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..data import afoot_arms as arms
from ..data import kit as kit_table
from ..sim import afoot_acts, afoot_fight, afoot_map, afoot_talk
from ..sim.afoot_state import party
from .widgets import Bar, Panel, Pill, button, label, note

#: How many lines of the walk's own log the column keeps in view.
LOG_LINES = 9

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
        b = button(who.name, lambda _=False, i=who.id: view.pick(i),
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
    """What the person in hand can do from where they stand."""
    p = Panel(f"{who.name} can")
    if not who.standing:
        p.add(note(f"{who.name} is {STATUS.get(who.status, who.status)}."))
        return p
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
    people.sort(key=lambda a: afoot_map.distance(who.x, who.y, a.x, a.y))
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
        buttons = []
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
        if other.standing:
            ok, why = afoot_talk.can_talk(walk, who, other)
            b = button("Talk", lambda _=False, i=other.id: view.talk_to(i),
                       enabled=ok, why=why)
            b.setObjectName(f"afoot_talk_{other.id}")
            buttons.append(b)
        p.add_buttons(*buttons)
    return p


def goals(walk):
    if not walk.goals:
        return None
    p = Panel("To do here")
    for _gid, words, done in walk.goals:
        p.add(label(("✓ " if done else "· ") + words, "note",
                    "chloro" if done else ""))
    return p


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
