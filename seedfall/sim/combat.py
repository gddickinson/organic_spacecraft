"""Tactical combat on a five-band range track.

Two things make this different from the usual exchange of fire. First, damage
lands on a stack of named layers — a grown hull sheds its epidermis, gives up its
rind, and only really cares once the pneumostat opens. Second, killing the other
ship is not the only way to win: every combatant has a resolve, and a hull that
simply refuses to die will break the other side's will to keep paying for the
ammunition. TESTUDO doctrine, fitted as a mechanic.
"""

from __future__ import annotations

from .battle_state import Battle, Side, finish as _finish
from .damage import _disable, _say, _who
from . import firing
from . import stations as st_mod
from . import turnplan
from . import tactical as tac
from .abilities import use_ability as _fire_ability
from .enemy_ai import enemy_turn as _enemy_turn
from . import consorts as consort_sim
from . import craft_battle
from . import parley
from ..data.part_types import BANDS
from .ship import hull_pct, is_breached, is_destroyed
# Resolving a shot, split out at 482 lines; re-exported because the turn,
# the enemy, the consorts, parley and the checks all fire through here.
from .shooting import DAZZLE_CAP, VARIANCE, _fire, _salvo  # noqa: F401

MAX_TURNS = 40

GRIND_TURN = 9      # turns of clean fighting before either side starts wanting out

#: The thermal rule lives in `sim/ship.py`, next to `cool()`, because the hull
#: owns its own physics and both the guns and the helm put heat into it. Kept
#: importable from here because that is where the fight reads it.
from .ship import HEAT_CEILING, add_heat, cook  # noqa: E402,F401

def start(player_ship, player_stats, enemy, *, bonuses=None, officers=(),
          rep=0.0, no_parley=False, band=3, game=None, rng=None,
          fleet=()) -> Battle:
    b = Battle(
        player=Side(player_ship, player_stats, "player"),
        enemy=Side(enemy["ship"], enemy["stats"], enemy.get("personality", "balanced")),
        enemy_name=enemy.get("name", "Unknown contact"),
        enemy_faction=enemy.get("faction"),
        no_parley=no_parley, rep=rep,
        bonuses=dict(bonuses or {}), officers=list(officers), game=game,
        loot=dict(enemy.get("loot", {})),
    )
    b.enemy.resolve = enemy.get("resolve", 100)
    if rng is not None:
        b.player.body, b.enemy.body = tac.initial_layout(rng, band)
    else:
        b.player.body = tac.Body2D(0, 0, 0, 0)
        b.enemy.body = tac.Body2D(0, -(band + 0.5) * tac.BAND_UNITS, 180, 0)

    # What they carry on their own flank (`sim/craft_battle`).
    craft_battle.fit_flight(b, rng)
    if fleet:
        consort_sim.deploy(b, list(fleet), rng, bonuses)
        names = ", ".join(c.name for c in b.consorts)
        _say(b, f"In company: {names}.", "good")
    _say(b, f"{b.enemy_name} at {BANDS[b.band].lower()} range, "
            f"{round(b.range_units)} units off.", "warn")
    return b


# ── abilities ──────────────────────────────────────────────────────────────

# ── turn resolution ────────────────────────────────────────────────────────


