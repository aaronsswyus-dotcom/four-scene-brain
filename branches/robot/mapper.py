"""RobotMapper — S11 mapping: primitives -> joint-torque Executable (mock).

Degrade support: primitives carrying meta['degrade']=True are mapped with
halved torques (SafetyGate DEGRADE path). torque_scale can be raised via
goal.constraints['torque_scale'] (used by the SafetyGate BLOCK demo).
"""

from common.interfaces.abstract import Mapper
from common.interfaces.data_objects import Primitive, SubGoal, Executable

DOF = 7
BASE_TORQUE_NM = {"grasp": 2.0, "move": 4.0, "place": 1.5, "open": 3.0, "push": 5.0, "act": 1.0}


class RobotMapper(Mapper):
    def map(self, primitives: list, goal: SubGoal) -> Executable:
        scale = float(goal.constraints.get("torque_scale", 1.0))
        degrade = any((p.meta or {}).get("degrade") for p in primitives)
        if degrade:
            scale *= 0.5
        steps = []
        for p in primitives:
            base = BASE_TORQUE_NM.get(p.kind, 1.0) * scale
            steps.append({
                "primitive": p.kind,
                "torques_nm": [round(base, 4)] * DOF,
                "target_xyz": p.params.get("target_xyz"),
            })
        peak = max((s["torques_nm"][0] for s in steps), default=0.0)
        return Executable(
            modality="physical",
            payload={"steps": steps, "dof": DOF, "peak_torque_nm": peak},
            meta={"degraded": degrade, "torque_scale": scale},
        )


if __name__ == "__main__":
    m = RobotMapper()
    prims = [Primitive("grasp", {"target_xyz": [0.4, 0, 0.2]}, {}),
             Primitive("move", {"target_xyz": [0.6, 0, 0.2]}, {})]
    g = SubGoal("s", "robot", "g", "", [], {})
    e = m.map(prims, g)
    assert e.payload["peak_torque_nm"] == 4.0 and not e.meta["degraded"]

    # degrade halves torques
    prims_d = [Primitive("move", {}, {"degrade": True})]
    e2 = m.map(prims_d, g)
    assert e2.payload["peak_torque_nm"] == 2.0 and e2.meta["degraded"]

    # torque_scale from constraints
    g3 = SubGoal("s", "robot", "g", "", [], {"torque_scale": 10.0})
    e3 = m.map(prims, g3)
    assert e3.payload["peak_torque_nm"] == 40.0
    print("[OK] robot mapper self-test passed")
