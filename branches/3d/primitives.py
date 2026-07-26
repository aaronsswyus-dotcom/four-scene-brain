"""Scene3DPrimitiveLibrary — S10 for 3d: layout -> scene-construction primitives.

Primitive kinds: floor / place_object (scene-defined, never known by common).
"""

from common.interfaces.abstract import PrimitiveLibrary
from common.interfaces.data_objects import Draft, Primitive


class Scene3DPrimitiveLibrary(PrimitiveLibrary):
    def abstract(self, draft: Draft) -> list:
        p = draft.payload or {}
        sem = p.get("semantics", {})
        prims = [Primitive(
            kind="floor",
            params={"area_m2": sem.get("walkable_area_m2", 4.0),
                    "walkable": sem.get("walkable", True)},
            meta={"subgoal_id": (draft.meta or {}).get("subgoal_id")},
        )]
        for item in p.get("layout", []):
            prims.append(Primitive(
                kind="place_object",
                params={"object": item["object"], "xyz": item["xyz"], "on": item.get("on")},
                meta={"subgoal_id": (draft.meta or {}).get("subgoal_id")},
            ))
        return prims


if __name__ == "__main__":
    lib = Scene3DPrimitiveLibrary()
    d = Draft("geometry", {
        "semantics": {"walkable": True, "walkable_area_m2": 7.5},
        "layout": [{"object": "table", "xyz": [1, 0, 0], "on": "floor"},
                   {"object": "cup", "xyz": [1, 0, 0.75], "on": "table"}],
    }, {"subgoal_id": "sg-1"})
    prims = lib.abstract(d)
    assert prims[0].kind == "floor" and prims[0].params["area_m2"] == 7.5
    assert [p.kind for p in prims[1:]] == ["place_object", "place_object"]
    assert prims[2].params["on"] == "table"
    print("[OK] 3d primitives self-test passed")
