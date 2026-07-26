"""test_integration — V5 P2: cross-branch integration tests.

Verifies the終局 proposition end-to-end:
  * one FROZEN kernel drives all four scenes registered in ONE Registry
  * cross-branch composite instructions run as SubGoal DAGs (3d->robot chaining)
  * every scene's Telemetry lands in ONE flywheel buffer; aggregate_by_branch
    groups by branch/kind correctly
  * single-branch closed loops still pass (no V1-V4 regression)
  * common/ git diff stays empty (integration must not leak into the kernel)

Branches interact ONLY via common's SubGoal DAG + State chaining — never import
each other. Runs under pytest OR plain python (python -m tests.test_integration).
"""

import importlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel
from branches.robot import register as register_robot
from branches.video import register as register_video
from branches.game import register as register_game
from examples._flywheel_view import aggregate_by_branch

register_3d = importlib.import_module("branches.3d.adapter").register

ROOT = Path(__file__).resolve().parent.parent


def _tmp_buffer(name: str) -> str:
    p = os.path.join(tempfile.gettempdir(), name)
    if os.path.exists(p):
        os.remove(p)
    return p


def _all_branches_registry(tmp_out: str) -> Registry:
    """One Registry with all four branches as plugins."""
    reg = Registry()
    register_3d(reg, task="robot_scene", output_dir=tmp_out)
    register_robot(reg)
    register_video(reg, safety_mode="audit")
    register_game(reg, direction="level", safety_mode="audit")
    return reg


def _orch(buffer_name: str, out_name: str):
    buf = _tmp_buffer(buffer_name)
    out = os.path.join(tempfile.gettempdir(), out_name)
    reg = _all_branches_registry(out)
    orch = Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf), max_retry=3)
    return orch, buf, reg


# ---------------------------------------------------------------- DAG chaining
def test_cross_branch_dag_3d_to_robot():
    """3d scene THEN robot grasp — robot depends_on 3d (State chaining)."""
    orch, _buf, _reg = _orch("fsb_int_dag.jsonl", "fsb_int_3d_a")
    m = orch.run({"subgoals": [
        {"id": "scene", "target": "3d",
         "goal": "generate a walkable room with a table and a red cup",
         "constraints": {"task": "robot_scene"}},
        {"id": "grasp", "target": "robot",
         "goal": "grasp the red cup and move to tray", "depends_on": ["scene"]},
    ]})
    assert m.success, m
    assert m.meta["subgoals"] == {"scene": "ok", "grasp": "ok"}, m
    assert len(m.critic_scores) >= 2


def test_dag_dependency_ordering_enforced():
    """Even if robot listed first, depends_on forces 3d to run before robot."""
    orch, _buf, _reg = _orch("fsb_int_order.jsonl", "fsb_int_3d_b")
    m = orch.run({"subgoals": [
        {"id": "grasp", "target": "robot",
         "goal": "grasp the cup", "depends_on": ["scene"]},
        {"id": "scene", "target": "3d",
         "goal": "generate a room with a table and a cup",
         "constraints": {"task": "robot_scene"}},
    ]})
    assert m.success and m.meta["subgoals"] == {"scene": "ok", "grasp": "ok"}, m


# ---------------------------------------------------------------- pixel composite
def test_pixel_composite_video_and_game():
    """video + game in one run (independent subgoals, pixel camp)."""
    orch, _buf, _reg = _orch("fsb_int_pixel.jsonl", "fsb_int_3d_c")
    m = orch.run({"subgoals": [
        {"id": "clip", "target": "video",
         "goal": "a cat running on the grass",
         "constraints": {"duration_s": 5.0, "fps": 24, "resolution": [640, 480]}},
        {"id": "playlevel", "target": "game",
         "goal": "a playable platformer level",
         "constraints": {"direction": "level"}},
    ]})
    assert m.success, m
    assert m.meta["subgoals"] == {"clip": "ok", "playlevel": "ok"}, m


# ---------------------------------------------------------------- unified flywheel
def test_unified_flywheel_aggregation():
    """Run both composites; one jsonl holds >=2 kinds; aggregate groups by branch."""
    orch, buf, _reg = _orch("fsb_int_fly.jsonl", "fsb_int_3d_d")
    orch.run({"subgoals": [
        {"id": "scene", "target": "3d",
         "goal": "generate a room with a table and a cup",
         "constraints": {"task": "robot_scene"}},
        {"id": "grasp", "target": "robot", "goal": "grasp the cup",
         "depends_on": ["scene"]},
    ]})
    orch.run({"subgoals": [
        {"id": "clip", "target": "video", "goal": "a cat running",
         "constraints": {"duration_s": 5.0}},
        {"id": "playlevel", "target": "game", "goal": "a playable level",
         "constraints": {"direction": "level"}},
    ]})
    rows = [json.loads(x) for x in Path(buf).read_text(encoding="utf-8").splitlines()]
    kinds = {r["kind"] for r in rows}
    assert kinds >= {"geometry", "torque", "video", "game"}, kinds

    agg = aggregate_by_branch(buf)
    branches = {g["branch"] for g in agg.values()}
    assert branches >= {"3d", "robot", "video", "game"}, branches
    assert agg["torque"]["branch"] == "robot"
    assert agg["geometry"]["branch"] == "3d"
    assert sum(g["count"] for g in agg.values()) == len(rows)


# ---------------------------------------------------------------- no regression
def test_single_branch_loops_still_pass():
    """Each branch, invoked alone via the shared registry, closes its own loop."""
    orch, _buf, _reg = _orch("fsb_int_single.jsonl", "fsb_int_3d_e")
    r_robot = orch.run({"subgoals": [
        {"id": "g", "target": "robot", "goal": "grasp the red cup"}]})
    assert r_robot.success, r_robot
    r_3d = orch.run({"subgoals": [
        {"id": "s", "target": "3d", "goal": "a room with a table and a cup",
         "constraints": {"task": "robot_scene"}}]})
    assert r_3d.success, r_3d
    r_video = orch.run({"subgoals": [
        {"id": "v", "target": "video", "goal": "a cat running",
         "constraints": {"duration_s": 5.0}}]})
    assert r_video.success, r_video
    r_game = orch.run({"subgoals": [
        {"id": "gm", "target": "game", "goal": "a playable level",
         "constraints": {"direction": "level"}}]})
    assert r_game.success, r_game


def test_all_four_targets_registered_one_registry():
    reg = _all_branches_registry(os.path.join(tempfile.gettempdir(), "fsb_int_3d_f"))
    assert set(reg.targets()) == {"robot", "3d", "video", "game"}, reg.targets()


# ---------------------------------------------------------------- zero-diff guard
def test_common_git_diff_empty_after_integration():
    """Registering all four branches must not have touched common/."""
    r = subprocess.run(["git", "status", "--porcelain", "--", "common/"],
                       cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("git repo required for zero-diff check")
    dirty = [line for line in r.stdout.splitlines() if line.strip()]
    assert not dirty, f"common/ dirtied by integration -> leak: {dirty}"


ALL = [
    test_cross_branch_dag_3d_to_robot,
    test_dag_dependency_ordering_enforced,
    test_pixel_composite_video_and_game,
    test_unified_flywheel_aggregation,
    test_single_branch_loops_still_pass,
    test_all_four_targets_registered_one_registry,
    test_common_git_diff_empty_after_integration,
]

if __name__ == "__main__":
    for t in ALL:
        t()
        print(f"[OK] {t.__name__}")
    print(f"[PASS] integration: {len(ALL)} tests green "
          "(cross-branch DAG + unified flywheel + no regression + zero-diff)")
