"""The Academy: the whole curriculum, and a way into any part of it.

The tutorial is twenty-nine lessons in ten courses, and a curriculum you can
only take from the beginning is one most players abandon at lesson three. This
is the page that makes it a *menu*: every chapter, what it teaches, how much
of it you have done, and a button that starts the tutorial there.

It holds no rules. Progress is `tutorial.progress`, jumping is
`tutorial.jump_to`, and the ticks are read from the same step counter the bar
along the top reads — so the page and the bar cannot disagree about where a
captain has got to.
"""

from __future__ import annotations

from ..data.lessons import chapter_of
from ..sim import tutorial as tutorial_sim
from .widgets import Panel, button, label, note, spacer


def build(view) -> None:
    """Draw the Academy onto a `View`'s column."""
    game = view.game
    standing = tutorial_sim.state(game)
    rows = tutorial_sim.progress(game)
    done = sum(r["done"] for r in rows)
    total = sum(r["of"] for r in rows)

    head = Panel("The Academy")
    head.add(note(
        "Twenty-nine things to do, in ten short courses. Every one is watched "
        "in the world rather than taken on trust: a lesson finishes when you "
        "have actually done the thing, and it will wait as long as you like. "
        "Nothing here is a cage — the tutorial never blocks a screen, and you "
        "can leave it running while you play."))
    head.add_row("Done so far", f"{done} of {total} lessons")
    if standing.get("running"):
        lesson = standing["lesson"]
        chapter = chapter_of(lesson)
        head.add_row("Open now",
                     f"{lesson.title} — {chapter.title if chapter else ''}")
    head.add_buttons(
        button("Start from the beginning",
               lambda: _jump(view, tutorial_sim.CHAPTERS[0].id),
               kind="primary"),
        *([button("Put it away", lambda: _stop(view), kind="flat")]
          if standing.get("running") else []))
    view.col.addWidget(head)

    for row in rows:
        chapter = row["chapter"]
        panel = Panel(f"{chapter.title}  ·  {row['done']}/{row['of']}")
        panel.add(note(chapter.blurb))
        if chapter.teaches:
            panel.add_row("By the end", chapter.teaches)
        for index, lesson in enumerate(row["lessons"]):
            got = index < row["done"]
            here = row["here"] and index == row["done"]
            mark = "✓" if got else ("▶" if here else "·")
            panel.add_row(f"{mark}  {lesson.title}", lesson.ask,
                          "chloro" if got else ("lumen" if here else ""))
        panel.add_buttons(button(
            "Teach me this" if not row["here"] else "Back to this one",
            lambda _=False, cid=chapter.id: _jump(view, cid), kind="flat"))
        view.col.addWidget(panel)
    view.col.addWidget(spacer(6))
    view.col.addWidget(label(
        "A course you can already fly is stepped over rather than re-taught: "
        "the tutorial reads what your chronicle can vouch for.", "note"))


def _jump(view, chapter_id: str) -> None:
    tutorial_sim.jump_to(view.game, chapter_id)
    lesson = tutorial_sim.current(view.game)
    view.win.toast(f"Academy: {lesson.title}." if lesson is not None
                   else "That course is already behind you.")
    view.win.refresh()


def _stop(view) -> None:
    tutorial_sim.skip(view.game)
    view.win.refresh()
