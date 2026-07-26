"""Orchestrator — S1-S14 state machine (common-contract §6, FROZEN behavior).

Modality-agnostic. Contains ZERO scene knowledge:
- discovers scenes only via Registry (never imports branches)
- never parses State/Draft/Executable payloads
- branch exceptions never penetrate common (mapped to FailureKind)
- retries bounded by max_retry; unregistered target fails fast

D1: rule/template intent parsing v0; LLM parser is an optional injectable plugin.
D6: S8 has no Generator interface — candidate State is wrapped into Draft here.
G4: synchronous v0; signatures upgradable to async without contract break.

Pure stdlib.
"""

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod

from common.interfaces.data_objects import (
    State,
    SubGoal,
    Intent,
    Draft,
    FailureKind,
    Verification,
    Telemetry,
    RunMetrics,
    SafetyVerdict,
)
from common.interfaces.abstract import Memory, Flywheel
from common.registry.registry import Registry, BranchBundle

logger = logging.getLogger("common.orchestrator")

SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------- S3/S4 plugin
class IntentParser(ABC):
    """S3/S4 plugin point (D1). Default is rule-based; LLM parser is optional."""

    @abstractmethod
    def parse(self, raw_input: object, source: str) -> Intent:
        ...


class RuleIntentParser(IntentParser):
    """Rule/template parser v0 — scene-agnostic input formats:

    1) dict (or JSON string) with key "subgoals":
       {"subgoals": [{"id": "...", "target": "...", "goal": "...",
                      "success_criteria": "...", "depends_on": [...],
                      "constraints": {...}, "priority": 0}, ...]}
       (id/depends_on/constraints/success_criteria optional; ids auto-filled)
    2) plain string lines "target: goal" — multiple lines form a sequential DAG
       (each line depends on the previous one).

    Targets are free strings supplied by the INPUT, never guessed by common.
    """

    def parse(self, raw_input: object, source: str) -> Intent:
        spec = raw_input
        if isinstance(spec, str):
            stripped = spec.strip()
            if stripped.startswith("{"):
                try:
                    spec = json.loads(stripped)
                except json.JSONDecodeError:
                    pass
        subgoals: list = []
        if isinstance(spec, dict) and "subgoals" in spec:
            for i, sg in enumerate(spec["subgoals"]):
                subgoals.append(SubGoal(
                    id=sg.get("id") or f"sg-{i + 1}",
                    target=sg["target"],
                    goal=sg.get("goal", ""),
                    success_criteria=sg.get("success_criteria", ""),
                    depends_on=list(sg.get("depends_on", [])),
                    constraints=dict(sg.get("constraints", {})),
                    priority=int(sg.get("priority", 0)),
                ))
        elif isinstance(spec, str):
            prev_id = None
            i = 0
            for line in spec.splitlines():
                line = line.strip()
                if not line or ":" not in line:
                    continue
                i += 1
                target, goal = line.split(":", 1)
                sg_id = f"sg-{i}"
                subgoals.append(SubGoal(
                    id=sg_id, target=target.strip(), goal=goal.strip(),
                    success_criteria="", depends_on=[prev_id] if prev_id else [],
                    constraints={},
                ))
                prev_id = sg_id
        if not subgoals:
            raise ValueError("RuleIntentParser: no subgoals parsed from input")
        raw_str = raw_input if isinstance(raw_input, str) else json.dumps(raw_input, ensure_ascii=False, default=str)
        return Intent(raw=raw_str, source=source, subgoals=subgoals)


