"""Scene3DSafetyGate — pass-through with a sanity bound (v1-plan §3: 3d may
use pass-through; we keep one generic sanity check so the hook is real).

BLOCK only if the mesh spec is absurdly large (mock resource guard).
"""

from common.interfaces.abstract import SafetyGate
from common.interfaces.data_objects import Executable, SafetyVerdict

MAX_VERTICES = 1_000_000


class Scene3DSafetyGate(SafetyGate):
    def check(self, executable: Executable) -> SafetyVerdict:
        p = executable.payload or {}
        if int(p.get("total_vertices", 0)) > MAX_VERTICES:
            return SafetyVerdict.BLOCK
        return SafetyVerdict.PASS


if __name__ == "__main__":
    g = Scene3DSafetyGate()
    assert g.check(Executable("geometry", {"total_vertices": 100}, {})) is SafetyVerdict.PASS
    assert g.check(Executable("geometry", {"total_vertices": 2_000_000}, {})) is SafetyVerdict.BLOCK
    print("[OK] 3d safety_gate self-test passed")
