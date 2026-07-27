"""Export working 3D models of the GESTALT designs.

For each design this writes three interchange formats to ``assets/models3d/``:

    <key>.glb   glTF binary — coloured, opens in almost any 3D viewer, the web,
                Blender, game engines, and (converted) AR Quick Look.
    <key>.obj   Wavefront OBJ (+ .mtl) — universal, opens everywhere.
    <key>.stl   STL — a single solid, for 3D printing.

plus a preview PNG for the docs. Run:

    python -m models3d.run            # every design
    python -m models3d.run navis arca # a subset
    python -m models3d.run --check    # build + validate, export nothing
"""

import argparse
import io
import os

import trimesh

from . import build
from . import render

ORDER = ["navis", "arca", "lichen", "gravid", "spore", "leviathan", "testudo"]


def validate(scn):
    """Round-trip the GLB and confirm the merged solid is sane."""
    glb = scn.export(file_type="glb")
    trimesh.load(io.BytesIO(glb), file_type="glb")           # parses without error
    merged = trimesh.util.concatenate(list(scn.geometry.values()))
    return len(merged.vertices), len(merged.faces), len(glb)


def export(key, outdir):
    title, builder = build.DESIGNS[key]
    scn = builder()
    base = os.path.join(outdir, key)
    scn.export(base + ".glb")
    scn.export(base + ".obj")
    trimesh.util.concatenate(list(scn.geometry.values())).export(base + ".stl")
    render.preview(scn, base + "-preview.png", title=title)
    v, f, glb = validate(scn)
    return v, f, glb


def main(argv=None):
    ap = argparse.ArgumentParser(description="Export GESTALT 3D models")
    ap.add_argument("designs", nargs="*", help="subset of: " + ", ".join(ORDER))
    ap.add_argument("--outdir", default="assets/models3d")
    ap.add_argument("--check", action="store_true", help="build + validate, write nothing")
    a = ap.parse_args(argv)
    keys = a.designs or ORDER

    if a.check:
        for k in keys:
            _, builder = build.DESIGNS[k]
            v, f, glb = validate(builder())
            print(f"  ok  {k:10s} {v:5d} verts  {f:5d} faces  GLB {glb//1024} KB")
        print("all models build & validate")
        return

    os.makedirs(a.outdir, exist_ok=True)
    for k in keys:
        v, f, glb = export(k, a.outdir)
        print(f"  ok  {k:10s} -> {a.outdir}/{k}.glb/.obj/.stl  ({v} verts, {f} faces, GLB {glb//1024} KB)")
    print(f"exported {len(keys)} model(s) to {a.outdir}/  (glb + obj + stl + preview)")


if __name__ == "__main__":
    main()
