"""Compare every number tagged in the documents with the value calcs computes.

A document marks a checked number with an element carrying ``data-calc``:

    <span data-calc="navis.hoop">1.14</span> MN/m

The element's text is parsed as one number: ``13,400``, ``~0.65``,
``2.0×10⁵``, ``10<sup>19</sup>`` and ``−3`` all work. A number passes when it
is within the key's tolerance of the computed value, or when rounding the
computed value to the printed precision gives the printed number.
"""

import html
import math
import pathlib
import re

from .registry import all_values

DOCS = pathlib.Path(__file__).resolve().parent.parent / "docs"
TAG = re.compile(r'<(span|tspan|b|strong|td)\b[^>]*\bdata-calc="([^"]+)"[^>]*>(.*?)</\1>', re.S)
SUP = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
NUM = re.compile(r"[-+]?\d+(?:\.\d+)?")


def parse_number(inner):
    """Parse the text inside a tagged element into a float."""
    s = re.sub(r"<sup>\s*([^<]+?)\s*</sup>", lambda m: "^" + m.group(1).translate(SUP), inner)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("−", "-").replace(",", "").replace(" ", "")
    s = s.replace(" ", "").replace(" ", "").strip()
    s = re.sub(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+", lambda m: "^" + m.group(0).translate(SUP), s)
    s = s.lstrip("~≈<>≳≲ ")
    m = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s*[×x]\s*10\^(-?\d+)", s)
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    m = re.fullmatch(r"10\^(-?\d+)", s)
    if m:
        return 10.0 ** int(m.group(1))
    m = re.fullmatch(r"([-+]?\d+(?:\.\d+)?)\s*k", s)
    if m:
        return float(m.group(1)) * 1e3
    m = NUM.fullmatch(s)
    if m:
        return float(s)
    raise ValueError(f"cannot parse {inner!r}")


def _decimals(inner):
    s = re.sub(r"<[^>]+>", "", html.unescape(inner)).replace(",", "")
    m = re.search(r"\.(\d+)", s)
    return len(m.group(1)) if m else 0


def _agrees(shown, calc, v, inner):
    if v.mode == "log":
        if shown <= 0 or calc <= 0:
            return False
        return abs(math.log10(shown) - math.log10(calc)) <= v.tol
    if calc == 0:
        return shown == 0
    if abs(shown - calc) <= v.tol * abs(calc):
        return True
    # accept honest rounding to the printed precision (e.g. 13,424 -> "13,400")
    d = _decimals(inner)
    if d == 0 and shown != 0 and "×" not in inner and "10^" not in inner:
        mag = 10 ** max(0, len(str(int(abs(shown)))) - len(str(int(abs(shown))).rstrip("0")))
        return abs(round(calc / mag) * mag - shown) < 1e-9 * max(1, abs(shown))
    return round(calc, d) == round(shown, d)


def scan(docs=DOCS):
    """Yield (file, line, key, inner) for every tagged number."""
    for f in sorted(pathlib.Path(docs).glob("*.html")):
        text = f.read_text(encoding="utf-8")
        for m in TAG.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            yield f.name, line, m.group(2), m.group(3)


def check(docs=DOCS, verbose=False):
    vals = all_values()
    rows, bad = [], 0
    used = set()
    for fname, line, key, inner in scan(docs):
        used.add(key)
        v = vals.get(key)
        if v is None:
            rows.append(("MISSING", fname, line, key, inner, None))
            bad += 1
            continue
        try:
            shown = parse_number(inner)
        except ValueError as e:
            rows.append(("UNPARSED", fname, line, key, str(e), v.value))
            bad += 1
            continue
        ok = _agrees(shown, v.value, v, inner)
        bad += not ok
        rows.append(("ok" if ok else "MISMATCH", fname, line, key, shown, v.value))
    for status, fname, line, key, shown, calc in rows:
        if verbose or status != "ok":
            c = "" if calc is None else f"{calc:.4g}"
            print(f"  {status:9s} {fname}:{line:<5d} {key:30s} shown={shown!s:<12.12s} calc={c}")
    files = len({r[1] for r in rows})
    print(f"calcs --check: {len(rows)} tagged numbers in {files} documents, "
          f"{len(used)} distinct keys, {bad} problem(s)")
    return bad == 0, rows
