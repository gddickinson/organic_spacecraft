"""Renown: milestones read from the chronicle, the ranks they climb, the
perks each rank carries, and the ending tracks.

The endings were all-or-nothing, and twenty honest three-year careers
reached none of them. This is the ladder in between. A milestone
(`data/milestones`, `data/milestone_tracks`) fires the first day its fact
(`sim/renown_facts`) reaches its mark, **once**, from the clock — so it
cannot be granted twice, and it cannot be earned by looking at a screen.
It pays renown and, sometimes, a reward out of a named power's purse;
renown climbs the ranks; each rank's perk is read at one line by the
system it names (`perk`).

**One door for a reward.** `reward_terms` prices it — what the payer's
purse can cover today, the standing, the bench work, the title — and the
Voyage screen, the moment's log line and the act all read that one dict.

This module imports no other `sim/` module at load time (they are fetched
inside the functions), so `sim/threat` and `sim/actions` can import it to
count what they do (`note`) without a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.milestones import (CAREER, PERKS, RANKS, STANDING_FLOOR,
                               TOPICS)
from ..data.milestone_tracks import TRACK_ORDER, TRACKS

ALL = CAREER + TRACKS
BY_ID = {m.id: m for m in ALL}

#: A chronicle this many days old when renown first reads it was played
#: before renown existed: what it had already done is credited — the renown,
#: not the purse, which never promised it — in one quiet line.
BACKDATE_AFTER = 30

#: Who signs a milestone's despatch.
REGISTRY = ("registry", "The Registry of Captains")


@register
@dataclass
class RenownState:
    #: Milestone id -> the day it fired. Never shrinks.
    achieved: dict = field(default_factory=dict)
    score: int = 0
    #: [rank id, day] for every rank reached, the first included.
    ranks: list = field(default_factory=list)
    #: Acts that leave no state behind, counted by `note`.
    counts: dict = field(default_factory=dict)
    titles: list = field(default_factory=list)
    #: Milestone id -> what was actually paid, as `reward_terms` said.
    paid: dict = field(default_factory=dict)
    #: Fired since the captain last opened the Voyage (the HUD chip).
    fresh: list = field(default_factory=list)
    #: The day renown first read this chronicle.
    since: int = 0
    #: The Assembly perk: {"res": id, "day": chosen, "used": day spent}.
    motion: dict = field(default_factory=dict)
    #: The Legend perk: {"system": id, "was": old name, "day": d}.
    named: dict = field(default_factory=dict)
    #: The first officer's counsel, dismissed until this day.
    quiet_until: int = -1
    #: The ending the captain has chosen to follow ("" = the leading one).
    course: str = ""
    #: The career written up at its end (`sim/memoir.compose`). Its `key`
    #: is this chronicle's name in the Hall, so a later ending (an epoch
    #: lived through, then a death) rewrites the entry rather than adding one.
    memoir: dict = field(default_factory=dict)


def state(game) -> RenownState | None:
    return getattr(game, "renown", None)


def ensure(game) -> RenownState:
    """Created on first use, so a chronicle from before renown loads."""
    st = state(game)
    if st is None:
        st = game.renown = RenownState(since=int(game.day),
                                       ranks=[[RANKS[0][0], int(game.day)]])
    return st


def note(game, key: str, amount: int = 1) -> None:
    """Count an act that leaves nothing behind to read — a Bloom system
    burned clean, a dive under the ice. Called by the act, never a screen."""
    st = ensure(game)
    st.counts[key] = st.counts.get(key, 0) + amount


# ── ranks and perks ────────────────────────────────────────────────────────

def rank_index(score: float) -> int:
    return max(i for i, (_rid, _n, need) in enumerate(RANKS) if score >= need)


def rank(game) -> dict:
    """The rank held, and how far to the next."""
    st = state(game)
    score = st.score if st else 0
    i = rank_index(score)
    rid, name, need = RANKS[i]
    nxt = RANKS[i + 1] if i + 1 < len(RANKS) else None
    span = (nxt[2] - need) if nxt else 1
    return {"id": rid, "name": name, "score": score, "index": i,
            "next": nxt[1] if nxt else "", "next_at": nxt[2] if nxt else None,
            "share": min(1.0, (score - need) / span) if nxt else 1.0}


def perks(game) -> list[str]:
    """The perk keys the captain's rank carries."""
    held = rank(game)["index"]
    order = [rid for rid, _n, _need in RANKS]
    return [key for key, (rid, _name, _words) in PERKS.items()
            if order.index(rid) <= held]


def perk(game, key: str) -> bool:
    """The one door every perk is read through."""
    if key not in PERKS:
        raise KeyError(f"no perk called {key!r}")
    return key in perks(game)


