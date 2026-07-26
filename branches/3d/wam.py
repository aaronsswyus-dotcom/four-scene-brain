"""Scene3DWAM — S7 imagination for branches/3d (physical camp, MOCK backbone).

Inherits PhysicalWorldModelBase (same WAM physical prior as robot).

TWO task families share ONE target="3d" (V4 multi-task, adapter `task` knob):
  - task="robot_scene" (V1, DEFAULT): robot-job scene payload. This path is
    UNCHANGED from V1 and does NOT use the backbone (byte-identical behaviour).
        representation='mesh'
        semantics={objects:[...], walkable:bool, walkable_area_m2:float}
        + layout (placements), fidelity
  - task in {text_to_3d, image_to_3d, pointcloud_completion, pbr_texture} (V4):
    routed through the ThreeDBackbone anti-corruption layer. Payload = the
    backbone dict (task/representation/geometry/semantics/texture/mesh/...).

Retry (state.meta["retry"]) is forwarded both ways: it raises robot_scene
fidelity, and it repairs a `challenge` generative asset on the backbone side.
"""

from branches._physical.base import PhysicalWorldModelBase
from common.interfaces.data_objects import State, SubGoal
from .scene_objects import objects_from_goal as _objects_from_goal
from .backbone_mock import MockThreeDBackbone


class Scene3DWAM(PhysicalWorldModelBase):
    """3D world model. robot_scene stays inline (V1); generative tasks go through
    the backbone (real TRELLIS/DreamGaussian on Azure replaces it via adapter)."""

    def __init__(self, backbone=None, task: str = "robot_scene") -> None:
        super().__init__()
        self.task = task
        self.backbone = backbone or MockThreeDBackbone()

    def _imagine(self, state: State, goal: SubGoal, dynamics: dict) -> object:
        retry = int((state.meta or {}).get("retry", 0))

        if self.task == "robot_scene":   # ---- V1 path, UNCHANGED ----
            objects = _objects_from_goal(goal.goal)
            walkable = ("walk" in goal.goal.lower()) or ("行走" in goal.goal) or ("通行" in goal.goal)
            fidelity = min(1.0, round(dynamics["plausibility"] + 0.15 * retry, 4))
            layout = [{"object": o, "xyz": [1.0 + i * 0.8, 0.0, 0.0 if o != "cup" else 0.75],
                       "on": "table" if o == "cup" else "floor"}
                      for i, o in enumerate(objects)]
            return {
                "representation": "mesh",
                "semantics": {
                    "objects": objects,
                    "walkable": walkable or True,   # mock scenes always leave a corridor
                    "walkable_area_m2": round(8.0 * dynamics["plausibility"], 2),
                },
                "layout": layout,
                "fidelity": fidelity,
                "refined_times": retry,
            }

        # ---- V4 generative tasks: through the anti-corruption backbone ----
        config = {"task": self.task, "retry": retry}
        config.update(goal.constraints or {})
        return self.backbone.generate(goal.goal, config)


if __name__ == "__main__":
    # ---- V1 robot_scene (default) — must be byte-identical to V1 ----
    wm = Scene3DWAM()
    assert wm.task == "robot_scene"
    s = State("geometry", None, {"trace_id": "t"})
    g = SubGoal("sg-1", "3d", "living room with a table and a cup, walkable", "", [], {})
    out = wm.predict_next_state(s, g)
    p = out.payload
    assert p["representation"] == "mesh"
    assert set(p["semantics"]["objects"]) == {"table", "cup"}
    assert p["semantics"]["walkable"] and "wam_dynamics" in out.meta
    s2 = State("geometry", None, {"trace_id": "t", "retry": 1})
    assert wm.predict_next_state(s2, g).payload["fidelity"] >= p["fidelity"]

    # ---- V4 text_to_3d through backbone ----
    wm2 = Scene3DWAM(task="text_to_3d")
    g2 = SubGoal("sg-2", "3d", "a red wooden chair", "", [], {})
    o2 = wm2.predict_next_state(State("geometry", None, {"trace_id": "t"}), g2)
    assert o2.payload["task"] == "text_to_3d" and o2.payload["geometry"]["manifold"]

    # ---- V4 retry repairs a challenge asset ----
    wm3 = Scene3DWAM(task="text_to_3d")
    gc = SubGoal("sg-3", "3d", "x", "", [], {"challenge": True})
    bad = wm3.predict_next_state(State("geometry", None, {"trace_id": "t", "retry": 0}), gc)
    good = wm3.predict_next_state(State("geometry", None, {"trace_id": "t", "retry": 1}), gc)
    assert bad.payload["geometry"]["faces"] == 0 and good.payload["geometry"]["faces"] == 12
    print("[OK] 3d wam self-test passed (robot_scene V1 + generative V4 + retry)")
