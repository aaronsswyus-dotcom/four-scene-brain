"""Scene3DWAM — S7 imagination for the robot-job 3D scene (MOCK backbone).

Inherits PhysicalWorldModelBase (same WAM physical prior as robot).
Payload structure (branch-frozen, see README.md):

    representation: 'gaussians' | 'pointcloud' | 'mesh'
    semantics:      {objects: [...], walkable: bool, walkable_area_m2: float}
    # mock extra: layout (object placements), fidelity
"""

from branches._physical.base import PhysicalWorldModelBase
from common.interfaces.data_objects import State, SubGoal

_KNOWN_OBJECTS = (
    (("table", "桌"), "table"),
    (("cup", "杯"), "cup"),
    (("tray", "托盘"), "tray"),
    (("sofa", "沙发"), "sofa"),
    (("door", "门"), "door"),
    (("shelf", "架"), "shelf"),
)


class Scene3DWAM(PhysicalWorldModelBase):
    """Mock 3D scene world model. Real DreamGaussian (Azure) replaces via adapter."""

    def _imagine(self, state: State, goal: SubGoal, dynamics: dict) -> object:
        retry = int((state.meta or {}).get("retry", 0))
        objects = self._objects_from_goal(goal.goal)
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

    @staticmethod
    def _objects_from_goal(goal_text: str) -> list:
        text = goal_text.lower()
        found = [name for keys, name in _KNOWN_OBJECTS if any(k in text for k in keys)]
        return found or ["floor"]


if __name__ == "__main__":
    wm = Scene3DWAM()
    s = State("geometry", None, {"trace_id": "t"})
    g = SubGoal("sg-1", "3d", "living room with a table and a cup, walkable", "", [], {})
    out = wm.predict_next_state(s, g)
    p = out.payload
    assert p["representation"] == "mesh"
    assert set(p["semantics"]["objects"]) == {"table", "cup"}
    assert p["semantics"]["walkable"] and "wam_dynamics" in out.meta

    # retry raises fidelity
    s2 = State("geometry", None, {"trace_id": "t", "retry": 1})
    assert wm.predict_next_state(s2, g).payload["fidelity"] >= p["fidelity"]
    print("[OK] 3d wam self-test passed")
