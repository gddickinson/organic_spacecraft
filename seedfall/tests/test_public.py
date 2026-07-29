"""Every public act pays for being public — not half of them.

`sim/allegiance.py` has charged you for being seen working for somebody since
the day it was written: relief to the Concordat costs you with the Charter and
the Freeholds, in proportion to how bad the rift actually is. Two acts on the
diplomatic board never got the same treatment. Measured, at 70 standing with
everyone:

    relief   (concordat)             charter -0.2, concordat +3.3, freeholds -1.3
    broker   (concordat, freeholds)  concordat +1.8, freeholds +1.8  <- nobody else
    denounce (concordat, freeholds)  charter +6, concordat +6, freeholds -14

Brokering is the most public thing a captain can do. It seats two powers at a
table, thanks you with **both**, moves their relation twenty-eight points and
decides the Concord ending — and the Charter, sitting at -20 and -35 with the
pair of them, did not notice. Denouncing thanked everyone already at odds with
the target and charged nobody close to them.

Two pieces were missing. `allegiance.defenders_of` is the mirror of
`offended_by`: who minds you **attacking** a power rather than serving one. It
is deliberately symmetric — offence starts below Cold and devotion above
Correct — which means it costs nothing at dawn, because the Verge opens with
no friendships in it. Denouncing gets more expensive exactly as you pacify the
sector, which is a better property than any number I could have tuned.

And brokering is priced on what it **moves** rather than on the thanks.
`courtship` has already shrunk the thanks to under two points at any standing
where brokering is permitted at all, so pricing the offence against it made
the loudest act on the board cost a third power six tenths of a point.
`BROKER_WEIGHT` is to a settlement what `TREATY_WEIGHT` is to a treaty.

What it does to the game, measured over twenty determined chronicles: a
captain who only brokers reaches the Concord **6 times in 20**, and one who
brokers and keeps everyone sweet **19 times in 20**. The ending is not harder
to reach; it now asks you to pay for it.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import allegiance
from ..sim import diplomacy as dip
from .harness import Suite

POWERS = ("charter", "concordat", "freeholds", "sanhedrin")


def run(suite: Suite) -> None:
    check = suite.check

    @check("the whole board pays for being public, not half of it")
    def _():
        # The general one, and the rule stated independently of the code:
        # **a power at odds with somebody you visibly served should pay, and
        # a power close to somebody you visibly attacked should pay.** Who
        # counts is read off the relations matrix here, not off
        # `offended_by` — sharing the code's own list would prove nothing.
        missed, checked = [], 0
        for seed in range(4):
            for action, args in (("relief", ("concordat",)),
                                 ("intelligence", ("freeholds",)),
                                 ("tribute", ("sanhedrin",)),
                                 ("treaty", ("concordat",)),
                                 ("broker", ("concordat", "freeholds")),
                                 ("denounce", ("concordat", "freeholds"))):
                game = new_game(f"public-{seed}")
                game.credits = 10_000_000
                for cid in ("biomass", "survey"):
                    game.ship.cargo[cid] = 99_999
                for power in POWERS:
                    game.rep[power] = 70
                # A sector with real friendships and real quarrels in it, so
                # both ramps have something to bite on.
                dip.shift_relation(game, "freeholds", "sanhedrin", 45)
                dip.shift_relation(game, "concordat", "sanhedrin", 50)
                game.recompute()

                # Who *ought* to mind, from the matrix alone.
                served = set(args) if action != "denounce" else {args[0]}
                attacked = {args[1]} if action == "denounce" else set()
                should = set()
                for third in POWERS:
                    if third in args:
                        continue
                    # A denunciation *thanks* everyone already at odds with
                    # the target, and that thanks can outweigh what they owe
                    # for the power you served. Where both apply the net is
                    # a wash by design, so only the unambiguous cases count.
                    thanked = any(dip.relation(game, third, p)
                                  < allegiance.INDIFFERENT for p in attacked)
                    if thanked:
                        continue
                    if any(dip.relation(game, third, p) < allegiance.INDIFFERENT
                           for p in served):
                        should.add(third)
                    if any(dip.relation(game, third, p) > allegiance.FRIENDLY
                           for p in attacked):
                        should.add(third)

                before = {p: game.rep.get(p, 0) for p in POWERS}
                result = dip.perform(game, action, *args)
                if not result.get("ok"):
                    continue
                checked += 1
                for third in should:
                    moved = game.rep.get(third, 0) - before[third]
                    if moved >= 0:
                        missed.append(
                            f"{action}{args}: {third} should mind and moved "
                            f"{moved:+.2f}")
        assert not missed, (
            f"{len(missed)} power(s) watched something they mind and were "
            f"charged nothing: {missed[:4]}")
        assert checked >= 20, checked
        return (f"{checked} overtures across four sectors; everyone the "
                "matrix says should mind was charged")

    @check("brokering is priced on what it moves, not on the thanks")
    def _():
        # `courtship` shrinks the thanks to under two points at good
        # standing, so pricing the offence against it made seating two
        # powers at a table cost a third six tenths of a point. It is
        # priced against the settlement now, the way a treaty is.
        from ..data.diplomacy import BROKER_WEIGHT

        game = new_game("weight")
        game.credits = 10_000_000
        for power in POWERS:
            game.rep[power] = 70
        game.recompute()
        assert dip.relation(game, "charter", "concordat") < -15
        assert dip.relation(game, "charter", "freeholds") < -15

        said = dip.preview(game, "broker", "concordat", "freeholds")
        charter = sum(amount for who, amount in said["standing"]
                      if who == "charter")
        thanks = sum(amount for who, amount in said["standing"]
                     if who in ("concordat", "freeholds"))
        assert charter < 0, (
            "the Charter is at odds with both parties and is quoted nothing")
        assert abs(charter) > 2.0, (
            f"the Charter watches its two enemies settle and pays "
            f"{charter:.1f} — a rounding error, not a consequence")
        assert BROKER_WEIGHT > thanks, (
            f"the settlement is priced at {BROKER_WEIGHT} against thanks of "
            f"{thanks:.1f}; it is the moving that is public, not the thanks")

        before = game.rep.get("charter", 0)
        dip.perform(game, "broker", "concordat", "freeholds")
        moved = game.rep.get("charter", 0) - before
        assert abs(moved - charter) < 0.11, (
            f"the board said {charter:.1f} and the act did {moved:.1f}")
        return (f"the Charter pays {moved:.1f} for a settlement between the "
                f"two powers it likes least, against {thanks:.1f} of thanks")

    @check("denouncing is free in a hostile sector and dear in a warm one")
    def _():
        # The emergent property, and the reason the mirror is symmetric with
        # `offended_by` rather than tuned to bite at dawn: the Verge opens
        # with no friendships in it, so there is nobody to offend. The more
        # peace you make, the more expensive it becomes to play powers off
        # against each other.
        def cost(pacified: bool) -> float:
            game = new_game("denounce-warmth")
            game.credits = 10_000_000
            for power in POWERS:
                game.rep[power] = 70
            if pacified:
                dip.shift_relation(game, "freeholds", "sanhedrin", 45)
            game.recompute()
            before = game.rep.get("sanhedrin", 0)
            out = dip.perform(game, "denounce", "concordat", "freeholds")
            assert out["ok"], out
            return game.rep.get("sanhedrin", 0) - before

        hostile = cost(False)
        warm = cost(True)
        assert hostile == 0, (
            f"the Sanhedrin minds a denunciation of a power it is merely "
            f"Correct with, by {hostile:.1f}")
        assert warm < -2.0, (
            f"the Sanhedrin is Cordial with the Freeholds and pays "
            f"{warm:.1f} when you denounce them in open session")
        assert allegiance.defenders_of(new_game("denounce-warmth"),
                                       "freeholds") == [], (
            "somebody is already a partisan on the opening day")
        return (f"nothing owed in a sector with no friendships; {warm:.1f} "
                "once the Freeholds have one")

    @check("the board promises exactly what the overture does")
    def _():
        # The forecast discipline, swept. Every overture, every ordered pair
        # of powers, in a hostile sector and a pacified one — `preview` must
        # predict every standing change `perform` makes, to the tenth.
        #
        # It was measured at 3,456 comparisons while the fix was being built
        # and then not written down, which is how a mutation that hid the
        # denunciation cost from the board survived the first sweep.
        import itertools

        worst, compared, wrong = 0.0, 0, []
        for seed in range(3):
            for pacified in (False, True):
                for a, b in itertools.permutations(POWERS, 2):
                    for action in ("tribute", "relief", "intelligence",
                                   "treaty", "broker", "denounce"):
                        game = new_game(f"promise-{seed}")
                        game.credits = 10_000_000
                        for cid in ("biomass", "survey"):
                            game.ship.cargo[cid] = 99_999
                        for power in POWERS:
                            game.rep[power] = 60
                        if pacified:
                            dip.shift_relation(game, "freeholds", "sanhedrin", 45)
                            dip.shift_relation(game, "concordat", "sanhedrin", 50)
                        game.recompute()
                        if not next((ok for act, ok, _w in dip.available(game, a)
                                     if act.id == action), False):
                            continue
                        said = dip.preview(game, action, a, b)
                        before = {p: game.rep.get(p, 0) for p in POWERS}
                        if not dip.perform(game, action, a, b).get("ok"):
                            continue
                        promised: dict = {}
                        for who, amount in said["standing"]:
                            promised[who] = promised.get(who, 0) + amount
                        for power in POWERS:
                            moved = game.rep.get(power, 0) - before[power]
                            gap = abs(promised.get(power, 0) - moved)
                            worst = max(worst, gap)
                            compared += 1
                            if gap > 0.11:
                                wrong.append(
                                    f"{action} {a}->{b}: said "
                                    f"{promised.get(power, 0):+.2f} to {power}, "
                                    f"did {moved:+.2f}")
        assert not wrong, (
            f"{len(wrong)} standing change(s) the board did not promise: "
            f"{wrong[:4]}")
        assert compared > 1500, compared
        return (f"{compared} standing predictions across every overture and "
                f"pair, worst gap {worst:.3f}")

    @check("a settlement never charges the two it settles")
    def _():
        # You are not offending the Concordat by serving the Freeholds when
        # the whole act is seating them together. Dropping that exemption
        # made each principal pay for the other and nothing noticed.
        moved_wrong = []
        for a, b in (("concordat", "freeholds"), ("charter", "concordat"),
                     ("freeholds", "sanhedrin")):
            game = new_game("principals")
            game.credits = 10_000_000
            for power in POWERS:
                game.rep[power] = 70
            game.recompute()
            said = dip.preview(game, "broker", a, b)
            before = {p: game.rep.get(p, 0) for p in POWERS}
            if not dip.perform(game, "broker", a, b).get("ok"):
                continue
            for principal in (a, b):
                moved = game.rep.get(principal, 0) - before[principal]
                if moved <= 0:
                    moved_wrong.append(
                        f"{principal} was seated at the table by you and came "
                        f"away {moved:+.2f}")
                quoted = sum(amount for who, amount in said["standing"]
                             if who == principal)
                if quoted <= 0:
                    moved_wrong.append(
                        f"the board quotes {principal} {quoted:+.2f} for a "
                        "settlement it is a party to")
        assert not moved_wrong, moved_wrong
        return "both parties to a settlement are thanked, never charged"
