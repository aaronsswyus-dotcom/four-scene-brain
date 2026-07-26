"""RobotWAM — S7 imagination for robot (MOCK backbone).

Inherits PhysicalWorldModelBase (shared WAM prior). Payload structure is the
branch-frozen physical State.payload (see README.md):

    pose:        SE3   {xyz: [x,y,z], quat: [w,x,y,z]}
    twist:       {linear: [vx,vy,vz], angular: [wx,wy,wz]}
    wrench:      {force: [fx,fy,fz], torque: [tx,ty,tz]}
    contact:     {in_contact: bool, points: [...]}
    joint_state: {angles_rad: [...], torques_nm: [...]}   # dexterous-hand DOF

Retry refinement: when the orchestrator retries (state.meta['retry']), the
imagined trajectory is "refined" — contact force drops. This is the mock
counterpart of scene-internal regeneration inside S7 (D6).
"""

from branches._physical.base import PhysicalWorldModelBase
from common.interfaces.data_objects import State, SubGoal

DOF = 7  # mock dexterous arm+hand degrees of freedom

_PLAN_KEYWORDS = (
    (("grasp", "grab", "pick", "抓", "拿"), "grasp"),
    (("move", "carry", "移", "转移"), "move"),
    (("place", "put", "放", "托盘"), "place"),
    (("open", "开"), "open"),
    (("push", "推"), "push"),
)


class RobotWAM(PhysicalWorldModelBase):
    """Mock robot world model. Real GR00T (Azure) replaces this behind adapter."""

    REFINE_FORCE_DROP_N = 3.0   # per-retry contact-force reduction (refinement)

    def _imagine(self, state: State, goal: SubGoal, dynamics: dict) -> object:
        retry = int((state.meta or {}).get("retry", 0))
        force = max(0.5, dynamics["est_contact_force_n"] - retry * self.REFINE_FORCE_DROP_N)
        plan = self._plan_from_goal(goal.goal)
        return {
            "pose": {"xyz": [0.4, 0.0, 0.2], "quat": [1.0, 0.0, 0.0, 0.0]},
            "twist": {"linear": [0.0, 0.0, 0.0], "angular": [0.0, 0.0, 0.0]},
            "wrench": {"force": [force, 0.0, 0.0], "torque": [0.1, 0.0, 0.0]},
            "contact": {"in_contact": bool(plan), "points": [[0.4, 0.0, 0.2]]},
            "joint_state": {"angles_rad": [0.1] * DOF, "torques_nm": [0.0] * DOF},
            "plan": plan,
            "peak_contact_force_n": force,
            "refined_times": retry,
        }

    @staticmethod
    def _plan_from_goal(goal_text: str) -> list:
        text = goal_text.lower()
        plan = [name for keys, name in _PLAN_KEYWORDS if any(k in text for k in keys)]
        return plan or ["act"]


if __name__ == "__main__":
    wm = RobotWAM()
    s = State("physical", None, {"trace_id": "t"})
    g = SubGoal("sg-1", "robot", "grasp the red cup and place it on the tray", "", [], {})
    out = wm.predict_next_state(s, g)
    p = out.payload
    assert set(p) >= {"pose", "twist", "wrench", "contact", "joint_state", "plan"}
    assert p["plan"] == ["grasp", "place"]
    assert len(p["joint_state"]["torques_nm"]) == DOF

    # retry refinement drops contact force
    s2 = State("physical", None, {"trace_id": "t", "retry": 1})
    out2 = wm.predict_next_state(s2, g)
    assert out2.payload["peak_contact_force_n"] < p["peak_contact_force_n"]
    print("[OK] robot wam self-test passed")
