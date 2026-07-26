"""Scene3DPrimitiveLibrary — S10 for 3d (multi-task dispatch on payload["task"]).

  - robot_scene (V1, UNCHANGED): floor / place_object primitives from layout.
  - generative (V4): ONE 'mesh_object' primitive carrying the asset mesh +
    geometry + texture + task + text_prompt. The full spec is stashed in
    primitive.meta["threed_spec"] so the Mapper (signature-limited) can rebuild
    the Executable without re-parsing the whole draft.

Primitive kinds are scene-defined and never known by common.
"""

from common.interfaces.abstract import PrimitiveLibrary
from common.interfaces.data_objects import Draft, Primitive

_GEN_TASKS = ("text_to_3d", "image_to_3d", "pointcloud_completion", "pbr_texture")


class Scene3DPrimitiveLibrary(PrimitiveLibrary):
    def abstract(self, draft: Draft) -> list:
        p = draft.payload or {}
        sid = (draft.meta or {}).get("subgoal_id")
        task = p.get("task", "robot_scene")

        if task in _GEN_TASKS:   # ---- generative single-asset ----
            spec = {
                "task": task,
                "representation": p.get("representation", "mesh"),
                "mesh": p.get("mesh", {"vertices": [], "faces": []}),
                "geometry": p.get("geometry", {}),
                "texture": p.get("texture"),
                "semantics": p.get("semantics", []),
                "text_prompt": p.get("text_prompt", ""),
                "source": p.get("source", ""),
            }
            return [Primitive(kind="mesh_object", params={"task": task},
                              meta={"subgoal_id": sid, "threed_spec": spec})]

        # ---- robot_scene (V1, UNCHANGED) ----
        sem = p.get("semantics", {})
        prims = [Primitive(
            kind="floor",
            params={"area_m2": sem.get("walkable_area_m2", 4.0),
                    "walkable": sem.get("walkable", True)},
            meta={"subgoal_id": sid},
        )]
        for item in p.get("layout", []):
            prims.append(Primitive(
                kind="place_object",
                params={"object": item["object"], "xyz": item["xyz"], "on": item.get("on")},
                meta={"subgoal_id": sid},
            ))
        return prims


if __name__ == "__main__":
    lib = Scene3DPrimitiveLibrary()

    # robot_scene (V1)
    d = Draft("geometry", {
        "semantics": {"walkable": True, "walkable_area_m2": 7.5},
        "layout": [{"object": "table", "xyz": [1, 0, 0], "on": "floor"},
                   {"object": "cup", "xyz": [1, 0, 0.75], "on": "table"}],
    }, {"subgoal_id": "sg-1"})
    prims = lib.abstract(d)
    assert prims[0].kind == "floor" and prims[0].params["area_m2"] == 7.5
    assert [p.kind for p in prims[1:]] == ["place_object", "place_object"]
    assert prims[2].params["on"] == "table"

    # generative (V4)
    dg = Draft("geometry", {
        "task": "text_to_3d", "representation": "mesh",
        "mesh": {"vertices": [[0, 0, 0]] * 8, "faces": [[0, 1, 2]] * 12},
        "geometry": {"vertices": 8, "faces": 12, "manifold": True, "bbox": [1, 1, 1]},
        "semantics": ["chair", "red"], "text_prompt": "a red chair",
    }, {"subgoal_id": "sg-2"})
    pg = lib.abstract(dg)
    assert len(pg) == 1 and pg[0].kind == "mesh_object"
    assert pg[0].meta["threed_spec"]["task"] == "text_to_3d"
    print("[OK] 3d primitives self-test passed (robot_scene V1 + generative V4)")