def take_turn(b: Battle, action: dict, rng) -> Battle:
    from . import gunfire
    gunfire.clear(b)
    """Run one full exchange. ``action`` is the player's choice."""
    if b.over:
        return b
    b.player.braced = False
    b.enemy.braced = False       # a brace that never cleared is permanent
    kind = action.get("type")

    # Legacy orders map onto the stations so older callers keep working.
    if kind == "move":
        b.player.station = "helm"
        b.player.helm_order = "close" if action.get("dir", 1) < 0 else "open"
        # Without the pending order, `_run_stations` handed the helm None
        # and `run_helm` overwrote the order this mapping had just written.
        b.pending_order = b.player.helm_order
        kind = "station"
    elif kind in ("fire", "salvo", "volley"):
        b.player.station = "gunnery"
    elif kind == "brace":
        b.player.station = "engineering"
    elif kind == "station":
        order = st_mod.ORDERS_BY_ID.get(action.get("order", ""))
        if order is None:
            # Say so — this was the one refusal in the fight that said
            # nothing at all, which a scripted driver reads as a hang.
            _say(b, "No such order is on any station's board.", "warn")
            return b
        b.player.station = order.station
        if order.station == "helm":
            b.player.helm_order = order.id
        b.pending_order = order.id

    if kind == "station":
        # A captain in a cockpit is not on the bridge (`sim/craft_battle`).
        conning, why = craft_battle.on_the_bridge(b)
        if not conning:
            _say(b, why, "warn")
            return b
        _run_stations(b, rng)
        _run_company(b, rng)
        if not b.over and is_destroyed(b.enemy.ship):
            return _finish(b, "destroyed")
        broke = None
        if not b.over:
            broke = _enemy_move(b, rng)
        if broke:
            return _finish(b, broke)
        if not b.over and is_destroyed(b.player.ship):
            return _finish(b, "lost")
        if not b.over:
            _end_of_turn(b, rng)
        return b

    # The seats the captain is *not* in are held by officers whichever way
    # the turn was ordered. Only the `station` path used to do this.
    if kind in ("fire", "salvo", "volley", "ability", "brace", "craft"):
        said = _run_seats(b, b.player.station)
        if said:
            _say(b, f"{b.player.ship.name}: {', '.join(said)}.", "dim")

    if kind == "fire":
        _fire(b, b.player, b.enemy, action["weapon_id"], rng)
    elif kind == "salvo":
        _salvo(b, b.player, b.enemy, rng)
    elif kind == "volley":
        # The gunner's own choice of mounts. `_salvo` fires everything that
        # bears, which on a five-mount hull is 69 points of heat against a
        # fault line of 40; this is the middle that did not exist.
        from . import gunnery
        out = gunnery.volley(b, action.get("mounts") or [], rng)
        if not out["fired"]:
            _say(b, out["why"], "dim")
        else:
            _say(b, f"{_who(b, b.player)} fires {len(out['fired'])} of "
                    f"{len([w for w in b.player.st.weapons if w.wpn])} "
                    "mounts.", "dim")
    elif kind == "ability":
        use_ability(b, b.player, action["id"], rng)
    elif kind == "brace":
        b.player.braced = True
        b.player.resolve += 6
        b.player.ship.heat = max(0.0, b.player.ship.heat - b.player.st.vent)
        _say(b, "You turn the thickest tissue into the fire and hold.", "good")
    elif kind == "craft":
        # The cradle deck, which is a seat like any other this turn: the
        # rules are `sim/craft_battle`, and a refusal costs nothing but the
        # line that says why.
        order = action.get("order", "launch")
        got = (craft_battle.recall(b) if order == "home"
               else craft_battle.launch(b, action.get("pilot", "")))
        if not got.get("ok"):
            _say(b, got["why"], "dim")
            return b
    elif kind == "hail":
        return parley.hail(b, rng, _ops())
    elif kind == "flee":
        return parley.flee(b, rng, _ops())

    if kind in ("ability", "brace", "craft"):
        # Nobody is laying a mount by hand on these turns, and the panel's
        # preview already promises the gunner keeps working.
        _idle_gunner(b, rng)

    _run_company(b, rng)
    if not b.over and is_destroyed(b.enemy.ship):
        return _finish(b, "destroyed")
    if not b.over:
        broke = _enemy_move(b, rng)
        if broke:
            return _finish(b, broke)
    if not b.over and is_destroyed(b.player.ship):
        return _finish(b, "lost")
    if not b.over:
        _end_of_turn(b, rng)
    return b


def _enemy_move(b: Battle, rng):
    """Their turn: the hull, and then whatever it launched at you."""
    broke = _enemy_turn(b, rng, _say, _fire, _salvo, use_ability)
    if not broke:
        craft_battle.their_run(b, rng)
    return broke


def _run_company(b: Battle, rng) -> None:
    """Everything of yours that fights on its own account: the consorts to
    their standing orders, and a launched craft's run (`sim/craft_battle`)."""
    if b.over:
        return
    if b.consorts:
        before = {c.uid for c in b.consorts if not c.out}
        consort_sim.run(b, rng, _say, _fire)
        for c in b.consorts:
            if c.uid in before and is_destroyed(c.ship):
                _say(b, f"{c.name} breaks apart.", "bad")
                b.player.resolve -= 12
    craft_battle.run(b, rng)


def _ops() -> parley.Ops:
    return parley.Ops(say=_say, fire=_fire, salvo=_salvo,
                      use_ability=use_ability, enemy_turn=_enemy_turn,
                      finish=_finish, end_of_turn=_end_of_turn)


def use_ability(b: Battle, s: Side, ability_id: str, rng) -> bool:
    """Fire a defensive ability and log what it did."""
    fired, message, kind = _fire_ability(b, s, ability_id, rng)
    if fired and message:
        _say(b, f"{_who(b, s)} {message}", kind)
    return fired


def _run_seats(b: Battle, seat: str, order=None) -> list:
    """Fly the ship and run the engineering section. Returns what they report.

    `seat` is where the captain is standing; the other two are held by
    officers, or by the battle computer if one is fitted.

    Split out because the seats were only ever run on the `station` path.
    Firing a named mount or using an ability goes through the older path,
    which the battle screen still uses for the firing picture and the ability
    buttons — and on those turns nobody flew the ship and nobody stood in the
    engineering section at all. Measured: heat 30 became 24.0 through the old
    door against 19.44 through the new one, and `helm_order` stayed `None`.
    """
    # Engineering first, because it is what decides where the power goes and
    # both the other seats spend it. `route_guns` was read by the guns, which
    # fire after the seats, so it landed on the turn it was given;
    # `route_engines` was read by the helm, which used to run *before*
    # engineering set it, so it landed a turn late. Measured: ordering "power
    # to the drive" left the ship at a dead stop, and it leapt to 74.9 on the
    # following turn — the turn the captain had ordered *hold station*.
    eng_text = st_mod.run_engineering(
        b.player, order.id if order and order.station == "engineering" else None,
        seat == "engineering", b.officers, b.enemy)
    helm_text = st_mod.run_helm(
        b.player, b.enemy,
        order.id if order and order.station == "helm" else None,
        seat == "helm", b.officers)
    return [t for t in (eng_text, helm_text) if t]


