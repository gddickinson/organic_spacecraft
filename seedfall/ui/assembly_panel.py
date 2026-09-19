"""The Assembly tab on the Diplomacy screen: the next sitting, the order paper,
what each power will vote and why, what moving a vote would cost, what is in
force, and what the last sittings did.

Every number here is the sim's: `assembly_vote.forecast` for the votes,
`assembly_lobby.preview` for an act — which is what the act then does — and
`assembly_lobby.speech` for a voice in the chamber. The screen draws; it
decides nothing and rolls nothing.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..core.util import duration
from ..data.assembly import RESOLUTIONS_BY_ID, TERM_DAYS
from ..data.factions import FACTIONS_BY_ID
from ..sim import assembly, assembly_lobby as lob, assembly_session as sess
from ..sim import assembly_vote as vote
from ..sim import diplomacy as dip
from .widgets import Panel, Pill, button, defer, label, mono_label, note, spacer

_VOTE_TINT = {"yes": "chloro", "no": "warn", "abstain": "dim"}
_ACT_NAME = {"petition": "Petition", "pay": "Pay for the vote",
             "leak": "Leak the sponsor's papers"}


def _short(power: str) -> str:
    return FACTIONS_BY_ID[power].short


def build(view, game) -> None:
    """Render the tab into `view`'s column."""
    state = assembly.ensure(game)
    view.col.addWidget(note(
        "Every season the four powers sit at a capital in turn and vote on "
        "what is tabled. A motion passes on three votes of four, or on two "
        "with the other two abstaining. Powers that vote together come "
        "closer; a power voted down takes it out on whoever did it — so "
        "brokering motions everybody can live with is the one road that "
        "raises every pair at once."))
    view.col.addWidget(_next(view, game, state))
    for item in state.agenda:
        view.col.addWidget(_motion(view, game, state, item))
    view.col.addWidget(_in_force(game))
    history = _history(game, state)
    if history is not None:
        view.col.addWidget(history)


def _next(view, game, state) -> Panel:
    power, seat = sess.seat(game, state)
    p = Panel("The next sitting")
    if seat is None:
        p.add(note("No power holds a quay to sit at. The Assembly is dark."))
        return p
    left = max(0, state.next_day - game.day)
    p.add_row("Where", f"{seat.name}, hosted by the {_short(power)}")
    p.add_row("When", f"day {state.next_day} — in {duration(left)}",
              "warn" if left <= 10 else "")
    here = sess.present(game)
    p.add_row("You", "there — you will speak" if here
              else "elsewhere — not heard", "chloro" if here else "dim")
    if not state.announced:
        p.add(note("The clerk publishes the order paper thirty days before "
                   "the sitting."))
    elif not state.agenda:
        p.add(note("Nothing was tabled for this sitting."))
    buttons = [] if here else [button(
        f"Set a course for {seat.name}",
        lambda _=False, sid=seat.id: _course(view, sid), kind="primary")]
    p.add_buttons(*buttons)
    return p


def _course(view, system_id: int) -> None:
    chart = view.win.views.get("map")
    if chart is not None:
        chart.selected = system_id
    view.win.go("map")


def _motion(view, game, state, item) -> Panel:
    res = RESOLUTIONS_BY_ID[item.res_id]
    p = Panel(vote.title(item), res.tint)
    p.add(label(f"Tabled by the {_short(item.sponsor)}", "sub"))
    p.add(label(res.text.format(power=_named(item, "power"),
                                a=_named(item, "a"), b=_named(item, "b")),
                "", wrap=True))
    # A wrapping line, not a row: a row's value does not wrap, and at
    # 1040 px the longest of these pushed the column into a side scroll.
    p.add(label(f"If it passes: {vote.words(item)}, for "
                f"{duration(res.term)}.", "", "osteo", wrap=True))
    told = vote.forecast(game, item.key)
    p.add(spacer(3), mono_label("How they will vote, as things stand"))
    for power in dip.POWERS:
        choice = told["votes"][power]
        p.add_row(f"{FACTIONS_BY_ID[power].name}",
                  f"{choice.upper()}  ({told['scores'][power]:+.1f})",
                  _VOTE_TINT[choice])
        reasons = sorted(told["reasons"][power], key=lambda r: -abs(r[1]))[:3]
        p.add(note("   " + "; ".join(f"{why} {v:+.1f}" for why, v in reasons)))
    verdict = "PASSES" if told["passes"] else "FAILS"
    p.add_row("As things stand",
              f"{verdict} — {told['yes']} yes, {told['no']} no, "
              f"{told['abstain']} abstaining",
              "chloro" if told["passes"] else "warn")
    moved = vote.moves(told["votes"], told["scores"], told["passes"])
    if moved:
        p.add(note("What the count would do between them: " + ", ".join(
            f"{_pair(k)} {d:+.0f}" for k, d in sorted(moved.items()))))
    _stance(view, p, state, item)
    side = state.positions.get(item.key, "")
    if side:
        _speech(p, game, item)
        _lobby(view, p, game, item)
    return p


def _named(item, key: str) -> str:
    who = item.params.get(key)
    return _short(who) if who else ""


def _pair(key: str) -> str:
    a, b = key.split("|")
    return f"{_short(a)}–{_short(b)}"


