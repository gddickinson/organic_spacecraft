"""3D geometry generators for the GESTALT simulations.

Each function returns numpy meshes (X, Y, Z) suitable for matplotlib's
plot_surface, plus helper point clouds (crew, cradles) for scatter overlays.
Kept deliberately low-resolution so animation stays smooth.
"""

import numpy as np


def spheroid(a, b, nu=40, nv=20):
    """Prolate spheroid surface, long axis along z. a = half-length, b = radius."""
    u = np.linspace(0, 2 * np.pi, nu)
    v = np.linspace(0, np.pi, nv)
    U, V = np.meshgrid(u, v)
    X = b * np.sin(V) * np.cos(U)
    Y = b * np.sin(V) * np.sin(U)
    Z = a * np.cos(V)
    return X, Y, Z


def drum(R, L, nu=48, nv=8):
    """Open cylinder (a spin drum) with its axis along z, length L, radius R."""
    u = np.linspace(0, 2 * np.pi, nu)
    z = np.linspace(-L / 2, L / 2, nv)
    U, Z = np.meshgrid(u, z)
    X = R * np.cos(U)
    Y = R * np.sin(U)
    return X, Y, Z


def dome(R, H, nu=40, nv=16):
    """Half-dome (a settlement blister) sitting on z = 0."""
    u = np.linspace(0, 2 * np.pi, nu)
    v = np.linspace(0, np.pi / 2, nv)
    U, V = np.meshgrid(u, v)
    X = R * np.cos(V) * np.cos(U)
    Y = R * np.cos(V) * np.sin(U)
    Z = H * np.sin(V)
    return X, Y, Z


def ground_disk(R, nu=40, nr=6):
    """A flat disk for regolith ground."""
    u = np.linspace(0, 2 * np.pi, nu)
    r = np.linspace(0, R, nr)
    U, Rr = np.meshgrid(u, r)
    X = Rr * np.cos(U)
    Y = Rr * np.sin(U)
    Z = np.zeros_like(X)
    return X, Y, Z


def sphere(cx, cy, cz, r, nu=16, nv=10):
    """A small sphere (an embryo, a pod) centred at (cx, cy, cz)."""
    u = np.linspace(0, 2 * np.pi, nu)
    v = np.linspace(0, np.pi, nv)
    U, V = np.meshgrid(u, v)
    X = cx + r * np.sin(V) * np.cos(U)
    Y = cy + r * np.sin(V) * np.sin(U)
    Z = cz + r * np.cos(V)
    return X, Y, Z


def crew_on_rim(R, L, n, seed=1):
    """Random points on the inner surface of a drum (people on the ground)."""
    rng = np.random.default_rng(seed)
    th = rng.uniform(0, 2 * np.pi, n)
    z = rng.uniform(-L / 2 * 0.9, L / 2 * 0.9, n)
    x = R * 0.97 * np.cos(th)
    y = R * 0.97 * np.sin(th)
    return np.array([x, y, z]), th


def rotate_z(pts, angle):
    """Rotate an array of shape (3, N) about the z-axis."""
    c, s = np.cos(angle), np.sin(angle)
    Rm = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return Rm @ pts


def cradle_positions(length, n):
    """Positions of nursery cradles budding along a central spine (z-axis)."""
    z = np.linspace(-0.4 * length, 0.4 * length, n)
    side = np.where(np.arange(n) % 2 == 0, 1.0, -1.0)
    x = side * 0.10 * length
    y = np.zeros(n)
    return np.array([x, y, z]), side
