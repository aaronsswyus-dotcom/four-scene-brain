"""game_demo — V3 DoD: game minimal closed loop (pixel camp, dual-direction).

Scenarios:
  1. level 正常闭环：「生成 2D 平台关卡：草地主题，3 金币，能跳到终点旗帜」-> level JSON + ASCII
  2. worldmodel 正常闭环：「游戏场景：角色向右移动 1 秒」-> replay JSON（帧随动作变化）
  3. 重试路径：level challenge（起点到不了终点）-> 回 S7 -> 成功（retries>=1）
  4. SafetyGate 审核模式：gore prompt -> BLOCK
  5. SafetyGate 放行模式：同一 prompt -> PASS（双模式可切换）

Run:  python -m examples.game_demo   (from project root)
"""

import json
import logging
from pathlib import Path

from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel
from branches.game import register as register_game

BUFFER = Path("output/flywheel/game_demo.jsonl")
GORE_PROMPT = "a gore massacre platformer level"   # deliberately triggers audit BLOCK


def _orch(direction="level", safety_mode="audit") -> Orchestrator:
    reg = Registry()
    register_game(reg, direction=direction, safety_mode=safety_mode)
    buf = str(BUFFER)
    return Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf), max_retry=3)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 72)
    print("DEMO 1 — level 正常闭环：生成 2D 平台关卡（草地，3 金币，终点旗帜）-> level JSON + ASCII")
    print("=" * 72)
    m1 = _orch("level").run({"subgoals": [
        {"id": "lvl", "target": "game",
         "goal": "生成一个 2D 平台关卡：草地主题，3 个金币，能跳到终点旗帜",
         "success_criteria": "可玩性：1P/1G/可达/边界/不悬空",
         "constraints": {"direction": "level", "theme": "grass", "n_coins": 3,
                         "n_enemies": 2, "n_hazards": 1, "width": 16, "height": 10}}]})
    assert m1.success and m1.retries == 0, m1
    print(f"-> RunMetrics: success={m1.success} retries={m1.retries} "
          f"scores={m1.critic_scores} trace={m1.trace_id}\n")

    print("=" * 72)
    print("DEMO 2 — worldmodel 正常闭环：游戏场景（角色向右移动 1 秒）-> replay JSON")
    print("=" * 72)
    m2 = _orch("worldmodel").run({"subgoals": [
        {"id": "wm", "target": "game", "goal": "游戏场景：角色向右移动 1 秒",
         "success_criteria": "帧随动作变化 + 动作一致性",
         "constraints": {"direction": "worldmodel", "action": "right",
                         "fps": 12, "resolution": [16, 12], "state_frames": 8}}]})
    assert m2.success and m2.retries == 0, m2
    print(f"-> RunMetrics: success={m2.success} retries={m2.retries} "
          f"scores={m2.critic_scores}\n")

    print("=" * 72)
    print("DEMO 3 — 重试路径：level challenge（起点到不了终点）-> 回 S7 -> 成功")
    print("=" * 72)
    m3 = _orch("level").run({"subgoals": [
        {"id": "ch", "target": "game", "goal": "挑战关卡",
         "constraints": {"direction": "level", "challenge": True,
                         "width": 16, "height": 10}}]})
    assert m3.success and m3.retries >= 1, m3
    print(f"-> RunMetrics: success={m3.success} retries={m3.retries} "
          f"scores={m3.critic_scores}\n")

    print("=" * 72)
    print("DEMO 4 — SafetyGate 审核模式：gore prompt -> BLOCK")
    print("=" * 72)
    m4 = _orch("level", "audit").run({"subgoals": [
        {"id": "gore", "target": "game", "goal": GORE_PROMPT,
         "constraints": {"direction": "level", "width": 16, "height": 10}}]})
    assert not m4.success and "BLOCK" in m4.meta["subgoals"]["gore"], m4
    print(f"-> RunMetrics: success={m4.success} reason={m4.meta['subgoals']['gore']}\n")

    print("=" * 72)
    print("DEMO 5 — SafetyGate 放行模式：同一 prompt -> PASS（双模式可切换）")
    print("=" * 72)
    m5 = _orch("level", "passthrough").run({"subgoals": [
        {"id": "gore-pass", "target": "game", "goal": GORE_PROMPT,
         "constraints": {"direction": "level", "width": 16, "height": 10}}]})
    assert m5.success, m5
    print(f"-> RunMetrics: success={m5.success} scores={m5.critic_scores}\n")

    rows = [json.loads(x) for x in BUFFER.read_text(encoding="utf-8").splitlines()]
    print(f"[flywheel] {BUFFER} 共 {len(rows)} 条 Telemetry，全部带 trace_id："
          f"{all(r.get('trace_id') for r in rows)}，kind 全为 game："
          f"{all(r.get('kind') == 'game' for r in rows)}")
    print(f"[memory]   写入 {len(InMemoryMemory())} 条记忆（占位）")
    levels = sorted(Path('output/game').glob('level_*.json'))
    replays = sorted(Path('output/game').glob('replay_*.json'))
    print(f"[artifact] output/game/ 共 {len(levels)} 个 level JSON + {len(replays)} 个 replay JSON")
    print("\n⚠️ 边界声明：本 demo 验证编排内核/接口/飞轮在像素阵营第二个场景（game）同样成立，"
          "不证明关卡好玩或推演逼真（全 mock 占位）。")
    print("[PASS] game 最小闭环全部通过（level/worldmodel/重试/审核BLOCK/放行PASS）")


if __name__ == "__main__":
    main()
