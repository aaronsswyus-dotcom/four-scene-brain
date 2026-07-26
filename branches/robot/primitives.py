"""RobotPrimitiveLibrary — S10 primitive abstraction for robot.

Maps the imagined plan into motion primitives: grasp / move / place / open /
push / act. Primitive params carry mock kinematic targets.
"""

from common.interfaces.abstract import PrimitiveLibrary
from common.interfaces.data_objects import Draft, Primitive


class RobotPrimitiveLibrary(PrimitiveLibrary):
    def abstract(self, draft: Draft) -> list:
        p = draft.payload or {}
        plan = list(p.get("plan", ["act"]))
        pose = p.get("pose", {})
        prims = []
        for i, step in enumerate(plan):
            prims.append(Primitive(
                kind=step,
                params={
                    "order": i,
                    "target_xyz": list(pose.get("xyz", [0.0, 0.0, 0.0])),
                    "grip_width_m": 0.06 if step == "grasp" else None,
                    "peak_force_n": p.get("peak_contact_force_n", 0.0),
                },
                meta={"subgoal_id": (draft.meta or {}).get("subgoal_id")},
            ))
        return prims


if __name__ == "__main__":
    lib = RobotPrimitiveLibrary()
    d = Draft("physical", {"plan": ["grasp", "move", "place"],
                           "pose": {"xyz": [0.4, 0, 0.2]},
                           "peak_contact_force_n": 2.5}, {"subgoal_id": "sg-1"})
    prims = lib.abstract(d)
    assert [p.kind for p in prims] == ["grasp", "move", "place"]
    assert prims[0].params["grip_width_m"] == 0.06
    assert prims[1].params["grip_width_m"] is None
    assert all(p.meta["subgoal_id"] == "sg-1" for p in prims)
    print("[OK] robot primitives self-test passed")
