"""GameSafetyGate — content compliance gate (game-specific, DUAL MODE).

Separation of concerns (v3-plan §3): the Critic judges GAME QUALITY (playability /
action consistency); this gate judges CONTENT COMPLIANCE.

Modes (configurable in adapter.build_bundle):
  - "audit" (default):
      * text_prompt contains gore / explicit keyword        -> BLOCK
        (hard; the orchestrator's degraded re-map cannot fix it -> stays BLOCK)
      * level size out of [8,32]x[6,16] range
        OR worldmodel resolution < [8,8] / frame_count < 4   -> DEGRADE
        (the degraded re-map clamps spec up to safe floor -> re-check PASSES)
      * otherwise                                            -> PASS
  - "passthrough":
      * no checks                                            -> PASS

Keyword lists are intentionally CONSERVATIVE ("rather miss than false-block",
v3-plan §8): normal game contexts ("打僵尸/战斗/怪物") are NOT gore. check() reads
only Executable.payload (it never sees the prompt otherwise), so the Mapper puts
text_prompt / width / height / resolution / frame_count there.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import SafetyGate
from common.interfaces.data_objects import Executable, SafetyVerdict

MIN_W, MAX_W = 8, 32
MIN_H, MAX_H = 6, 16
MIN_RES = 8
MIN_FRAMES = 4

# Conservative: only unambiguous gore/explicit. Normal combat is NOT included.
_GORE = ("gore", "血腥", "explicit", "裸露", "graphic violence", "暴力斩杀", "realistic dismemberment")


class GameSafetyGate(SafetyGate):
    def __init__(self, mode: str = "audit") -> None:
        if mode not in ("audit", "passthrough"):
            raise ValueError(f"unknown safety mode '{mode}' (expected audit|passthrough)")
        self.mode = mode

    def check(self, executable: Executable) -> SafetyVerdict:
        if self.mode == "passthrough":
            return SafetyVerdict.PASS

        p = executable.payload or {}
        text = str(p.get("text_prompt", "")).lower()
        for term in _GORE:
            if term in text:
                return SafetyVerdict.BLOCK

        direction = p.get("direction", "level")
        if direction == "worldmodel":
            res = p.get("resolution") or [0, 0]
            frames = int(p.get("frame_count", 0))
            if (len(res) >= 2 and (res[0] < MIN_RES or res[1] < MIN_RES)) or frames < MIN_FRAMES:
                return SafetyVerdict.DEGRADE
        else:  # level
            w = int(p.get("width", 0))
            h = int(p.get("height", 0))
            if not (MIN_W <= w <= MAX_W and MIN_H <= h <= MAX_H):
                return SafetyVerdict.DEGRADE
        return SafetyVerdict.PASS


if __name__ == "__main__":
    g = GameSafetyGate()  # default audit
    ok = Executable("pixel", {"direction": "level", "text_prompt": "草地关卡 3 金币 终点", "width": 16, "height": 10}, {})
    assert g.check(ok) is SafetyVerdict.PASS

    blocked = Executable("pixel", {"direction": "level", "text_prompt": "gore massacre level", "width": 16, "height": 10}, {})
    assert g.check(blocked) is SafetyVerdict.BLOCK

    small = Executable("pixel", {"direction": "level", "text_prompt": "tiny level", "width": 4, "height": 4}, {})
    assert g.check(small) is SafetyVerdict.DEGRADE

    wm_low = Executable("pixel", {"direction": "worldmodel", "text_prompt": "ok", "resolution": [4, 4], "frame_count": 8}, {})
    assert g.check(wm_low) is SafetyVerdict.DEGRADE

    wm_few = Executable("pixel", {"direction": "worldmodel", "text_prompt": "ok", "resolution": [16, 12], "frame_count": 2}, {})
    assert g.check(wm_few) is SafetyVerdict.DEGRADE

    # passthrough: even gore passes (user explicitly opted out of audit)
    pt = GameSafetyGate(mode="passthrough")
    assert pt.check(blocked) is SafetyVerdict.PASS

    try:
        GameSafetyGate(mode="bogus")
        raise AssertionError("bad mode should raise")
    except ValueError:
        pass
    print("[OK] game safety_gate self-test passed (audit + passthrough)")
