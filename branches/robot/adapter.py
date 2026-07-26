"""robot adapter — anti-corruption layer + registration (contract §13, E1-E6).

- The ONLY place a real backbone (GR00T via Azure) will ever be wired in.
- Backbone default: MOCK (RobotWAM). Switch via `backbone=` argument later;
  the rest of the branch and ALL of common stay unchanged.
- Ships `register(registry)` so the orchestrator discovers this scene ONLY
  via Registry.
"""

from common.registry.registry import Registry, BranchBundle
from branches.robot.wam import RobotWAM
from branches.robot.critic import RobotCritic
from branches.robot.primitives import RobotPrimitiveLibrary
from branches.robot.mapper import RobotMapper
from branches.robot.executor import RobotExecutor
from branches.robot.safety_gate import RobotSafetyGate

TARGET = "robot"
MODALITY = "physical"


def build_bundle(backbone: str = "mock") -> BranchBundle:
    """backbone: 'mock' (V1) | 'groot-azure' (future, must pass T1-T5 gates)."""
    if backbone != "mock":
        raise NotImplementedError(
            f"backbone '{backbone}' not integrated yet; V1 is mock-only "
            "(real GR00T goes through Azure after engineering-setup §2 gates)")
    return BranchBundle(
        target=TARGET,
        modality=MODALITY,
        world_model=RobotWAM(),
        critic=RobotCritic(),
        primitives=RobotPrimitiveLibrary(),
        mapper=RobotMapper(),
        executor=RobotExecutor(),
        safety_gate=RobotSafetyGate(),   # physical MUST provide
    )


def register(registry: Registry, backbone: str = "mock") -> None:
    registry.register(build_bundle(backbone))


if __name__ == "__main__":
    r = Registry()
    register(r)
    b = r.resolve(TARGET)
    assert b.modality == MODALITY and b.safety_gate is not None
    try:
        build_bundle("groot-azure")
        raise AssertionError("non-mock backbone should raise")
    except NotImplementedError:
        pass
    print("[OK] robot adapter/registration self-test passed")