# ── rewards ────────────────────────────────────────────────────────────────

def reward_terms(game, milestone) -> dict:
    """What this milestone would pay today — the one price everything reads.

    Credits come out of the payer's purse, and a purse pays what it holds:
    `short` is what it could not cover (`sim/hunts.pay`, the same rule a
    bounty is paid by)."""
    from . import diplomacy, exchequer
    out = {"credits": 0, "payer": "", "short": 0, "standing": {},
           "research": 0, "title": "", "words": ""}
    r = milestone.reward
    if r is None:
        return out
    words = []
    if r.credits and r.payer:
        held = max(0.0, exchequer.purse(game, r.payer).credits)
        pay = int(min(r.credits, held))
        out.update(credits=pay, payer=r.payer, short=r.credits - pay)
        whose = _short(r.payer)
        whose += "'" if whose.endswith("s") else "'s"
        words.append(f"₡{pay:,} from the {whose} purse"
                     + (f" (₡{r.credits - pay:,} it cannot find)"
                        if pay < r.credits else ""))
    for power, delta in r.standing.items():
        for p in (diplomacy.POWERS if power == "*" else (power,)):
            out["standing"][p] = out["standing"].get(p, 0) + delta
    if out["standing"]:
        if "*" in r.standing:
            words.append(f"{r.standing['*']:+g} with all four powers")
        words += [f"{_short(p)} {d:+g}" for p, d in r.standing.items()
                  if p != "*"]
    if r.research:
        out["research"] = r.research
        words.append(f"+{r.research} research")
    if r.title:
        out["title"] = r.title
        words.append(f"the title «{r.title}»")
    out["words"] = " · ".join(words)
    return out


def _short(power: str) -> str:
    from ..data.factions import FACTIONS_BY_ID
    f = FACTIONS_BY_ID.get(power)
    return f.short if f else power


def _grant(game, st, milestone) -> dict:
    """Pay exactly what `reward_terms` says. Returns it, as paid."""
    from . import hunts, research as research_sim
    terms = reward_terms(game, milestone)
    if terms["credits"]:
        terms["credits"] = int(hunts.pay(game, terms["payer"],
                                         terms["credits"]))
    for power, delta in terms["standing"].items():
        game.adjust_rep(power, delta)
    if terms["research"]:
        research_sim.grant(game.research, terms["research"])
    if terms["title"] and terms["title"] not in st.titles:
        st.titles.append(terms["title"])
    return terms


# ── the check ──────────────────────────────────────────────────────────────

def met(values: dict, milestone) -> bool:
    return all(values[f] >= at for f, at in
               ((milestone.fact, milestone.at),) + milestone.also)


def _values(game, wanted) -> dict:
    """Each fact the unreached milestones ask for, computed once."""
    from . import renown_facts
    return {key: renown_facts.fact(game, key) for key in wanted}


def check(game) -> list[tuple[str, str]]:
    """Fire every milestone whose fact has reached its mark. Returns the
    moment's log lines; `tick` writes them."""
    st = ensure(game)
    todo = [m for m in ALL if m.id not in st.achieved]
    if not todo:
        return []
    wanted = {m.fact for m in todo} | {f for m in todo for f, _at in m.also}
    values = _values(game, wanted)
    fired = [m for m in todo if met(values, m)]
    if not fired:
        return []
    day = int(game.day)
    backdated = (not st.achieved and game.day - st.since <= 0
                 and st.since >= BACKDATE_AFTER)
    out: list[tuple[str, str]] = []
    before = rank_index(st.score)
    for m in fired:
        st.achieved[m.id] = day
        st.score += m.renown
        if backdated:
            continue
        st.fresh.append(m.id)
        paid = _grant(game, st, m)
        if m.reward is not None:
            st.paid[m.id] = paid
        line = f"Milestone — {m.name}. {m.text}"
        if m.renown:
            line += f" (+{m.renown} renown)"
        out.append(("good" if m.renown else "warn", line))
        if paid["words"]:
            out.append(("good", f"Paid: {paid['words']}."))
    after = rank_index(st.score)
    for i in range(before + 1, after + 1):
        rid, name, _need = RANKS[i]
        st.ranks.append([rid, day])
        gains = [p[1] for p in PERKS.values() if p[0] == rid]
        if not backdated:
            out.append(("good", f"Promoted: {name}."
                        + (f" {'; '.join(gains)}." if gains else "")))
    if backdated:
        out.append(("", f"The Registry of Captains has read your record: "
                        f"{len(fired)} milestones already behind you, "
                        f"{st.score} renown — {RANKS[after][1]}."))
    if not backdated:
        _despatch(game, fired, after > before)
    return out


