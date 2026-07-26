"""Build the viewer's landing page — a themed index of all GESTALT documents."""

from catalog import DOCS

# Dark-field-microscopy identity, theme-aware (mirrors the documents' palette).
_STYLE = """
:root{--ground:#0a1512;--ground-2:#0e1c18;--ink:#e2f0e8;--ink-2:#a9c2b6;
--ink-3:#7c9689;--line:rgba(150,196,176,.16);--line-2:rgba(150,196,176,.30);
--chloro:#54cf7c;--lumen:#4fd6d0;--osteo:#e6ac6d}
@media(prefers-color-scheme:light){:root{--ground:#e9eee7;--ground-2:#e1e8df;
--ink:#152219;--ink-2:#3c4d43;--ink-3:#5d6f64;--line:rgba(22,54,40,.16);
--line-2:rgba(22,54,40,.30);--chloro:#1f9a4c;--lumen:#0c8079;--osteo:#a9691f}}
body{background:var(--ground);color:var(--ink);
font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
line-height:1.55}
.wrap{max-width:1040px;margin:0 auto;padding:56px 24px 80px}
.brand{font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:12px;
letter-spacing:.28em;text-transform:uppercase;color:var(--chloro)}
h1{font-family:'Iowan Old Style','Palatino Linotype',Palatino,Georgia,serif;
font-size:clamp(2.1rem,5vw,3.2rem);margin:.3em 0 .1em;letter-spacing:-.01em;
text-wrap:balance}
.lead{color:var(--ink-2);max-width:64ch;font-size:1.05rem;margin:0 0 8px}
.meta{font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:11.5px;
color:var(--ink-3);letter-spacing:.06em;margin-bottom:36px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));
gap:16px}
.card{display:block;text-decoration:none;color:inherit;background:var(--ground-2);
border:1px solid var(--line);border-radius:14px;padding:22px 22px 20px;
transition:border-color .2s,transform .2s}
.card:hover{border-color:var(--lumen);transform:translateY(-2px)}
.ct{display:flex;align-items:baseline;gap:10px;margin-bottom:8px}
.emoji{font-size:1.5rem;line-height:1}
.kind{font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:10px;
letter-spacing:.14em;text-transform:uppercase;color:var(--osteo);
margin-left:auto}
.title{font-family:'Iowan Old Style',Palatino,Georgia,serif;font-size:1.28rem;
color:var(--ink)}
.blurb{color:var(--ink-2);font-size:.92rem;margin:0}
footer{margin-top:44px;font-family:ui-monospace,'SF Mono',Menlo,monospace;
font-size:11px;color:var(--ink-3);border-top:1px solid var(--line);
padding-top:18px;display:flex;flex-wrap:wrap;gap:6px 16px}
"""


def _card(doc):
    return (
        f'<a class="card" href="/d/{doc.slug}">'
        f'<div class="ct"><span class="emoji">{doc.favicon}</span>'
        f'<span class="kind">{doc.kind}</span></div>'
        f'<div class="title">{doc.title}</div>'
        f'<p class="blurb">{doc.blurb}</p></a>'
    )


def render():
    cards = "\n".join(_card(d) for d in DOCS)
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GESTALT Program — document viewer</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http%3A//www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>◈</text></svg>">
<style>*,*::before,*::after{{box-sizing:border-box}}body{{margin:0}}{_STYLE}</style>
</head><body>
<div class="wrap">
  <div class="brand">◈ GESTALT Program</div>
  <h1>Grown Spacecraft &amp; Habitats</h1>
  <p class="lead">A conceptual design program for living, grown-from-a-seed
  spacecraft and habitats — biocomposite hulls, photosynthetic interiors, and a
  gated, mostly-fundable ground program to find out whether any of it can be built.</p>
  <p class="meta">{len(DOCS)} documents · every quantitative claim python-grounded and cited · real science, honest gaps</p>
  <div class="grid">
{cards}
  </div>
  <footer><span>Local viewer · self-contained</span><span>Cross-links resolve offline</span><span>Real science green · bets named</span></footer>
</div>
</body></html>
"""
