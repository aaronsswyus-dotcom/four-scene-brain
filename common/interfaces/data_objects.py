"""Data objects — The Language (common-contract §4, FROZEN, field-level).

Rules:
- `payload` is always opaque to common; scene-defined.
- `meta: dict` is the ONLY extension point (trace_id / session_id / schema_version / ...).
- `modality` / `target` are free strings (D7), NOT enums; Registry validates.
  Known conventions: modality in {physical, sim, geometry, pixel},
                     target   in {robot, game, 3d, video}.
- common NEVER adds fields for a new scene.

Pure stdlib. Zero third-party dependencies.
"""

from dataclasses import dataclass, field
from enum import Enum


@dataclass
class State:
    """World state snapshot. payload is opaque, scene-defined."""

    modality: str
    payload: object
    meta: dict


@dataclass
class SubGoal:
    """Structured sub-goal with DAG dependency (G1)."""

    id: str
    target: str                     # routing key (free string)
    goal: str
    success_criteria: str
    depends_on: list                # list[str], predecessor SubGoal ids -> DAG
    constraints: dict               # modality-agnostic (timeout_s / safety_level / ...)
    priority: int = 0


@dataclass
class Intent:
    """S3 output."""

    raw: str
    source: str                     # 'human' | 'self_observe'
    subgoals: list                  # list[SubGoal]


@dataclass
class Draft:
    """S8 generic wrap of a candidate State (D6: no separate Generator)."""

    modality: str
    payload: object                 # opaque
    meta: dict


class FailureKind(Enum):
    """Error taxonomy (G2) — frozen enum, part of The Language."""

    NONE = "none"
    RETRYABLE_QUALITY = "retryable_quality"          # -> back to S7
    STRUCTURAL_INFEASIBLE = "structural_infeasible"  # -> back to S4
    HARDWARE_OFFLINE = "hardware_offline"            # -> terminate
    LICENSE_BLOCKED = "license_blocked"              # -> terminate/degrade
    TIMEOUT = "timeout"                              # -> bounded retry


@dataclass
class Verification:
    """S9 output."""

    passed: bool
    score: float
    reason: str
    failure_kind: FailureKind = FailureKind.NONE
    meta: dict = None


@dataclass
class Primitive:
    """S10 output unit. kind is scene-defined: grasp/place/attack/wall/cut/..."""

    kind: str
    params: dict
    meta: dict


@dataclass
class Executable:
    """S11 output. payload: joint torques / engine commands / mesh / pixel frames."""

    modality: str
    payload: object                 # opaque
    meta: dict


@dataclass
class Delivery:
    """S12 output — final artifact (path/handle/description)."""

    target: str
    artifact: object
    meta: dict


@dataclass
class Telemetry:
    """S13 unified recycling record (G3, carries trace_id)."""

    trace_id: str
    subgoal_id: str
    kind: str                       # 'torque'|'player'|'geometry'|'watch'|...
    data: dict
    ts: float


@dataclass
class RunMetrics:
    """Global closed-loop metrics (G6) — verifiable propositions."""

    trace_id: str
    success: bool
    retries: int
    duration_s: float
    critic_scores: list             # list[float]
    meta: dict = None


class SafetyVerdict(Enum):
    """SafetyGate verdict (G5)."""

    PASS = "pass"
    DEGRADE = "degrade"
    BLOCK = "block"


if __name__ == "__main__":
    # __main__ self-test (contract DoD #1)
    s = State(modality="physical", payload={"anything": True}, meta={"trace_id": "t-1"})
    sg = SubGoal(
        id="sg-1", target="robot", goal="grasp cup",
        success_criteria="force-torque within threshold",
        depends_on=[], constraints={"timeout_s": 30}, priority=1,
    )
    it = Intent(raw="pick up the red cup", source="human", subgoals=[sg])
    d = Draft(modality=s.modality, payload=s.payload, meta=dict(s.meta))
    v = Verification(passed=True, score=0.95, reason="ok")
    assert v.failure_kind is FailureKind.NONE
    p = Primitive(kind="grasp", params={"width": 0.06}, meta={})
    e = Executable(modality="physical", payload=[0.0] * 7, meta={})
    dl = Delivery(target="robot", artifact="mock://zero-torque", meta={})
    t = Telemetry(trace_id="t-1", subgoal_id="sg-1", kind="torque", data={}, ts=0.0)
    m = RunMetrics(trace_id="t-1", success=True, retries=0, duration_s=0.1, critic_scores=[0.95])
    assert SafetyVerdict.BLOCK.value == "block"
    assert FailureKind.STRUCTURAL_INFEASIBLE.value == "structural_infeasible"
    assert it.subgoals[0].depends_on == []
    assert d.payload is s.payload  # opaque pass-through, no copy semantics imposed
    print("[OK] data_objects self-test passed:", len([s, sg, it, d, v, p, e, dl, t, m]), "objects")