def _stance(view, p: Panel, state, item) -> None:
    side = state.positions.get(item.key, "")
    p.add(spacer(3), mono_label("Where you stand"))
    if side:
        p.add(Pill("you are for it" if side == "for"
                   else "you are against it",
                   "chloro" if side == "for" else "warn"))
    p.add_buttons(
        button("For it", lambda _=False: _position(view, item.key, "for"),
               kind="primary" if side != "for" else "", enabled=side != "for"),
        button("Against it",
               lambda _=False: _position(view, item.key, "against"),
               enabled=side != "against"),
        button("No position", lambda _=False: _position(view, item.key, ""),
               kind="flat", enabled=bool(side)))


def _position(view, key: str, side: str) -> None:
    told = lob.position(view.game, key, side)
    if not told["ok"]:
        view.win.toast(told["why"], "warn")
        return
    view.win.refresh()


def _speech(p: Panel, game, item) -> None:
    sway = lob.speech(game, item.key)
    p.add(note("In the chamber on the day, your speech moves every power: "
               + ", ".join(f"{_short(w)} {d:+.1f}" for w, d in sway.items())
               + ". Comms and your standing with each carry it."))


def _lobby(view, p: Panel, game, item) -> None:
    targets = getattr(view, "assembly_targets", None)
    if targets is None:
        targets = view.assembly_targets = {}
    who = targets.get(item.key) or next(
        (w for w in dip.POWERS if w != item.sponsor), dip.POWERS[0])
    p.add(spacer(3), mono_label("Move a vote before the sitting"))
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(label("Whose vote", "dim"))
    combo = QComboBox()
    for power in dip.POWERS:
        combo.addItem(FACTIONS_BY_ID[power].name, power)
    combo.setCurrentIndex(list(dip.POWERS).index(who))
    # Deferred, as the desk's partner combo is: the rebuild frees the combo
    # while its popup is still delivering the release that closed it.
    combo.activated.connect(lambda _i, cb=combo, key=item.key: defer(
        lambda: _target(view, key, cb.currentData())))
    h.addWidget(combo, 1)
    p.add(row)
    for act in lob.ACTS:
        told = lob.preview(game, act, who, item.key)
        _act_rows(view, p, act, told, item)


def _target(view, key: str, power: str) -> None:
    view.assembly_targets[key] = power
    view.refresh()


def _act_rows(view, p: Panel, act: str, told: dict, item) -> None:
    power = told.get("power") or item.sponsor
    title = _ACT_NAME[act] + (f" — {_short(power)}" if act != "leak" else "")
    p.add(label(title, "h3", "chloro" if told["ok"] else "dim"))
    if not told["ok"]:
        p.add(label(told["why"], "", "warn", wrap=True))
        return
    swing = ", ".join(f"{_short(w)} {d:+.1f}" for w, d in told["swing"].items())
    cost = []
    if told["credits"]:
        cost.append(cr(-told["credits"]))
    cost += [f"{d:+.1f} standing with {_short(w)}"
             for w, d in told["standing"].items()]
    if told["intel"]:
        cost.append("the " + ("chart" if told["intel"].startswith("chart")
                              else "field note") + " you hold on them")
    p.add_row("Moves", swing)
    p.add_row("Costs", " · ".join(cost) or "nothing", "warn" if cost else "")
    if told["feeling"]:
        p.add_row("And they remember it", ", ".join(
            f"{_short(w)} {d:+.1f}" for w, d in told["feeling"].items()),
            "warn")
    before, after = told["before"], told["after"]
    p.add_row("The count becomes",
              f"{_count(before)} → {_count(after)}",
              "chloro" if after["passes"] != before["passes"] else "")
    p.add_buttons(button(
        _ACT_NAME[act],
        lambda _=False, a=act, w=power, k=item.key: _act(view, a, w, k)))


def _count(told: dict) -> str:
    return (f"{'passes' if told['passes'] else 'fails'} "
            f"{told['yes']}-{told['no']}-{told['abstain']}")


def _act(view, act: str, power: str, key: str) -> None:
    told = lob.lobby(view.game, act, power, key)
    if not told["ok"]:
        view.win.toast(told["why"], "warn")
        return
    view.win.refresh()


def _in_force(game) -> Panel:
    p = Panel("In force")
    live = assembly.in_force(game)
    if not live:
        p.add(note(f"Nothing the Assembly has passed binds anybody today. A "
                   f"passed motion binds for {duration(TERM_DAYS)}."))
        return p
    for act in live:
        p.add(label(f"{vote.title(act)} — passed day {act.passed}, lapses "
                    f"day {act.until}, in {duration(act.until - game.day)}", "",
                    RESOLUTIONS_BY_ID[act.res_id].tint, wrap=True))
        p.add(note("   " + vote.words(act) + "."))
    return p


def _history(game, state) -> Panel | None:
    if not state.history:
        return None
    p = Panel("The last sittings")
    rate = state.tallies.get("all")
    if rate and rate[0]:
        p.add(note(f"{rate[1]} of {rate[0]} motions tabled so far have "
                   "passed."))
    for sitting in reversed(state.history[-4:]):
        p.add(spacer(2), mono_label(
            f"Day {sitting['day']} at {sitting['system']}"
            + (" — you spoke" if sitting.get("present") else "")))
        for r in sitting["results"]:
            said = ", ".join(f"{_short(w)} {v}"
                             for w, v in sorted(r["votes"].items()))
            p.add(label(f"{r['name']} — {'passed' if r['passed'] else 'lost'}"
                        f" ({said})", "", "chloro" if r["passed"] else "dim",
                        wrap=True))
    return p
