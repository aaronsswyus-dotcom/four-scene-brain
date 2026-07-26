"""video adapter — anti-corruption layer + registration (contract §13, E1-E6).

- The ONLY place a real backbone (HunyuanVideo / Wan-2.1 via Azure) is ever wired in.
- Backbone default: MOCK (MockVideoBackbone). Switch via `backbone=`; the rest of
  the branch and ALL of common stay unchanged (swap = one line here).
- SafetyGate is DUAL-MODE: `safety_mode='audit'` (default) or `'passthrough'`.
- Ships `register(registry)` so the orchestrator discovers this scene ONLY via
  Registry (it never imports branch modules).
"""

from branches.video.backbone_mock import MockVideoBackbone
from branches.video.wam import VideoWAM
from branches.video.critic import VideoCritic
from branches.video.primitives import VideoPrimitiveLibrary
from branches.video.mapper import VideoMapper
from branches.video.executor import VideoExecutor
from branches.video.safety_gate import VideoSafetyGate
from common.registry.registry import Registry, BranchBundle

TARGET = "video"
MODALITY = "pixel"


def _make_backbone(backbone: str):
    if backbone == "mock":
        return MockVideoBackbone()
    if backbone in ("hunyuan-azure", "wan-azure", "cogvideox-azure"):
        raise NotImplementedError(
            f"backbone '{backbone}' not integrated yet; V2 is mock-only "
            "(real models go through Azure after engineering-setup §2 T1-T5 gates)")
    raise ValueError(f"unknown backbone '{backbone}'")


def build_bundle(backbone: str = "mock", safety_mode: str = "audit") -> BranchBundle:
    """backbone: 'mock' (V2) | 'hunyuan-azure'|... (future, must pass T1-T5).
    safety_mode: 'audit' (content moderation) | 'passthrough' (no checks)."""
    return BranchBundle(
        target=TARGET,
        modality=MODALITY,
        world_model=VideoWAM(_make_backbone(backbone)),
        critic=VideoCritic(),
        primitives=VideoPrimitiveLibrary(),
        mapper=VideoMapper(),
        executor=VideoExecutor(),
        safety_gate=VideoSafetyGate(mode=safety_mode),
    )


def register(registry: Registry, backbone: str = "mock", safety_mode: str = "audit") -> None:
    registry.register(build_bundle(backbone, safety_mode))


if __name__ == "__main__":
    # default (audit) bundle registers
    r = Registry()
    register(r)
    b = r.resolve(TARGET)
    assert b.modality == MODALITY and b.safety_gate is not None
    assert b.safety_gate.mode == "audit"

    # passthrough mode switch
    r2 = Registry()
    register(r2, safety_mode="passthrough")
    assert r2.resolve(TARGET).safety_gate.mode == "passthrough"

    # non-mock backbone rejected until Azure gates pass
    try:
        build_bundle("hunyuan-azure")
        raise AssertionError("non-mock backbone should raise")
    except NotImplementedError:
        pass
    print("[OK] video adapter/registration self-test passed (audit + passthrough + gate)")
