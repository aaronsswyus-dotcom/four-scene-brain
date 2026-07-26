"""Contract test (oss-integration §B1) — locks the FROZEN membrane by reflection.

If ANY interface signature or data-object field changes, this test fails.
Runs under pytest OR plain python (python -m tests.test_contract).
Pure stdlib.
"""

import dataclasses
import inspect

from common.interfaces import (
    State, SubGoal, Intent, Draft, Verification, Primitive, Executable,
    Delivery, Telemetry, RunMetrics, FailureKind, SafetyVerdict,
    WorldModel, Critic, PrimitiveLibrary, Mapper, Executor, SafetyGate,
    Memory, Flywheel,
)

# ---- frozen expectations (common-contract §4/§5) ---------------------------
EXPECTED_FIELDS = {
    State: ["modality", "payload", "meta"],
    SubGoal: ["id", "target", "goal", "success_criteria", "depends_on",
              "constraints", "priority"],
    Intent: ["raw", "source", "subgoals"],
    Draft: ["modality", "payload", "meta"],
    Verification: ["passed", "score", "reason", "failure_kind", "meta"],
    Primitive: ["kind", "params", "meta"],
    Executable: ["modality", "payload", "meta"],
    Delivery: ["target", "artifact", "meta"],
    Telemetry: ["trace_id", "subgoal_id", "kind", "data", "ts"],
    RunMetrics: ["trace_id", "success", "retries", "duration_s",
                 "critic_scores", "meta"],
}

EXPECTED_SIGNATURES = {
    (WorldModel, "predict_next_state"): ["self", "state", "goal"],
    (Critic, "verify"): ["self", "draft", "goal"],
    (PrimitiveLibrary, "abstract"): ["self", "draft"],
    (Mapper, "map"): ["self", "primitives", "goal"],
    (Executor, "execute"): ["self", "executable"],
    (SafetyGate, "check"): ["self", "executable"],
    (Memory, "read"): ["self", "query", "top_k"],
    (Memory, "write"): ["self", "item"],
    (Flywheel, "record"): ["self", "telemetry"],
    (Flywheel, "distill"): ["self"],
}

EXPECTED_FAILURE_KINDS = {"none", "retryable_quality", "structural_infeasible",
                          "hardware_offline", "license_blocked", "timeout"}
EXPECTED_VERDICTS = {"pass", "degrade", "block"}


def test_data_object_fields_frozen():
    for cls, fields in EXPECTED_FIELDS.items():
        actual = [f.name for f in dataclasses.fields(cls)]
        assert actual == fields, f"{cls.__name__} fields drifted: {actual} != {fields}"


def test_interface_signatures_frozen():
    for (cls, name), params in EXPECTED_SIGNATURES.items():
        sig = inspect.signature(getattr(cls, name))
        actual = list(sig.parameters)
        assert actual == params, f"{cls.__name__}.{name} signature drifted: {actual}"
    assert inspect.signature(Memory.read).parameters["top_k"].default == 5


def test_enums_frozen():
    assert {k.value for k in FailureKind} == EXPECTED_FAILURE_KINDS
    assert {v.value for v in SafetyVerdict} == EXPECTED_VERDICTS


def test_abstracts_not_instantiable():
    for cls in (WorldModel, Critic, PrimitiveLibrary, Mapper, Executor,
                SafetyGate, Memory, Flywheel):
        try:
            cls()  # type: ignore[abstract]
            raise AssertionError(f"{cls.__name__} must be abstract")
        except TypeError:
            pass


def test_common_never_imports_branches():
    """Red line: common must not import branches/ (contract §10)."""
    import pathlib
    common_dir = pathlib.Path(__file__).resolve().parent.parent / "common"
    offenders = []
    for py in common_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import branches", "from branches")):
                offenders.append(f"{py.name}: {stripped}")
    assert not offenders, f"common/ imports branches/: {offenders}"


def test_common_pure_stdlib():
    """Red line: common has zero third-party imports (contract §10)."""
    import pathlib, sys
    std = set(sys.stdlib_module_names)
    common_dir = pathlib.Path(__file__).resolve().parent.parent / "common"
    offenders = []
    for py in common_dir.rglob("*.py"):
        for line in py.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            root = None
            if s.startswith("import ") and not s.startswith("import common"):
                root = s.split()[1].split(".")[0]
            elif s.startswith("from ") and not s.startswith("from common"):
                root = s.split()[1].split(".")[0]
            if root and root not in std and root != "common" and not root.startswith("."):
                offenders.append(f"{py.name}: {s}")
    assert not offenders, f"common/ has non-stdlib imports: {offenders}"


ALL = [test_data_object_fields_frozen, test_interface_signatures_frozen,
       test_enums_frozen, test_abstracts_not_instantiable,
       test_common_never_imports_branches, test_common_pure_stdlib]

if __name__ == "__main__":
    for t in ALL:
        t()
        print(f"[OK] {t.__name__}")
    print(f"[PASS] contract test: {len(ALL)}/{len(ALL)} checks — membrane is FROZEN")
