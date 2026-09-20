"""The command line, the launcher, and what "a new chronicle" keeps.

`--help` launched the game until 2026-09, an unknown flag was ignored, and
`--new` — like the title screen's "New chronicle" — deleted the chronicle in
play, `.bak` and all, without a word. Each is checked here in the process
that would meet it: a fresh interpreter, started the way a player starts one.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

from .harness import Suite

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _run(args: list, cwd=None) -> subprocess.CompletedProcess:
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, cwd=str(cwd or ROOT), env=env, timeout=60)


def run(suite: Suite) -> None:
    check = suite.check

    @check("--help answers, exits 0, and never loads Qt")
    def _():
        probe = ("import sys\n"
                 "sys.argv = ['seedfall', '--help']\n"
                 "import seedfall.__main__ as m\n"
                 "try:\n    m.main()\n"
                 "except SystemExit as e:\n    print('EXIT', e.code)\n"
                 "print('QT', any(k.startswith('PyQt6') for k in sys.modules))")
        out = _run(["-c", probe]).stdout
        for flag in ("--new", "--seed", "--bridge", "--port", "--help"):
            assert flag in out, f"{flag} is not in the help"
        assert "EXIT 0" in out, out[-300:]
        assert "QT False" in out, "the help loaded PyQt6"
        assert "save.json" in out, "the help does not say where the save is"
        return "every flag named, the save's place said, no Qt loaded"

    @check("play.py starts the game from any folder, with the same flags")
    def _():
        with tempfile.TemporaryDirectory() as elsewhere:
            got = _run([str(ROOT / "play.py"), "--help"], cwd=elsewhere)
        assert got.returncode == 0, got.stderr[-300:]
        assert got.stdout.startswith("usage: python3 play.py"), got.stdout[:80]
        assert os.access(ROOT / "play.py", os.X_OK), "play.py is not executable"
        return "help from a temp folder, usage names play.py"

    @check("a flag it does not know is refused, not ignored")
    def _():
        from ..core import cli
        got = _run(["-m", "seedfall", "--frobnicate"])
        assert got.returncode == 2, got.returncode
        assert "--frobnicate" in got.stderr, got.stderr[-200:]
        options = cli.parse(["--seed", "verge-7", "--port", "8765"])
        assert options.new and options.seed == "verge-7"
        assert options.port == 8765 and not options.bridge
        assert not cli.parse([]).new
        return "exit 2 with the flag named; --seed implies --new"

    @check("a new chronicle keeps the one in play as a slot, byte for byte")
    def _():
        from ..core import save as save_mod
        from ..core import slots
        from ..core.state import begin_new, new_game
        old = new_game("cli-kept")
        old.advance_days(5)
        assert old.save()
        before = save_mod.save_path().read_bytes()
        fresh = begin_new("cli-fresh")
        kept = [e for e in slots.listing() if e["name"].startswith("Set aside")]
        try:
            assert len(kept) == 1, kept
            name = kept[0]["name"]
            assert slots.slot_path(name).read_bytes() == before
            assert fresh.seed == "cli-fresh" and fresh.day == 0
            assert any(name in text for _d, text, _k in fresh.log), (
                "the new chronicle's log does not say where the old one went")
            assert not save_mod.save_path().exists()
            # Nothing in play: nothing to keep, and no empty slot made.
            again = begin_new("cli-third")
            assert not [e for e in slots.listing()
                        if e["name"].startswith("Set aside")
                        and e["name"] != name]
            assert again.day == 0
        finally:
            for entry in kept:
                slots.delete(entry["name"])
        return f"kept as «{name}», identical, and the log says so"

    @check("no screen clears the save except through the one door")
    def _():
        # `begin_new` keeps what it replaces; a screen calling `clear_save`
        # itself would be back to deleting the chronicle in play.
        import ast
        ui = ROOT / "seedfall" / "ui"
        direct = []
        for path in sorted(ui.glob("*.py")):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Call):
                    fn = node.func
                    name = getattr(fn, "attr", getattr(fn, "id", ""))
                    if name == "clear_save":
                        direct.append(f"{path.name}:{node.lineno}")
        assert not direct, direct
        return "every new chronicle goes through core/loading.begin_new"
