"""game adapter — anti-corruption layer + registration (contract §13, E1-E6).

- The ONLY place a real backbone (MarioGPT / GameGen-O / OASIS via Azure) is ever
  wired in. Backbone default: MockGameBackbone. Switch via `backbone=`; the rest of
  the branch and ALL of common stay unchanged (swap = one line here).
- Two generation directions share ONE target="game", selected by `direction`
  ("level" | "worldmodel") — a build-time knob, never in common/orchestrator.
- SafetyGate is DUAL-MODE: `safety_mode='audit'` (default) or `'passthrough'`.
- Ships `register(registry)` so the orchestrator discovers this scene ONLY via
  Registry (it never imports branch modules).

Pure stdlib. Zero third-party dependencies.
"""

from branches.game.backbone_mock import MockGameBackbone
from branches.game.wam import GameWAM
from branches.game.critic import GameCritic
from branches.game.primitives import GamePrimitiveLibrary
from branches.game.mapper import GameMapper
from branches.game.executor import GameExecutor
from branches.game.safety_gate import GameSafetyGate
from common.registry.registry import Registry, BranchBundle

TARGET = "game"
MODALITY = "pixel"


def _make_backbone(backbone: str):
    if backbone == "mock":
        return MockGameBackbone()
    if backbone in ("gamegen-azure", "oasis-azure", "mariogpt-azure"):
        raise NotImplementedError(
            f"backbone '{backbone}' not integrated yet; V3 is mock-only "
            "(real models go through Azure after engineering-setup §2 T1-T5 gates)")
    raise ValueError(f"unknown backbone '{backbone}'")


def build_bundle(direction: str = "level", backbone: str = "mock",
                 safety_mode: str = "audit") -> BranchBundle:
    """direction: 'level' | 'worldmodel' (shared target='game').
    backbone: 'mock' (V3) | 'gamegen-azure'|... (future, must pass T1-T5).
    safety_mode: 'audit' (content moderation) | 'passthrough' (no checks)."""
    return BranchBundle(
        target=TARGET,
        modality=MODALITY,
        world_model=GameWAM(_make_backbone(backbone), direction=direction),
        critic=GameCritic(),
        primitives=GamePrimitiveLibrary(),
        mapper=GameMapper(),
        executor=GameExecutor(),
        safety_gate=GameSafetyGate(mode=safety_mode),
    )


def register(registry: Registry, direction: str = "level", backbone: str = "mock",
             safety_mode: str = "audit") -> None:
    registry.register(build_bundle(direction, backbone, safety_mode))


if __name__ == "__main__":
    # default (audit, level) bundle registers
    r = Registry()
    register(r)
    b = r.resolve(TARGET)
    assert b.modality == MODALITY and b.safety_gate is not None
    assert b.safety_gate.mode == "audit"

    # worldmodel direction
    r2 = Registry()
    register(r2, direction="worldmodel")
    assert r2.resolve(TARGET).world_model.direction == "worldmodel"

    # passthrough mode switch
    r3 = Registry()
    register(r3, safety_mode="passthrough")
    assert r3.resolve(TARGET).safety_gate.mode == "passthrough"

    # non-mock backbone rejected until Azure gates pass
    try:
        build_bundle("level", "gamegen-azure")
        raise AssertionError("non-mock backbone should raise")
    except NotImplementedError:
        pass
    print("[OK] game adapter/registration self-test passed (level + worldmodel + audit + passthrough + gate)")
