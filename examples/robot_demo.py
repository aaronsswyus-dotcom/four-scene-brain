"""robot_demo — V1 DoD #1/#3/#4: robot minimal closed loop.

1. 「用灵巧手把桌上红杯拿到托盘」 DAG: grasp -> move -> place, S1-S14,
   zero-torque mock Delivery + trace_id Telemetry.
2. Retry path: one S9 failure (force threshold) -> back to S7 -> success.
3. SafetyGate: one BLOCK (torque over limit) and one DEGRADE->PASS.

Run:  python -m examples.robot_demo   (from project root)
"""

import json
import logging
from pathlib import Path

from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel
from branches.robot import register as register_robot

BUFFER = Path("output/flywheel/robot_demo.jsonl")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    registry = Registry()
    register_robot(registry)                       # scene plugs in; common untouched
    memory = InMemoryMemory()
    flywheel = FileBufferFlywheel(str(BUFFER))
    orch = Orchestrator(registry, memory, flywheel, max_retry=3)

    print("=" * 72)
    print("DEMO 1 — 复合指令 DAG：抓杯 -> 移动 -> 放置（零力矩 mock 执行）")
    print("=" * 72)
    m1 = orch.run({"subgoals": [
        {"id": "grasp-cup", "target": "robot",
         "goal": "grasp the red cup on the table with the dexterous hand",
         "success_criteria": "force-torque within threshold"},
        {"id": "move-arm", "target": "robot", "goal": "move the cup towards the tray",
         "depends_on": ["grasp-cup"]},
        {"id": "place-cup", "target": "robot", "goal": "place the cup onto the tray",
         "depends_on": ["move-arm"]},
    ]})
    assert m1.success, m1
    print(f"-> RunMetrics: success={m1.success} retries={m1.retries} "
          f"scores={m1.critic_scores} trace={m1.trace_id}\n")

    print("=" * 72)
    print("DEMO 2 — 重试路径：S9 力阈值不过 -> 回 S7 细化 -> 通过")
    print("=" * 72)
    m2 = orch.run({"subgoals": [
        {"id": "tight-grasp", "target": "robot",
         "goal": "grasp the fragile glass gently",
         "constraints": {"force_threshold_n": 2.5}},
    ]})
    assert m2.success and m2.retries >= 1, m2
    print(f"-> RunMetrics: success={m2.success} retries={m2.retries} "
          f"scores={m2.critic_scores}\n")

    print("=" * 72)
    print("DEMO 3 — SafetyGate：力矩超限 BLOCK")
    print("=" * 72)
    m3 = orch.run({"subgoals": [
        {"id": "dangerous", "target": "robot", "goal": "push the heavy cart",
         "constraints": {"torque_scale": 10.0}},
    ]})
    assert not m3.success and "BLOCK" in m3.meta["subgoals"]["dangerous"], m3
    print(f"-> RunMetrics: success={m3.success} reason={m3.meta['subgoals']['dangerous']}\n")

    print("=" * 72)
    print("DEMO 4 — SafetyGate：偏高力矩 DEGRADE -> 减半重映射 -> 放行")
    print("=" * 72)
    m4 = orch.run({"subgoals": [
        {"id": "firm-push", "target": "robot", "goal": "push the door open",
         "constraints": {"torque_scale": 3.0}},
    ]})
    assert m4.success, m4
    print(f"-> RunMetrics: success={m4.success}\n")

    rows = [json.loads(x) for x in BUFFER.read_text(encoding="utf-8").splitlines()]
    print(f"[flywheel] {BUFFER} 共 {len(rows)} 条 Telemetry，全部带 trace_id："
          f"{all(r.get('trace_id') for r in rows)}")
    print(f"[memory]   写入 {len(memory)} 条记忆")
    print("\n⚠️ 边界声明：本 demo 验证编排内核/接口/飞轮，不证明物理可行性（全 mock）。")
    print("[PASS] robot 最小闭环全部通过")


if __name__ == "__main__":
    main()
