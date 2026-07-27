"""Interactive 3D-model gallery page for the local viewer.

Renders a dark-field page that loads the exported GLB models with Google's
<model-viewer> web component — real lit, rotatable, zoomable 3D (and AR on a
phone). Served by app.py at /models, with the GLB/OBJ/STL files under /models/.

The model-viewer script loads from a CDN, so this page needs a network
connection; the .glb/.obj/.stl files themselves are local and work offline in
any 3D tool.
"""

# (key, display name, one-line description)
MODELS = [
    ("navis", "NAVIS", "Crewed explorer — 120 m × 50 m grown spheroid"),
    ("arca", "ARCA", "Million-person spin-gravity drum, 5 × 10 km"),
    ("lichen", "LICHEN", "Settlement grown into planetary regolith"),
    ("gravid", "GRAVID", "Nursery — cradles gestating vessels on a spine"),
    ("spore", "SPORE", "One-to-two person lifeboat pod"),
    ("leviathan", "LEVIATHAN", "Interstellar ark — 12 drums on a spine"),
    ("testudo", "TESTUDO", "Armoured escort — a regrowing carapace"),
]

_CDN = "https://unpkg.com/@google/model-viewer@3.5.0/dist/model-viewer.min.js"


def render():
    buttons = "".join(
        f'<button data-k="{k}" data-d="{d}"{" class=on" if i == 0 else ""}>{n}</button>'
        for i, (k, n, d) in enumerate(MODELS)
    )
    first = MODELS[0]
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>GESTALT · Interactive 3D Models</title>
<script type=module src="{_CDN}"></script>
<style>
  :root{{--ground:#0a1512;--ground2:#0e1c18;--ink:#e2f0e8;--ink2:#a9c2b6;--ink3:#7c9689;
    --line:rgba(150,196,176,.16);--line2:rgba(150,196,176,.30);--chloro:#54cf7c;--lumen:#4fd6d0;
    --mono:ui-monospace,'SF Mono',Menlo,monospace;--serif:'Iowan Old Style',Palatino,Georgia,serif}}
  *{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(900px 600px at 80% -8%,rgba(84,207,124,.10),transparent 60%),var(--ground);
    color:var(--ink);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;min-height:100vh}}
  .wrap{{max-width:1080px;margin:0 auto;padding:20px 20px 60px}}
  .nav{{font-family:var(--mono);font-size:11px;letter-spacing:.08em}}
  .nav a{{color:var(--ink3);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:3px 10px}}
  .brand{{color:var(--chloro);letter-spacing:.16em;text-transform:uppercase;margin-right:10px}}
  h1{{font-family:var(--serif);font-size:clamp(1.7rem,4vw,2.5rem);margin:.3em 0 .1em}}
  .kick{{font-family:var(--mono);font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--chloro);margin:0}}
  .sub{{color:var(--ink2);max-width:70ch;margin:.4em 0 16px}}
  .bar{{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 14px}}
  button{{font-family:var(--mono);font-size:12px;color:var(--ink2);background:var(--ground2);border:1px solid var(--line);
    border-radius:999px;padding:6px 13px;cursor:pointer;transition:color .15s,border-color .15s}}
  button:hover{{color:var(--ink);border-color:var(--line2)}}button.on{{color:var(--chloro);border-color:var(--chloro)}}
  .stage{{border:1px solid var(--line2);border-radius:14px;overflow:hidden;background:linear-gradient(180deg,var(--ground2),var(--ground))}}
  model-viewer{{width:100%;height:min(66vh,560px);--poster-color:transparent}}
  .meta{{display:flex;flex-wrap:wrap;gap:8px 18px;align-items:baseline;margin:12px 2px}}
  .meta h2{{font-family:var(--serif);font-size:1.3rem;margin:0}}
  .meta .d{{color:var(--ink2);font-size:.95rem}}
  .dl{{margin-left:auto;font-family:var(--mono);font-size:11px}}
  .dl a{{color:var(--lumen);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:3px 10px;margin-left:6px}}
  .foot{{font-family:var(--mono);font-size:10.5px;color:var(--ink3);margin-top:22px;border-top:1px solid var(--line);padding-top:14px;max-width:80ch}}
</style></head>
<body><div class=wrap>
  <p class=nav><span class=brand>◈ GESTALT</span><a href="/">← all documents</a></p>
  <p class=kick>Interactive · drag to orbit · scroll to zoom · view in AR on a phone</p>
  <h1>GESTALT — Working 3D Models</h1>
  <p class=sub>Real, lit 3D models of the grown-vehicle designs, exported to glTF. Rotate and zoom
  them here, or download the <b>.glb</b> / <b>.obj</b> / <b>.stl</b> to open in Blender, a game
  engine, an online glTF viewer, or a 3D printer.</p>
  <div class=bar id=bar>{buttons}</div>
  <div class=stage>
    <model-viewer id=mv src="/models/{first[0]}.glb" alt="GESTALT {first[1]} 3D model"
      camera-controls auto-rotate rotation-per-second="18deg" shadow-intensity="0.9"
      exposure="1.05" environment-image="neutral" ar ar-modes="webxr scene-viewer quick-look"
      touch-action="pan-y"></model-viewer>
  </div>
  <div class=meta>
    <h2 id=name>{first[1]}</h2><span class=d id=desc>{first[2]}</span>
    <span class=dl>download:
      <a id=glb href="/models/{first[0]}.glb">glb</a>
      <a id=obj href="/models/{first[0]}.obj">obj</a>
      <a id=stl href="/models/{first[0]}.stl">stl</a></span>
  </div>
  <p class=foot>Colour key — green = living / photosynthetic · cyan = engineered systems · amber =
  structure &amp; docking · grey = rock · shell = armour · warm = radiator. Concept models to the
  reference proportions, generated by <span style="color:var(--ink2)">models3d/</span> (trimesh).
  If the viewer stays blank, you are offline — the .glb files still open in any 3D tool.</p>
</div>
<script>
  var mv=document.getElementById('mv'), bar=document.getElementById('bar');
  bar.addEventListener('click', function(e){{
    var b=e.target.closest('button'); if(!b) return;
    var k=b.dataset.k;
    [].forEach.call(bar.children, function(x){{x.classList.toggle('on', x===b);}});
    mv.src='/models/'+k+'.glb'; mv.alt='GESTALT '+b.textContent+' 3D model';
    document.getElementById('name').textContent=b.textContent;
    document.getElementById('desc').textContent=b.dataset.d;
    document.getElementById('glb').href='/models/'+k+'.glb';
    document.getElementById('obj').href='/models/'+k+'.obj';
    document.getElementById('stl').href='/models/'+k+'.stl';
  }});
</script>
</body></html>"""
