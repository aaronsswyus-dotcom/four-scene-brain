"""V4 3d-branch tests — full-3D multi-task through the frozen common kernel.

Covers the task family (ONE target="3d", adapter `task` knob):
  - text_to_3d / image_to_3d / pointcloud_completion / pbr_texture closed loops
  - S9->S7 retry (challenge asset: degenerate geometry -> refine -> pass)
  - SafetyGate audit BLOCK (nsfw/copyright) / passthrough PASS (dual-mode)
  - backbone anti-corruption contract + determinism
  - Critic correctness per task + V1 robot_scene NON-regression

The package dir 'branches/3d' starts with a digit, so imports go through
importlib (same as examples/3d_scene_demo). Runs under pytest OR plain python
(python -m tests.test_3d_branch).
"""

import importlib
import os
import tempfile

from common.interfaces.data_objects import (
    Draft, SubGoal, Executable, SafetyVerdict, FailureKind)
from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel

_adapter = importlib.import_module("branches.3d.adapter")
register_3d = _adapter.register
MockThreeDBackbone = importlib.import_module("branches.3d.backbone_mock").MockThreeDBackbone
ThreeDBackbone = importlib.import_module("branches.3d.backbone_interface").ThreeDBackbone
Scene3DCritic = importlib.import_module("branches.3d.critic").Scene3DCritic
Scene3DSafetyGate = importlib.import_module("branches.3d.safety_gate").Scene3DSafetyGate

BLOCK = "a nsfw mickey mouse statue"


def _orch(task="text_to_3d", safety_mode="audit"):
    reg = Registry()
    out = os.path.join(tempfile.gettempdir(), "fsb_3d_out")
    register_3d(reg, task=task, safety_mode=safety_mode, output_dir=out)
    buf = os.path.join(tempfile.gettempdir(), f"fsb_3d_{task}_{safety_mode}.jsonl")
    return Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf), max_retry=3)


def _sg(task, goal, constraints):
    return {"subgoals": [{"id": "sg", "target": "3d", "goal": goal, "constraints": constraints}]}


# ----------------------------- end-to-end -----------------------------------

def test_text_to_3d_closed_loop():
    m = _orch("text_to_3d").run(_sg("text_to_3d", "生成一个红色木椅 red wooden chair", {}))
    assert m.success and m.retries == 0 and m.meta["subgoals"]["sg"] == "ok"


def test_image_to_3d_closed_loop():
    m = _orch("image_to_3d").run(_sg("image_to_3d", "concept image -> a chair",
                                     {"source_image": "chair.png"}))
    assert m.success and m.meta["subgoals"]["sg"] == "ok"


def test_pointcloud_completion_closed_loop():
    m = _orch("pointcloud_completion").run(_sg("pointcloud_completion",
                                               "complete the cloud", {"source_points": 500}))
    assert m.success


def test_pbr_texture_closed_loop():
    m = _orch("pbr_texture").run(_sg("pbr_texture", "shiny metal helmet", {}))
    assert m.success


def test_retry_challenge_asset():
    m = _orch("text_to_3d").run(_sg("text_to_3d", "challenge asset", {"challenge": True}))
    assert m.success and m.retries >= 1


def test_all_tasks_share_one_target():
    for t in ("robot_scene", "text_to_3d", "image_to_3d", "pointcloud_completion", "pbr_texture"):
        reg = Registry()
        register_3d(reg, task=t)
        b = reg.resolve("3d")
        assert b.target == "3d" and b.modality == "geometry" and b.world_model.task == t


# ------------------------------- safety -------------------------------------

def test_safety_audit_block():
    m = _orch("text_to_3d", "audit").run(_sg("text_to_3d", BLOCK, {}))
    assert not m.success and "BLOCK" in m.meta["subgoals"]["sg"]


def test_safety_passthrough_pass():
    m = _orch("text_to_3d", "passthrough").run(_sg("text_to_3d", BLOCK, {}))
    assert m.success


def test_safety_dual_mode_and_v1_guard():
    blk = Executable("geometry", {"task": "text_to_3d", "text_prompt": BLOCK,
                                  "total_vertices": 8, "geometry": {"vertices": 8, "bbox": [1, 1, 1]}}, {})
    assert Scene3DSafetyGate("audit").check(blk) is SafetyVerdict.BLOCK
    assert Scene3DSafetyGate("passthrough").check(blk) is SafetyVerdict.PASS
    # V1 resource guard preserved
    huge = Executable("geometry", {"total_vertices": 2_000_000}, {})
    assert Scene3DSafetyGate("audit").check(huge) is SafetyVerdict.BLOCK
    assert Scene3DSafetyGate("audit").check(Executable("geometry", {"total_vertices": 100}, {})) is SafetyVerdict.PASS


