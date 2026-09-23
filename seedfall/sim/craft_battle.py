"""A craft in an engagement: off the cradle, and making runs.

`sim/craft.py` is the cradle deck and the sortie; this is what a single seat
does once the shooting has started, which is the thing a carrier keeps one
for. It is deliberately not a second tactical plane: a fighter is too small
to hold a place in the line — `sim/consorts.py` is what does that, a whole
hull with its own stats — and what a craft has instead is a **run**: in at
the enemy with everything she carries, and out again through whatever
answers.

- **Launched into the fight.** The cradle deck works under fire, so she can
  go out on any turn (`may_launch`), with the best ticket aboard. Launching
  spends the turn, the way taking a station does, and the turn she launches
  is the turn she makes her first run.
- **A run a turn** (`run`, called from `sim/combat`'s turn beside the
  consorts): her guns' dice plus the pilot's own rating, through the same
  door a shell goes through (`sim/damage`), so a run strips layers, breaches
  hulls and feeds the hull's adaptation exactly as gunnery does.
- **The answer.** A hull that is still fighting turns its close-in fire on
  her, and her armour is all that is between that and the pilot. A dazzled
  enemy shoots at where she was.
- **Shot down is a person.** The craft is gone for good (`sim/craft.lose`);
  the pilot gets clear with a wound on them, because a game that spends an
  officer on a dice roll nobody chose is not a game anybody plays twice.
- **Home at the end** (`settle`, from `sim/aftermath`): whatever is still
  flying comes back on the cradle and the tank is filled from the hold.
"""

from __future__ import annotations

from . import abilities
from . import craft as craft_sim
from .damage import _apply_to_layers, _say
from .ship import is_destroyed

#: What a point of the pilot's Pilot rating adds to the weight of a run.
RATING_BITE = 2.0
#: The share of a run that lands however thick the plating is — the same
#: floor a shell has (`sim/shooting`), for the same reason.
ARMOUR_FLOOR = 0.15
#: How much resolve a run in through their point defence costs the hull it is
#: made at, and what losing the craft costs yours.
RUN_NERVE, LOST_NERVE = 4.0, 8.0
#: The close-in fire a hull answers a run with: two dice, and two more for
#: every mount it still has, between these. Sized by measurement — a WASP
#: (120 of hull, 3 of armour) comes back from a ten-turn fight against a
#: one-mount patrol with about half of herself, and a four-mount hull kills
#: her in five or six runs. That is what makes calling her in a decision
#: rather than a formality.
ANSWER_LEAST, ANSWER_MOST = 3, 8
#: Dice a single live mount is worth to the hull's close-in fire.
PER_MOUNT = 2
#: What a dazzled hull's point defence is worth, and the stamina a pilot who
#: is shot out of their seat carries home (`game.wounds`).
BLIND_SHARE, PILOT_HURT = 0.5, 4.0


def flying(game):
    """The craft out on a run, or None."""
    return craft_sim.flying(game) if game is not None else None


def may_launch(b) -> tuple:
    """May a craft go out into this engagement? `(ok, why, craft)`."""
    game = getattr(b, "game", None) if b is not None else None
    if b is None or b.over or game is None:
        return False, "There is nothing to fly into.", None
    if flying(game) is not None:
        return False, "She is already out.", None
    ready = [c for c in craft_sim.aboard(game) if c.state == "cradled"]
    if not ready:
        return False, "This hull carries no craft on the cradle.", None
    # The one with the most gun in her: a hull that carries a fighter and a
    # lander sends the fighter, and complains about the lander's empty
    # mounts only when the lander is all there is.
    craft = max(ready, key=lambda c: sum(
        dice for _name, dice in craft_sim.kind_of(c).guns))
    kind = craft_sim.kind_of(craft)
    if craft.hp <= 0:
        return False, f"{craft.name} is wrecked.", None
    if craft.fuel <= craft_sim.STRIKE_T:
        return False, f"{craft.name} has no reaction mass in her.", None
    if not kind.guns:
        return False, f"{craft.name} carries no guns.", None
    if not craft_sim.best_pilot(game, craft):
        return (False, "Nobody aboard holds the certificate for her "
                f"(Pilot {kind.needs}).", None)
    return True, "", craft


