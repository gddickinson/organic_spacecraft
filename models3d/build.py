"""Solid, colour-coded 3D meshes of the main GESTALT designs.

Each builder returns a ``trimesh.Scene`` of named, coloured parts, built from
primitives (scaled icospheres, cylinders, cones, tori) in proportions matching
the interactive 3D document and the drawing sets. The long axis is +Z.

Colours follow the GESTALT identity: green = living / photosynthetic,
cyan = engineered systems, amber = structure & docking, grey = rock,
shell = armour, warm = radiator.

See models3d/INTERFACE.md for how the package fits together.
"""

import numpy as np
import trimesh
from trimesh import creation
from trimesh import transformations as tf

GREEN = [84, 207, 124, 255]
AMBER = [230, 172, 109, 255]
CYAN = [79, 214, 208, 255]
ROCK = [138, 128, 114, 255]
SHELL = [176, 158, 126, 255]
WARM = [214, 140, 96, 255]


# ---- primitive helpers ----
def _col(mesh, color):
    mesh.visual.face_colors = color
    return mesh


def ellipsoid(sx, sy, sz, color, subdiv=3, at=(0, 0, 0)):
    m = creation.icosphere(subdivisions=subdiv, radius=1.0)
    m.apply_scale([sx, sy, sz])
    m.apply_translation(at)
    return _col(m, color)


def dome_half(sx, sy, sz, color, at=(0, 0, 0), nu=44, nv=16):
    """Upper half of an ellipsoid — a dome / carapace, flat-capped underneath.

    Built by hand (apex + rings + a bottom fan) so it needs no triangulation
    engine, unlike slicing a full ellipsoid.
    """
    us = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    vs = np.linspace(0, np.pi / 2, nv)           # 0 = apex, pi/2 = equator (z=0)
    V = [[0, 0, sz]]                              # apex
    for k in range(1, nv):
        v = vs[k]
        for u in us:
            V.append([sx * np.sin(v) * np.cos(u), sy * np.sin(v) * np.sin(u), sz * np.cos(v)])
    F = [[0, 1 + j, 1 + (j + 1) % nu] for j in range(nu)]            # apex fan
    for i in range(nv - 2):                                          # ring bands
        r0, r1 = 1 + i * nu, 1 + (i + 1) * nu
        for j in range(nu):
            a, b, c, d = r0 + j, r0 + (j + 1) % nu, r1 + j, r1 + (j + 1) % nu
            F.append([a, b, d]); F.append([a, d, c])
    cidx = len(V); V.append([0, 0, 0.0])                            # bottom-cap centre
    last = 1 + (nv - 2) * nu
    for j in range(nu):
        F.append([last + j, last + (j + 1) % nu, cidx])
    m = trimesh.Trimesh(vertices=np.array(V, float) + np.array(at, float),
                        faces=np.array(F), process=False)
    return _col(m, color)


