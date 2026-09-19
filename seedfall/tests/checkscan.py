"""Reading the checks themselves for the shapes that pass without looking.

Not a suite: a helper the `harness` suite calls. It parses every check file
and finds the `@check` functions whose assertions cannot fail for the reason
they were written, because nothing they assert is ever reached.

**A loop is where a check goes to pass on nothing.** `for row in rows: assert
row.ok` is green when `rows` is empty, and `rows` is exactly what goes empty
when the thing under test breaks — a filter that matches nothing, a sector
seeded with no port, a screen that builds no buttons. Counted when this went
in: 86 checks had every assertion inside a loop and none outside it.

The fix is one line before the loop — `assert rows, "..."`, or a counted
minimum where the number matters — so the scan asks only that *some*
assertion stands outside every loop. A loop over a literal (`for kind in
("a", "b"):`, `range(3)`) cannot run zero times and is not counted as one.
"""

from __future__ import annotations

import ast
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def _is_check(fn: ast.FunctionDef) -> bool:
    """`@check("...")` or `@suite.check("...")`, the two spellings in use."""
    for dec in fn.decorator_list:
        call = dec.func if isinstance(dec, ast.Call) else dec
        name = getattr(call, "id", None) or getattr(call, "attr", None)
        if name == "check":
            return True
    return False


def _label(fn: ast.FunctionDef) -> str:
    for dec in fn.decorator_list:
        if isinstance(dec, ast.Call) and dec.args:
            arg = dec.args[0]
            if isinstance(arg, ast.Constant):
                return str(arg.value)
            if isinstance(arg, ast.JoinedStr):
                return "".join(v.value if isinstance(v, ast.Constant) else "{…}"
                               for v in arg.values)
    return fn.name


def _cannot_be_empty(loop: ast.AST) -> bool:
    """A loop whose iterable is written out in the source runs at least once."""
    if isinstance(loop, ast.While):
        return False
    it = loop.iter
    if isinstance(it, (ast.Tuple, ast.List, ast.Set)):
        return bool(it.elts)
    if isinstance(it, ast.Dict):
        return bool(it.keys)
    if isinstance(it, ast.Call) and getattr(it.func, "id", "") in (
            "range", "enumerate", "sorted", "zip", "reversed"):
        inner = it.args[0] if it.args else None
        if getattr(it.func, "id", "") == "range":
            last = it.args[-1] if len(it.args) == 1 else it.args[1] if it.args else None
            return isinstance(last, ast.Constant) and isinstance(last.value, int) \
                and last.value > (it.args[0].value if len(it.args) > 1
                                  and isinstance(it.args[0], ast.Constant) else 0)
        if inner is not None:
            fake = ast.For(target=loop.target, iter=inner, body=[], orelse=[])
            return _cannot_be_empty(fake)
    return False


def _asserts(fn: ast.FunctionDef, helpers: dict | None = None
             ) -> tuple[int, int]:
    """(assertions outside every possibly-empty loop, assertions inside one).

    A call to a module-level `helpers` function that itself asserts outside
    a loop counts as an assertion where it is called: a check that hands its
    work to `_hints(...)` is judged by `_hints`.
    """
    counts = [0, 0]
    helpers = helpers or {}

    def visit(node, looped: bool) -> None:
        if node is not fn and isinstance(node, (ast.FunctionDef, ast.Lambda,
                                                ast.AsyncFunctionDef,
                                                ast.ClassDef)):
            return          # a nested def runs only if something calls it
        if isinstance(node, ast.Assert) or (
                isinstance(node, ast.Raise) and node.exc is not None
                and "AssertionError" in ast.dump(node.exc)):
            counts[looped] += 1
        if isinstance(node, ast.Call) and helpers.get(
                getattr(node.func, "id", None)):
            counts[looped] += 1
        if isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            visit(node.test if isinstance(node, ast.While) else node.iter, looped)
            inner = looped or not _cannot_be_empty(node)
            for part in node.body:
                visit(part, inner)
            for part in node.orelse:
                visit(part, looped)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, looped)

    visit(fn, False)
    return counts[0], counts[1]


def checks(paths=None):
    """Yield (file, line, label, outside, inside) for every `@check`."""
    for path in sorted(paths or HERE.glob("test_*.py")):
        tree = ast.parse(path.read_text())
        helpers = {fn.name: _asserts(fn)[0] for fn in tree.body
                   if isinstance(fn, ast.FunctionDef)}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and _is_check(node):
                out, inside = _asserts(node, helpers)
                yield path.name, node.lineno, _label(node), out, inside


def loop_only(paths=None) -> list:
    """Checks with assertions, every one of them inside a loop that can be
    empty, and none outside it: they pass on zero iterations."""
    return [(f, n, label) for f, n, label, out, inside in checks(paths)
            if inside and not out]


def assertion_free(paths=None) -> list:
    """Checks with no assertion of their own at all."""
    return [(f, n, label) for f, n, label, out, inside in checks(paths)
            if not inside and not out]
