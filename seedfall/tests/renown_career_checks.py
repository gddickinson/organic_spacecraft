"""The career half of `test_renown` (split at the length rule): the careful
captain's ending, the first rungs' timing, the memoir and the Hall, and a
chronicle carried across processes.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

from ..core import save as save_mod
from ..core.state import new_game
from ..sim import memoir, renown
from . import careful_captain as cc
from . import renown_kit as kit
from .harness import Suite

#: The seed the ending is pinned on — measured, it reaches Genesis on day
#: 1,234 with the rewards and not at all in five years without them.
ENDING_SEED = "s1"

_READ = r'''
import json, sys
from seedfall.core.state import load_game
from seedfall.sim import memoir, renown
g = load_game()
st = renown.state(g) if g is not None else None
print(json.dumps({"hall": [r["key"] for r in memoir.hall()],
                  "achieved": dict(st.achieved) if st else None,
                  "score": st.score if st else None,
                  "counts": dict(st.counts) if st else None,
                  "course": st.course if st else None}))
'''


def _fresh_process(save_path) -> dict:
    env = dict(os.environ, **{save_mod.SAVE_ENV: str(save_path)})
    root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    out = subprocess.run([sys.executable, "-c", _READ], capture_output=True,
                         text=True, env=env, timeout=120)
    assert out.returncode == 0, out.stderr[-600:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _career(seed: str, days: int, rewards: bool = True):
    real = renown.reward_terms
    if not rewards:
        renown.reward_terms = lambda g, m: dict(
            real(g, m), credits=0, standing={}, research=0, title="",
            words="", payer="")
    try:
        g = new_game(seed)
        rng = cc.RNG(f"careful-{seed}")
        plan: dict = {}
        renown.follow(g, "genesis")
        while g.day < days and not g.dead and not g.victory:
            day = g.day
            cc.turn(g, rng, plan)
            if g.day == day:
                g.advance_days(1)
        return g
    finally:
        renown.reward_terms = real


def run(suite: Suite) -> None:
    check = suite.check

    @check("the careful captain reaches an ending in five years, and "
           "without the rewards does not")
    def _():
        with kit.hall_folder():
            g = _career(ENDING_SEED, 5 * 365)
            assert g.victory == "genesis" and not g.dead, (
                f"day {g.day}: {g.victory} dead={g.dead}")
            assert g.day <= 5 * 365
            paid = renown.state(g).paid
            assert {"gen_1", "gen_2", "gen_3"} <= set(paid)
            bare = _career(ENDING_SEED, 5 * 365, rewards=False)
            assert bare.victory is None, (
                f"withheld, the rewards still reached {bare.victory} on "
                f"day {bare.day}: the check would not see them matter")
            page = memoir.page_of(g)
            assert page and page["ending"] == "Genesis"
        return (f"{ENDING_SEED}: Genesis on day {g.day} "
                f"({renown.rank(g)['name']}, {renown.state(g).score} renown); "
                f"without rewards none by day {bare.day}")

    @check("the first milestone comes in days, the first rank in a season")
    def _():
        firsts, ranks = [], []
        for seed in ("s1", "s2", "s3"):
            g = _career(seed, 100)
            st = renown.state(g)
            assert st.achieved, f"{seed}: nothing in 100 days"
            firsts.append(min(st.achieved.values()))
            up = [day for rid, day in st.ranks if rid == "captain"]
            assert up, f"{seed}: still a Master on day {g.day}"
            ranks.append(up[0])
        assert max(firsts) <= 10, firsts
        assert max(ranks) <= 90, ranks
        return f"first milestone on days {firsts}; Captain on days {ranks}"

    @check("the memoir is written at an ending and at a death, into the Hall")
    def _():
        with kit.hall_folder() as where:
            win = new_game("memoir-win")
            renown.note(win, "battle:destroyed")
            win.flags["contact_made"] = True
            win.research.unlocked.append("firstcontact")
            win.advance_days(1)
            assert win.victory == "genesis"
            page = memoir.page_of(win)
            assert page and page["outcome"] == "triumph"
            assert any("Genesis" in line for line in page["lines"])
            lost = new_game("memoir-lost")
            lost.die("Taken apart by a raider off Wick Deep.")
            page = memoir.page_of(lost)
            assert page and page["ending"] == "Lost"
            assert "raider off Wick Deep" in " ".join(page["lines"])
            hall = memoir.hall()
            assert [r["seed"] for r in hall] == ["memoir-lost", "memoir-win"]
            assert memoir.hall_path() == where / memoir.HALL_NAME
            # Written once: a second look at the same ending adds nothing.
            memoir.record(lost)
            assert len(memoir.hall()) == 2
        return (f"triumph and loss both written; the Hall holds "
                f"{len(hall)}, newest first")

    @check("the Hall outlasts a new chronicle and the process")
    def _():
        from ..core.state import clear_save
        with kit.hall_folder() as where:
            g = new_game("hall-keep")
            g.save()
            g.die("Lost in the Hollow.")
            key = memoir.page_of(g)["key"]
            clear_save()                         # what "New" does
            fresh = new_game("hall-next")
            fresh.save()
            assert key in [r["key"] for r in memoir.hall()]
            seen = _fresh_process(where / save_mod.SAVE_NAME)
            assert key in seen["hall"], seen
        return "kept across New and read back by a fresh process"

    @check("a chronicle carries its renown across a process")
    def _():
        with kit.hall_folder() as where:
            g = _career("s2", 240)
            st = renown.state(g)
            renown.follow(g, "lineage")
            assert st.achieved and st.counts
            assert g.save()
            seen = _fresh_process(where / save_mod.SAVE_NAME)
            assert seen["achieved"] == dict(st.achieved)
            assert seen["score"] == st.score and seen["course"] == "lineage"
            assert seen["counts"] == dict(st.counts)
        return (f"{len(st.achieved)} milestones, {st.score} renown and the "
                "chosen road read back in a fresh process")

    @check("an old chronicle is credited what it did, and paid nothing")
    def _():
        g = _career("s3", 400)
        before = renown.state(g)
        assert before.achieved
        credits = g.credits
        purses = {p: pu.credits for p, pu in g.exchequer.purses.items()}
        g.renown = None                       # a save from before renown
        out = renown.check(g)
        st = renown.state(g)
        # What the old save kept, it is credited; acts it never counted
        # (`renown_facts.COUNTED`) wait for the next time they are done.
        from ..sim.renown_facts import COUNTED
        kept = {mid for mid in before.achieved
                if renown.BY_ID[mid].fact not in COUNTED}
        assert kept and set(st.achieved) >= kept, kept - set(st.achieved)
        assert not st.paid and not st.fresh, "backdated milestones paid"
        assert g.credits == credits
        assert {p: pu.credits for p, pu in g.exchequer.purses.items()} == \
            purses
        assert len(out) <= 2 and "already behind you" in out[0][1], out
        return f"{len(st.achieved)} credited in one line: {out[0][1][:80]}"
