"""Scene3DCritic — S9 verification for the robot-job 3D scene (V1 scene-oriented).

Checks (v1-plan §4): walkability + geometric fidelity + text-scene alignment
(e.g. "contains table / cup / walkable"). Thresholds via goal.constraints:
    min_fidelity (default 0.7), required objects parsed from the goal itself.
"""

from common.interfaces.abstract import Critic
from common.interfaces.data_objects import Draft, SubGoal, Verification, FailureKind

from .scene_objects import objects_from_goal as _objects_from_goal

DEFAULT_MIN_FIDELITY = 0.7


class Scene3DCritic(Critic):
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        p = draft.payload or {}
        if not isinstance(p, dict) or "representation" not in p or "semantics" not in p:
            return Verification(False, 0.0, "malformed 3d payload",
                                FailureKind.STRUCTURAL_INFEASIBLE,
                                meta={"verification_source": "schema"})
        sem = p["semantics"]
        checks = {}

        # 1) walkability
        need_walk = any(k in goal.goal.lower() for k in ("walk",)) or "行走" in goal.goal or "通行" in goal.goal
        checks["walkable"] = (not need_walk) or bool(sem.get("walkable"))

        # 2) geometric fidelity
        min_fid = float(goal.constraints.get("min_fidelity", DEFAULT_MIN_FIDELITY))
        fidelity = float(p.get("fidelity", 0.0))
        checks["fidelity"] = fidelity >= min_fid

        # 3) text-scene alignment: required objects present
        required = set(_objects_from_goal(goal.goal)) - {"floor"}
        present = set(sem.get("objects", []))
        checks["alignment"] = required <= present

        passed = all(checks.values())
        score = round((0.34 * checks["walkable"] + 0.33 * checks["fidelity"]
                       + 0.33 * checks["alignment"]) * min(1.0, max(fidelity, 0.5) + 0.2), 4)
        reason = "; ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in checks.items())
        return Verification(
            passed, score, reason,
            FailureKind.NONE if passed else FailureKind.RETRYABLE_QUALITY,
            meta={"verification_source": "walkable+fidelity+alignment",
                  "fidelity": fidelity, "required_objects": sorted(required)},
        )


if __name__ == "__main__":
    c = Scene3DCritic()
    g = SubGoal("s", "3d", "walkable living room with table and cup", "", [], {})
    good = Draft("geometry", {
        "representation": "mesh", "fidelity": 0.9,
        "semantics": {"objects": ["table", "cup"], "walkable": True},
    }, {})
    v = c.verify(good, g)
    assert v.passed, v

    low = Draft("geometry", {
        "representation": "mesh", "fidelity": 0.4,
        "semantics": {"objects": ["table", "cup"], "walkable": True},
    }, {})
    v2 = c.verify(low, g)
    assert not v2.passed and v2.failure_kind is FailureKind.RETRYABLE_QUALITY

    missing = Draft("geometry", {
        "representation": "mesh", "fidelity": 0.9,
        "semantics": {"objects": ["table"], "walkable": True},
    }, {})
    assert not c.verify(missing, g).passed  # cup missing -> alignment FAIL

    assert c.verify(Draft("geometry", {}, {}), g).failure_kind is FailureKind.STRUCTURAL_INFEASIBLE
    print("[OK] 3d critic self-test passed")
