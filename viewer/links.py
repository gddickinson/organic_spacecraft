"""Audit the documents' links: the program nav, every artifact URL, every anchor.

The thirteen documents link to each other by published-artifact URL, and each
carries the same program nav. Nothing checked either: a document added out of
order, a renamed anchor or a stale artifact id failed silently, in a browser,
for a reader. `app.py --check` runs this, and CI runs `--check`.
"""

import re
from pathlib import Path

from catalog import BY_ARTIFACT_ID, DOCS

_URL = re.compile(r'https://claude\.ai/code/artifact/([0-9a-f-]{8,})(?:#([\w.-]+))?')
_LOCAL = re.compile(r'href="#([\w.-]+)"')
_ID = re.compile(r'\bid="([\w.-]+)"')
_NAV = re.compile(r'<nav class="prog-nav".*?</nav>', re.S)
_NAV_ITEM = re.compile(r'<a href="(#|https://claude\.ai/code/artifact/([0-9a-f-]+))"')


def audit(docs_dir: Path) -> list[str]:
    """Every problem found, as a sentence. Empty means the links hold."""
    texts = {d.slug: (docs_dir / d.filename).read_text(encoding="utf-8")
             for d in DOCS}
    ids = {slug: set(_ID.findall(text)) for slug, text in texts.items()}
    order = [d.slug for d in DOCS]
    problems = []
    for doc in DOCS:
        text = texts[doc.slug]
        nav = _NAV.search(text)
        if nav is None:
            problems.append(f"{doc.slug}: no program nav")
        else:
            seen = []
            for href, art in _NAV_ITEM.findall(nav.group(0)):
                target = BY_ARTIFACT_ID.get(art) if art else doc
                seen.append(target.slug if target else f"?{art}")
            if seen != order:
                problems.append(f"{doc.slug}: nav reads {seen}, catalog {order}")
        for art, anchor in _URL.findall(text):
            target = BY_ARTIFACT_ID.get(art)
            if target is None:
                problems.append(f"{doc.slug}: links to unknown artifact {art}")
            elif anchor and anchor not in ids[target.slug]:
                problems.append(f"{doc.slug}: #{anchor} is not in {target.slug}")
        for anchor in _LOCAL.findall(text):
            if anchor not in ids[doc.slug]:
                problems.append(f"{doc.slug}: #{anchor} is not on the page")
    return problems
