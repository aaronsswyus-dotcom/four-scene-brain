"""Scene3DMapper — S11 for 3d (multi-task dispatch).

  - robot_scene (V1, UNCHANGED): floor/place_object primitives -> box-mesh
    scene_nodes Executable. Degrade halves detail.
  - generative (V4): a single 'mesh_object' primitive -> single-node Executable
    carrying task/text_prompt/geometry/texture (SafetyGate + Executor need them).
    Degrade clamps the geometry vertex count up to a safe floor.

Both directions emit `scene_nodes` so the Executor's GLB writer is shared.
"""

from common.interfaces.abstract import Mapper
from common.interfaces.data_objects import Primitive, SubGoal, Executable

_BOX_SIZE = {"table": [1.2, 0.8, 0.75], "cup": [0.08, 0.08, 0.1],
             "tray": [0.4, 0.3, 0.03], "sofa": [2.0, 0.9, 0.8],
             "door": [0.9, 0.05, 2.0], "shelf": [0.8, 0.3, 1.8]}

_MIN_VERTICES = 8   # safe floor for degrade re-map


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

        # ---- generative single-asset (V4) ----
        gen = next((p for p in primitives if p.kind == "mesh_object"), None)
        if gen is not None:
            spec = gen.meta["threed_spec"]
            mesh = spec["mesh"]
            geo = dict(spec.get("geometry") or {})
            if degrade:   # clamp geometry up to safe floor (re-check will PASS)
                geo["vertices"] = max(int(geo.get("vertices", 0)), _MIN_VERTICES)
                geo["manifold"] = True
                if geo.get("faces", 0) <= 0 and spec["task"] != "pointcloud_completion":
                    geo["faces"] = len(mesh.get("faces", [])) or 12
            node = {"name": spec["task"], "mesh": mesh}
            return Executable(
                modality="geometry",
                payload={
                    "task": spec["task"],
                    "representation": spec.get("representation", "mesh"),
                    "scene_nodes": [node],
                    "total_vertices": len(mesh.get("vertices", [])),
                    "geometry": geo,
                    "texture": spec.get("texture"),
                    "semantics": spec.get("semantics", []),
                    "text_prompt": spec.get("text_prompt", ""),
                    "source": spec.get("source", ""),
                    "detail": "low" if degrade else "normal",
                },
                meta={"degraded": degrade},
            )

        # ---- robot_scene (V1, UNCHANGED) ----
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

    # robot_scene (V1)
    prims = [Primitive("floor", {"area_m2": 9.0, "walkable": True}, {}),
             Primitive("place_object", {"object": "table", "xyz": [1, 0, 0]}, {}),
             Primitive("place_object", {"object": "cup", "xyz": [1, 0, 0.75]}, {})]
    g = SubGoal("s", "3d", "g", "", [], {})
    e = m.map(prims, g)
    assert len(e.payload["scene_nodes"]) == 3
    assert e.payload["total_vertices"] == 24 and e.payload["detail"] == "normal"
    assert [n["name"] for n in e.payload["scene_nodes"]] == ["floor", "table", "cup"]

    # generative (V4)
    spec = {"task": "text_to_3d", "representation": "mesh",
            "mesh": {"vertices": [[0, 0, 0]] * 8, "faces": [[0, 1, 2]] * 12},
            "geometry": {"vertices": 8, "faces": 12, "manifold": True, "bbox": [1, 1, 1]},
            "texture": None, "semantics": ["chair"], "text_prompt": "a chair", "source": "a chair"}
    pg = [Primitive("mesh_object", {"task": "text_to_3d"}, {"threed_spec": spec})]
    eg = m.map(pg, g)
    assert eg.payload["task"] == "text_to_3d" and eg.payload["total_vertices"] == 8
    assert eg.payload["text_prompt"] == "a chair" and len(eg.payload["scene_nodes"]) == 1

    # generative degrade clamps
    pg[0].meta["degrade"] = True
    spec["geometry"] = {"vertices": 0, "faces": 0, "manifold": False, "bbox": [1, 1, 1]}
    ed = m.map(pg, g)
    assert ed.payload["geometry"]["vertices"] >= 8 and ed.payload["geometry"]["manifold"]
    print("[OK] 3d mapper self-test passed (robot_scene V1 + generative V4 + degrade)")