def launch(b, pilot: str = "") -> dict:
    """Off the cradle and into the fight.

    No `sim/conn` flight: inside an engagement the craft is on the tactical
    plane with everybody else, and where she is is *in among them*. The
    sortie's free flight (`sim/craft.launch`) is the other thing a cradle is
    for, and the two do not run at once.
    """
    ok, why, craft = may_launch(b)
    if not ok:
        return {"ok": False, "why": why}
    game = b.game
    pilot = pilot or craft_sim.who_flies(game, craft)
    craft.state, craft.pilot = "out", pilot
    craft.sorties += 1
    craft.fuel = max(0.0, craft.fuel - craft_sim.STRIKE_T)
    who = craft_sim.name_of(game, pilot)
    _say(b, f"{craft.name} drops off the cradle with {who} flying, "
            f"and comes round onto {b.enemy_name}.", "good")
    return {"ok": True, "craft": craft, "who": who}


def may_recall(b) -> tuple:
    """May she be called in? `(ok, why)`."""
    game = getattr(b, "game", None) if b is not None else None
    craft = flying(game)
    if b is None or b.over or craft is None:
        return False, "Nothing is out."
    return True, ""


def recall(b) -> dict:
    """Call her in: the cradle deck takes her, and she makes no run."""
    ok, why = may_recall(b)
    if not ok:
        return {"ok": False, "why": why}
    craft = flying(b.game)
    home(b.game)
    _say(b, f"{craft.name} breaks off and comes in. The cradle has her.", "")
    return {"ok": True, "craft": craft}


def on_the_bridge(b) -> tuple:
    """Is the captain where a station order can be given from?

    A captain who is flying is in a cockpit, not on the bridge: the seats
    are held by the officers until she is called in. Only the *station*
    orders are refused — the gunner keeps working and the ship keeps
    fighting, which is what makes sending an officer instead the obvious
    thing to have done.
    """
    game = getattr(b, "game", None) if b is not None else None
    if game is None or "captain" not in craft_sim.away(game):
        return True, ""
    craft = flying(game)
    return False, (f"You are flying {craft.name}, not conning "
                   f"{b.player.ship.name}. Call her in to take a station.")


def run(b, rng) -> None:
    """The craft's turn: one run in, and whatever comes back out.

    Called from `sim/combat` where the consorts run, because a flight is the
    same kind of thing — something of yours that fights on its own account
    while you fight the ship.
    """
    game = getattr(b, "game", None)
    craft = flying(game)
    if craft is None or b.over or is_destroyed(b.enemy.ship):
        return
    kind = craft_sim.kind_of(craft)
    if craft.fuel <= craft_sim.STRIKE_T:
        _say(b, f"{craft.name} is dry and breaks off.", "warn")
        home(game)
        return
    craft.fuel = max(0.0, craft.fuel - craft_sim.STRIKE_T)
    craft.struck += 1
    who = craft_sim.name_of(game, craft.pilot)
    rating = max(0, craft_sim.rating(game, craft.pilot))
    weight = sum(sum(rng.int(1, 6) for _n in range(dice))
                 for _name, dice in kind.guns) + rating * RATING_BITE
    # Their armour soaks it with the same floor a shell gets (`sim/shooting`,
    # where the 15% floor is argued): a stinger does not get to ignore
    # plating because it is bolted to something small.
    weight = max(weight * ARMOUR_FLOOR, weight - abilities.armour_of(b.enemy))
    # Then through the same door gunnery uses, so a run strips layers,
    # breaches a hull and feeds its adaptation exactly as a shell does.
    dealt = _apply_to_layers(b, b.enemy, weight, (), rng)
    b.enemy.taken += dealt
    b.player.dealt += dealt
    b.enemy.resolve -= RUN_NERVE
    _say(b, f"{craft.name} runs in on {b.enemy_name}: {dealt:.0f} along "
            "her flank.", "good")
    if is_destroyed(b.enemy.ship):
        return
    _answer(b, rng, craft, kind, who)


def _answer(b, rng, craft, kind, who: str) -> None:
    """The enemy's close-in fire, at something the size of a launch."""
    mounts = len([w for w in b.enemy.st.weapons if w.wpn])
    dice = max(ANSWER_LEAST, min(ANSWER_MOST, 2 + PER_MOUNT * mounts))
    back = max(0, sum(rng.int(1, 6) for _n in range(dice)) - kind.armour)
    if b.enemy.blind:
        # Armour first, then the dazzle: a blinded gunlayer misses, it does
        # not make her plating thicker twice over.
        back = int(back * BLIND_SHARE)
        _say(b, f"Dazzled, they shoot at where {who} was.", "dim")
    if not back:
        _say(b, f"Nothing they have can get on {who}.", "dim")
        return
    craft.hp = max(0, craft.hp - back)
    if craft.hp > 0:
        _say(b, f"{craft.name} takes {back} coming out — {craft.hp} of "
                f"{kind.hull} left in her.", "warn")
        return
    _lose(b, craft, who)