def cyl(r, h, color, at=(0, 0, 0), axis="z", sections=40):
    m = creation.cylinder(radius=r, height=h, sections=sections)
    if axis == "x":
        m.apply_transform(tf.rotation_matrix(np.pi / 2, [0, 1, 0]))
    elif axis == "y":
        m.apply_transform(tf.rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_translation(at)
    return _col(m, color)


def cone(r, h, color, at=(0, 0, 0), point="+z", sections=32):
    m = creation.cone(radius=r, height=h, sections=sections)   # base at z=0, apex +z
    if point == "-z":
        m.apply_transform(tf.rotation_matrix(np.pi, [1, 0, 0]))
    m.apply_translation(at)
    return _col(m, color)


def ring(major, minor, color, at=(0, 0, 0)):
    m = creation.torus(major, minor, major_sections=48, minor_sections=12)
    m.apply_translation(at)
    return _col(m, color)


def scene(parts):
    s = trimesh.Scene()
    for i, (name, m) in enumerate(parts):
        s.add_geometry(m, geom_name=f"{name}_{i}")
    return s


# ---- the designs (long axis +Z), proportioned to the drawing sets ----
def navis():
    """Crewed explorer — 120 m x 50 m prolate spheroid + appendages."""
    p = [("hull", ellipsoid(0.417, 0.417, 1.0, GREEN)),
         ("dockband", ring(0.42, 0.028, AMBER)),
         ("phototropic_cap", ellipsoid(0.13, 0.13, 0.13, CYAN, subdiv=2, at=(0, 0, 1.02))),
         ("radiator_bloom", cone(0.42, 0.55, WARM, at=(0, 0, -1.55), point="+z")),
         ("mining_root", cone(0.12, 0.55, CYAN, at=(0, 0, -1.05), point="-z")),
         ("resource_anchor", ellipsoid(0.17, 0.17, 0.17, ROCK, subdiv=2, at=(0, 0, -1.72)))]
    return scene(p)


def arca():
    """Million-person spin drum, 5 km x 10 km."""
    p = [("drum", cyl(0.5, 2.0, GREEN, sections=56)),
         ("cap_fore", ring(0.5, 0.03, AMBER, at=(0, 0, 1.0))),
         ("cap_aft", ring(0.5, 0.03, AMBER, at=(0, 0, -1.0))),
         ("sun_cord", cyl(0.03, 1.94, CYAN, sections=16))]
    return scene(p)


def lichen():
    """Surface dome on regolith."""
    p = [("dome", dome_half(1.0, 1.0, 0.62, GREEN)),
         ("regolith", cyl(2.1, 0.05, ROCK, at=(0, 0, -0.025), sections=56)),
         ("light_shaft", cyl(0.04, 0.6, CYAN, at=(0, 0, 0.3)))]
    return scene(p)


def gravid():
    """Nursery — feedstock spine with cradles budding on alternating sides."""
    p = [("feedstock_spine", cyl(0.08, 2.2, CYAN, sections=20))]
    n = 5
    for i in range(n):
        z = -0.9 + i * 0.45
        r = 0.30 + 0.04 * np.sin(i * 1.3)
        col = GREEN if i == n - 1 else AMBER
        p.append((f"cradle_{i}", ellipsoid(r, r, r * 0.95, col, subdiv=2, at=(0.55, 0, z))))
        p.append((f"cradle_alt_{i}", ellipsoid(r * 0.85, r * 0.85, r * 0.8, AMBER, subdiv=2,
                                               at=(-0.55, 0, z + 0.22))))
    return scene(p)


def spore():
    """One-to-two person lifeboat — a small egg-ovoid."""
    m = creation.icosphere(subdivisions=3, radius=1.0)
    v = m.vertices
    v[:, 2] *= 0.85
    v[:, 0] *= 0.6 * (1 + 0.16 * v[:, 2])   # taper: wider at the base
    v[:, 1] *= 0.6 * (1 + 0.16 * v[:, 2])
    m.vertices = v
    return scene([("pod", _col(m, GREEN))])


def leviathan():
    """Interstellar ark — a siphonophore of 12 drums on one spine."""
    p = [("spine", cyl(0.06, 2.5, CYAN, sections=16))]
    for i in range(12):
        row = i // 2
        side = 1 if i % 2 == 0 else -1
        z = -1.0 + row * 0.4
        x = side * 0.7
        p.append((f"drum_{i}", cyl(0.30, 0.46, GREEN, at=(x, 0, z), sections=28)))
        p.append((f"strut_{i}", cyl(0.03, 0.7, AMBER, at=(x * 0.5, 0, z), axis="x", sections=10)))
    return scene(p)


def testudo():
    """The armoured tortoise — an oblate carapace over a living base."""
    p = [("carapace", dome_half(0.9, 0.9, 0.55, SHELL)),
         ("base", cyl(0.9, 0.06, GREEN, at=(0, 0, -0.02), sections=48))]
    return scene(p)


DESIGNS = {
    "navis": ("NAVIS — crewed explorer", navis),
    "arca": ("ARCA — million-person world", arca),
    "lichen": ("LICHEN — surface settlement", lichen),
    "gravid": ("GRAVID — the nursery", gravid),
    "spore": ("SPORE — lifeboat", spore),
    "leviathan": ("LEVIATHAN — interstellar ark", leviathan),
    "testudo": ("TESTUDO — armoured escort", testudo),
}
