"""PhysicalWorldModelBase — shared WAM physical prior (v1-plan §4, scene-side).

Shared by branches/robot and branches/3d (V1 robot-job-scene). Implements the
frozen `WorldModel` interface; subclasses provide the modality-specific
imagination via `_imagine`.

The "WAM prior" here is a MOCK: deterministic, physics-flavored plausibility
heuristics. Real backbone (e.g. GR00T on Azure) replaces MockWAMPrior behind
the same adapter seam — this base class does not change.

sim2real declaration: mock "assumed reachable" != physically feasible.
V1 verifies the orchestration kernel + interfaces + flywheel, NOT physics.
"""

from abc import abstractmethod

from common.interfaces.abstract import WorldModel
from common.interfaces.data_objects import State, SubGoal


class MockWAMPrior:
    """Mock World-Action-Model physical prior.

    Deterministic pseudo-physics: given a goal string, produces bounded,
    repeatable "plausibility" numbers. Replaceable by a real WAM adapter.
    """

    GRAVITY = 9.81           # m/s^2, used by heuristics only
    MAX_REACH_M = 1.2        # mock arm/scene interaction radius

    def plausibility(self, goal_text: str) -> float:
        """Deterministic [0.55, 1.0) score derived from the goal text."""
        h = sum(ord(c) for c in goal_text) % 45
        return 0.55 + h / 100.0

    def imagined_dynamics(self, goal_text: str) -> dict:
        """Mock forward dynamics summary shared by robot & 3d imagination."""
        p = self.plausibility(goal_text)
        return {
            "plausibility": round(p, 4),
            "est_contact_force_n": round(2.0 + 10.0 * (1.0 - p), 3),
            "est_duration_s": round(0.5 + 3.0 * (1.0 - p), 3),
            "within_reach": True,   # mock: always reachable — see sim2real note
        }


class PhysicalWorldModelBase(WorldModel):
    """Physical-camp base: shared prior + State plumbing; subclass fills payload."""

    def __init__(self, prior: MockWAMPrior = None) -> None:
        self.prior = prior or MockWAMPrior()

    def predict_next_state(self, state: State, goal: SubGoal) -> State:
        """S7: shared physical imagination -> candidate State.

        Template method: computes shared dynamics, then delegates payload
        construction to the scene-specific `_imagine`.
        """
        dynamics = self.prior.imagined_dynamics(goal.goal)
        payload = self._imagine(state, goal, dynamics)
        meta = dict(state.meta or {})
        meta.update({"wam_dynamics": dynamics, "imagined_for": goal.id})
        return State(modality=state.modality, payload=payload, meta=meta)

    @abstractmethod
    def _imagine(self, state: State, goal: SubGoal, dynamics: dict) -> object:
        """Scene-specific candidate payload (robot: pose/twist/...; 3d: geometry)."""
        ...


if __name__ == "__main__":
    class _Toy(PhysicalWorldModelBase):
        def _imagine(self, state, goal, dynamics):
            return {"toy": True, "p": dynamics["plausibility"]}

    prior = MockWAMPrior()
    p1 = prior.plausibility("open the door")
    p2 = prior.plausibility("open the door")
    assert p1 == p2 and 0.55 <= p1 < 1.0            # deterministic + bounded

    wm = _Toy()
    s = State("physical", None, {"trace_id": "t"})
    g = SubGoal("sg-1", "robot", "open the door", "", [], {})
    out = wm.predict_next_state(s, g)
    assert out.modality == "physical"
    assert out.payload["toy"] and "wam_dynamics" in out.meta
    assert out.meta["imagined_for"] == "sg-1"

    # base is abstract
    try:
        PhysicalWorldModelBase()  # type: ignore[abstract]
        raise AssertionError("base should be abstract")
    except TypeError:
        pass
    print("[OK] _physical base self-test passed")
