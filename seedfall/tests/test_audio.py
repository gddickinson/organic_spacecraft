"""The soundscape: made from nothing, heard on cue, silent when it should be.

Innovation 10 of review 2026-09-17. The game had no sound — "not one byte" —
and the backlog said four cues would carry more than any HUD addition. What
this suite pins:

- **the synthesiser** writes valid WAV for every cue: PCM at the cue's rate,
  the length the recipe says to within 5%, nothing at full scale, one-shots
  that start and end on zero and loops whose seam straddles zero in one
  ordinary step — in under two seconds of CPU;
- **the cache** is reused, a changed recipe remakes that cue alone, and it
  lives beside the save, wherever the save has been sent;
- **the façade** is silent offscreen, never raises, and goes quiet for good
  when a device fails;
- **the soundmap**, with a fake speaker put in through `audio.install`,
  plays the right cues through the game's own doors — see `test_soundmap`;
- **the layers**: nothing outside `ui/` imports audio, and only `ui/audio`
  imports QtMultimedia.

The four settings' efficacy is in `test_options`, where "every setting does
something" lives.
"""

from __future__ import annotations

import array
import ast
import dataclasses
import pathlib
import shutil
import sys
import tempfile
import time
import wave

from ..data.sounds import CUES, CUES_BY_ID
from ..ui import audio, synth
from .harness import Suite

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: One synthesis shared by the first two checks: it is the expensive part.
_MADE: dict = {}

#: The whole cache, in bytes. Measured at 1.56 MB; it is written to the
#: player's disk and read at the first sound, and doubling the loop rate
#: (`data/sounds.LOW`) would take it past this for nothing anyone can hear.
BUDGET = 2_000_000


def _top_hz(layer) -> float:
    """The highest frequency a layer asks for: its top partial or corner."""
    if hasattr(layer, "partials"):
        return max(layer.hz, layer.to) * max(r for r, _a in layer.partials)
    return max(layer.lp, layer.lp_to)


class Recorder:
    """A speaker that remembers instead of sounding. `audio.install` it."""

    def __init__(self):
        self.heard: list = []

    def play(self, cue: str, volume: float) -> None:
        self.heard.append(("play", cue, round(volume, 4)))

    def loop(self, cue: str, volume: float) -> None:
        self.heard.append(("loop", cue, round(volume, 4)))

    def played(self, mark: int = 0) -> list:
        """One-shots since `mark`, in order."""
        return [cue for verb, cue, _v in self.heard[mark:] if verb == "play"]

    def loops(self, mark: int = 0) -> list:
        """Loops since `mark`, as (cue, on)."""
        return [(cue, vol > 0) for verb, cue, vol in self.heard[mark:]
                if verb == "loop"]


def read(path) -> tuple[int, list]:
    """A WAV's rate and samples, checking it is the format we promised."""
    raw = pathlib.Path(path).read_bytes()
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WAVE", f"{path} is no WAV"
    with wave.open(str(path)) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getcomptype()) == (
            1, 2, "NONE"), f"{path} is not 16-bit mono PCM"
        rate = w.getframerate()
        pcm = array.array("h", w.readframes(w.getnframes()))
    if sys.byteorder == "big":
        pcm.byteswap()
    return rate, list(pcm)


#: The synthesis budget, in units of `_reference()`: 2 s of CPU on the
#: machine it was tuned on, where the reference loop takes about 0.05 s. A
#: fixed "2 s" failed on CI's shared runners (3.35 s), which are slower at
#: everything; this measures the synthesiser, not the hardware.
SYNTH_REFERENCES = 40


def _reference() -> float:
    """CPU seconds for a fixed pure-Python loop, best of three."""
    best = float("inf")
    for _ in range(3):
        start = time.process_time()
        sum(i * i % 7 for i in range(1_000_000))
        best = min(best, time.process_time() - start)
    return best


def _made():
    if not _MADE:
        folder = pathlib.Path(tempfile.mkdtemp(prefix="seedfall-sounds-"))
        cpu = time.process_time()
        files = synth.ensure(folder)
        _MADE.update(folder=folder, files=files,
                     cpu=time.process_time() - cpu, last=dict(synth.LAST))
    return _MADE


