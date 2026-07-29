"""Evidence: the four kinds, who names them, and whether the names are real.

`inquiry.add` returns 0.0 for a kind it does not recognise — silently, with no
log line and no exception, which is right for a sim that must survive an old
save and wrong for anybody typing a name by hand.

`test_provisional` typed six by hand: `survey`, `specimen`, `field`, `relic`,
`trade`, `hardware`. Three of those are not evidence kinds and never have
been, so stocking them did nothing at all — and the tuple omitted `reading`,
which is. Six of the ten branch mixes ask for `reading`; cognition asks for
35% of it. So the suite that decides whether any research approach dominates
was measuring every programme in those branches on a bench starved of a
quarter to a third of its input. Measured: cognition unlocks in 165 days on a
full bench and 214 without `reading`, morphogenesis 150 against 180.

`test_bench` has always derived its list from `EVIDENCE`. `test_provisional`
does now.

The claims:

- **Every evidence kind named anywhere in the package is a real one.** The
  general guard, and the one that would have caught this.
- **Every kind a branch mix asks for exists, and turns up in play.**
- **Starving a branch of a kind it wants slows it**, or none of this matters.
- **Every technology is reachable, and every bonus it grants is read.**
"""

from __future__ import annotations

import ast
import pathlib
import re
import statistics

from ..core.state import new_game
from ..data.inquiry import BRANCH_MIX, DEFAULT_MIX, EVIDENCE
from ..data.tech import TECH, TECH_BY_ID
from ..sim import inquiry
from .harness import Suite

KINDS = tuple(e.id for e in EVIDENCE)

#: Calls that take an evidence kind as their second argument. Qualified on
#: purpose: a bare `add(` matched a widget call in `options_view` on the first
#: run, and a guard that cries wolf gets switched off.
CALLS = re.compile(r"\b(?:inquiry|inquiry_sim)\.(?:add|held)\s*\("
                   r"\s*[^,()]+,\s*"
                   r"""(['"])([a-z_]+)\1""")

#: The other door: `sim/actions.py` imports it under its own name.
ALIASED = re.compile(r"\b_add_evidence\s*\(\s*[^,()]+,\s*"
                     r"""(['"])([a-z_]+)\1""")


