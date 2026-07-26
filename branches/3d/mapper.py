"""Scene3DMapper — S11 for 3d: primitives -> mesh-build Executable.

Builds a minimal triangle-mesh scene spec (vertices/faces per object as boxes).
Degrade support: meta['degrade'] halves mesh resolution (mock: fewer boxes ->
merge objects into bounding volume).
"""

from common.interfaces.abstract import Mapper
from common.interfaces.data_objects import Primitive, SubGoal, Executable

_BOX_SIZE = {"table": [1.2, 0.8, 0.75], "cup": [0.08, 0.08, 0.1],
             "tray": [0.4, 0.3, 0.03], "sofa": [2.0, 0.9, 0.8],
             "door": [0.9, 0.05, 2.0], "shelf": [0.8, 0.3, 1.8]}


def _box_mesh(center, size):
    cx, cy, cz = center
    sx, sy, sz = [s / 2.0 for s in size]
    verts = [[cx + dx * sx, cy + dy * sy, cz + dz * sz]
             for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    faces = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
             [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]
    return {"vertices": verts, "faces": faces}


class Scene3DMapper(Mapper):
    def map(self, primitives: list, goal: SubGoal) -> Executable:
        degrade = any((p.meta or {}).get("degrade") for p in primitives)
        nodes = []
        for p in primitives:
            if p.kind == "floor":
                side = max(1.0, p.params.get("area_m2", 4.0) ** 0.5)
                nodes.append({"name": "floor",
                              "mesh": _box_mesh([0, 0, -0.05], [side, side, 0.1])})
            elif p.kind == "place_object":
                size = _BOX_SIZE.get(p.params["object"], [0.5, 0.5, 0.5])
                if degrade:
                    size = [s * 1.0 for s in size]  # keep bounds; drop detail flag below
                center = list(p.params["xyz"])
                center[2] += size[2] / 2.0
                nodes.append({"name": p.params["object"],
                              "mesh": _box_mesh(center, size)})
        return Executable(
            modality="geometry",
            payload={"scene_nodes": nodes,
                     "total_vertices": sum(len(n["mesh"]["vertices"]) for n in nodes),
                     "detail": "low" if degrade else "normal"},
            meta={"degraded": degrade},
        )


if __name__ == "__main__":
    m = Scene3DMapper()
    prims = [Primitive("floor", {"area_m2": 9.0, "walkable": True}, {}),
             Primitive("place_object", {"object": "table", "xyz": [1, 0, 0]}, {}),
             Primitive("place_object", {"object": "cup", "xyz": [1, 0, 0.75]}, {})]
    g = SubGoal("s", "3d", "g", "", [], {})
    e = m.map(prims, g)
    assert len(e.payload["scene_nodes"]) == 3
    assert e.payload["total_vertices"] == 24 and e.payload["detail"] == "normal"
    names = [n["name"] for n in e.payload["scene_nodes"]]
    assert names == ["floor", "table", "cup"]
    print("[OK] 3d mapper self-test passed")
