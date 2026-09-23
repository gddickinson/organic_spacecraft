"""What the chronicle has done to somebody since they signed on.

Split out of `sim/lifepath.py` when that crossed five hundred lines, along
the seam its own docstring already draws: a *service record* is the career
that made somebody, derived from their id and the sector's seed and stored
nowhere; these three are the facts the chronicle has added on top of it
afterwards, and they live on the save.

They are folded onto the record at the one place it is built, rather than at
the twenty places that read one — which is the only arrangement in which a
cortex link fitted at a concourse is worth anything at all.
"""

from __future__ import annotations

from ..data import careers as table
from . import lifespan


def bought(game, record, officer) -> None:
    """Fold on what a concourse has done to them since they signed on.

    A service record is *derived* and may be recomputed at will; a fitted
    cortex link and a course somebody paid for are **facts**, and they live
    on the save (`sim/clinic.py`, `game.fitted` and `game.taught`). Folding
    them on here rather than at the twenty places that read a record is what
    makes a muscle weave show up in the gunnery check, the boarding action,
    the ship's abilities table and the officer's own sheet at once.

    Nothing is taken away and nothing goes past `SCORE_CAP`: a treatment is
    a floor under a characteristic, never a replacement for a life.
    """
    if game is None:
        return
    from ..data import treatments as clinic_table
    key = str(getattr(officer, "id", 0))
    for tid in (getattr(game, "fitted", None) or {}).get(key, []):
        got = clinic_table.TREATMENT_BY_ID.get(tid)
        if got is None:
            continue
        for cid, delta in got.gives.items():
            if cid in record.characteristics:
                record.characteristics[cid] = min(
                    clinic_table.SCORE_CAP,
                    record.characteristics[cid] + delta)
        if got.skill:
            record.skills[got.skill] = max(record.skills.get(got.skill, -1), 0)
    for name, levels in (getattr(game, "taught", None) or {}).get(
            key, {}).items():
        if name in table.SKILLS:
            record.skills[name] = record.skills.get(name, -1) + int(levels)


def staged(game, record, officer) -> None:
    """Fold on where they are in their run, and how far apart their clocks are.

    `data/stages.py` is what a stretch of life is worth — the green are
    quick and unlistened-to, the declining slow and worth hearing — and what
    decades lived beyond the body's years do to somebody. Both are deltas on
    the six scores, kept between 1 and the clinic's cap like everything else
    folded on here.
    """
    from ..data import treatments as clinic_table
    for got in (lifespan.stage_of(officer, game).gives,
                lifespan.gap_of(officer, game).gives):
        for cid, delta in got.items():
            if cid in record.characteristics:
                record.characteristics[cid] = max(1, min(
                    clinic_table.SCORE_CAP,
                    record.characteristics[cid] + delta))


def qualify(record, officer) -> None:
    """Make sure they can do the job the crew list says they do.

    A career is only *weighted* towards a station, so the dice could leave a
    Chief Engineer who had never touched a drive and a Navigator who could
    not plot — which reads as a broken crew list rather than as an unlucky
    life. Their station's own skill is brought up to what their level claims
    and the one beside it to trained, and **nothing is ever taken away**: an
    engineer who really did spend four terms learning it keeps all of it.
    """
    pair = table.STATION_SKILLS.get(record.station or "", ())
    if not pair:
        return
    want = max(1, min(4, int(getattr(officer, "level", 1) or 1) - 1))
    record.skills[pair[0]] = max(record.skills.get(pair[0], -1), want)
    # A station may name more than two: the first is brought to what their
    # level claims, and everything beside it to trained.
    for beside in pair[1:]:
        record.skills[beside] = max(record.skills.get(beside, -1), 0)
