"""GESTALT document viewer — a zero-dependency local web server.

Serves a themed landing page at /, and each document at /d/<slug>, wrapping the
published-artifact fragments into standalone HTML and rewriting cross-document
links to local routes. Standard library only (http.server); no install needed.

Usage:
    python viewer/app.py            # serve on http://127.0.0.1:8731
    python viewer/app.py -p 9000    # choose a port
    python viewer/app.py --open     # also open a browser tab
    python viewer/app.py --check    # validate all docs load, then exit

Run from the project root or the viewer/ directory — paths are resolved
relative to this file, so either works.
"""

import argparse
import sys
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import index  # noqa: E402
from catalog import BY_SLUG, artifact_id_to_slug  # noqa: E402
from wrap import wrap  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"
ID_TO_SLUG = artifact_id_to_slug()


def load_document(slug):
    """Return the wrapped standalone HTML for a slug, or None if unknown."""
    doc = BY_SLUG.get(slug)
    if doc is None:
        return None
    path = DOCS_DIR / doc.filename
    if not path.is_file():
        return None
    fragment = path.read_text(encoding="utf-8")
    return wrap(fragment, f"GESTALT · {doc.title}", doc.favicon, ID_TO_SLUG)


def _not_found(slug):
    links = "".join(
        f'<li><a href="/d/{s}">{d.title}</a></li>' for s, d in BY_SLUG.items()
    )
    return (
        "<!doctype html><meta charset=utf-8><title>Not found</title>"
        "<body style='font-family:sans-serif;max-width:40em;margin:4em auto'>"
        f"<h1>No document '{slug}'</h1><p>Available documents:</p>"
        f"<ul>{links}</ul><p><a href='/'>← index</a></p></body>"
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "GestaltViewer/1.0"

    def _send(self, body, status=200):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0].rstrip("/")
        if path in ("", "/index.html"):
            return self._send(index.render())
        if path.startswith("/d/"):
            slug = path[3:]
            html = load_document(slug)
            if html is None:
                return self._send(_not_found(slug), status=404)
            return self._send(html)
        return self._send(_not_found(path.lstrip("/")), status=404)

    do_HEAD = do_GET

    def log_message(self, fmt, *args):  # quieter, single-line logging
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


def check():
    """Validate that every catalogued document exists and wraps cleanly."""
    ok = True
    for slug, doc in BY_SLUG.items():
        html = load_document(slug)
        if html and "<body" in html and len(html) > 500:
            print(f"  ok   /d/{slug:12s} {doc.filename} ({len(html):,} bytes)")
        else:
            print(f"  FAIL /d/{slug:12s} {doc.filename}")
            ok = False
    idx = index.render()
    print(f"  ok   /             index ({len(idx):,} bytes)")
    return ok


def main(argv=None):
    ap = argparse.ArgumentParser(description="Serve the GESTALT documents locally.")
    ap.add_argument("-p", "--port", type=int, default=8731)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--open", action="store_true", help="open a browser tab")
    ap.add_argument("--check", action="store_true",
                    help="validate all documents load, then exit")
    args = ap.parse_args(argv)

    if args.check:
        sys.exit(0 if check() else 1)

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"GESTALT viewer serving {len(BY_SLUG)} documents at {url}")
    print("Press Ctrl+C to stop.")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