def _lose(b, craft, who: str) -> None:
    """Shot down: the seat gets the pilot clear, and that is all it gets."""
    game = b.game
    key = craft.pilot or "captain"
    craft_sim.lose(game, f"shot down by {b.enemy_name}")
    hurt = dict(getattr(game, "wounds", None) or {})
    who_key = "captain" if key == "captain" else key.split(":")[-1]
    hurt[who_key] = round(float(hurt.get(who_key, 0.0)) + PILOT_HURT, 1)
    game.wounds = hurt
    b.player.resolve -= LOST_NERVE
    _say(b, f"{craft.name} comes apart. {who} is clear of her, and hurt.",
         "bad")


def home(game) -> dict:
    """Back on the cradle, and the tank filled from the hull's own hold."""
    craft = flying(game)
    if craft is None:
        return {"ok": False, "why": "Nothing is out."}
    craft.state, craft.pilot = "cradled", ""
    return {"ok": True, "fuelled": round(craft_sim.top_up(game, craft), 2)}


# ── and theirs ─────────────────────────────────────────────────────────────

#: Hands a hull needs before it keeps a cradle of its own, and the most any
#: of them launches at you. A patrol boat carries none; a cruiser carries a
#: flight, and you will know about it.
CARRIER_CREW, THEIR_MOST = 40, 3
#: What one of theirs has in it, what it makes a run with, and what your
#: close-in fire needs to roll to knock one down.
THEIR_HULL, THEIR_DICE, KNOCK_DOWN = 14, 3, 9


def fit_flight(b, rng) -> int:
    """Whether the hull you are fighting carries craft, and how many.

    Off the chassis, so it is the same answer every time you meet that class
    and a silhouette means something: a hull with the hands to work a cradle
    deck has one. `sim/combat.start` asks once.
    """
    if rng is None or b.enemy.ship is None:
        return 0
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(getattr(b.enemy.ship, "chassis", ""))
    rated = getattr(chassis, "crew", 0) or 0
    if rated < CARRIER_CREW:
        return 0
    many = min(THEIR_MOST, 1 + rated // CARRIER_CREW)
    b.enemy_flight = [THEIR_HULL] * many
    _say(b, f"{many} launch{'es' if many != 1 else ''} drop off "
            f"{b.enemy_name}'s flank and come round at you.", "bad")
    return many


def their_run(b, rng) -> None:
    """Their flight's turn: a run at you, and your close-in fire answers.

    The mirror of `run`, and deliberately thinner: you do not fly theirs, so
    what matters is that a carrier is a different kind of fight — damage
    that arrives however the range track stands, and a reason for a hull to
    carry mounts it can spare for the sky.
    """
    flight = list(getattr(b, "enemy_flight", []) or [])
    if not flight or b.over or is_destroyed(b.enemy.ship):
        return
    weight = sum(sum(rng.int(1, 6) for _n in range(THEIR_DICE))
                 for _one in flight)
    weight = max(weight * ARMOUR_FLOOR, weight - abilities.armour_of(b.player))
    dealt = _apply_to_layers(b, b.player, weight, (), rng)
    b.player.taken += dealt
    b.enemy.dealt += dealt
    _say(b, f"{b.enemy_name}'s flight runs in: {dealt:.0f} across your "
            "plating.", "bad")
    if is_destroyed(b.player.ship):
        return
    # Your own close-in fire, off the mounts you have: one of theirs at a
    # time, which is what makes a second mount worth fitting.
    mounts = len([w for w in b.player.st.weapons if w.wpn])
    if not mounts or b.player.blind:
        return
    for index in range(len(flight)):
        if rng.int(1, 6) + rng.int(1, 6) + mounts < KNOCK_DOWN:
            continue
        flight[index] = 0
        _say(b, "One of theirs comes apart under the close-in fire.", "good")
        break
    b.enemy_flight = [hp for hp in flight if hp > 0]
    if not b.enemy_flight:
        _say(b, f"{b.enemy_name}'s flight is gone.", "good")
        b.enemy.resolve -= RUN_NERVE * 2


def settle(game, result: str = "") -> dict:
    """The engagement is over: whatever is still flying comes home.

    `sim/aftermath` calls it however the fight ended — taken, driven off,
    talked down or run from. A craft left "out" after the battle would be a
    boat the crossing could not use (`sim/crossing.has_boat`) and a sortie
    with no flight behind it. The one ending that is not a homecoming is the
    hull's own: a cradle that is gone cannot take her back.
    """
    craft = flying(game)
    if craft is None:
        return {"ok": False, "why": "Nothing is out."}
    if result == "lost":
        craft_sim.lose(game, "lost with the ship she flew off")
        return {"ok": True, "lost": True}
    got = home(game)
    game.add_log(f"{craft.name} is back on the cradle.", "good")
    return got
