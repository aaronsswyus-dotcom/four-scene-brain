"""3d_full_demo — V4 DoD: full-3D multi-task minimal closed loop (physical camp).

ONE target="3d" spans a task family via the adapter `task` knob:
  1. text_to_3d           : 「生成一个红色木椅的 3D 模型」-> 占位 GLB
  2. image_to_3d          : 「概念图 -> 3D GLB（一把椅子）」-> 占位 GLB
  3. pointcloud_completion: 稀疏点云 -> 补全（点数增加）
  4. pbr_texture          : 金属头盔 + PBR 材质（albedo/roughness/metallic）
  5. 重试路径            : 几何退化（faces=0/非 manifold）-> 回 S7 -> 成功
  6. SafetyGate 审核     : 版权/NSFW prompt -> BLOCK
  7. SafetyGate 放行     : 同一 prompt -> PASS（双模式可切换）
  8. V1 robot_scene 回归 : robot 作业场景仍走 V1 路径成功（不回归）

Run:  python -m examples.3d_full_demo   (from project root)
"""

import importlib
import json
import logging
from pathlib import Path

from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel

# package dir '3d' starts with a digit -> load via importlib (see branch README)
register_3d = importlib.import_module("branches.3d.adapter").register

BUFFER = Path("output/flywheel/3d_full_demo.jsonl")
BLOCK_PROMPT = "a nsfw mickey mouse statue"   # deliberately triggers audit BLOCK


def _orch(task="text_to_3d", safety_mode="audit") -> Orchestrator:
    reg = Registry()
    register_3d(reg, task=task, safety_mode=safety_mode, output_dir="output/3d")
    return Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(str(BUFFER)), max_retry=3)


def _run(orch, sid, goal, constraints, sc=""):
    return orch.run({"subgoals": [
        {"id": sid, "target": "3d", "goal": goal,
         "success_criteria": sc, "constraints": constraints}]})


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 72)
    print("DEMO 1 — text_to_3d：生成一个红色木椅的 3D 模型 -> 占位 GLB")
    print("=" * 72)
    m1 = _run(_orch("text_to_3d"), "t2d", "生成一个红色木椅 red wooden chair 的 3D 模型",
              {}, "几何达标 + text-3D 语义对齐")
    assert m1.success and m1.retries == 0, m1
    print(f"-> RunMetrics: success={m1.success} retries={m1.retries} scores={m1.critic_scores} trace={m1.trace_id}\n")

    print("=" * 72)
    print("DEMO 2 — image_to_3d：概念图 -> 3D GLB（一把椅子）")
    print("=" * 72)
    m2 = _run(_orch("image_to_3d"), "i2d", "concept image of a chair -> 3D",
              {"source_image": "chair_concept.png"}, "几何达标 + source 绑定")
    assert m2.success, m2
    print(f"-> RunMetrics: success={m2.success} retries={m2.retries} scores={m2.critic_scores}\n")

    print("=" * 72)
    print("DEMO 3 — pointcloud_completion：稀疏点云 -> 补全（点数增加）")
    print("=" * 72)
    m3 = _run(_orch("pointcloud_completion"), "pc", "complete this sparse point cloud",
              {"source_points": 500}, "补全后点数 >= 输入")
    assert m3.success, m3
    print(f"-> RunMetrics: success={m3.success} retries={m3.retries} scores={m3.critic_scores}\n")

    print("=" * 72)
    print("DEMO 4 — pbr_texture：金属头盔 + PBR 材质")
    print("=" * 72)
    m4 = _run(_orch("pbr_texture"), "pbr", "shiny metal helmet 金属头盔",
              {}, "albedo/roughness/metallic ∈ [0,1]")
    assert m4.success, m4
    print(f"-> RunMetrics: success={m4.success} retries={m4.retries} scores={m4.critic_scores}\n")

    print("=" * 72)
    print("DEMO 5 — 重试路径：几何退化（faces=0/非 manifold）-> 回 S7 -> 成功")
    print("=" * 72)
    m5 = _run(_orch("text_to_3d"), "ch", "challenge asset",
              {"challenge": True}, "退化几何触发重试后修复")
    assert m5.success and m5.retries >= 1, m5
    print(f"-> RunMetrics: success={m5.success} retries={m5.retries} scores={m5.critic_scores}\n")

    print("=" * 72)
    print("DEMO 6 — SafetyGate 审核模式：版权/NSFW prompt -> BLOCK")
    print("=" * 72)
    m6 = _run(_orch("text_to_3d", "audit"), "blk", BLOCK_PROMPT, {})
    assert not m6.success and "BLOCK" in m6.meta["subgoals"]["blk"], m6
    print(f"-> RunMetrics: success={m6.success} reason={m6.meta['subgoals']['blk']}\n")

    print("=" * 72)
    print("DEMO 7 — SafetyGate 放行模式：同一 prompt -> PASS（双模式可切换）")
    print("=" * 72)
    m7 = _run(_orch("text_to_3d", "passthrough"), "pass", BLOCK_PROMPT, {})
    assert m7.success, m7
    print(f"-> RunMetrics: success={m7.success} scores={m7.critic_scores}\n")

    print("=" * 72)
    print("DEMO 8 — V1 robot_scene 回归：robot 作业客厅场景仍走 V1 路径成功")
    print("=" * 72)
    m8 = _run(_orch("robot_scene"), "rs",
              "generate a walkable living room for robot work: a table with a red cup on it",
              {}, "walkable + fidelity + contains table/cup")
    assert m8.success, m8
    print(f"-> RunMetrics: success={m8.success} retries={m8.retries} scores={m8.critic_scores}\n")

    rows = [json.loads(x) for x in BUFFER.read_text(encoding="utf-8").splitlines()]
    tasks = sorted({r.get("data", {}).get("task") for r in rows if r.get("data", {}).get("task")})
    print(f"[flywheel] {BUFFER} 共 {len(rows)} 条 Telemetry，全部带 trace_id："
          f"{all(r.get('trace_id') for r in rows)}，kind 全为 geometry："
          f"{all(r.get('kind') == 'geometry' for r in rows)}")
    print(f"[flywheel] 生成式任务标签: {tasks}")
    glbs = sorted(Path("output/3d").glob("model_*.glb"))
    scenes = sorted(Path("output/3d").glob("scene_*.glb"))
    print(f"[artifact] output/3d/ 共 {len(glbs)} 个 model_*.glb（生成式）+ {len(scenes)} 个 scene_*.glb（robot_scene）")
    print("\n⚠️ 边界声明：本 demo 验证编排内核/接口/飞轮在物理阵营第二个分支（完整 3D 多任务）同样成立，"
          "不证明 3D 几何质量（全 mock 占位盒体）。")
    print("[PASS] 3d 完整多任务最小闭环全部通过（text/image/pointcloud/pbr/重试/BLOCK/PASS/V1回归）")


if __name__ == "__main__":
    main()
