"""RobotExecutor — S12 execution (ZERO-TORQUE MOCK, no real hardware).

Produces a Delivery describing what WOULD be sent to the arm, plus telemetry
kind/data in Delivery.meta (contract §8: scene fills kind/data, common stores).
"""

import time

from common.interfaces.abstract import Executor
from common.interfaces.data_objects import Executable, Delivery


class RobotExecutor(Executor):
    def execute(self, executable: Executable) -> Delivery:
        p = executable.payload or {}
        steps = p.get("steps", [])
        # ZERO-TORQUE mock: we log the commanded torques but "send" zeros.
        commanded = [{"primitive": s["primitive"], "sent_torques_nm": [0.0] * p.get("dof", 7)}
                     for s in steps]
        return Delivery(
            target="robot",
            artifact={"mock_execution": True, "steps_executed": len(steps),
                      "commanded": commanded},
            meta={
                "telemetry_kind": "torque",
                "telemetry_data": {
                    "peak_torque_nm": p.get("peak_torque_nm", 0.0),
                    "steps": len(steps),
                    "degraded": (executable.meta or {}).get("degraded", False),
                    "executed_at": time.time(),
                },
            },
        )


if __name__ == "__main__":
    ex = RobotExecutor()
    e = Executable("physical", {"steps": [{"primitive": "grasp", "torques_nm": [2.0] * 7}],
                                "dof": 7, "peak_torque_nm": 2.0}, {})
    d = ex.execute(e)
    assert d.target == "robot" and d.artifact["steps_executed"] == 1
    assert d.artifact["commanded"][0]["sent_torques_nm"] == [0.0] * 7  # zero-torque mock
    assert d.meta["telemetry_kind"] == "torque"
    print("[OK] robot executor self-test passed")
