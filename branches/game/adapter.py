"""game adapter — anti-corruption layer + registration (contract §13, E1-E6).

- The ONLY place a real backbone is ever wired in. Backbone default:
  MockGameBackbone. Switch via `backbone=`; the rest of the branch and ALL of
  common stay unchanged (swap = one line here).
    * backbone='mock'      -> MockGameBackbone (V3 default, dep-free)
    * backbone='mariogpt'  -> MarioGPTBackbone (Phase 4 real, distilgpt2 ~82M,
                              CPU-runnable, MIT; mario_gpt lazily imported)
    * backbone='gamegen-azure'/'oasis-azure' -> NotImplementedError (Azure T1-T5 pending)
- Two generation directions share ONE target="game", selected by `direction`
  ("level" | "worldmodel") — a build-time knob, never in common/orchestrator.
- SafetyGate is DUAL-MODE: `safety_mode='audit'` (default) or `'passthrough'`.
- Ships `register(registry)` so the orchestrator discovers this scene ONLY via
  Registry (it never imports branch modules).

Pure stdlib. Zero third-party dependencies at import time (mariogpt is lazy).
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
    if backbone == "mariogpt":
        # Phase 4 real integration (game-A primary). distilgpt2 ~82M, CPU-runnable,
        # MIT license. mario_gpt is lazily imported inside generate() so mock tests
        # stay dependency-free. See branches/game/backbone_mariogpt.py.
        from branches.game.backbone_mariogpt import MarioGPTBackbone
        return MarioGPTBackbone()
    if backbone in ("gamegen-azure", "oasis-azure", "mariogpt-azure"):
        # gamegen-azure / oasis-azure: real backbones need Azure GPU (T1-T5 pending).
        # mariogpt-azure: legacy alias kept for V3 doc compat; use backbone='mariogpt'
        # for the real CPU-local MarioGPT integration (Phase 4).
        raise NotImplementedError(
            f"backbone '{backbone}' not integrated yet; "
            "gamegen-azure/oasis-azure need Azure T1-T5 gates; "
            "for MarioGPT use backbone='mariogpt' (CPU-local, Phase 4 real).")
    raise ValueError(f"unknown backbone '{backbone}'")


def build_bundle(direction: str = "level", backbone: str = "mock",
                 safety_mode: str = "audit") -> BranchBundle:
    """direction: 'level' | 'worldmodel' (shared target='game').
    backbone: 'mock' (default, dep-free) | 'mariogpt' (Phase 4 real, CPU)
              | 'gamegen-azure'/'oasis-azure' (future, Azure T1-T5 pending).
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
        raise AssertionError("non-mock azure backbone should raise")
    except NotImplementedError:
        pass

    # mariogpt (Phase 4 real) instantiates without importing mario_gpt (lazy);
    # the model is only pulled on first generate() call
    r4 = Registry()
    register(r4, backbone="mariogpt")
    bb = r4.resolve(TARGET)
    assert bb.world_model.backbone.__class__.__name__ == "MarioGPTBackbone"
    assert bb.world_model.backbone.get_info()["status"] == "real"

    print("[OK] game adapter/registration self-test passed "
          "(level + worldmodel + audit + passthrough + azure-gate + mariogpt-real)")
