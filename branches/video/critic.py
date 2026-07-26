"""VideoCritic — S9 verification for video.

Success criteria (v2-plan §4):
  HARD metrics first:
    - duration_s within +/- DURATION_TOL of target (default 20%)
    - fps        >= target
    - resolution >= target (both width and height)
  SOFT metric second:
    - text-video semantic alignment: overlap between the prompt's recognized
      keywords and the backbone's scene_description.

Failure kinds:
  - malformed payload            -> STRUCTURAL_INFEASIBLE (terminal-ish)
  - hard metric miss             -> RETRYABLE_QUALITY (back to S7; WAM refines)
  - zero alignment (prompt had recognizable objects but none surfaced)
                                 -> RETRYABLE_QUALITY

Verification.meta.verification_source records which check decided the verdict.

Pure stdlib. Zero third-party dependencies.
"""

from branches.video.scene_objects import keywords_of
from common.interfaces.abstract import Critic
from common.interfaces.data_objects import Draft, SubGoal, Verification, FailureKind

DEFAULT_DURATION_S = 5.0
DEFAULT_FPS = 24
DEFAULT_RESOLUTION = [640, 480]
DURATION_TOL = 0.20            # +/- 20%
_REQUIRED_KEYS = ("duration_s", "fps", "resolution", "scene_description")


class VideoCritic(Critic):
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        p = draft.payload or {}
        if not isinstance(p, dict) or not all(k in p for k in _REQUIRED_KEYS):
            return Verification(False, 0.0, "malformed video payload (missing keys)",
                                FailureKind.STRUCTURAL_INFEASIBLE,
                                meta={"verification_source": "schema"})

        c = goal.constraints or {}
        tgt_dur = float(c.get("duration_s", DEFAULT_DURATION_S))
        tgt_fps = int(c.get("fps", DEFAULT_FPS))
        tgt_res = list(c.get("resolution", DEFAULT_RESOLUTION))

        dur = float(p["duration_s"])
        fps = int(p["fps"])
        res = list(p["resolution"])

        # 1) HARD: duration within tolerance
        dur_err = abs(dur - tgt_dur) / tgt_dur if tgt_dur else 0.0
        if dur_err > DURATION_TOL:
            score = max(0.0, round(1.0 - dur_err, 4))
            return Verification(
                False, score,
                f"duration {dur:.2f}s off target {tgt_dur:.2f}s by {dur_err*100:.0f}%",
                FailureKind.RETRYABLE_QUALITY,
                meta={"verification_source": "duration", "duration_s": dur})

        # 1) HARD: fps / resolution floors
        if fps < tgt_fps:
            return Verification(False, 0.5, f"fps {fps} below target {tgt_fps}",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": "fps"})
        if res[0] < tgt_res[0] or res[1] < tgt_res[1]:
            return Verification(False, 0.5,
                                f"resolution {res} below target {tgt_res}",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": "resolution"})

        # 2) SOFT: semantic alignment
        want = keywords_of(goal.goal)
        got = set(str(p["scene_description"]).lower().replace("+", " ").split())
        if want:
            overlap = len(want & got) / len(want)
            if overlap == 0.0:
                return Verification(False, 0.5,
                                    "text-video alignment failed: no keyword overlap",
                                    FailureKind.RETRYABLE_QUALITY,
                                    meta={"verification_source": "alignment", "overlap": 0.0})
        else:
            overlap = 1.0

        # passed: score blends duration accuracy + alignment
        score = round(min(1.0, 0.6 + (1.0 - dur_err) * 0.2 + overlap * 0.2), 4)
        return Verification(True, score, "duration/fps/resolution met; text-video aligned",
                            meta={"verification_source": "hard_metrics+alignment",
                                  "duration_s": dur, "overlap": round(overlap, 4)})


if __name__ == "__main__":
    c = VideoCritic()
    g = SubGoal("s", "video", "a cat running on the grass", "", [], {"duration_s": 5.0})

    good = Draft("pixel", {"duration_s": 5.0, "fps": 24, "resolution": [640, 480],
                           "scene_description": "cat run in grass"}, {})
    v = c.verify(good, g)
    assert v.passed and v.meta["verification_source"] == "hard_metrics+alignment"

    short = Draft("pixel", {"duration_s": 3.0, "fps": 24, "resolution": [640, 480],
                            "scene_description": "cat run in grass"}, {})
    v2 = c.verify(short, g)
    assert not v2.passed and v2.failure_kind is FailureKind.RETRYABLE_QUALITY
    assert v2.meta["verification_source"] == "duration"

    lowfps = Draft("pixel", {"duration_s": 5.0, "fps": 12, "resolution": [640, 480],
                             "scene_description": "cat run in grass"}, {})
    assert c.verify(lowfps, g).meta["verification_source"] == "fps"

    lowres = Draft("pixel", {"duration_s": 5.0, "fps": 24, "resolution": [320, 240],
                             "scene_description": "cat run in grass"}, {})
    assert c.verify(lowres, g).meta["verification_source"] == "resolution"

    bad = Draft("pixel", {"nope": 1}, {})
    assert c.verify(bad, g).failure_kind is FailureKind.STRUCTURAL_INFEASIBLE
    print("[OK] video critic self-test passed")
