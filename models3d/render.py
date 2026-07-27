"""Static preview render of a model scene (for verification and the README).

Uses matplotlib's 3D triangle collection so it needs no display or GPU — it
draws each coloured part of a ``trimesh.Scene`` from a fixed viewpoint.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

GROUND = "#0a1512"
INK3 = "#7c9689"


def preview(scn, path, title="", elev=20, azim=-58, dpi=100):
    verts = np.vstack([g.vertices for g in scn.geometry.values()])
    lo, hi = verts.min(0), verts.max(0)
    ctr = (lo + hi) / 2
    rad = (hi - lo).max() / 2 * 1.05

    fig = plt.figure(figsize=(6.4, 6.0), dpi=dpi)
    fig.patch.set_facecolor(GROUND)
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor(GROUND)
    # merge every part into ONE collection so matplotlib depth-sorts across parts
    light = np.array([0.4, 0.5, 0.75]); light = light / np.linalg.norm(light)
    all_tris, all_cols = [], []
    for g in scn.geometry.values():
        tris = g.vertices[g.faces]
        base = np.array(g.visual.face_colors[0][:3]) / 255.0
        n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        n = n / np.where(ln == 0, 1, ln)
        shade = np.clip(np.abs(n @ light), 0, 1) * 0.6 + 0.4
        all_tris.append(tris)
        all_cols.append(np.clip(base[None, :] * shade[:, None], 0, 1))
    tris = np.vstack(all_tris)
    cols = np.vstack(all_cols)
    pc = Poly3DCollection(tris, facecolors=cols, edgecolors="none", zsort="average")
    ax.add_collection3d(pc)
    ax.set_xlim(ctr[0] - rad, ctr[0] + rad)
    ax.set_ylim(ctr[1] - rad, ctr[1] + rad)
    ax.set_zlim(ctr[2] - rad, ctr[2] + rad)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    if title:
        fig.text(0.5, 0.05, title, color=INK3, ha="center", family="monospace", fontsize=10)
    fig.savefig(path, facecolor=GROUND, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    return path
