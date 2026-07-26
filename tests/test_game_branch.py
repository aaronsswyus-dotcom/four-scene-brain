"""V3 game-branch tests — end-to-end through the frozen common kernel.

Covers BOTH generation directions (D-V3-1: level | worldmodel share ONE
target="game", selected by the `direction` knob), plus:
  - normal closed loop (level + worldmodel)
  - S9->S7 retry (level challenge: start can't reach goal -> refine -> pass)
  - SafetyGate audit BLOCK (gore) / passthrough PASS (dual-mode switch)
  - backbone anti-corruption contract + determinism (both directions)
  - Critic correctness: unreachable level rejected, static / wrong-direction
    worldmodel rejected, malformed payload -> STRUCTURAL_INFEASIBLE

Runs under pytest OR plain python (python -m tests.test_game_branch).
"""

import os
import tempfile

from branches.game import register as register_game
from branches.game.backbone_mock import MockGameBackbone
from branches.game.backbone_interface import GameBackbone
from branches.game.critic import GameCritic
from branches.game.safety_gate import GameSafetyGate
from common.interfaces.data_objects import (
    Draft, SubGoal, Executable, SafetyVerdict, FailureKind)
from common.orchestrator import Orchestrator
from common.registry import Registry
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel

GORE = "a gore massacre platformer level"


def _orch(direction="level", safety_mode="audit"):
    reg = Registry()
    register_game(reg, direction=direction, safety_mode=safety_mode)
    buf = os.path.join(tempfile.gettempdir(), f"fsb_game_{direction}_{safety_mode}.jsonl")
    return Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf), max_retry=3)


# ----------------------------- end-to-end -----------------------------------

def test_level_normal_closed_loop():
    m = _orch("level").run({"subgoals": [
        {"id": "lvl", "target": "game",
         "goal": "生成一个 2D 平台关卡：草地主题，3 个金币，能跳到终点旗帜",
         "constraints": {"direction": "level", "theme": "grass", "n_coins": 3,
                         "n_enemies": 2, "n_hazards": 1, "width": 16, "height": 10}}]})
    assert m.success and m.retries == 0 and m.meta["subgoals"]["lvl"] == "ok"


def test_worldmodel_normal_closed_loop():
    m = _orch("worldmodel").run({"subgoals": [
        {"id": "wm", "target": "game", "goal": "游戏场景：角色向右移动 1 秒",
         "constraints": {"direction": "worldmodel", "action": "right",
                         "fps": 12, "resolution": [16, 12], "state_frames": 8}}]})
    assert m.success and m.retries == 0 and m.meta["subgoals"]["wm"] == "ok"


def test_level_retry_challenge():
    # challenge seals the corridor on retry==0 -> unreachable -> S9 rejects ->
    # S7 refines (retry increments) -> corridor opens -> pass.
    m = _orch("level").run({"subgoals": [
        {"id": "ch", "target": "game", "goal": "挑战关卡",
         "constraints": {"direction": "level", "challenge": True,
                         "width": 16, "height": 10}}]})
    assert m.success and m.retries >= 1


def test_dual_direction_shares_one_target():
    # Both directions register the SAME target string ("game"); the difference is
    # a build-time knob, never a new target and never visible to common.
    for d in ("level", "worldmodel"):
        reg = Registry()
        register_game(reg, direction=d)
        b = reg.resolve("game")
        assert b.target == "game" and b.modality == "pixel"
        assert b.world_model.direction == d


# ------------------------------- safety -------------------------------------

def test_safety_audit_block():
    m = _orch("level", "audit").run({"subgoals": [
        {"id": "g", "target": "game", "goal": GORE,
         "constraints": {"direction": "level", "width": 16, "height": 10}}]})
    assert not m.success and "BLOCK" in m.meta["subgoals"]["g"]


def test_safety_passthrough_pass():
    m = _orch("level", "passthrough").run({"subgoals": [
        {"id": "g", "target": "game", "goal": GORE,
         "constraints": {"direction": "level", "width": 16, "height": 10}}]})
    assert m.success


def test_safety_dual_mode_switch():
    blk = Executable("pixel", {"direction": "level", "text_prompt": GORE,
                               "width": 16, "height": 10}, {})
    assert GameSafetyGate("audit").check(blk) is SafetyVerdict.BLOCK
    assert GameSafetyGate("passthrough").check(blk) is SafetyVerdict.PASS


def test_safety_bad_mode_raises():
    try:
        GameSafetyGate("bogus")
        raise AssertionError("bad mode should raise")
    except ValueError:
        pass