def _hand_written_lists(text: str):
    """Constants ending in KINDS that are a plain tuple or list of strings.

    A list that names *any* real evidence kind must name only real ones. That
    rule catches `test_provisional`'s hand-typed six — which held `survey`
    beside `field` — and leaves `test_cargo`'s `CARGO_KINDS`, which is about
    contracts and mentions no evidence at all, entirely alone.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if not any(n.upper().endswith("KINDS") for n in names):
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List)):
            continue
        members = [e.value for e in node.value.elts
                   if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if len(members) != len(node.value.elts) or not members:
            continue
        if any(m in KINDS for m in members):
            yield names[0], members


def _sources():
    root = pathlib.Path(__file__).resolve().parent.parent
    for folder in ("sim", "core", "ui", "world", "bridge", "tests"):
        for path in (root / folder).rglob("*.py"):
            yield path


def _unlock_days(branch: str, stock, trials: int = 6, cap: int = 4000):
    """Mean days to finish one programme in `branch`, fed only `stock`."""
    spans = []
    for trial in range(trials):
        game = new_game(f"kb{branch}{trial}")
        target = next((t for t in TECH if t.branch == branch
                       and t.id not in game.research.unlocked), None)
        if target is None:
            return None
        game.research.current = target.id
        game.research.progress = 0.0
        day = 0
        while game.research.current == target.id and day < cap:
            for kind in stock:
                inquiry.add(game.research, kind, 300)
            game.advance_days(30)
            day += 30
            if game.dead or game.victory:
                break
        spans.append(day)
    return statistics.mean(spans)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every evidence kind named anywhere is a kind that exists")
    def _():
        # `tests/` is searched too, and deliberately: the bug this exists for
        # was in a fixture, where a name that does nothing is invisible —
        # the programme simply runs slower and the numbers still look like
        # numbers.
        wrong, checked = [], 0
        for path in _sources():
            text = path.read_text(encoding="utf-8")
            for pattern in (CALLS, ALIASED):
                for _quote, name in pattern.findall(text):
                    checked += 1
                    if name not in KINDS:
                        wrong.append(f"{path.name}: {name!r}")
            # And the hand-written lists, which is where this actually went
            # wrong: the call site passed a variable, so no search of the
            # call sites could ever have seen it.
            for const, members in _hand_written_lists(text):
                checked += len(members)
                for name in members:
                    if name not in KINDS:
                        wrong.append(f"{path.name}:{const} {name!r}")
        assert checked > 15, f"only {checked} call sites found — the search "\
                             "has stopped matching anything"
        assert not wrong, (
            f"{len(wrong)} call(s) name evidence that does not exist, and "
            f"`inquiry.add` swallows them silently: {sorted(set(wrong))[:6]}")
        return (f"{checked} named uses across call sites and hand-written "
                f"lists, every kind real ({', '.join(KINDS)})")

    @check("every kind a branch asks for exists and turns up in play")
    def _():
        wanted = set(DEFAULT_MIX)
        for mix in BRANCH_MIX.values():
            wanted |= set(mix)
        unreal = sorted(k for k in wanted if k not in KINDS)
        assert not unreal, (
            f"branch mixes ask for evidence that does not exist: {unreal}")

        # And a real chronicle produces all of them, or a mix is asking for
        # something no captain can ever bring back.
        from . import chronicle
        held = {k: 0.0 for k in wanted}
        for seed in ("kinds1", "kinds2"):
            game = new_game(seed)
            chronicle.play(game, years=10)
            for kind in wanted:
                held[kind] += inquiry.held(game.research, kind)
        dry = sorted(k for k, v in held.items() if v <= 0)
        assert not dry, (
            f"two decades of play produced none of: {dry} — a programme that "
            "needs it can never finish")
        return " · ".join(f"{k} {held[k]:.0f}" for k in sorted(held))

    @check("starving a branch of a kind it wants slows it down")
    def _():
        # Otherwise the mixes are decoration and the fixture bug cost nothing.
        greedy = max(BRANCH_MIX.items(),
                     key=lambda kv: kv[1].get("reading", 0.0))
        branch, mix = greedy
        assert mix.get("reading", 0) > 0.2, (branch, mix)
        full = _unlock_days(branch, KINDS)
        starved = _unlock_days(branch, [k for k in KINDS if k != "reading"])
        assert full and starved, (full, starved)
        assert starved > full * 1.1, (
            f"{branch} wants {mix['reading']:.0%} `reading` and finishes in "
            f"{starved:.0f} days without it against {full:.0f} with it — the "
            "mix decides nothing")
        # A branch that does not want it must not care either way.
        indifferent = next((b for b, m in BRANCH_MIX.items()
                            if "reading" not in m), None)
        if indifferent:
            same = _unlock_days(indifferent,
                                [k for k in KINDS if k != "reading"])
            base = _unlock_days(indifferent, KINDS)
            assert abs(same - base) < max(1.0, base * 0.05), (
                f"{indifferent} does not ask for `reading` and still ran "
                f"{same:.0f} against {base:.0f} without it")
        return (f"{branch} ({mix['reading']:.0%} reading): {full:.0f} d full, "
                f"{starved:.0f} d starved")

    @check("every technology can actually be reached")
    def _():
        dangling = [(t.id, r) for t in TECH for r in (t.reqs or ())
                    if r not in TECH_BY_ID]
        assert not dangling, (
            f"prerequisites naming a technology that does not exist: "
            f"{dangling}")
        known, moved = set(), True
        while moved:
            moved = False
            for tech in TECH:
                if tech.id in known:
                    continue
                if all(r in known for r in (tech.reqs or ())):
                    known.add(tech.id)
                    moved = True
        stuck = sorted(t.id for t in TECH if t.id not in known)
        assert not stuck, (
            f"{len(stuck)} technologies cannot be reached from a bare "
            f"chronicle: {stuck[:6]}")
        assert len(known) == len(TECH)
        return f"{len(TECH)} technologies, every one reachable"

    @check("every bonus a technology grants is read by something")
    def _():
        granted = {}
        for tech in TECH:
            for key in (tech.bonus or {}):
                granted.setdefault(key, []).append(tech.id)
        assert len(granted) >= 5, sorted(granted)
        blob = "\n".join(p.read_text(encoding="utf-8") for p in _sources()
                         if p.parent.name != "tests")
        dead = sorted(k for k in granted
                      if f'"{k}"' not in blob and f"'{k}'" not in blob)
        assert not dead, (
            f"technologies grant bonuses nothing reads: "
            + ", ".join(f"{k} (from {granted[k][0]})" for k in dead))
        return f"{len(granted)} bonus keys, every one consumed"
