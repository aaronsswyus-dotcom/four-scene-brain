"""Zero-diff acceptance test (contract §9) — the write-once-freeze proof.

Defines a BRAND-NEW mock scene ('mock5') entirely in this file:
(a) only a new scene package is added (here: in-memory, no common edits);
(b) common/ requires ZERO changes (git diff on common/ must be empty);
(c) the orchestrator routes and completes it end-to-end.

All three pass => common is genuinely write-once.
Runs under pytest OR plain python (python -m tests.test_zero_diff).
"""

import subprocess
import tempfile
import os
from pathlib import Path

from common.interfaces import (
    State, SubGoal, Draft, Verification, Primitive, Executable, Delivery,
    SafetyVerdict,
    WorldModel, Critic, PrimitiveLibrary, Mapper, Executor, SafetyGate,
)
from common.orchestrator import Orchestrator
from common.registry import Registry, BranchBundle
from common.memory import InMemoryMemory
from common.flywheel import FileBufferFlywheel

ROOT = Path(__file__).resolve().parent.parent


# ---- the brand-new mock scene: target='mock5', modality='dream' ------------
class Mock5WM(WorldModel):
    def predict_next_state(self, state: State, goal: SubGoal) -> State:
        return State(state.modality, {"dreamed": goal.goal}, dict(state.meta))


class Mock5Critic(Critic):
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        return Verification(True, 1.0, "mock5 always dreams well")


class Mock5PL(PrimitiveLibrary):
    def abstract(self, draft: Draft) -> list:
        return [Primitive("dream_step", {"about": draft.payload["dreamed"]}, {})]


class Mock5Mapper(Mapper):
    def map(self, primitives: list, goal: SubGoal) -> Executable:
        return Executable("dream", {"steps": [p.params for p in primitives]}, {})


class Mock5Executor(Executor):
    def execute(self, executable: Executable) -> Delivery:
        return Delivery("mock5", "dream://artifact",
                        {"telemetry_kind": "dream", "telemetry_data": {"depth": 5}})


class Mock5Gate(SafetyGate):
    def check(self, executable: Executable) -> SafetyVerdict:
        return SafetyVerdict.PASS


def register_mock5(registry: Registry) -> None:
    registry.register(BranchBundle(
        target="mock5", modality="dream",
        world_model=Mock5WM(), critic=Mock5Critic(), primitives=Mock5PL(),
        mapper=Mock5Mapper(), executor=Mock5Executor(), safety_gate=Mock5Gate()))


# ---- (c) orchestrator routes the new scene end-to-end ----------------------
def test_mock5_end_to_end():
    reg = Registry()
    register_mock5(reg)
    buf = os.path.join(tempfile.gettempdir(), "fsb_zero_diff.jsonl")
    orch = Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf))
    metrics = orch.run("mock5: dream a fifth scene")
    assert metrics.success and metrics.meta["subgoals"]["sg-1"] == "ok"


# ---- (b) common/ git diff must be empty ------------------------------------
def test_common_git_diff_empty():
    r = subprocess.run(["git", "status", "--porcelain", "--", "common/"],
                       cwd=str(ROOT), capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError("git repo required for zero-diff check (run git init + commit)")
    dirty = [line for line in r.stdout.splitlines() if line.strip()]
    assert not dirty, f"common/ has uncommitted changes -> scene leaked into common: {dirty}"


ALL = [test_mock5_end_to_end, test_common_git_diff_empty]

if __name__ == "__main__":
    for t in ALL:
        t()
        print(f"[OK] {t.__name__}")
    print("[PASS] zero-diff acceptance: common is write-once (mock5 plugged in, common untouched)")