def _idle_gunner(b: Battle, rng) -> None:
    """The gunner keeps working while the captain is elsewhere, less well.

    `turnplan.idle_gunnery` is asked what they do, because the orders panel
    asks the same function to cost it — quoted separately, the panel once
    forecast *vent* while the walked-away-from gunner fired everything.
    """
    idle = turnplan.idle_gunnery(b.player, b.enemy, b.officers)
    if idle["order"] == "salvo":
        _salvo(b, b.player, b.enemy, rng)
    elif idle["mounts"]:
        _fire(b, b.player, b.enemy, idle["mounts"][0].id, rng)


def _run_stations(b: Battle, rng) -> None:
    """Resolve the player's chosen seat, then the two the officers hold."""
    order_id = getattr(b, "pending_order", None)
    order = st_mod.ORDERS_BY_ID.get(order_id or "")
    seat = b.player.station

    bits = _run_seats(b, seat, order)

    if order and order.station == "gunnery":
        if order.id == "salvo":
            _salvo(b, b.player, b.enemy, rng)
        elif order.id == "aimed":
            usable = [w for w in b.player.st.weapons
                      if w.wpn.bears_at(b.band) <= firing.WORTH_FIRING
                      and st_mod.bears_on(b.player, b.enemy, w)[0]]
            if usable:
                best = max(usable, key=lambda w: w.wpn.dmg)
                _fire(b, b.player, b.enemy, best.id, rng)
            else:
                _say(b, "Nothing will bear for an aimed shot.", "dim")
    elif seat != "gunnery":
        _idle_gunner(b, rng)

    if bits:
        _say(b, f"{b.player.ship.name}: {', '.join(bits)}.", "dim")
    b.pending_order = None


def _end_of_turn(b: Battle, rng) -> None:
    from . import gunnery
    for s in (b.player, b.enemy):
        s.ship.heat = max(0.0, s.ship.heat - s.st.vent)
        # `gunnery.fault_line` is the same number, and the gunner's board
        # quotes it before the trigger. Asked here rather than written twice.
        if s.ship.heat > gunnery.fault_line(s):
            over = s.ship.heat - gunnery.fault_line(s)
            _say(b, f"{_who(b, s)} is overheating — systems faulting.", "warn")
            s.resolve -= over * 0.3
            if rng.chance(0.25):
                _disable(b, s, rng, "Thermal shutdown takes")
        if is_breached(s.ship):
            s.resolve -= 6
        s.blind = max(0, s.blind - 1)
        s.jammed = max(0, s.jammed - 1)
        s.grappled = max(0, s.grappled - 1)
        for k in list(s.cd):
            s.cd[k] = max(0, s.cd[k] - 1)
        # Living hulls close wounds even mid-fight, slowly.
        if s.st.regen > 0:
            for L in reversed(s.ship.layers):
                if 0 < L.hp < L.max:
                    L.hp = min(L.max, L.hp + L.max * L.regen * s.st.regen * 0.5)
                    break

    b.turn += 1
    # Nobody fights forever. Past a dozen turns without resolution the
    # ammunition and the heat stop being worth it. It starts late deliberately:
    # a decisive hull should still be able to finish the job on its own terms.
    # Nerve goes when a hull is being taken apart and is not giving as good as
    # it gets. This used to be a pure function of the turn counter — and the
    # enemy lost it twice as fast as the player — so a ship with no armament at
    # all drove off a battleship three times in four simply by waiting. The
    # clock term survives only to guarantee the fight ends.
    grind = max(0, b.turn - GRIND_TURN) * 0.12
    for side, other in ((b.player, b.enemy), (b.enemy, b.player)):
        hurt = max(0.0, 1.0 - hull_pct(side.ship))
        behind = max(0.0, (other.dealt - side.dealt) / 220.0)
        # Futility is what makes endurance a real strategy: a hull built to be
        # hit and not break wins by convincing the other side there is no point
        # continuing. Weighted by how little progress the attacker has made, so
        # a ship that *is* being taken apart cannot outlast anybody.
        progress = 1.0 - hull_pct(other.ship)
        futile = max(0.0, (b.turn - GRIND_TURN) / 16.0) * (1.0 - progress)
        side.resolve -= grind + hurt * 3.6 + behind * 2.4 + futile * 1.8

    if b.enemy.resolve <= 0:
        _finish(b, "driven-off")
    elif b.player.resolve <= -40:
        _finish(b, "routed")
    elif b.turn > MAX_TURNS:
        _finish(b, "stalemate")


__all__ = ["Battle", "Side", "start", "take_turn", "use_ability", "BANDS",
           "MAX_TURNS", "GRIND_TURN", "HEAT_CEILING", "cook"]
