"""RobotCritic — S9 verification for robot.

Success criteria: FORCE-TORQUE THRESHOLD FIRST, visual confirmation second
(v1-plan §4). Threshold comes from goal.constraints['force_threshold_n']
(default 8.0 N). Verification.meta.verification_source records which check
decided the verdict.
"""

from common.interfaces.abstract import Critic
from common.interfaces.data_objects import Draft, SubGoal, Verification, FailureKind

DEFAULT_FORCE_THRESHOLD_N = 8.0


class RobotCritic(Critic):
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        p = draft.payload or {}
        if not isinstance(p, dict) or "wrench" not in p:
            return Verification(False, 0.0, "malformed robot payload (no wrench)",
                                FailureKind.STRUCTURAL_INFEASIBLE,
                                meta={"verification_source": "schema"})

        threshold = float(goal.constraints.get("force_threshold_n", DEFAULT_FORCE_THRESHOLD_N))
        force = float(p.get("peak_contact_force_n",
                            max(abs(x) for x in p["wrench"]["force"])))

        # 1) force-torque check (primary)
        if force > threshold:
            score = max(0.0, round(1.0 - (force - threshold) / threshold, 4))
            return Verification(
                False, score,
                f"contact force {force:.2f}N exceeds threshold {threshold:.2f}N",
                FailureKind.RETRYABLE_QUALITY,
                meta={"verification_source": "force_torque", "force_n": force},
            )

        # 2) visual confirmation (secondary, mock: contact expected when plan touches)
        visually_ok = bool(p.get("contact", {}).get("in_contact", False)) or not p.get("plan")
        score = round(min(1.0, 0.6 + (threshold - force) / threshold * 0.4), 4)
        if not visually_ok:
            return Verification(False, score, "visual confirmation failed: no contact observed",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": "visual"})
        return Verification(True, score, "force within threshold; visual confirmed",
                            meta={"verification_source": "force_torque+visual",
                                  "force_n": force, "threshold_n": threshold})


if __name__ == "__main__":
    c = RobotCritic()
    good = Draft("physical", {
        "wrench": {"force": [2.0, 0, 0], "torque": [0, 0, 0]},
        "contact": {"in_contact": True}, "plan": ["grasp"],
        "peak_contact_force_n": 2.0,
    }, {})
    g = SubGoal("s", "robot", "grasp", "", [], {})
    v = c.verify(good, g)
    assert v.passed and v.meta["verification_source"] == "force_torque+visual"

    bad = Draft("physical", {
        "wrench": {"force": [12.0, 0, 0], "torque": [0, 0, 0]},
        "contact": {"in_contact": True}, "plan": ["grasp"],
        "peak_contact_force_n": 12.0,
    }, {})
    v2 = c.verify(bad, g)
    assert not v2.passed and v2.failure_kind is FailureKind.RETRYABLE_QUALITY

    v3 = c.verify(Draft("physical", {"nope": 1}, {}), g)
    assert v3.failure_kind is FailureKind.STRUCTURAL_INFEASIBLE
    print("[OK] robot critic self-test passed")