# ---------------------- backbone anti-corruption layer ----------------------

def test_backbone_is_anticorruption_layer():
    assert isinstance(MockThreeDBackbone(), ThreeDBackbone)
    info = MockThreeDBackbone().get_info()
    assert set(info) >= {"name", "version", "license", "capabilities"}


def test_backbone_determinism():
    b = MockThreeDBackbone()
    o1 = b.generate("a red wooden chair", {"task": "text_to_3d"})
    o2 = b.generate("a red wooden chair", {"task": "text_to_3d"})
    assert o1 == o2 and o1["geometry"]["manifold"]


def test_backbone_rejects_robot_scene():
    try:
        MockThreeDBackbone().generate("x", {"task": "robot_scene"})
        raise AssertionError("robot_scene must not go through backbone")
    except ValueError:
        pass


# --------------------------- Critic correctness -----------------------------

def test_critic_accepts_valid_text_to_3d():
    b, c = MockThreeDBackbone(), Scene3DCritic()
    d = Draft("geometry", b.generate("a red wooden chair", {"task": "text_to_3d"}), {})
    assert c.verify(d, SubGoal("s", "3d", "a red wooden chair", "", [], {})).passed


def test_critic_rejects_degenerate_geometry():
    b, c = MockThreeDBackbone(), Scene3DCritic()
    bad = b.generate("x", {"task": "text_to_3d", "challenge": True, "retry": 0})
    v = c.verify(Draft("geometry", bad, {}), SubGoal("s", "3d", "x", "", [], {}))
    assert not v.passed and v.failure_kind is FailureKind.RETRYABLE_QUALITY


def test_critic_rejects_pointcloud_shrink():
    b, c = MockThreeDBackbone(), Scene3DCritic()
    bad = b.generate("y", {"task": "pointcloud_completion", "source_points": 400,
                           "challenge": True, "retry": 0})
    assert not c.verify(Draft("geometry", bad, {}), SubGoal("s", "3d", "y", "", [], {})).passed


def test_critic_rejects_pbr_out_of_range():
    b, c = MockThreeDBackbone(), Scene3DCritic()
    bad = b.generate("metal helmet", {"task": "pbr_texture", "challenge": True, "retry": 0})
    assert not c.verify(Draft("geometry", bad, {}), SubGoal("s", "3d", "metal helmet", "", [], {})).passed


def test_critic_v1_robot_scene_not_regressed():
    c = Scene3DCritic()
    g = SubGoal("s", "3d", "walkable living room with table and cup", "", [], {})
    good = Draft("geometry", {"representation": "mesh", "fidelity": 0.9,
                              "semantics": {"objects": ["table", "cup"], "walkable": True}}, {})
    assert c.verify(good, g).passed
    low = Draft("geometry", {"representation": "mesh", "fidelity": 0.4,
                             "semantics": {"objects": ["table", "cup"], "walkable": True}}, {})
    assert not c.verify(low, g).passed
    assert c.verify(Draft("geometry", {}, {}), g).failure_kind is FailureKind.STRUCTURAL_INFEASIBLE


ALL = [test_text_to_3d_closed_loop, test_image_to_3d_closed_loop,
       test_pointcloud_completion_closed_loop, test_pbr_texture_closed_loop,
       test_retry_challenge_asset, test_all_tasks_share_one_target,
       test_safety_audit_block, test_safety_passthrough_pass,
       test_safety_dual_mode_and_v1_guard, test_backbone_is_anticorruption_layer,
       test_backbone_determinism, test_backbone_rejects_robot_scene,
       test_critic_accepts_valid_text_to_3d, test_critic_rejects_degenerate_geometry,
       test_critic_rejects_pointcloud_shrink, test_critic_rejects_pbr_out_of_range,
       test_critic_v1_robot_scene_not_regressed]

if __name__ == "__main__":
    for t in ALL:
        t()
        print(f"[OK] {t.__name__}")
    print(f"[PASS] 3d branch: {len(ALL)} tests green")
