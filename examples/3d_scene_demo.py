"""3d_scene_demo — V1 DoD #2: robot-job 3D scene minimal closed loop.

「生成机器人作业的客厅场景：可行走，含桌子和桌上红杯」 -> S1-S14 ->
placeholder GLB Delivery (+ optional cross-branch DAG: 3d scene then robot acts).

Run:  python -m examples.3d_scene_demo   (from project root)
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

# package dir '3d' starts with a digit -> load via importlib (see branch README)
register_3d = importlib.import_module("branches.3d.adapter").register

BUFFER = Path("output/flywheel/3d_demo.jsonl")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    registry = Registry()
    register_3d(registry, output_dir="output/3d")
    register_robot(registry)
    memory = InMemoryMemory()
    flywheel = FileBufferFlywheel(str(BUFFER))
    orch = Orchestrator(registry, memory, flywheel, max_retry=3)

    print("=" * 72)
    print("DEMO 1 — 3D 最小闭环：生成机器人作业客厅场景 -> 占位 GLB")
    print("=" * 72)
    m1 = orch.run({"subgoals": [
        {"id": "build-scene", "target": "3d",
         "goal": "generate a walkable living room for robot work: a table with a red cup on it",
         "success_criteria": "walkable + fidelity + contains table/cup"},
    ]})
    assert m1.success, m1
    glbs = sorted(Path("output/3d").glob("scene_*.glb"))
    assert glbs, "no GLB produced"
    print(f"-> RunMetrics: success={m1.success} retries={m1.retries} scores={m1.critic_scores}")
    print(f"-> GLB 交付物: {glbs[-1]} ({glbs[-1].stat().st_size} bytes)\n")

    print("=" * 72)
    print("DEMO 2 — 跨分支复合指令（D3）：先建 3D 作业场景，再让 robot 抓杯")
    print("=" * 72)
    m2 = orch.run({"subgoals": [
        {"id": "scene", "target": "3d",
         "goal": "generate a walkable room with a table and a cup for the robot"},
        {"id": "grasp", "target": "robot",
         "goal": "grasp the red cup on the table", "depends_on": ["scene"]},
    ]})
    assert m2.success, m2
    print(f"-> RunMetrics: success={m2.success} subgoals={m2.meta['subgoals']}\n")

    rows = [json.loads(x) for x in BUFFER.read_text(encoding="utf-8").splitlines()]
    kinds = sorted({r["kind"] for r in rows})
    print(f"[flywheel] {BUFFER} 共 {len(rows)} 条 Telemetry，kind 种类：{kinds}")
    print("\n⚠️ 边界声明：本 demo 验证编排内核/接口/飞轮，不证明物理可行性（全 mock）。")
    print("[PASS] 3d 最小闭环全部通过")


if __name__ == "__main__":
    main()
