"""Officer arcs: every story can be lived, every answer does what it says.

What the suite holds `sim/arcs` to, each performed rather than asserted:

- every one of the twelve stories is seen through by a captain who engages,
  from each officer of the opening bridge, and leaves its signature;
- each kind of trigger sets a beat off — a date, a place, their trust, a
  fight, a burn, a holding — and nothing before its condition;
- every answer of every beat does exactly what its preview said, and one
  the ship cannot pay for is refused and changes nothing;
- a lapse costs what `data/arcs` says, and a neglected last beat walks an
  officer out through `loyalty.tick` and nowhere else;
- every signature moves its number (`arc_probes`), and nothing without it;
- dealing is the officer's own key, and looking changes nothing;
- a story past an unopened rim waits and does not lapse;
- ignoring every story costs some loyalty, and nobody walks out over it.

The screens and a save crossing processes are `arcs_screens`, run here.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import arcs as data
from ..data.arcs import ARCS, SIGNATURES
from ..data.convictions import WALKOUT
from ..sim import arcs as arcs_sim
from ..sim import comms as comms_sim
from ..sim import loyalty as loyalty_sim
from . import arc_captain as cap
from . import arc_probes, arcs_screens
from .harness import Suite


def _held(game) -> dict:
    """Everything an answer can move, as numbers."""
    from ..sim import exchequer, stores
    return {"credits": game.credits, "rep": dict(game.rep),
            "goods": {c: stores.held(game, c) for c in
                      ("volatiles", "biomass", "alloy")},
            "loyalty": {o.id: o.loyalty for o in game.officers},
            "purses": {p: exchequer.purse(game, p).credits
                       for p in ("charter", "concordat", "freeholds")}}


def run(suite: Suite) -> None:
    check = suite.check

    @check("every story is seen through, from any officer, by a captain "
           "who engages")
    def _():
        told, longest = [], 0
        for arc in ARCS:
            for index in range(3):
                game = cap.chronicle(f"arcs-all-{arc.id}-{index}")
                officer = game.officers[index]
                cap.deal(game, officer, arc.id)
                end = cap.see_through(game, officer)
                assert officer.signature == arc.signature, (
                    f"{arc.id} from the {officer.role}: beat "
                    f"{officer.arc_beat}, {officer.arc_state}")
                assert all(officer.arc_state["chose"]), (
                    f"{arc.id}: a beat lapsed under an engaged captain")
                if arc.id == "cartographer":
                    from ..world import regions as world_regions
                    hollow = {s.id for s in world_regions.systems_of(
                        game.galaxy, "hollow")}
                    assert hollow <= set(game.charts), "no free chart"
                told.append(arc.id)
                longest = max(longest, end)
        assert len(told) == 36, told
        assert longest < 3 * 365, f"a story took {longest} days"
        return (f"12 stories × 3 officers, all told with their signature; "
                f"the longest ended on day {longest}")

    @check("each kind of trigger sets a beat off, and nothing before it")
    def _():
        from . import nemesis_kit as kit
        kinds = [("date", "old_debts", 2, lambda g, o: None),
                 ("place", "old_debts", 1, None),
                 ("loyalty", "defector", 2,
                  lambda g, o: setattr(o, "loyalty", data.LOYAL_AT)),
                 ("fight", "deserter", 2, lambda g, o: kit.ended(
                     g, kit.plain_fight(g, "bloom", "arcs-trig"),
                     "destroyed")),
                 ("burn", "last_signal", 2, lambda g, o: cap.burn(g)),
                 ("colony", "grower", 2, lambda g, o: cap.plant(g))]
        said = []
        for kind, arc_id, index, act in kinds:
            game = cap.chronicle(f"arcs-trigger-{kind}")
            officer = game.officers[1]
            cap.deal(game, officer, arc_id)
            officer.arc_beat = index
            officer.arc_state = {"chose": ["x"] * index,
                                 "next": int(game.day) + 1}
            officer.loyalty = data.LOYAL_AT - 20
            for _ in range(20):
                cap.provisioned(game)
                game.advance_days(1)
            st = officer.arc_state
            if kind != "date":
                assert st.get("armed") is not None and not st.get("sig"), (
                    f"{kind}: opened before its condition ({st})")
                if act is None:
                    cap.arrive(game, st["place"])
                else:
                    act(game, officer)
                cap.provisioned(game)
                game.advance_days(1)
            assert st.get("sig"), f"{kind}: nothing opened ({st})"
            said.append(kind)
        assert said == [k[0] for k in kinds]
        return "date, place, loyalty, a fight, a burn and a holding"

    @check("every answer does what its preview said, and a refused one "
           "nothing")
    def _():
        compared = 0
        for arc in ARCS:
            game = cap.chronicle(f"arcs-preview-{arc.id}")
            officer = game.officers[2]
            for index, beat in enumerate(arc.beats):
                for choice in beat.choices:
                    cap.at_beat(game, officer, arc.id, index)
                    game.ship.cargo = {"biomass": 120, "volatiles": 60}
                    sig = cap.opened(game, officer)
                    said = arcs_sim.preview(game, sig, choice.key)
                    assert said and not said["why"], (arc.id, choice.key)
                    before = _held(game)
                    assert comms_sim.answer(game, sig.id, choice.key)
                    after = _held(game)
                    got = after["credits"] - before["credits"]
                    assert abs(got - said["credits"]) < 1e-6, (
                        arc.id, choice.key, got, said["credits"])
                    for power, moved in said["rep"].items():
                        real = after["rep"][power] - before["rep"][power]
                        assert abs(real - moved) < 1e-9, (arc.id, power)
                    for cid, tonnes in said["cargo"].items():
                        real = after["goods"][cid] - before["goods"][cid]
                        assert abs(real - tonnes) < 1e-6, (arc.id, cid, real)
                    mine = (after["loyalty"][officer.id]
                            - before["loyalty"][officer.id])
                    assert abs(mine - said["loyalty"]) < 1e-9, (
                        arc.id, choice.key, mine, said["loyalty"])
                    if choice.purse:
                        spent = (before["purses"][choice.purse]
                                 - after["purses"][choice.purse])
                        assert abs(spent - said["credits"]) < 1e-6
                    assert bool(officer.signature) == bool(said["signature"])
                    officer.signature = None
                    compared += 1
        # A treasury that cannot pay: refused, and nothing moves.
        game = cap.chronicle("arcs-refused")
        officer = game.officers[0]
        cap.at_beat(game, officer, "old_debts", 1)
        sig = cap.opened(game, officer)
        game.credits = 100
        before = _held(game)
        assert arcs_sim.preview(game, sig, "pay")["why"]
        assert not comms_sim.answer(game, sig.id, "pay")
        assert _held(game) == before and sig.asks, "a refusal moved something"
        assert compared > 80, compared
        return (f"{compared} answers, each exactly as previewed; a slate the "
                "treasury cannot pay is refused and changes nothing")

    @check("a lapse costs what it says, and a neglected last beat walks an "
           "officer out through loyalty.tick alone")
    def _():
        assert (data.LAPSE_FIRST, data.LAPSE_SECOND, data.LAPSE_LAST) == (
            4.0, 6.0, 14.0) and data.ANSWER_DAYS == 60
        costs = []
        for index in range(3):
            game = cap.chronicle(f"arcs-lapse-{index}")
            officer = game.officers[0]
            cap.at_beat(game, officer, "heir", index)
            sig = cap.opened(game, officer)
            officer.loyalty = 50.0
            game.day = officer.arc_state["until"]
            arcs_sim.tick(game, 1)
            assert sig.asks, "it lapsed on its last day, not after it"
            game.day += 1
            arcs_sim.tick(game, 1)
            assert not sig.asks and sig.answered == arcs_sim.LAPSED
            costs.append(50.0 - officer.loyalty)
            assert officer.arc_beat == index + 1
        assert costs == [4.0, 6.0, 14.0], costs
        # The last one, from "Restless": arcs takes the loyalty, and the one
        # path lets them go.
        game = cap.chronicle("arcs-walkout")
        officer = game.officers[1]
        cap.at_beat(game, officer, "widow", 2)
        cap.opened(game, officer)
        officer.loyalty = WALKOUT + 10
        game.day = officer.arc_state["until"] + 1
        arcs_sim.tick(game, 1)
        assert officer in game.officers, "arcs removed an officer itself"
        assert officer.loyalty < WALKOUT
        said = loyalty_sim.tick(game, 1, True)
        assert officer not in game.officers, "they stayed below the line"
        assert any(officer.name in text for _k, text in said)
        return f"lapses cost {costs}; the last one took a restless officer out"

    @check("every signature moves its number, and nothing moves without it")
    def _():
        moved = []
        for sig_id, rows in arc_probes.PROBES.items():
            for what, probe in rows:
                off, on = probe()
                if sig_id == "lucky":
                    (said_off, rolled_off), (said_on, rolled_on) = off, on
                    assert said_on > said_off + 0.02, (said_off, said_on)
                    assert abs(rolled_on - said_on) < 0.04, (said_on,
                                                              rolled_on)
                    assert abs(rolled_off - said_off) < 0.04
                elif sig_id == "landed":
                    assert off == (0, 0.0), off
                    assert on[0] == on[1] == data.LANDED_MONTHLY, on
                else:
                    assert on != off, f"{sig_id}: {what} did not move"
                moved.append(f"{what} {_fmt(off)}→{_fmt(on)}")
        assert len(moved) == sum(len(r) for r in arc_probes.PROBES.values())
        assert len(arc_probes.PROBES) == len(SIGNATURES) == 12
        return "; ".join(moved)

    @check("a story is dealt from the officer's own key, and asking about "
           "it changes nothing")
    def _():
        a, b = new_game("arcs-deal"), new_game("arcs-deal")
        before = arcs_sim.planned(a)
        a.advance_days(1)
        b.advance_days(1)
        dealt = {o.id: o.arc for o in a.officers}
        assert dealt == before == {o.id: o.arc for o in b.officers}
        assert len(set(dealt.values())) == len(dealt), "two alike on a bridge"
        spread = {o.arc for seed in range(8)
                  for o in _dealt(new_game(f"arcs-spread-{seed}"))}
        assert len(spread) >= 8, spread
        from ..core import save as save_mod
        game = cap.chronicle("arcs-look")
        cap.at_beat(game, game.officers[0], "gambler", 1)
        sig = cap.opened(game, game.officers[0])
        frozen = (game.rng_seed, save_mod.encode({"game": game}))
        for officer in game.officers:
            arcs_sim.status(game, officer)
        arcs_sim.planned(game), arcs_sim.progress(game), arcs_sim.record(game)
        arcs_sim.preview(game, sig, "back")
        assert (game.rng_seed, save_mod.encode({"game": game})) == frozen
        return (f"the same bridge dealt the same stories twice; eight seeds "
                f"dealt {len(spread)} of twelve; looking moved nothing")

    @check("nothing arms before day 45 or while the tutorial teaches flying")
    def _():
        assert data.QUIET_DAYS == 45 and data.QUIET_CHAPTER == "rock-and-ice"
        game = new_game("arcs-quiet")
        game.advance_days(1)
        first = min(o.arc_state["next"] for o in game.officers)
        assert first >= data.QUIET_DAYS + data.GAP_MIN, first
        from ..sim import tutorial
        taught = new_game("arcs-taught")
        tutorial.begin(taught)
        taught.advance_days(1)
        held = taught.officers[0].arc_state["next"]
        taught.advance_days(30)
        assert taught.officers[0].arc_state["next"] == held + 30, (
            "a story's clock ran during the first lessons")
        tutorial.skip(taught)
        taught.advance_days(30)
        assert taught.officers[0].arc_state["next"] == held + 30
        return (f"the earliest beat arms on day {first}; the tutorial's "
                "first chapters hold every clock still")

    @check("a story past an unopened rim waits, says what opens it, and "
           "goes on once it is open")
    def _():
        game = cap.chronicle("arcs-rim")
        officer = game.officers[0]
        cap.deal(game, officer, "cartographer")
        officer.arc_beat = 2
        officer.arc_state = {"chose": ["fly", "survey"],
                             "next": int(game.day) + 1}
        for _ in range(2 * data.PLACE_DAYS):
            cap.provisioned(game)
            game.advance_days(1)
        told = arcs_sim.status(game, officer)
        assert officer.arc_beat == 2 and not officer.arc_state.get("sig"), (
            "it lapsed while the Hollow was dark")
        assert "Hollow Gate" in told["waiting"], told
        cap.open_region(game, "hollow")
        game.advance_days(1)
        cap.arrive(game, officer.arc_state["place"])
        game.advance_days(1)
        assert officer.arc_state.get("sig"), "it never opened in the Hollow"
        return f"waited {2 * data.PLACE_DAYS} days: “{told['waiting']}”"

    @check("ignoring every story costs some loyalty, and nobody walks out")
    def _():
        means, left = [], []
        for on in (False, True):
            real = arcs_sim.tick
            if not on:
                arcs_sim.tick = lambda *a, **k: None
            try:
                game = new_game("arcs-ignored")
                start = {o.id for o in game.officers}
                seen = []
                for day in range(3 * 365):
                    cap.provisioned(game)
                    game.advance_days(1)
                    if day % 30 == 0:
                        seen.append(loyalty_sim.summary(game)["mean"])
            finally:
                arcs_sim.tick = real
            means.append(sum(seen) / len(seen))
            left.append(len(start - {o.id for o in game.officers}))
        cost = means[0] - means[1]
        assert 0.5 < cost < 20, means
        assert left == [0, 0], left
        return (f"mean loyalty over three years {means[0]:.1f} without "
                f"stories, {means[1]:.1f} ignoring them all; nobody left")

    arcs_screens.run(suite)


def _dealt(game) -> list:
    game.advance_days(1)
    return game.officers


def _fmt(value) -> str:
    if isinstance(value, tuple):
        return "(" + ", ".join(_fmt(v) for v in value) + ")"
    return f"{value:.3g}" if isinstance(value, float) else str(value)
