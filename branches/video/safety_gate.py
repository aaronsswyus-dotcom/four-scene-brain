"""VideoSafetyGate — content compliance gate (video-specific, DUAL MODE).

Separation of concerns (v2-plan §3): the Critic judges VIDEO QUALITY
(duration/fps/resolution/alignment); this gate judges CONTENT COMPLIANCE.

Modes (configurable in adapter.build_bundle):
  - "audit" (default):
      * text_prompt contains NSFW / violence / copyright keyword  -> BLOCK
        (hard; the orchestrator's degraded re-map cannot fix it -> stays BLOCK)
      * resolution below 240p OR duration below 0.5s              -> DEGRADE
        (the degraded re-map clamps spec up to safe floor -> re-check PASSES)
      * otherwise                                                 -> PASS
  - "passthrough":
      * no checks                                                 -> PASS

Keyword lists are intentionally CONSERVATIVE ("rather miss than false-block",
v2-plan §8). check() reads only Executable.payload (it never sees the prompt
otherwise), so the Mapper puts text_prompt/resolution/duration there.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import SafetyGate
from common.interfaces.data_objects import Executable, SafetyVerdict

MIN_HEIGHT_P = 240
MIN_DURATION_S = 0.5

_NSFW = ("nsfw", "nude", "naked", "porn", "explicit sex", "色情", "裸露")
_VIOLENCE = ("gore", "beheading", "bloody massacre", "graphic violence", "血腥", "暴力斩杀")
_COPYRIGHT = ("mickey mouse", "米老鼠", "elsa frozen", "marvel spider-man")
_BLOCK_TERMS = _NSFW + _VIOLENCE + _COPYRIGHT


class VideoSafetyGate(SafetyGate):
    def __init__(self, mode: str = "audit") -> None:
        if mode not in ("audit", "passthrough"):
            raise ValueError(f"unknown safety mode '{mode}' (expected audit|passthrough)")
        self.mode = mode

    def check(self, executable: Executable) -> SafetyVerdict:
        if self.mode == "passthrough":
            return SafetyVerdict.PASS

        p = executable.payload or {}
        text = str(p.get("text_prompt", "")).lower()
        for term in _BLOCK_TERMS:
            if term in text:
                return SafetyVerdict.BLOCK

        res = p.get("resolution") or [0, 0]
        dur = float(p.get("duration_s") or 0.0)
        if (len(res) >= 2 and res[1] < MIN_HEIGHT_P) or dur < MIN_DURATION_S:
            return SafetyVerdict.DEGRADE
        return SafetyVerdict.PASS


if __name__ == "__main__":
    # audit mode
    g = VideoSafetyGate()  # default audit
    ok = Executable("pixel", {"text_prompt": "a cat running on the grass",
                              "resolution": [640, 480], "duration_s": 5.0}, {})
    assert g.check(ok) is SafetyVerdict.PASS

    blocked = Executable("pixel", {"text_prompt": "explicit sex scene",
                                   "resolution": [640, 480], "duration_s": 5.0}, {})
    assert g.check(blocked) is SafetyVerdict.BLOCK

    low = Executable("pixel", {"text_prompt": "a cat",
                               "resolution": [160, 120], "duration_s": 5.0}, {})
    assert g.check(low) is SafetyVerdict.DEGRADE

    short = Executable("pixel", {"text_prompt": "a cat",
                                 "resolution": [640, 480], "duration_s": 0.2}, {})
    assert g.check(short) is SafetyVerdict.DEGRADE

    # passthrough mode: even NSFW passes (user explicitly opted out of audit)
    pt = VideoSafetyGate(mode="passthrough")
    assert pt.check(blocked) is SafetyVerdict.PASS

    try:
        VideoSafetyGate(mode="bogus")
        raise AssertionError("bad mode should raise")
    except ValueError:
        pass
    print("[OK] video safety_gate self-test passed (audit + passthrough)")
