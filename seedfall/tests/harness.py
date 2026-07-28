"""A very small check runner.

No pytest dependency: the project ships with a plain-stdlib test entry point so
``python -m seedfall.tests`` works anywhere the game itself does.
"""

from __future__ import annotations

import traceback


class Suite:
    def __init__(self, name: str):
        self.name = name
        self.passed: list[str] = []
        self.failed: list[str] = []

    def check(self, label: str):
        """Decorator: run the function immediately and record the outcome."""
        def wrap(fn):
            try:
                detail = fn()
                self.passed.append(f"  ok   {label}" + (f" — {detail}" if detail else ""))
            except Exception as err:                       # noqa: BLE001
                tb = traceback.format_exc().strip().splitlines()
                where = next((l.strip() for l in reversed(tb)
                              if l.strip().startswith("File")), "")
                self.failed.append(f"  FAIL {label}\n       {err}\n       {where}")
            return fn
        return wrap

    def report(self) -> bool:
        print(f"── {self.name} " + "─" * max(0, 54 - len(self.name)))
        for line in self.passed:
            print(line)
        for line in self.failed:
            print(line)
        if self.failed:
            print(f"\n  {len(self.failed)} FAILED, {len(self.passed)} passed\n")
            return False
        print(f"  all {len(self.passed)} checks passed\n")
        return True
