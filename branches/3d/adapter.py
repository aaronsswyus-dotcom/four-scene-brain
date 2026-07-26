"""3d adapter — anti-corruption layer + registration (contract §13, E1-E6).

Scope: ONE target="3d" / modality="geometry" spanning the multi-task family
(V4). The generation task is a BUILD-TIME knob — never in common/orchestrator:
    task = "robot_scene" (V1, DEFAULT, backbone-free inline path)
         | "text_to_3d" | "image_to_3d" | "pointcloud_completion" | "pbr_texture"

- The ONLY place a real backbone (TRELLIS / DreamGaussian / TripoSR / Shap-E via
  Azure) is ever wired in. Default: MockThreeDBackbone. Switch via `backbone=`;
  the rest of the branch and ALL of common stay unchanged (swap = one line here).
- SafetyGate is DUAL-MODE: `safety_mode='audit'` (default) | 'passthrough'.

Import note: package dir is 'branches/3d' (digit prefix). Load this module via
    importlib.import_module('branches.3d.adapter')
Intra-package imports below are RELATIVE, which works fine.
"""

from common.registry.registry import Registry, BranchBundle

from .wam import Scene3DWAM
from .critic import Scene3DCritic
from .primitives import Scene3DPrimitiveLibrary
from .mapper import Scene3DMapper
from .exporter import Scene3DExporter
from .safety_gate import Scene3DSafetyGate
from .backbone_mock import MockThreeDBackbone

TARGET = "3d"
MODALITY = "geometry"
TASKS = ("robot_scene", "text_to_3d", "image_to_3d", "pointcloud_completion", "pbr_texture")


def _make_backbone(backbone: str):
    if backbone == "mock":
        return MockThreeDBackbone()
    if backbone in ("trellis-azure", "dreamgaussian-azure", "triposr-azure", "shape-azure"):
        raise NotImplementedError(
            f"backbone '{backbone}' not integrated yet; V4 is mock-only "
            "(real models go through Azure after engineering-setup §2 T1-T5 gates)")
    raise ValueError(f"unknown backbone '{backbone}'")


def build_bundle(task: str = "robot_scene", backbone: str = "mock",
                 safety_mode: str = "audit", output_dir: str = "output/3d") -> BranchBundle:
    """task: 'robot_scene' (V1) | 'text_to_3d'|'image_to_3d'|'pointcloud_completion'|'pbr_texture' (V4).
    backbone: 'mock' (V4) | 'trellis-azure'|... (future, must pass T1-T5).
    safety_mode: 'audit' (content moderation) | 'passthrough' (no checks)."""
    if task not in TASKS:
        raise ValueError(f"unknown 3d task '{task}' (expected one of {TASKS})")
    return BranchBundle(
        target=TARGET,
        modality=MODALITY,
        world_model=Scene3DWAM(_make_backbone(backbone), task=task),
        critic=Scene3DCritic(),
        primitives=Scene3DPrimitiveLibrary(),
        mapper=Scene3DMapper(),
        executor=Scene3DExporter(output_dir),
        safety_gate=Scene3DSafetyGate(mode=safety_mode),
    )


def register(registry: Registry, task: str = "robot_scene", backbone: str = "mock",
             safety_mode: str = "audit", output_dir: str = "output/3d") -> None:
    registry.register(build_bundle(task, backbone, safety_mode, output_dir))


if __name__ == "__main__":
    # default (robot_scene, audit) — V1 behaviour
    r = Registry()
    register(r)
    b = r.resolve(TARGET)
    assert b.modality == MODALITY and b.safety_gate is not None
    assert b.world_model.task == "robot_scene" and b.safety_gate.mode == "audit"

    # V4 task knob
    r2 = Registry()
    register(r2, task="text_to_3d")
    assert r2.resolve(TARGET).world_model.task == "text_to_3d"

    # passthrough mode switch
    r3 = Registry()
    register(r3, safety_mode="passthrough")
    assert r3.resolve(TARGET).safety_gate.mode == "passthrough"

    # unknown task rejected
    try:
        build_bundle(task="hologram")
        raise AssertionError("unknown task should raise")
    except ValueError:
        pass

    # non-mock backbone rejected until Azure gates pass
    try:
        build_bundle("text_to_3d", "trellis-azure")
        raise AssertionError("non-mock backbone should raise")
    except NotImplementedError:
        pass
    print("[OK] 3d adapter/registration self-test passed (robot_scene V1 + task knob + dual-mode)")
