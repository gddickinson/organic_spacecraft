"""GESTALT 3D models.

Builds solid, colour-coded 3D meshes of the main GESTALT designs and exports
them as working interchange files (glTF/GLB, OBJ, STL) that open in any 3D
viewer, Blender, a game engine, or a 3D printer.

    python -m models3d.run

See models3d/INTERFACE.md.
"""

from . import build  # noqa: F401

__all__ = ["build", "render", "run"]
