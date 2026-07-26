"""Wrap a published-artifact *fragment* into a standalone HTML document.

The GESTALT pages were authored for the Artifact host, which injects the
`<!doctype html>…<head>…</head><body>` skeleton and a minimal CSS reset at
publish time. The files on disk therefore start at `<style>` and contain only
head-and-body content. To view them in an ordinary browser we re-create that
skeleton here, and rewrite the inter-document `claude.ai/code/artifact/<id>`
links to local `/d/<slug>` routes so navigation stays offline.
"""

import re

# The minimal reset the artifact host applies, reproduced so pages render the
# same offline as they do when published.
RESET = (
    "*,*::before,*::after{box-sizing:border-box}"
    "html{-webkit-text-size-adjust:100%}"
    "body{margin:0;min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,"
    "'Segoe UI',Roboto,Helvetica,Arial,sans-serif;line-height:1.5}"
    "img,svg,video{max-width:100%;height:auto}"
    "a{color:inherit}"
    "table{border-collapse:collapse}"
)

SKELETON = (
    "<!doctype html>\n<html lang=\"en\">\n<head>\n"
    "<meta charset=\"utf-8\">\n"
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
    "<title>{title}</title>\n"
    "<link rel=\"icon\" href=\"data:image/svg+xml,"
    "<svg xmlns='http%3A//www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<text y='26' font-size='26'>{favicon}</text></svg>\">\n"
    "<style>{reset}</style>\n"
    "</head>\n<body>\n{body}\n</body>\n</html>\n"
)

_ARTIFACT_RE = re.compile(
    r"https://claude\.ai/code/artifact/([0-9a-f-]{8,})"
)


def rewrite_links(fragment, id_to_slug):
    """Rewrite artifact URLs to local /d/<slug> routes, preserving #anchors.

    A URL like https://claude.ai/code/artifact/<id>#wp4 becomes /d/<slug>#wp4.
    Unknown ids are left untouched (they still resolve online).
    """
    def repl(match):
        art_id = match.group(1)
        slug = id_to_slug.get(art_id)
        return f"/d/{slug}" if slug else match.group(0)

    return _ARTIFACT_RE.sub(repl, fragment)


def wrap(fragment, title, favicon, id_to_slug):
    """Return a complete HTML document for a fragment."""
    body = rewrite_links(fragment, id_to_slug)
    # Escape a lone favicon char safely into the SVG data URI.
    fav = favicon if favicon else "◈"
    return SKELETON.format(title=title, favicon=fav, reset=RESET, body=body)
