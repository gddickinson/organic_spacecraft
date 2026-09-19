"""The Voyage: the rank and the next, the ten ending tracks as ladders, the
milestones lately reached, and the perks a rank carries.

A tab on Holdings (`ui/empire_view`), where the ending bars used to sit.
Presentation only: every number is `sim/renown`'s — the ladders read
`renown.ladder`, every reward is `renown.reward_terms`' words, and the two
perks that are acts (a motion, a name) go through `sim/renown_perks`, which
logs itself.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from ..core.util import num
from ..data.lore import VICTORIES
from ..data.milestones import PERKS
from ..sim import renown
from ..sim import renown_perks
from ..sim import threat as threat_sim
from . import renown_chip
from .flow import Flow
from .widgets import Panel, Pill, button, label, note, spacer

#: The ending's name and tint, from the endings' own table.
_ENDINGS = {vid: (name, tint, goal) for vid, name, tint, goal, _b in VICTORIES}


def build(view) -> None:
    """Draw the Voyage into the Holdings view's column."""
    g = view.game
    renown.ensure(g)
    renown.seen(g)                  # the chip stops counting
    renown_chip.sync(view.win)
    view.row(_rank(view, g), _perks(view, g))
    view.col.addWidget(_tracks(view, g))
    view.col.addWidget(_recent(g))


def _rank(view, g) -> Panel:
    held = renown.rank(g)
    st = renown.state(g)
    p = Panel("Renown", "chloro")
    p.add(label(held["name"], "h2", "chloro"))
    if st.titles:
        p.add(note("Called " + ", ".join(f"«{t}»" for t in st.titles) + "."))
    p.add_row("Renown", num(held["score"]))
    if held["next"]:
        p.add_row(f"To {held['next']}", f"{num(held['next_at'] - held['score'])}"
                  " more")
        p.add_bar(held["share"], "chloro")
    else:
        p.add(note("The top of the ladder. There is nowhere further to climb."))
    done = sum(1 for m in renown.ALL if m.id in st.achieved)
    p.add_row("Milestones", f"{done} of {len(renown.ALL)}")
    for topic, (have, total) in renown.by_topic(g).items():
        p.add_row(topic, f"{have}/{total}", "chloro" if have else "dim")
    return p


def _perks(view, g) -> Panel:
    p = Panel("What your rank carries")
    held = set(renown.perks(g))
    for key, (rid, name, words) in PERKS.items():
        rank_name = next(n for r, n, _need in renown.RANKS if r == rid)
        p.add(label(name, "h3", "chloro" if key in held else "dim"))
        p.add(note(f"{rank_name}. {words}"))
    if "table" in held:
        p.add(spacer(4))
        p.add(_motion(view, g))
    if "name" in held:
        p.add(spacer(4))
        p.add(_naming(view, g))
    return p


def _motion(view, g) -> QWidget:
    terms = renown_perks.table_terms(g)
    if not terms["ok"]:
        return note(terms["why"])
    from ..sim import assembly_vote as vote
    box = QComboBox()
    box.setObjectName("voyage_motion")
    for item in terms["options"]:
        box.addItem(vote.title(item), item.key)
    return _picker(box, "Table it", lambda: _act(
        view, renown_perks.table(g, box.currentData())))


def _naming(view, g) -> QWidget:
    st = renown.state(g)
    if st.named:
        return note(f"{st.named['was']} is {st.named['now']} on every chart.")
    box = QComboBox()
    box.setObjectName("voyage_name")
    for s in g.galaxy.systems:
        if s.visited:
            box.addItem(s.name, s.id)
    return _picker(box, f"Name it {renown_perks.name_of(g)}", lambda: _act(
        view, renown_perks.name_system(g, box.currentData())))


def _picker(box, text: str, go) -> QWidget:
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(box, 1)
    h.addWidget(button(text, go, kind="primary"))
    return row


def _act(view, out: dict) -> None:
    if not out.get("ok"):
        view.win.toast(out.get("why", "No."), "warn")
    view.win.refresh()


def _tracks(view, g) -> Panel:
    """Ten ladders. The bar under each is the ending's own measure (fogged
    as the chart is fogged); the rungs are the three milestones. "Follow"
    sets the road the first officer's counsel steers by."""
    p = Panel("The ten endings")
    p.add(note("Three rungs on each, and every rung pays toward the next. "
               "The bar is the ending itself; you do not have to pick one — "
               "follow one, and the first officer steers by it."))
    progress = threat_sim.victory_progress(g, seen_only=True)
    ladders = renown.tracks(g)
    lead = renown.leading(g)
    course = renown.state(g).course
    for tid, rows in ladders.items():
        name, tint, goal = _ENDINGS[tid]
        have, need, done = progress[tid]
        p.add(spacer(6))
        head = QWidget()
        h = QHBoxLayout(head)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(8)
        h.addWidget(label(name, "h3", tint))
        if done:
            h.addWidget(Pill("achieved", "chloro"))
        elif tid == course:
            h.addWidget(Pill("following", "chloro"))
        elif tid == lead:
            h.addWidget(Pill("furthest along", "lumen"))
        h.addStretch(1)
        h.addWidget(label(f"{num(have)}/{num(need)}", "dim"))
        if tid != "ruin" and not done:
            follow = button("Stop following" if tid == course else "Follow",
                            lambda _=False, t=tid: _act(view, renown.follow(
                                g, "" if t == course else t)), kind="flat")
            follow.setObjectName(f"follow:{tid}")
            h.addWidget(follow)
        p.add(head)
        p.add(note(goal))
        p.add_bar(have / need if need else 0, tint)
        p.add(_rungs(rows))
        nxt = next((r for r in rows if r["day"] is None), None)
        if nxt is not None:
            m = nxt["milestone"]
            said = f"Next: {m.name} — {m.feeds}, {nxt['share']:.0%} of the way."
            if nxt["terms"]["words"]:
                said += f" Pays {nxt['terms']['words']}."
            p.add(label(said, "", "dim", wrap=True))
    return p


def _rungs(rows) -> QWidget:
    """The three rungs, wrapping at a narrow window (`ui/flow`)."""
    pills = []
    for row in rows:
        m = row["milestone"]
        mark = "●" if row["day"] is not None else "○"
        pill = Pill(f"{mark} {m.name}",
                    "chloro" if row["day"] is not None else "dim")
        pill.setToolTip(m.text + (f" Reached on day {row['day']}."
                                  if row["day"] is not None else ""))
        pills.append(pill)
    return Flow(pills)


def _recent(g) -> Panel:
    p = Panel("Lately")
    rows = renown.recent(g, 8)
    if not rows:
        p.add(note("Nothing on the record yet. Survey something, sell "
                   "something, go somewhere: the Registry is watching."))
        return p
    for m, day in rows:
        p.add_row(f"Day {day} · {m.name}",
                  f"+{m.renown}" if m.renown else "—",
                  "chloro" if m.renown else "warn")
        paid = renown.state(g).paid.get(m.id)
        if paid and paid.get("words"):
            p.add(note(f"Paid {paid['words']}."))
    return p
