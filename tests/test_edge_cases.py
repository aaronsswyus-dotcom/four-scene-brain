"""Edge-case tests — boundary/robustness coverage beyond __main__ self-tests.

Covers:
- SafetyGate raises exception -> orchestrator maps to BLOCK
- Executor raises exception -> orchestrator maps to FailureKind
- Memory.read raises exception -> orchestrator suppresses, continues
- Critic raises exception -> orchestrator maps to FailureKind
- WorldModel raises TimeoutError -> bounded retry then fail
- Empty payload / malformed payload edge cases
- SubGoal with self-dependency (cycle of 1)
- Duplicate SubGoal ids
- max_retry=0 (no retries allowed)
- robot critic with empty force list (P1-2 regression)
"""

import os
import tempfile
import pytest

from common.interfaces import (
    State, SubGoal, Draft, Verification, Primitive, Executable, Delivery,
    Telemetry, RunMetrics, FailureKind, SafetyVerdict,
    WorldModel, Critic, PrimitiveLibrary, Mapper, Executor, SafetyGate,
    Memory, Flywheel,
)
from common.orchestrator import Orchestrator, RuleIntentParser, topological_order
from common.registry import Registry, BranchBundle
from common.memory.in_memory import InMemoryMemory
from common.flywheel.file_buffer import FileBufferFlywheel


# ---- helper: minimal mock branch implementations ----

class _OKWM(WorldModel):
    def predict_next_state(self, state, goal):
        return State(state.modality, {"ok": True}, dict(state.meta))


class _OKCritic(Critic):
    def verify(self, draft, goal):
        return Verification(True, 1.0, "ok")


class _OKPL(PrimitiveLibrary):
    def abstract(self, draft):
        return [Primitive("noop", {}, {})]


class _OKMapper(Mapper):
    def map(self, primitives, goal):
        return Executable("m", {"n": len(primitives)}, {})


class _OKExecutor(Executor):
    def execute(self, executable):
        return Delivery("t", "mock://ok",
                        {"telemetry_kind": "test", "telemetry_data": {}})


class _PassGate(SafetyGate):
    def check(self, executable):
        return SafetyVerdict.PASS


class _BlockGate(SafetyGate):
    def check(self, executable):
        return SafetyVerdict.BLOCK


class _CrashGate(SafetyGate):
    def check(self, executable):
        raise RuntimeError("gate hardware fault")


class _CrashExecutor(Executor):
    def execute(self, executable):
        raise TimeoutError("executor timed out")


class _CrashCritic(Critic):
    def verify(self, draft, goal):
        raise ConnectionError("critic sensor disconnected")


class _TimeoutWM(WorldModel):
    def predict_next_state(self, state, goal):
        raise TimeoutError("model inference timeout")


class _CrashMemory(Memory):
    def read(self, query, top_k=5):
        raise OSError("memory backend down")
    def write(self, item):
        pass


def _make_orch(world_model=_OKWM(), critic=_OKCritic(), pl=_OKPL(),
               mapper=_OKMapper(), executor=_OKExecutor(), gate=_PassGate(),
               memory=None, max_retry=3):
    reg = Registry()
    reg.register(BranchBundle("t1", "m1", world_model, critic, pl, mapper,
                              executor, gate))
    buf = os.path.join(tempfile.gettempdir(), "fsb_edge_test.jsonl")
    return Orchestrator(reg, memory or InMemoryMemory(),
                        FileBufferFlywheel(buf), max_retry=max_retry)


def _run_input(orch, **kw):
    return orch.run({"subgoals": [{"id": "sg-1", "target": "t1", **kw}]})


# ---- 1. SafetyGate raises -> BLOCK ----
def test_safety_gate_exception_blocks():
    orch = _make_orch(gate=_CrashGate())
    m = _run_input(orch, goal="test")
    assert not m.success and "safety BLOCK" in m.meta["subgoals"]["sg-1"]


# ---- 2. SafetyGate BLOCK -> terminate ----
def test_safety_gate_block_terminates():
    orch = _make_orch(gate=_BlockGate())
    m = _run_input(orch, goal="test")
    assert not m.success and "safety BLOCK" in m.meta["subgoals"]["sg-1"]


# ---- 3. Executor raises TimeoutError -> mapped, fail ----
def test_executor_timeout_maps_and_fails():
    orch = _make_orch(executor=_CrashExecutor())
    m = _run_input(orch, goal="test")
    assert not m.success
    assert "execute failed" in m.meta["subgoals"]["sg-1"]


