"""Every `module.name` the tree reads is a name that module has.

An import check cannot see this: `from ..sim import conn as conn_sim` imports
fine, and `conn_sim.orbit_note` fails only when the line runs. The 2026-09
unused-import sweep removed six re-exports that callers read that way
(`conn.orbit_note`, `conn.target_from_contact`, four `works3d` constants) and
33 checks failed at runtime; this finds the same shape statically, in
seconds, for every file.

Two readings are not errors: an alias guarded by `hasattr(alias, "name")` in
the same file (a deliberate probe), and an alias rebound as a local variable
(a `threat` that is a collision reading, not `sim/threat`).
"""

from __future__ import annotations

import ast
import importlib
import pathlib

from .harness import Suite

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _aliases(tree, pkg: str) -> dict:
    """alias -> module, for every `from <pkg> import <module>` in a file."""
    out = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.level:
            continue
        parts = pkg.split(".")[:len(pkg.split(".")) - node.level + 1]
        base = ".".join(parts + ([node.module] if node.module else []))
        for a in node.names:
            try:
                out[a.asname or a.name] = importlib.import_module(
                    f"{base}.{a.name}")
            except ImportError:
                pass                     # a name, not a module: not ours
    return out


def _probed(tree) -> set:
    """(alias, name) pairs a `hasattr` in this file asks about first."""
    out = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") ==
                "hasattr" and len(node.args) == 2
                and isinstance(node.args[0], ast.Name)
                and isinstance(node.args[1], ast.Constant)):
            out.add((node.args[0].id, node.args[1].value))
    return out


def _rebound(tree) -> set:
    """Names assigned to anywhere in the file — not module aliases there."""
    return {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}


def missing() -> list:
    found = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT.parent).with_suffix("")
        here = ".".join(rel.parts)
        pkg = here if path.name == "__init__.py" else here.rsplit(".", 1)[0]
        tree = ast.parse(path.read_text())
        aliases = _aliases(tree, pkg)
        if not aliases:
            continue
        probed, rebound = _probed(tree), _rebound(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Attribute)
                    and isinstance(node.value, ast.Name)
                    and isinstance(node.ctx, ast.Load)):
                continue
            alias = node.value.id
            module = aliases.get(alias)
            if module is None or alias in rebound:
                continue
            if (alias, node.attr) in probed or hasattr(module, node.attr):
                continue
            found.append(f"{path.relative_to(ROOT)}:{node.lineno} reads "
                         f"{module.__name__}.{node.attr}")
    return found


#: Built, not written, or the check would find itself.
HOMES = tuple(f"/{top}/" for top in ("Users", "home"))


def machine_paths() -> list:
    """String literals naming somebody's home directory. `test_detection`
    ran its subprocess in "/Users/…/organic_spacecraft", which held for two
    months on one machine and failed on the first CI runner."""
    found = []
    for path in sorted(ROOT.parent.rglob("*.py")):
        if ".git" in path.parts or "site-packages" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and node.value.startswith(HOMES)):
                found.append(f"{path.relative_to(ROOT.parent)}:{node.lineno}")
    return found


def run(suite: Suite) -> None:
    @suite.check("every module.name the tree reads is a name that module has")
    def _():
        gone = missing()
        assert not gone, f"{len(gone)} read(s) of a name that is not there: {gone[:6]}"
        files = sum(1 for _ in ROOT.rglob("*.py"))
        assert files > 500, f"only {files} files scanned"
        return f"{files} files scanned, every module attribute read exists"

    @suite.check("no source file names a machine's own home directory")
    def _():
        found = machine_paths()
        assert not found, found[:6]
        return "every path is derived, none written out"
