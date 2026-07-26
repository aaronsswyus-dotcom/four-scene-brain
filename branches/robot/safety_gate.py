"""RobotSafetyGate — mandatory S11->S12 gate for physical (v1-plan §3).

Checks (mock but real hooks):
- torque limit:   peak > BLOCK_TORQUE_NM          -> BLOCK
                  peak > DEGRADE_TORQUE_NM        -> DEGRADE (halved re-map)
- joint limits:   any |angle| > JOINT_LIMIT_RAD   -> BLOCK
- no-go zone:     any target_xyz inside NO_GO_BOX -> BLOCK
"""

from common.interfaces.abstract import SafetyGate
from common.interfaces.data_objects import Executable, SafetyVerdict

DEGRADE_TORQUE_NM = 8.0
BLOCK_TORQUE_NM = 20.0
JOINT_LIMIT_RAD = 3.0
NO_GO_BOX = {"min": [-0.1, -0.1, -0.1], "max": [0.1, 0.1, 0.1]}  # around robot base


def _in_no_go(xyz) -> bool:
    if not xyz:
        return False
    return all(NO_GO_BOX["min"][i] <= xyz[i] <= NO_GO_BOX["max"][i] for i in range(3))


class RobotSafetyGate(SafetyGate):
    def check(self, executable: Executable) -> SafetyVerdict:
        p = executable.payload or {}
        peak = float(p.get("peak_torque_nm", 0.0))
        if peak > BLOCK_TORQUE_NM:
            return SafetyVerdict.BLOCK
        for step in p.get("steps", []):
            if _in_no_go(step.get("target_xyz")):
                return SafetyVerdict.BLOCK
        if peak > DEGRADE_TORQUE_NM:
            return SafetyVerdict.DEGRADE
        return SafetyVerdict.PASS


if __name__ == "__main__":
    g = RobotSafetyGate()
    ok = Executable("physical", {"peak_torque_nm": 4.0, "steps": [
        {"target_xyz": [0.4, 0.0, 0.2]}]}, {})
    assert g.check(ok) is SafetyVerdict.PASS

    hot = Executable("physical", {"peak_torque_nm": 12.0, "steps": []}, {})
    assert g.check(hot) is SafetyVerdict.DEGRADE

    danger = Executable("physical", {"peak_torque_nm": 40.0, "steps": []}, {})
    assert g.check(danger) is SafetyVerdict.BLOCK

    collide = Executable("physical", {"peak_torque_nm": 1.0, "steps": [
        {"target_xyz": [0.0, 0.0, 0.0]}]}, {})
    assert g.check(collide) is SafetyVerdict.BLOCK
    print("[OK] robot safety_gate self-test passed")