# ---------------------- backbone anti-corruption layer ----------------------

def test_backbone_is_anticorruption_layer():
    assert isinstance(MockGameBackbone(), GameBackbone)
    info = MockGameBackbone().get_info()
    assert set(info) >= {"name", "version", "license", "capabilities"}


def test_backbone_determinism_level():
    b = MockGameBackbone()
    o1 = b.generate("草地关卡 3 金币 终点", {"direction": "level", "n_coins": 3})
    o2 = b.generate("草地关卡 3 金币 终点", {"direction": "level", "n_coins": 3})
    assert o1["level_map"] == o2["level_map"]
    assert o1["direction"] == o2["direction"] == "level"


def test_backbone_determinism_worldmodel():
    b = MockGameBackbone()
    o1 = b.generate("角色向右移动", {"direction": "worldmodel", "action": "right"})
    o2 = b.generate("角色向右移动", {"direction": "worldmodel", "action": "right"})
    assert o1["frames"] == o2["frames"]
    assert o1["direction"] == o2["direction"] == "worldmodel"


# --------------------------- Critic correctness -----------------------------

def _lvl_goal():
    return SubGoal("sg", "game", "草地关卡 3 金币 终点旗帜", "", [],
                   {"direction": "level", "n_coins": 3})


def test_critic_accepts_playable_level():
    b, c = MockGameBackbone(), GameCritic()
    lvl = b.generate("草地关卡 3 金币 终点旗帜", {"direction": "level", "n_coins": 3})
    v = c.verify(Draft("pixel", lvl, {}), _lvl_goal())
    assert v.passed and v.meta["verification_source"] == "level:playability"


def test_critic_rejects_unreachable_level():
    b, c = MockGameBackbone(), GameCritic()
    sealed = b.generate("challenge", {"direction": "level", "challenge": True, "retry": 0})
    v = c.verify(Draft("pixel", sealed, {}), _lvl_goal())
    assert not v.passed and v.failure_kind is FailureKind.RETRYABLE_QUALITY
    assert v.meta["verification_source"] == "level:reachable"


def test_critic_malformed_level_is_structural():
    c = GameCritic()
    v = c.verify(Draft("pixel", {"direction": "level", "nope": 1}, {}), _lvl_goal())
    assert v.failure_kind is FailureKind.STRUCTURAL_INFEASIBLE


def test_critic_accepts_moving_worldmodel():
    b, c = MockGameBackbone(), GameCritic()
    wm = b.generate("角色向右移动", {"direction": "worldmodel", "action": "right"})
    gw = SubGoal("sg", "game", "角色向右移动", "", [], {"direction": "worldmodel", "action": "right"})
    v = c.verify(Draft("pixel", wm, {}), gw)
    assert v.passed and v.meta["verification_source"] == "wm:action-consistency"


def test_critic_rejects_unknown_action_worldmodel():
    b, c = MockGameBackbone(), GameCritic()
    wm = b.generate("角色向右移动", {"direction": "worldmodel", "action": "right"})
    gw = SubGoal("sg", "game", "角色向右移动", "", [], {"direction": "worldmodel", "action": "right"})
    v = c.verify(Draft("pixel", dict(wm, current_action="spin"), {}), gw)
    assert not v.passed and v.failure_kind is FailureKind.RETRYABLE_QUALITY


def test_critic_unknown_direction_is_structural():
    c = GameCritic()
    v = c.verify(Draft("pixel", {"direction": "nope"}, {}), _lvl_goal())
    assert v.failure_kind is FailureKind.STRUCTURAL_INFEASIBLE


ALL = [test_level_normal_closed_loop, test_worldmodel_normal_closed_loop,
       test_level_retry_challenge, test_dual_direction_shares_one_target,
       test_safety_audit_block, test_safety_passthrough_pass,
       test_safety_dual_mode_switch, test_safety_bad_mode_raises,
       test_backbone_is_anticorruption_layer, test_backbone_determinism_level,
       test_backbone_determinism_worldmodel, test_critic_accepts_playable_level,
       test_critic_rejects_unreachable_level, test_critic_malformed_level_is_structural,
       test_critic_accepts_moving_worldmodel, test_critic_rejects_unknown_action_worldmodel,
       test_critic_unknown_direction_is_structural]

if __name__ == "__main__":
    for t in ALL:
        t()
        print(f"[OK] {t.__name__}")
    print(f"[PASS] game branch: {len(ALL)} tests green")