def _imports(path: pathlib.Path) -> list:
    out = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            out.append(base)
            out += [f"{base}.{a.name}" if base else a.name for a in node.names]
    return out


def _strays(files) -> list:
    """(file, what) for every import that breaks the audio layering."""
    out = []
    for rel, names in files:
        in_ui = rel.startswith("ui/")
        for name in names:
            leaf = name.split(".")[-1]
            if leaf in ("audio", "soundmap", "synth") and not in_ui:
                out.append((rel, name))
            if "QtMultimedia" in name and rel != "ui/audio.py":
                out.append((rel, name))
    return out


def run(suite: Suite) -> bool:
    """True: it ran. An optional suite returning nothing reads as skipped."""
    check = suite.check

    @check("every cue synthesises to valid WAV, within its CPU budget")
    def _():
        made = _made()
        files = made["files"]
        assert set(files) == set(CUES_BY_ID), sorted(set(CUES_BY_ID)
                                                     - set(files))
        for cue in CUES:
            rate, s = read(files[cue.id])
            assert rate == cue.rate, (cue.id, rate)
            seconds = len(s) / rate
            assert abs(seconds - cue.seconds) <= 0.05 * cue.seconds, (
                f"{cue.id} is {seconds:.3f} s against {cue.seconds} s")
            top = max(abs(v) for v in s)
            assert top < 32767 and top <= cue.peak * 32767 + 1, (
                f"{cue.id} peaks at {top}: clipped, or over its recipe")
            if cue.loop:
                # The seam: the last sample and the first straddle zero, and
                # the step across it is no bigger than any step inside. (`<=`
                # both sides: a sample a hair under zero is written as 0.)
                inside = max(abs(b - a) for a, b in zip(s, s[1:]))
                assert s[-1] <= 0 <= s[0], (cue.id, s[-1], s[0])
                assert s[0] - s[-1] <= inside, (
                    f"{cue.id}'s seam jumps {s[0] - s[-1]}, more than the "
                    f"loop's largest step of {inside}")
            else:
                assert s[0] == 0 and s[-1] == 0, (
                    f"{cue.id} starts at {s[0]} and ends at {s[-1]}: a cue "
                    "that does not begin and end on zero clicks")
            # And the rate holds what the recipe plays: halve the loop rate
            # and the attitude jets' hiss is above what the file can carry.
            over = [_top_hz(layer) for layer in cue.layers
                    if _top_hz(layer) >= rate / 2]
            assert not over, f"{cue.id} asks for {over} Hz at {rate} Hz"
        unit = _reference()
        assert made["cpu"] < SYNTH_REFERENCES * unit, (
            f"first-run synthesis took {made['cpu']:.2f} s of CPU, "
            f"{made['cpu'] / unit:.0f} reference loops of "
            f"{SYNTH_REFERENCES}")
        assert made["last"]["bytes"] < BUDGET, (
            f"the cache is {made['last']['bytes']:,} bytes")
        loops = sum(1 for c in CUES if c.loop)
        return (f"{len(files)} cues ({loops} loops), "
                f"{made['last']['bytes'] / 1e6:.2f} MB, made in "
                f"{made['cpu']:.2f} s of CPU")

    @check("the cache is reused, and a changed recipe remakes only itself")
    def _():
        made = _made()
        folder, first = made["folder"], made["files"]
        try:
            when = {cid: p.stat().st_mtime_ns for cid, p in first.items()}
            synth.ensure(folder)
            assert synth.LAST["made"] == 0, synth.LAST
            assert synth.LAST["kept"] == len(CUES), synth.LAST
            assert all(p.stat().st_mtime_ns == when[cid]
                       for cid, p in first.items()), "a cached file was remade"

            edited = tuple(dataclasses.replace(c, peak=c.peak * 0.5)
                           if c.id == "warn" else c for c in CUES)
            after = synth.ensure(folder, edited)
            assert synth.LAST["made"] == 1, synth.LAST
            assert after["warn"] != first["warn"], "the edit kept its name"
            assert not first["warn"].exists(), (
                "the old recipe's file was left behind")
            assert all(after[cid] == p for cid, p in first.items()
                       if cid != "warn")
            _rate, quieter = read(after["warn"])
            ceiling = 0.5 * CUES_BY_ID["warn"].peak * 32767 + 1
            assert max(abs(v) for v in quieter) <= ceiling, (
                "the regenerated file is not the edited recipe")

            # A renderer change remakes everything: the version is in every
            # cue's stamp.
            was = synth.SYNTH_VERSION
            try:
                synth.SYNTH_VERSION = was + 1
                bumped = {c.id: synth.stamp(c) for c in CUES}
            finally:
                synth.SYNTH_VERSION = was
            assert all(bumped[c.id] != synth.stamp(c) for c in CUES)
        finally:
            shutil.rmtree(folder, ignore_errors=True)

        # Beside the save, wherever the harness has sent it — never the home.
        from ..core import save as save_mod
        where = synth.cache_dir()
        assert where == save_mod.save_path().parent / "sounds", where
        assert save_mod.SAVE_DIR not in (where, *where.parents), (
            f"under test the sound cache would be written to {where}")
        return (f"{len(CUES)} kept on a second run, 1 remade on an edit, "
                f"cache at {where}")

    @check("the façade is silent offscreen, and never raises into a slot")
    def _():
        audio.install(None)
        assert audio.play("click") is False
        audio.loop("burn_low", True)
        audio.set_level("bloom", 0.5)
        audio.volume(0.7, 1.0, 1.0)
        quiet = audio.status()
        assert "offscreen" in quiet, quiet
        assert "PyQt6.QtMultimedia" not in sys.modules, (
            "QtMultimedia was imported with no speaker to play through")

        class Broken:
            """A device whose C++ side has gone, as a closed one does."""

            def play(self, cue, volume):
                raise RuntimeError("wrapped C/C++ object has been deleted")

            loop = play

        audio.install(Broken())
        try:
            assert audio.play("click") is False
            said = audio.status()
            assert "deleted" in said, said
            audio.set_level("amb_red", 1.0)      # not asked again, no raise
            audio.volume(0.3, 1.0, 0.0)
            assert audio.play("good") is False
            assert audio.REQUESTED.get("good") == 1 and not audio.PLAYED
        finally:
            audio.install(None)
        return f"offscreen: \"{quiet}\"; a dead device: \"{said}\""

    @check("a fake speaker hears exactly what the façade lets through")
    def _():
        ear = Recorder()
        audio.install(ear)
        try:
            audio.volume(0.5, 1.0, 1.0)
            assert audio.play("warn") is True
            audio.set_level("amb_red", 0.5)
            audio.set_level("amb_red", 0.5)      # re-asserted: no second call
            audio.loop("burn_mid", True)
            audio.volume(0.5, 0.0, 1.0)          # effects off: the burn stops
            audio.loop("burn_mid", False)
            assert ear.heard == [("play", "warn", 0.25),
                                 ("loop", "amb_red", 0.125),
                                 ("loop", "burn_mid", 0.25),
                                 ("loop", "burn_mid", 0.0)], ear.heard
            assert audio.wanted() == {"amb_red": 0.5}, audio.wanted()
        finally:
            audio.install(None)
        return "square-law master, levels once, a muted loop stopped"

    @check("nothing outside ui/ imports audio; only ui/audio imports "
           "QtMultimedia")
    def _():
        files = [(str(p.relative_to(ROOT)), _imports(p))
                 for p in sorted(ROOT.rglob("*.py"))
                 if "tests" not in p.parts and "__pycache__" not in p.parts]
        strays = _strays(files)
        assert not strays, f"audio reached past the interface: {strays}"
        synth_imports = dict(files)["ui/synth.py"]
        assert not any("PyQt6" in n for n in synth_imports), synth_imports
        # And the matcher can still see a stray when there is one.
        planted = [("sim/combat.py", ["seedfall.ui.audio"]),
                   ("ui/hud.py", ["PyQt6.QtMultimedia.QSoundEffect"]),
                   ("ui/soundmap.py", [".audio", "..sim.collision"])]
        assert [rel for rel, _n in _strays(planted)] == \
            ["sim/combat.py", "ui/hud.py"], _strays(planted)
        return f"{len(files)} modules; the synthesiser imports no Qt"

    return True
