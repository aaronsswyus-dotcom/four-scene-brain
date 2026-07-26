"""integration_demo — V5 P1: full four-scene integration + cross-branch flywheel.

The終局 proposition: one FROZEN kernel (common) simultaneously drives all four
scenes (robot / 3d / video / game), and every scene's Telemetry flows into ONE
flywheel buffer, then grouped by branch on the examples/ side.

Two composite (cross-branch) instructions:
  A. 3d -> robot  (State-chained DAG, physical camp):
     「生成机器人作业的客厅 3D 场景，然后让机器人把桌上红杯拿到托盘」
     -> [SubGoal 3d(robot_scene), SubGoal robot depends_on 3d]
  B. video + game (pixel camp, independent SubGoals in one run):
     「生成一段猫奔跑的视频，再生成一个可玩平台关卡」
     -> [SubGoal video, SubGoal game]

S4 decomposition here uses a tiny RULE/TEMPLATE parser (keyword -> target /
depends_on). No LLM (D1/D3: LLM parser is an optional plugin, not wired in v0).

Branches never import each other; they interact ONLY through common's SubGoal
DAG + State chaining (contract §6). common is untouched (zero-diff holds).

Pure stdlib. Run:  python -m examples.integration_demo   (from project root)
"""

import importlib
import json
import logging
from pathlib import Path

from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel
from branches.robot import register as register_robot
from branches.video import register as register_video
from branches.game import register as register_game
from examples._flywheel_view import aggregate_by_branch, print_summary

# '3d' package dir starts with a digit -> import via importlib (branch README caveat)
register_3d = importlib.import_module("branches.3d.adapter").register

BUFFER = Path("output/flywheel/integration_demo.jsonl")


# --------------------------------------------------------------- S4 template parser
def decompose(instruction: str) -> dict:
    """Rule/template S4 decomposition (v0, no LLM).

    Maps a known composite instruction to a SubGoal DAG spec that Orchestrator's
    RuleIntentParser consumes. Keyword-driven; targets/depends_on come from the
    template, never guessed by common.
    """
    text = instruction.lower()
    subgoals: list = []

    # physical composite: build 3D scene THEN robot acts on it (State chaining)
    if ("3d" in text or "场景" in instruction or "scene" in text) and \
       ("机器人" in instruction or "robot" in text or "拿" in instruction or "grasp" in text):
        subgoals = [
            {"id": "scene", "target": "3d",
             "goal": "generate a walkable living room for robot work: table with a red cup",
             "success_criteria": "walkable + contains table/cup",
             "constraints": {"task": "robot_scene"}},
            {"id": "grasp", "target": "robot",
             "goal": "grasp the red cup on the table and move it to the tray",
             "success_criteria": "force-torque within threshold",
             "depends_on": ["scene"]},
        ]
    # pixel composite: a video AND a playable level (independent subgoals)
    elif ("视频" in instruction or "video" in text) and \
         ("关卡" in instruction or "level" in text or "game" in text or "可玩" in instruction):
        subgoals = [
            {"id": "clip", "target": "video",
             "goal": "a cat running on the grass / 一只猫在草地上奔跑",
             "constraints": {"duration_s": 5.0, "fps": 24, "resolution": [640, 480]}},
            {"id": "playlevel", "target": "game",
             "goal": "a playable platformer level with a reachable goal / 可通关平台关卡",
             "constraints": {"direction": "level"}},
        ]
    if not subgoals:
        raise ValueError(f"decompose: no template matched instruction: {instruction!r}")
    return {"subgoals": subgoals}


def _build_registry() -> Registry:
    """One Registry, all four branches registered as plugins (contract §5)."""
    reg = Registry()
    register_3d(reg, task="robot_scene", output_dir="output/3d")  # physical camp
    register_robot(reg)                                           # physical camp
    register_video(reg, safety_mode="audit")                     # pixel camp
    register_game(reg, direction="level", safety_mode="audit")   # pixel camp
    return reg


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # fresh buffer so the aggregate view reflects this run only (truncate, don't delete)
    BUFFER.parent.mkdir(parents=True, exist_ok=True)
    BUFFER.write_text("", encoding="utf-8")

    registry = _build_registry()
    memory = InMemoryMemory()
    flywheel = FileBufferFlywheel(str(BUFFER))
    orch = Orchestrator(registry, memory, flywheel, max_retry=3)

    print("=" * 72)
    print("四场景已注册到同一内核：", sorted(registry.targets()))
    print("=" * 72)

    # ---- Composite A: 3d -> robot (State-chained DAG, physical camp) ----
    print("\n" + "=" * 72)
    print("复合指令 A（3d→robot，State 串联 DAG）：")
    print("  「生成机器人作业的客厅 3D 场景，然后让机器人把桌上红杯拿到托盘」")
    print("=" * 72)
    specA = decompose("生成机器人作业的客厅 3D 场景，然后让机器人把桌上红杯拿到托盘")
    print(f"S4 分解 -> {[ (s['id'], s['target'], s.get('depends_on', [])) for s in specA['subgoals'] ]}")
    mA = orch.run(specA)
    assert mA.success, mA
    assert mA.meta["subgoals"] == {"scene": "ok", "grasp": "ok"}, mA
    print(f"-> RunMetrics: success={mA.success} retries={mA.retries} "
          f"scores={mA.critic_scores}\n   subgoals={mA.meta['subgoals']} trace={mA.trace_id}")

    # ---- Composite B: video + game (pixel camp) ----
    print("\n" + "=" * 72)
    print("复合指令 B（video+game，像素阵营）：")
    print("  「生成一段猫奔跑的视频，再生成一个可玩平台关卡」")
    print("=" * 72)
    specB = decompose("生成一段猫奔跑的视频，再生成一个可玩平台关卡")
    print(f"S4 分解 -> {[ (s['id'], s['target'], s.get('depends_on', [])) for s in specB['subgoals'] ]}")
    mB = orch.run(specB)
    assert mB.success, mB
    assert mB.meta["subgoals"] == {"clip": "ok", "playlevel": "ok"}, mB
    print(f"-> RunMetrics: success={mB.success} retries={mB.retries} "
          f"scores={mB.critic_scores}\n   subgoals={mB.meta['subgoals']} trace={mB.trace_id}")

    # ---- Cross-branch flywheel aggregation (V5 core) ----
    print("\n" + "=" * 72)
    print("统一飞轮 —— 跨分支聚合视图（读同一 jsonl，按 branch/kind 分组）")
    print("=" * 72)
    agg = aggregate_by_branch(BUFFER)
    print_summary(agg)
    branches_hit = sorted({g["branch"] for g in agg.values()})
    assert set(branches_hit) >= {"3d", "robot", "video", "game"}, branches_hit
    print(f"\n✅ 四个分支的 Telemetry 全部落入同一飞轮缓冲：{branches_hit}")

    print("\n⚠️ 边界声明：本 demo 验证「冻结内核多场景并发驱动 + 跨分支数据飞轮闭环」，"
          "不证明任一分支的真实质量（全 mock backbone）。")
    print("[PASS] 集成 demo 全部通过（3d→robot 串联 + video+game + 跨分支飞轮聚合）")


if __name__ == "__main__":
    main()
