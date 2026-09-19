"""The suites, as pytest sees them: one pytest test per `Suite`.

    pytest                                   # every suite, from the repo root
    pytest -k "combat or window"             # by suite key
    pytest --durations=10 --junitxml=out.xml
    SEEDFALL_INPROCESS=1 pytest --cov=seedfall -k sim

Not a migration. `harness.Suite` and `python -m seedfall.tests` stay the
source of truth — the checks, their order and their report are theirs — and
this file only hands each suite to pytest so the things pytest is good at
(selection, `--durations`, junit for CI, pytest-cov, xdist's `-n`) come
free. It is the only file pytest collects: `python_files` in
`pyproject.toml` names it, because the ~220 `test_*.py` modules are
suites, not pytest modules: collecting them imports every one to find no
pytest tests at all, and needs PyQt6 merely to look at the ones that
import it at the top.

**A process per suite by default**, the same `--child` the runner's `-j`
uses: a suite that segfaults fails one test, not the session, and no
window outlives its suite into the next. `SEEDFALL_INPROCESS=1` runs them
in this process instead, which is what `--cov` needs to see anything.
`SEEDFALL_REQUIRE_QT=1` is `--require-qt`.

Named so that no suite key is a substring of the node id: `-k` matches
substrings, and this was `pytest_suites.py::test_suite` until
`pytest -k ui` selected all 201 suites, "ui" being in "suite".
"""

from __future__ import annotations

import os

import pytest

from .runner import run_child, run_here
from .suites import SUITES

INPROCESS = os.environ.get("SEEDFALL_INPROCESS", "") not in ("", "0")
REQUIRE_QT = os.environ.get("SEEDFALL_REQUIRE_QT", "") not in ("", "0")


@pytest.mark.parametrize("spec", SUITES, ids=[s.key for s in SUITES])
def test(spec):
    if INPROCESS:
        from .__main__ import _tidy
        out = run_here(spec, REQUIRE_QT)
        _tidy()
    else:
        out = run_child(spec, require_qt=REQUIRE_QT)
        print(out.output)
    if out.status == "skip":
        pytest.skip(f"{spec.key}: needs PyQt6")
    assert out.good, (f"{spec.key} ({spec.label}): {out.status}, "
                      f"{out.failed} failed of {out.passed + out.failed}\n"
                      f"{out.output}")