def _despatch(game, fired, promoted: bool) -> None:
    from . import comms
    heads = [m for m in fired if m.renown]
    if not heads:
        return
    subject = (f"Promoted: {rank(game)['name']}" if promoted
               else f"On the record: {heads[0].name}"
               + (f" and {len(heads) - 1} more" if len(heads) > 1 else ""))
    body = "\n".join(f"{m.name} (+{m.renown}): {m.text}" for m in heads)
    comms.send(game, REGISTRY[0], REGISTRY[1], "news", subject, body)


def tick(game) -> None:
    """The daily check, and the standing floor the Admiral's perk holds.
    One line in `core/sectortime.reckoning`; logs itself."""
    if getattr(game, "dead", False):
        return
    for kind, text in check(game):
        game.add_log(text, kind)
    if perk(game, "floor"):
        hold(game)


def hold(game) -> None:
    """No power's standing below Neutral, for an Admiral of the Verge."""
    from . import diplomacy
    for power in diplomacy.POWERS:
        have = game.rep.get(power, 0.0)
        if have < STANDING_FLOOR:
            game.adjust_rep(power, STANDING_FLOOR - have)


def seen(game) -> None:
    """The captain has looked at the Voyage: the HUD chip stops counting."""
    st = state(game)
    if st is not None:
        st.fresh.clear()


def dismiss_counsel(game, days: int = 30) -> None:
    """The first officer keeps quiet for a month (the menu brings it back)."""
    ensure(game).quiet_until = int(game.day) + int(days)


def counsel_quiet(game) -> bool:
    st = state(game)
    return st is not None and game.day < st.quiet_until


def recall_counsel(game) -> None:
    st = state(game)
    if st is not None:
        st.quiet_until = -1


# ── the ending tracks ──────────────────────────────────────────────────────

def ladder(game, track: str) -> list[dict]:
    """One ending's three rungs: done or not, and how far the next has got."""
    st = state(game)
    rows = []
    steps = sorted((m for m in TRACKS if m.track == track),
                   key=lambda m: m.step)
    values = _values(game, {f for m in steps
                            for f, _at in ((m.fact, m.at),) + m.also})
    for m in steps:
        share = min(values[f] / at if at else 1.0
                    for f, at in ((m.fact, m.at),) + m.also)
        rows.append({"milestone": m, "day": st.achieved.get(m.id)
                     if st else None, "share": max(0.0, min(1.0, share)),
                     "value": values[m.fact],
                     "terms": reward_terms(game, m)})
    return rows


def tracks(game) -> dict:
    """Every ending's ladder, in the endings' own order."""
    return {t: ladder(game, t) for t in TRACK_ORDER}


def leading(game) -> str | None:
    """The ending track furthest along — steps done, then the next step's
    share. Ruin is never "leading": it is the one you are losing."""
    best = None
    for t, rows in tracks(game).items():
        if t == "ruin":
            continue
        done = sum(1 for r in rows if r["day"] is not None)
        nxt = next((r for r in rows if r["day"] is None), None)
        key = (done, nxt["share"] if nxt else 1.0)
        if best is None or key > best[0]:
            best = (key, t)
    return best[1] if best else None


def follow(game, track: str) -> dict:
    """Set the road counsel steers by; "" goes back to the leading one."""
    if track and track not in TRACK_ORDER:
        return {"ok": False, "why": "No such ending."}
    if track == "ruin":
        return {"ok": False, "why": "Nobody sets a course for Ruin."}
    ensure(game).course = track
    return {"ok": True, "why": ""}


def focus(game) -> str | None:
    """The road counsel steers by: the one chosen, else the leading one."""
    st = state(game)
    return (st.course if st and st.course else None) or leading(game)


def next_step(game, track: str) -> dict | None:
    """The next unreached rung on a track, as `ladder` shows it."""
    return next((r for r in ladder(game, track) if r["day"] is None), None)


def recent(game, limit: int = 8) -> list[tuple]:
    """(milestone, day), newest first."""
    st = state(game)
    if st is None:
        return []
    rows = sorted(st.achieved.items(), key=lambda kv: -kv[1])
    return [(BY_ID[mid], day) for mid, day in rows[:limit] if mid in BY_ID]


def by_topic(game) -> dict:
    """{topic label: (done, total)} over the career milestones."""
    st = state(game)
    out: dict = {}
    for m in CAREER:
        label = TOPICS.get(m.topic, m.topic)
        done, total = out.get(label, (0, 0))
        out[label] = (done + (1 if st and m.id in st.achieved else 0),
                      total + 1)
    return out