# ---- 4. Critic raises ConnectionError -> mapped as HARDWARE_OFFLINE (terminal) ----
def test_critic_crash_terminal():
    # ConnectionError is an OSError subclass -> HARDWARE_OFFLINE -> no retry, immediate fail
    orch = _make_orch(critic=_CrashCritic(), max_retry=2)
    m = _run_input(orch, goal="test")
    assert not m.success
    assert "hardware_offline" in m.meta["subgoals"]["sg-1"]


# ---- 5. WorldModel TimeoutError -> bounded retry then fail ----
def test_worldmodel_timeout_retries():
    orch = _make_orch(world_model=_TimeoutWM(), max_retry=2)
    m = _run_input(orch, goal="test")
    assert not m.success
    assert "max_retry" in m.meta["subgoals"]["sg-1"] or "timeout" in m.meta["subgoals"]["sg-1"]


# ---- 6. Memory.read raises -> orchestrator suppresses, continues ----
def test_memory_read_crash_suppressed():
    orch = _make_orch(memory=_CrashMemory())
    m = _run_input(orch, goal="test")
    assert m.success  # memory error doesn't kill the run


# ---- 7. Empty payload doesn't crash critic ----
def test_robot_critic_empty_force_list():
    from branches.robot.critic import RobotCritic
    c = RobotCritic()
    g = SubGoal("s", "robot", "g", "", [], {})
    # wrench with empty force list — should NOT raise ValueError (P1-2 fix)
    # max(..., default=0.0) -> force=0.0 < threshold -> force check passes
    d = Draft("physical", {"wrench": {"force": [], "torque": []},
                            "contact": {"in_contact": False}, "plan": []}, {})
    v = c.verify(d, g)
    assert v.passed  # no crash, force=0 within threshold, empty plan -> visual ok


# ---- 8. Self-dependency cycle ----
def test_self_dependency_cycle():
    orch = _make_orch()
    m = orch.run({"subgoals": [{"id": "a", "target": "t1", "goal": "g",
                                 "depends_on": ["a"]}]})
    assert not m.success and "cycle" in m.meta["error"]


# ---- 9. Duplicate SubGoal ids ----
def test_duplicate_subgoal_ids():
    with pytest.raises(ValueError, match="duplicate"):
        topological_order([
            SubGoal("a", "t", "g", "", [], {}),
            SubGoal("a", "t", "g", "", [], {}),
        ])


# ---- 10. Unknown dependency ----
def test_unknown_dependency():
    with pytest.raises(ValueError, match="unknown"):
        topological_order([
            SubGoal("a", "t", "g", "", ["nonexistent"], {}),
        ])


# ---- 11. max_retry=0 — no retries allowed ----
def test_zero_retries():
    class _FailOnceCritic(Critic):
        calls = 0
        def verify(self, draft, goal):
            _FailOnceCritic.calls += 1
            if _FailOnceCritic.calls == 1:
                return Verification(False, 0.3, "fail once",
                                    FailureKind.RETRYABLE_QUALITY)
            return Verification(True, 0.9, "ok")
    orch = _make_orch(critic=_FailOnceCritic(), max_retry=0)
    m = _run_input(orch, goal="test")
    assert not m.success  # first failure with max_retry=0 -> immediate fail
    assert m.retries == 1  # first retry attempt counted


# ---- 12. Parallel DAG (two independent subgoals, no depends_on) ----
def test_parallel_dag_both_succeed():
    orch = _make_orch()
    m = orch.run({"subgoals": [
        {"id": "a", "target": "t1", "goal": "task a"},
        {"id": "b", "target": "t1", "goal": "task b"},
    ]})
    assert m.success and m.meta["subgoals"] == {"a": "ok", "b": "ok"}


# ---- 13. First subgoal fails -> second skipped ----
def test_first_fails_second_skipped():
    class _AlwaysFail(Critic):
        def verify(self, draft, goal):
            return Verification(False, 0.0, "always fails",
                                FailureKind.STRUCTURAL_INFEASIBLE)
    orch = _make_orch(critic=_AlwaysFail())
    m = orch.run({"subgoals": [
        {"id": "a", "target": "t1", "goal": "a"},
        {"id": "b", "target": "t1", "goal": "b", "depends_on": ["a"]},
    ]})
    assert not m.success
    assert "failed" in m.meta["subgoals"]["a"]
    assert m.meta["subgoals"]["b"] == "skipped"


# ---- 14. Empty input string -> ValueError ----
def test_empty_input():
    orch = _make_orch()
    m = orch.run("")
    assert not m.success
    assert "intent/decompose" in m.meta["error"]


# ---- 15. RunMetrics has trace_id and critic_scores ----
def test_metrics_fields():
    orch = _make_orch()
    m = _run_input(orch, goal="test")
    assert m.trace_id and m.trace_id.startswith("tr-")
    assert m.critic_scores == [1.0]
    assert m.success is True
