"""V2 video-branch tests — end-to-end through the frozen common kernel.

Covers: normal closed loop, S9->S7 retry (duration refinement), SafetyGate
audit BLOCK, passthrough PASS, DEGRADE->PASS, plus determinism and the
component-level contract of the VideoBackbone anti-corruption layer.

Runs under pytest OR plain python (python -m tests.test_video_branch).
"""

import os
import tempfile

from branches.video import register as register_video
from branches.video.backbone_mock import MockVideoBackbone
from branches.video.backbone_interface import VideoBackbone
from branches.video.safety_gate import VideoSafetyGate
from common.interfaces.data_objects import Executable, SafetyVerdict
from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel

NSFW = "an explicit sex scene"


def _orch(safety_mode="audit"):
    reg = Registry()
    register_video(reg, safety_mode=safety_mode)
    buf = os.path.join(tempfile.gettempdir(), f"fsb_video_{safety_mode}.jsonl")
    return Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf), max_retry=3)


def test_normal_closed_loop():
    m = _orch().run({"subgoals": [
        {"id": "sg", "target": "video", "goal": "a cat running on the grass",
         "constraints": {"duration_s": 5.0, "fps": 24, "resolution": [640, 480]}}]})
    assert m.success and m.retries == 0 and m.meta["subgoals"]["sg"] == "ok"


def test_retry_duration_refinement():
    m = _orch().run({"subgoals": [
        {"id": "sg", "target": "video", "goal": "a dog running on the road",
         "constraints": {"duration_s": 5.0, "initial_drift_s": 2.0}}]})
    assert m.success and m.retries >= 1


def test_safety_audit_block():
    m = _orch("audit").run({"subgoals": [
        {"id": "sg", "target": "video", "goal": NSFW, "constraints": {"duration_s": 5.0}}]})
    assert not m.success and "BLOCK" in m.meta["subgoals"]["sg"]


def test_safety_passthrough_pass():
    m = _orch("passthrough").run({"subgoals": [
        {"id": "sg", "target": "video", "goal": NSFW, "constraints": {"duration_s": 5.0}}]})
    assert m.success


def test_safety_degrade_then_pass():
    m = _orch("audit").run({"subgoals": [
        {"id": "sg", "target": "video", "goal": "a bird flying in the sky",
         "constraints": {"duration_s": 2.0, "resolution": [160, 120]}}]})
    assert m.success  # DEGRADE -> clamp to 240p -> re-check PASS


def test_backbone_is_anticorruption_layer():
    assert isinstance(MockVideoBackbone(), VideoBackbone)
    info = MockVideoBackbone().get_info()
    assert set(info) >= {"name", "version", "license", "capabilities"}


def test_backbone_determinism():
    b = MockVideoBackbone()
    o1 = b.generate("a cat running on the grass", {"duration_s": 5.0})
    o2 = b.generate("a cat running on the grass", {"duration_s": 5.0})
    assert o1["meta"]["color"] == o2["meta"]["color"]
    assert o1["duration_s"] == o2["duration_s"] == 5.0


def test_safety_dual_mode_switch():
    blk = Executable("pixel", {"text_prompt": NSFW, "resolution": [640, 480],
                               "duration_s": 5.0}, {})
    assert VideoSafetyGate("audit").check(blk) is SafetyVerdict.BLOCK
    assert VideoSafetyGate("passthrough").check(blk) is SafetyVerdict.PASS


ALL = [test_normal_closed_loop, test_retry_duration_refinement, test_safety_audit_block,
       test_safety_passthrough_pass, test_safety_degrade_then_pass,
       test_backbone_is_anticorruption_layer, test_backbone_determinism,
       test_safety_dual_mode_switch]

if __name__ == "__main__":
    for t in ALL:
        t()
        print(f"[OK] {t.__name__}")
    print(f"[PASS] video branch: {len(ALL)} tests green")