# ---------------------------------------------------------------- DAG ordering
def topological_order(subgoals: list) -> list:
    """Kahn topological sort by depends_on; ties broken by (-priority, id).

    Raises ValueError on unknown dependency or cycle.
    """
    by_id = {sg.id: sg for sg in subgoals}
    if len(by_id) != len(subgoals):
        raise ValueError("duplicate SubGoal ids")
    indeg = {sg.id: 0 for sg in subgoals}
    dependents: dict = {sg.id: [] for sg in subgoals}
    for sg in subgoals:
        for dep in sg.depends_on:
            if dep not in by_id:
                raise ValueError(f"SubGoal '{sg.id}' depends on unknown id '{dep}'")
            indeg[sg.id] += 1
            dependents[dep].append(sg.id)
    ready = sorted([i for i, d in indeg.items() if d == 0],
                   key=lambda i: (-by_id[i].priority, i))
    order: list = []
    while ready:
        cur = ready.pop(0)
        order.append(by_id[cur])
        for nxt in dependents[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
        ready.sort(key=lambda i: (-by_id[i].priority, i))
    if len(order) != len(subgoals):
        raise ValueError("SubGoal DAG contains a cycle")
    return order


# ------------------------------------------------------- exception -> failure
def map_exception(exc: Exception) -> FailureKind:
    """Branch exceptions never penetrate common (contract §6)."""
    if isinstance(exc, TimeoutError):
        return FailureKind.TIMEOUT
    if isinstance(exc, PermissionError):
        return FailureKind.LICENSE_BLOCKED
    if isinstance(exc, (ConnectionError, OSError)):
        return FailureKind.HARDWARE_OFFLINE
    return FailureKind.RETRYABLE_QUALITY


_TERMINAL = (FailureKind.HARDWARE_OFFLINE, FailureKind.LICENSE_BLOCKED)


# ------------------------------------------------------------------ the brain
class Orchestrator:
    """brain = Orchestrator. Runs S1-S14 over registered branches."""

    def __init__(self, registry: Registry, memory: Memory, flywheel: Flywheel,
                 max_retry: int = 3, intent_parser: IntentParser = None) -> None:
        self.registry = registry
        self.memory = memory
        self.flywheel = flywheel
        self.max_retry = max_retry
        self.intent_parser = intent_parser or RuleIntentParser()

    # -- public API (contract §6) --
    def run(self, raw_input: object, source: str = "human") -> RunMetrics:
        t0 = time.time()
        trace_id = f"tr-{uuid.uuid4().hex[:12]}"                     # S1
        session_id = f"ss-{uuid.uuid4().hex[:8]}"
        base_meta = {"trace_id": trace_id, "session_id": session_id,
                     "schema_version": SCHEMA_VERSION}
        log = lambda step, msg: logger.info("[%s] %s %s", trace_id, step, msg)

        retries_total = 0
        critic_scores: list = []
        subgoal_status: dict = {}
        deliveries: dict = {}
        success = True
        abort_reason = ""

        initial_state = State(modality="", payload=raw_input, meta=dict(base_meta))  # S2
        log("S2", "encoded raw input into initial State")

        try:                                                          # S3 + S4
            intent = self.intent_parser.parse(raw_input, source)
            ordered = topological_order(intent.subgoals)
            log("S3/S4", f"intent -> {len(ordered)} subgoal(s), topo order: {[s.id for s in ordered]}")
        except Exception as exc:
            log("S3/S4", f"FAILED: {exc}")
            return RunMetrics(trace_id=trace_id, success=False, retries=0,
                              duration_s=round(time.time() - t0, 6), critic_scores=[],
                              meta={"error": f"intent/decompose failed: {exc}"})

        chained_states: dict = {}   # subgoal_id -> post-verification State (DAG chaining)

        for sg in ordered:
            if not success:
                subgoal_status[sg.id] = "skipped"
                continue
            ok, retries, scores, reason = self._run_subgoal(
                sg, initial_state, chained_states, deliveries, base_meta, log)
            retries_total += retries
            critic_scores.extend(scores)
            subgoal_status[sg.id] = "ok" if ok else f"failed: {reason}"
            if not ok:
                success = False
                abort_reason = f"subgoal '{sg.id}': {reason}"

        try:                                                          # S14
            self.flywheel.distill()
            log("S14", "flywheel distilled (local buffer only)")
        except Exception as exc:
            log("S14", f"distill error suppressed: {exc}")

        metrics = RunMetrics(
            trace_id=trace_id, success=success, retries=retries_total,
            duration_s=round(time.time() - t0, 6), critic_scores=critic_scores,
            meta={"subgoals": subgoal_status, "deliveries": {k: True for k in deliveries},
                  **({"abort_reason": abort_reason} if abort_reason else {})},
        )
        log("DONE", f"success={success} retries={retries_total}")
        return metrics

    # -- single SubGoal: S5 -> S13 --
    def _run_subgoal(self, sg: SubGoal, initial_state: State, chained: dict,
                     deliveries: dict, base_meta: dict, log) -> tuple:
        try:                                                          # S5
            bundle: BranchBundle = self.registry.resolve(sg.target)
        except KeyError as exc:
            log("S5", f"route FAILED for '{sg.id}': {exc}")
            return False, 0, [], "unregistered target"
        log("S5", f"routed '{sg.id}' -> target='{bundle.target}' modality='{bundle.modality}'")

        try:                                                          # S6
            context = self.memory.read(sg.goal)
        except Exception as exc:
            log("S6", f"memory read error suppressed: {exc}")
            context = []

        # branch input State: modality = bundle.modality (routing check holds);
        # upstream payloads passed opaquely via meta (common never parses them)
        upstream = {dep: chained[dep].payload for dep in sg.depends_on if dep in chained}
        state = State(modality=bundle.modality, payload=initial_state.payload,
                      meta={**base_meta, "subgoal_id": sg.id, "context": context,
                            "upstream": upstream})
        assert bundle.modality == state.modality  # contract §7 routing check

        retries = 0
        scores: list = []
        while True:
            try:                                                      # S7
                candidate = bundle.world_model.predict_next_state(state, sg)
            except Exception as exc:
                fk = map_exception(exc)
                log("S7", f"exception -> {fk.value}: {exc}")
                if fk in _TERMINAL:
                    return False, retries, scores, fk.value
                retries += 1
                if retries > self.max_retry:
                    return False, retries, scores, "max_retry exceeded at S7"
                continue

            draft = Draft(modality=candidate.modality, payload=candidate.payload,  # S8
                          meta={**dict(candidate.meta or {}), **base_meta, "subgoal_id": sg.id})

            try:                                                      # S9
                verification: Verification = bundle.critic.verify(draft, sg)
            except Exception as exc:
                verification = Verification(False, 0.0, f"critic exception: {exc}",
                                            failure_kind=map_exception(exc))
            scores.append(verification.score)

            if verification.passed:
                log("S9", f"'{sg.id}' verified score={verification.score}")
                break
            fk = verification.failure_kind or FailureKind.RETRYABLE_QUALITY
            log("S9", f"'{sg.id}' rejected ({fk.value}): {verification.reason}")
            if fk in _TERMINAL:
                return False, retries, scores, fk.value
            if fk == FailureKind.STRUCTURAL_INFEASIBLE:
                # v0: structural re-decompose is bounded — surface as failure with
                # explicit kind; caller/upper layer may re-issue a refined instruction.
                return False, retries, scores, fk.value
            retries += 1                                              # RETRYABLE/TIMEOUT -> S7
            if retries > self.max_retry:
                return False, retries, scores, "max_retry exceeded at S9"
            state = State(modality=state.modality, payload=state.payload,
                          meta={**state.meta, "retry": retries,
                                "last_reason": verification.reason})

        try:                                                          # S10 + S11
            primitives = bundle.primitives.abstract(draft)
            executable = bundle.mapper.map(primitives, sg)
        except Exception as exc:
            fk = map_exception(exc)
            log("S10/S11", f"exception -> {fk.value}: {exc}")
            return False, retries, scores, f"abstract/map failed: {fk.value}"

        if bundle.safety_gate is not None:                            # S11.5 SafetyGate
            verdict = self._safety_check(bundle, primitives, sg, executable, log)
            if verdict is SafetyVerdict.BLOCK:
                return False, retries, scores, "safety BLOCK"
            if isinstance(verdict, tuple):                            # degraded re-map result
                executable = verdict[1]

        try:                                                          # S12
            delivery = bundle.executor.execute(executable)
        except Exception as exc:
            fk = map_exception(exc)
            log("S12", f"exception -> {fk.value}: {exc}")
            return False, retries, scores, f"execute failed: {fk.value}"
        deliveries[sg.id] = delivery
        log("S12", f"'{sg.id}' delivered artifact")

        try:                                                          # S13
            d_meta = delivery.meta or {}
            telemetry = Telemetry(
                trace_id=base_meta["trace_id"], subgoal_id=sg.id,
                kind=d_meta.get("telemetry_kind", "delivery"),        # scene fills kind/data
                data=d_meta.get("telemetry_data", {}), ts=time.time())
            self.flywheel.record(telemetry)
            self.memory.write({"subgoal_id": sg.id, "goal": sg.goal,
                               "score": scores[-1] if scores else None,
                               "trace_id": base_meta["trace_id"]})
        except Exception as exc:
            log("S13", f"recycle error suppressed: {exc}")

        chained[sg.id] = candidate                                    # DAG State chaining
        return True, retries, scores, ""

    def _safety_check(self, bundle: BranchBundle, primitives: list, sg: SubGoal,
                      executable, log):
        """BLOCK -> terminate; DEGRADE -> one bounded degraded re-map, then re-check."""
        try:
            verdict = bundle.safety_gate.check(executable)
        except Exception as exc:
            log("SafetyGate", f"exception -> BLOCK: {exc}")
            return SafetyVerdict.BLOCK
        if verdict is SafetyVerdict.PASS:
            return verdict
        if verdict is SafetyVerdict.BLOCK:
            log("SafetyGate", "verdict BLOCK -> terminate subgoal")
            return verdict
        # DEGRADE: re-map once with degrade hint in primitive meta (opaque to common)
        log("SafetyGate", "verdict DEGRADE -> degraded re-map (bounded, once)")
        try:
            degraded = [type(p)(kind=p.kind, params=p.params,
                                meta={**(p.meta or {}), "degrade": True}) for p in primitives]
            new_exec = bundle.mapper.map(degraded, sg)
            if bundle.safety_gate.check(new_exec) is SafetyVerdict.PASS:
                return (SafetyVerdict.DEGRADE, new_exec)
        except Exception as exc:
            log("SafetyGate", f"degraded re-map failed -> BLOCK: {exc}")
        return SafetyVerdict.BLOCK


if __name__ == "__main__":
    # __main__ self-test with in-file fake branches (no branches/ imports).
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from common.interfaces.abstract import (
        WorldModel, Critic, PrimitiveLibrary, Mapper, Executor, SafetyGate as SG_ABC,
    )
    from common.interfaces.data_objects import (
        Primitive, Executable, Delivery,
    )
    from common.memory.in_memory import InMemoryMemory
    from common.flywheel.file_buffer import FileBufferFlywheel

    class FakeWM(WorldModel):
        def predict_next_state(self, state, goal):
            return State(state.modality, {"imagined": goal.goal}, dict(state.meta))

    class FlakyCritic(Critic):
        """Fails once with RETRYABLE_QUALITY, then passes (tests S9->S7 retry)."""
        def __init__(self):
            self.calls = 0
        def verify(self, draft, goal):
            self.calls += 1
            if self.calls == 1:
                return Verification(False, 0.3, "first attempt low quality",
                                    FailureKind.RETRYABLE_QUALITY)
            return Verification(True, 0.9, "ok")

    class FakePL(PrimitiveLibrary):
        def abstract(self, draft):
            return [Primitive("noop", {}, {})]

    class FakeMP(Mapper):
        def map(self, primitives, goal):
            return Executable("m1", {"n": len(primitives)}, {})

    class FakeEX(Executor):
        def execute(self, executable):
            return Delivery("t1", "mock://artifact",
                            {"telemetry_kind": "test", "telemetry_data": {"ok": 1}})

    class PassGate(SG_ABC):
        def check(self, executable):
            return SafetyVerdict.PASS

    import tempfile, os
    reg = Registry()
    reg.register(BranchBundle("t1", "m1", FakeWM(), FlakyCritic(), FakePL(), FakeMP(),
                              FakeEX(), PassGate()))
    buf = os.path.join(tempfile.gettempdir(), "fsb_orch_selftest.jsonl")
    orch = Orchestrator(reg, InMemoryMemory(), FileBufferFlywheel(buf), max_retry=3)

    # DAG: sg-2 depends on sg-1 (State chaining) + one S9 retry
    m = orch.run({"subgoals": [
        {"id": "sg-1", "target": "t1", "goal": "step one"},
        {"id": "sg-2", "target": "t1", "goal": "step two", "depends_on": ["sg-1"]},
    ]})
    assert m.success and m.retries == 1 and len(m.critic_scores) == 3, m
    assert m.meta["subgoals"] == {"sg-1": "ok", "sg-2": "ok"}

    # unregistered target -> fail fast
    m2 = orch.run("nope: do something")
    assert not m2.success and "unregistered" in m2.meta["subgoals"]["sg-1"]

    # cycle detection
    m3 = orch.run({"subgoals": [
        {"id": "a", "target": "t1", "goal": "g", "depends_on": ["b"]},
        {"id": "b", "target": "t1", "goal": "g", "depends_on": ["a"]},
    ]})
    assert not m3.success and "cycle" in m3.meta["error"]

    print("[OK] orchestrator self-test passed (DAG + retry + fail-fast + cycle)")
