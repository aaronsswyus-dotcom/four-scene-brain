"""video_demo — V2 DoD: video minimal closed loop (pixel camp).

Scenarios:
  1. 正常闭环：「生成一个 5 秒的视频：一只猫在草地上奔跑」-> 占位 mp4 + trace_id Telemetry
  2. 重试路径：S9 duration 不达标 -> 回 S7 backbone 细化 -> 通过
  3. SafetyGate 审核模式：含 NSFW 关键词的 prompt -> BLOCK
  4. SafetyGate 放行模式：同一 prompt -> PASS（验证双模式可切换）
  5. SafetyGate 降级：分辨率过低 -> DEGRADE -> 钳制到安全下限 -> PASS

Run:  python -m examples.video_demo   (from project root)
"""

import json
import logging
from pathlib import Path

from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel
from branches.video import register as register_video

BUFFER = Path("output/flywheel/video_demo.jsonl")
NSFW_PROMPT = "an explicit sex scene, close up"   # deliberately triggers audit BLOCK


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    memory = InMemoryMemory()
    flywheel = FileBufferFlywheel(str(BUFFER))

    # two registries: audit gate (default) vs passthrough gate
    reg_audit = Registry()
    register_video(reg_audit, safety_mode="audit")
    reg_pass = Registry()
    register_video(reg_pass, safety_mode="passthrough")

    orch = Orchestrator(reg_audit, memory, flywheel, max_retry=3)
    orch_pass = Orchestrator(reg_pass, memory, flywheel, max_retry=3)

    print("=" * 72)
    print("DEMO 1 — 正常闭环：生成 5 秒视频「一只猫在草地上奔跑，镜头拉近」-> 占位 mp4")
    print("=" * 72)
    m1 = orch.run({"subgoals": [
        {"id": "cat-run", "target": "video",
         "goal": "a cat running on the grass, camera zoom in / 一只猫在草地上奔跑",
         "success_criteria": "duration/fps/resolution + text-video alignment",
         "constraints": {"duration_s": 5.0, "fps": 24, "resolution": [640, 480]}},
    ]})
    assert m1.success and m1.retries == 0, m1
    print(f"-> RunMetrics: success={m1.success} retries={m1.retries} "
          f"scores={m1.critic_scores} trace={m1.trace_id}\n")

    print("=" * 72)
    print("DEMO 2 — 重试路径：S9 duration 不达标 -> 回 S7 backbone 细化 -> 通过")
    print("=" * 72)
    m2 = orch.run({"subgoals": [
        {"id": "drifted", "target": "video",
         "goal": "a dog running on the road / 一只狗在马路上奔跑",
         "constraints": {"duration_s": 5.0, "initial_drift_s": 2.0}},
    ]})
    assert m2.success and m2.retries >= 1, m2
    print(f"-> RunMetrics: success={m2.success} retries={m2.retries} "
          f"scores={m2.critic_scores}\n")

    print("=" * 72)
    print("DEMO 3 — SafetyGate 审核模式：NSFW prompt -> BLOCK")
    print("=" * 72)
    m3 = orch.run({"subgoals": [
        {"id": "nsfw", "target": "video", "goal": NSFW_PROMPT,
         "constraints": {"duration_s": 5.0}},
    ]})
    assert not m3.success and "BLOCK" in m3.meta["subgoals"]["nsfw"], m3
    print(f"-> RunMetrics: success={m3.success} reason={m3.meta['subgoals']['nsfw']}\n")

    print("=" * 72)
    print("DEMO 4 — SafetyGate 放行模式：同一 prompt -> PASS（双模式可切换）")
    print("=" * 72)
    m4 = orch_pass.run({"subgoals": [
        {"id": "nsfw-pass", "target": "video", "goal": NSFW_PROMPT,
         "constraints": {"duration_s": 5.0}},
    ]})
    assert m4.success, m4
    print(f"-> RunMetrics: success={m4.success} scores={m4.critic_scores}\n")

    print("=" * 72)
    print("DEMO 5 — SafetyGate 降级：分辨率过低 -> DEGRADE -> 钳制到 240p -> PASS")
    print("=" * 72)
    m5 = orch.run({"subgoals": [
        {"id": "lowres", "target": "video",
         "goal": "a bird flying in the sky / 一只鸟在天空中飞",
         "constraints": {"duration_s": 2.0, "resolution": [160, 120]}},
    ]})
    assert m5.success, m5
    print(f"-> RunMetrics: success={m5.success} scores={m5.critic_scores}\n")

    rows = [json.loads(x) for x in BUFFER.read_text(encoding="utf-8").splitlines()]
    print(f"[flywheel] {BUFFER} 共 {len(rows)} 条 Telemetry，全部带 trace_id："
          f"{all(r.get('trace_id') for r in rows)}，kind 全为 video："
          f"{all(r.get('kind') == 'video' for r in rows)}")
    print(f"[memory]   写入 {len(memory)} 条记忆")
    mp4s = sorted(Path('output/video').glob('*.mp4'))
    print(f"[artifact] output/video/ 共 {len(mp4s)} 个占位 mp4：{[p.name for p in mp4s]}")
    print("\n⚠️ 边界声明：本 demo 验证编排内核/接口/飞轮在像素阵营同样成立，"
          "不证明视频质量（全 mock 占位帧）。")
    print("[PASS] video 最小闭环全部通过（正常/重试/审核BLOCK/放行PASS/降级PASS）")


if __name__ == "__main__":
    main()
