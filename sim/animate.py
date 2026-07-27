"""Animated 3D visualisations of the GESTALT designs with their systems running.

Each builder combines a geometry (sim/geometry.py) with system dynamics
(sim/systems.py) into a matplotlib figure — a 3D scene plus live gauges — and
saves it as an animated GIF. The 3D scene shows the design *doing something*
(growing, spinning, cycling day/night); the gauges track the driving numbers.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

from . import geometry as G
from . import systems as S
from .params import COL


# ---------- shared styling ----------
def _blend(c0, c1, t):
    a = np.array(matplotlib.colors.to_rgb(c0)); b = np.array(matplotlib.colors.to_rgb(c1))
    return tuple(a + (b - a) * float(np.clip(t, 0, 1)))


def _fig():
    fig = plt.figure(figsize=(9.6, 5.4), dpi=92)
    fig.patch.set_facecolor(COL["ground"])
    return fig


def _ax3(fig, rect, lim, elev=18, azim=-60):
    ax = fig.add_axes(rect, projection="3d")
    ax.set_facecolor(COL["ground"])
    ax.set_axis_off()
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    return ax


def _gauge(fig, rect, title):
    ax = fig.add_axes(rect)
    ax.set_facecolor(COL["ground2"])
    for s in ax.spines.values():
        s.set_color(COL["line"])
    ax.tick_params(colors=COL["ink3"], labelsize=7, length=2)
    ax.set_title(title, color=COL["ink2"], fontsize=8.5, loc="left", family="monospace")
    ax.grid(True, color=COL["line"], lw=0.4, alpha=0.5)
    return ax


def _title(fig, name, sub):
    fig.text(0.035, 0.94, name, color=COL["ink"], fontsize=13, family="serif", weight="bold")
    fig.text(0.035, 0.90, sub, color=COL["chloro"], fontsize=8.5, family="monospace")
    fig.text(0.035, 0.045, "GESTALT simulation · grounded in the program's canonical numbers",
             color=COL["ink3"], fontsize=7.5, family="monospace")


def _save(anim, out, fps):
    anim.save(out, writer=PillowWriter(fps=fps))
    plt.close(anim._fig)
    return out


# ---------- NAVIS: growth + metabolism + day/night ----------
def navis(design, out, frames=72, fps=14):
    g = S.growth(design); eb = S.energy_budget(design)
    a, b = design.a, design.b
    X0, Y0, Z0 = G.spheroid(a, b, 40, 20)
    fig = _fig(); _title(fig, design.name, "growth · photosynthesis day/night · mining")
    ax = _ax3(fig, [0.0, 0.06, 0.60, 0.86], lim=a * 1.15)
    gm = _gauge(fig, [0.66, 0.58, 0.31, 0.32], "grown mass  ·  tonnes")
    gr = _gauge(fig, [0.66, 0.13, 0.31, 0.32], "deposition rate  ·  t/day")
    gm.plot(g["t_years"], g["mass_t"], color=COL["chloro"], lw=1.3)
    gr.plot(g["t_years"], g["rate_tpd"], color=COL["osteo"], lw=1.3)
    gm.set_xlim(0, g["t_years"].max()); gr.set_xlim(0, g["t_years"].max())
    gr.set_xlabel("years from germination", color=COL["ink3"], fontsize=7.5, family="monospace")
    mdot, = gm.plot([], [], "o", color=COL["ink"], ms=5)
    rdot, = gr.plot([], [], "o", color=COL["ink"], ms=5)
    idx = np.linspace(0, len(g["t_years"]) - 1, frames).astype(int)

    def update(f):
        ax.clear(); ax.set_axis_off()
        ax.set_xlim(-a * 1.15, a * 1.15); ax.set_ylim(-a * 1.15, a * 1.15); ax.set_zlim(-a * 1.15, a * 1.15)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(18, -60 + f * 1.6)
        k = idx[f]; frac = max(g["frac"][k], 0.06)
        glow = 0.5 + 0.5 * np.sin(2 * np.pi * f / frames * 4)     # day/night
        col = _blend("#123", COL["chloro"], 0.35 + 0.65 * glow)
        s = frac ** (1 / 3)
        ax.plot_surface(X0 * s, Y0 * s, Z0 * s, color=col, rstride=1, cstride=1,
                        linewidth=0, antialiased=False, shade=True, alpha=0.96)
        # aft mining root reaching to a resource rock
        rz = -a * s
        ax.plot([0, 0], [0, 0], [rz, rz - a * 0.5], color=COL["lumen"], lw=2)
        ax.scatter([0], [0], [rz - a * 0.62], color=COL["rock"], s=140)
        # equatorial docking band hint
        th = np.linspace(0, 2 * np.pi, 60)
        ax.plot(b * s * np.cos(th), b * s * np.sin(th), np.zeros_like(th),
                color=COL["osteo"], lw=1.2, alpha=0.8)
        ax.text2D(0.5, 0.02, f"t = {g['t_years'][k]:.1f} yr   ·   {g['mass_t'][k]:,.0f} t   ·   "
                  + ("DAY" if glow > 0.5 else "NIGHT"), transform=ax.transAxes,
                  color=COL["ink2"], fontsize=8.5, ha="center", family="monospace")
        mdot.set_data([g["t_years"][k]], [g["mass_t"][k]])
        rdot.set_data([g["t_years"][k]], [g["rate_tpd"][k]])
        return ()
    fig.text(0.66, 0.035, f"photosynthesis → air ({eb['photo_biomass_tpd']} t/d); "
             f"body MINED ({eb['growth_tpd']} t/d, ~{eb['ore_ratio']}:1 ore)", color=COL["ink3"],
             fontsize=7.0, family="monospace")
    anim = FuncAnimation(fig, update, frames=frames, blit=False); anim._fig = fig
    return _save(anim, out, fps)


# ---------- ARCA: spin gravity + closed-loop life support ----------
def arca(design, out, frames=90, fps=16):
    sp = S.spin_gravity(design); ls = S.life_support(design, years=140, n=frames)
    R, L = design.a, design.length
    Xd, Yd, Zd = G.drum(R, L, 48, 6)
    crew, _ = G.crew_on_rim(R, L, 120)
    fig = _fig(); _title(fig, design.name, f"spin {design.rpm} rpm → 1 g · day/night · O₂ buffer")
    ax = _ax3(fig, [0.0, 0.06, 0.60, 0.86], lim=max(R, L / 2) * 1.05, elev=14, azim=-70)
    gg = _gauge(fig, [0.66, 0.58, 0.31, 0.32], "spin gravity  ·  g vs radius")
    go = _gauge(fig, [0.66, 0.13, 0.31, 0.32], "O₂ reserve  ·  % over 140 yr")
    gg.plot(sp["r"] / 1000, sp["g_of_r"] / 9.81, color=COL["osteo"], lw=1.4)
    gg.set_xlabel("radius, km", color=COL["ink3"], fontsize=7.5, family="monospace")
    gg.axhline(1.0, color=COL["chloro"], lw=0.8, ls="--")
    go.plot(ls["t_days"] / 365, ls["o2_pct"], color=COL["lumen"], lw=1.4)
    go.set_ylim(design.o2_fraction * 100 - 2, design.o2_fraction * 100 + 2)
    go.set_xlabel("years", color=COL["ink3"], fontsize=7.5, family="monospace")
    odot, = go.plot([], [], "o", color=COL["ink"], ms=5)

    def update(f):
        ax.clear(); ax.set_axis_off()
        lim = max(R, L / 2) * 1.05
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(14, -70)
        ang = f * 0.18                                    # the drum spins
        glow = 0.5 + 0.5 * np.sin(2 * np.pi * f / frames * 6)   # axial sun-cord day/night
        ax.plot_surface(Xd, Yd, Zd, color=_blend(COL["ground2"], COL["chloro"], 0.22),
                        rstride=1, cstride=1, linewidth=0, alpha=0.30, shade=False)
        # axial sun-cord brightening with the day cycle
        ax.plot([0, 0], [0, 0], [-L / 2, L / 2], color=_blend("#134", COL["lumen"], glow), lw=3.5)
        cr = G.rotate_z(crew, ang)
        ax.scatter(cr[0], cr[1], cr[2], color=COL["ink"], s=5, alpha=0.7)
        # a dropped object showing the Coriolis curve
        n = 1 + int((f % (frames // 2)) / (frames // 2) * (len(sp["drop_x"]) - 1))
        dx = G.rotate_z(np.array([sp["drop_x"][:n], sp["drop_y"][:n], np.zeros(n)]), ang)
        ax.plot(dx[0], dx[1], dx[2], color=COL["warm"], lw=1.6)
        ax.text2D(0.5, 0.02, f"rim {sp['rim_v']:.0f} m/s → {sp['g_rim']/9.81:.2f} g   ·   "
                  + ("DAY" if glow > 0.5 else "NIGHT") + f"   ·   O₂ {ls['o2_pct'][f]:.1f}%",
                  transform=ax.transAxes, color=COL["ink2"], fontsize=8.5, ha="center", family="monospace")
        odot.set_data([ls["t_days"][f] / 365], [ls["o2_pct"][f]])
        return ()
    fig.text(0.66, 0.035, f"113 Mt air ≈ {ls['buffer_years']:.0f} yr O₂ reserve — a huge buffer",
             color=COL["ink3"], fontsize=7.2, family="monospace")
    anim = FuncAnimation(fig, update, frames=frames, blit=False); anim._fig = fig
    return _save(anim, out, fps)


# ---------- LICHEN: day/night thermal + pressure ----------
def lichen(design, out, frames=72, fps=14):
    th = S.thermal(design, days=2.0, n=frames)
    R = design.dome_span_m / 2; H = design.dome_rise_m
    Xd, Yd, Zd = G.dome(R, H, 40, 14); Xg, Yg, Zg = G.ground_disk(R * 2.2)
    fig = _fig(); _title(fig, design.name, "day/night on the surface · a stable interior")
    ax = _ax3(fig, [0.0, 0.06, 0.60, 0.86], lim=R * 1.8, elev=10, azim=-55)
    gt = _gauge(fig, [0.66, 0.58, 0.31, 0.32], "temperature  ·  K over 2 days")
    gt.plot(th["t_days"], th["T_skin"], color=COL["osteo"], lw=1.3, label="surface")
    gt.plot(th["t_days"], th["T_interior"], color=COL["chloro"], lw=1.3, label="interior")
    gt.legend(fontsize=6.5, facecolor=COL["ground2"], edgecolor=COL["line"], labelcolor=COL["ink2"])
    gt.set_xlabel("days", color=COL["ink3"], fontsize=7.5, family="monospace")
    tdot, = gt.plot([], [], "o", color=COL["ink"], ms=5)
    gp = _gauge(fig, [0.66, 0.13, 0.31, 0.32], "pressure balance")
    gp.axis("off")
    gp.text(0.0, 0.7, f"interior  {design.pressure_kpa:.0f} kPa", color=COL["lumen"], family="monospace", fontsize=9)
    gp.text(0.0, 0.45, "regolith over-blanket balances\nρgh with the internal pressure",
            color=COL["ink3"], family="monospace", fontsize=7.5)
    gp.text(0.0, 0.12, "thin CO₂ sky  ~0.6 kPa", color=COL["osteo"], family="monospace", fontsize=8.5)

    def update(f):
        ax.clear(); ax.set_axis_off()
        lim = R * 1.8
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim * 0.4, lim * 1.2)
        ax.set_box_aspect((1, 1, 0.8)); ax.view_init(10, -55)
        lit = th["lit"][f]
        ax.plot_surface(Xg, Yg, Zg, color=_blend("#161008", COL["rock"], 0.3 + 0.5 * lit),
                        rstride=1, cstride=1, linewidth=0, alpha=0.9, shade=False)
        ax.plot_surface(Xd, Yd, Zd, color=_blend(COL["ground2"], COL["chloro"], 0.25),
                        rstride=1, cstride=1, linewidth=0, alpha=0.45, shade=True)
        # a sun crossing the sky
        sa = 2 * np.pi * th["t_days"][f]
        sx, sz = R * 2.4 * np.cos(sa), R * 1.6 * abs(np.sin(sa))
        if np.sin(sa) > 0:
            ax.scatter([sx], [0], [sz], color=COL["osteo"], s=180)
        ax.text2D(0.5, 0.02, f"t = {th['t_days'][f]:.2f} d   ·   surface {th['T_skin'][f]:.0f} K   ·   "
                  f"interior {th['T_interior'][f]:.0f} K", transform=ax.transAxes,
                  color=COL["ink2"], fontsize=8.5, ha="center", family="monospace")
        tdot.set_data([th["t_days"][f]], [th["T_skin"][f]])
        return ()
    anim = FuncAnimation(fig, update, frames=frames, blit=False); anim._fig = fig
    return _save(anim, out, fps)


# ---------- GRAVID: gestation throughput ----------
def gravid(design, out, frames=80, fps=14):
    ge = S.gestation(design); L = design.length
    pos, side = G.cradle_positions(L, design.cradles)
    fig = _fig(); _title(fig, design.name, "cradles gestating vessels from seeds · a ship hatches")
    ax = _ax3(fig, [0.0, 0.06, 0.60, 0.86], lim=L * 0.55, elev=16, azim=-60)
    gc = _gauge(fig, [0.66, 0.30, 0.31, 0.5], "cradle maturity  ·  0 → hatch")
    for c in range(design.cradles):
        gc.plot(ge["t_years"], ge["frac"][:, c], lw=1.0, alpha=0.8,
                color=_blend(COL["osteo"], COL["chloro"], c / design.cradles))
    gc.set_xlabel("years", color=COL["ink3"], fontsize=7.5, family="monospace")
    gc.set_ylim(0, 1.05)
    vln = gc.axvline(0, color=COL["ink"], lw=1)
    idx = np.linspace(0, len(ge["t_years"]) - 1, frames).astype(int)

    def update(f):
        ax.clear(); ax.set_axis_off()
        lim = L * 0.55
        ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim, lim)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(16, -60 + f * 1.0)
        k = idx[f]
        ax.plot([0, 0], [0, 0], [-L * 0.42, L * 0.42], color=COL["lumen"], lw=3)  # feedstock spine
        rmax = L * 0.05
        for c in range(design.cradles):
            fr = ge["frac"][k, c]
            r = rmax * (0.2 + 0.8 * fr)
            col = _blend(COL["osteo"], COL["chloro"], fr)
            xs, ys, zs = G.sphere(pos[0, c], pos[1, c], pos[2, c], r, 14, 9)
            ax.plot_surface(xs, ys, zs, color=col, rstride=1, cstride=1, linewidth=0,
                            alpha=0.9, shade=True)
            if fr > 0.96:                                  # hatching: a ship leaving
                ax.scatter([pos[0, c] * 2.3], [0], [pos[2, c]], color=COL["chloro"], s=90)
        ax.text2D(0.5, 0.02, f"t = {ge['t_years'][k]:.1f} yr   ·   {design.cradles} of 12–24 cradles   "
                  f"·   ~{ge['throughput_tpd']:.0f} t/day each", transform=ax.transAxes,
                  color=COL["ink2"], fontsize=8.5, ha="center", family="monospace")
        vln.set_xdata([ge["t_years"][k], ge["t_years"][k]])
        return ()
    anim = FuncAnimation(fig, update, frames=frames, blit=False); anim._fig = fig
    return _save(anim, out, fps)


BUILDERS = {"navis": navis, "arca": arca, "lichen": lichen, "gravid": gravid}
