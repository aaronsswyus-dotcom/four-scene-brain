"""GameMapper — S11 mapping: primitives -> game Executable (level / replay spec).

The frozen signature is map(primitives, goal); the game spec travels inside
primitives[0].meta['game_spec'] (stashed by GamePrimitiveLibrary). The resulting
Executable.payload carries text_prompt / width / height / resolution / frame_count
so the SafetyGate (which only sees the Executable) can audit content and enforce
safe bounds.

DEGRADE path (SafetyGate): when any primitive meta carries degrade=True, the spec
is CLAMPED UP to safe minimums (level size kept; worldmodel resolution >= 8,
frame_count >= 4). This is the one bounded degraded re-map the orchestrator
performs before re-checking SafetyGate.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import Mapper
from common.interfaces.data_objects import SubGoal, Executable, Primitive

SAFE_MIN_RES = 8
SAFE_MIN_FRAMES = 4


class GameMapper(Mapper):
    def map(self, primitives: list, goal: SubGoal) -> Executable:
        spec = {}
        if primitives:
            spec = dict((primitives[0].meta or {}).get("game_spec", {}) or {})
        degrade = any((p.meta or {}).get("degrade") for p in primitives)
        direction = spec.get("direction") or (
            "worldmodel" if "frames" in spec else "level")

        if direction == "worldmodel":
            resolution = list(spec.get("resolution") or [SAFE_MIN_RES, SAFE_MIN_RES])
            frame_count = len(spec.get("frames") or [])
            if degrade:
                resolution = [max(resolution[0], SAFE_MIN_RES), max(resolution[1], SAFE_MIN_RES)]
                frame_count = max(frame_count, SAFE_MIN_FRAMES)
            replay_spec = {
                "fps": spec.get("fps"),
                "resolution": resolution,
                "frame_count": frame_count,
                "action_history": spec.get("action_history"),
                "current_action": spec.get("current_action"),
            }
            return Executable(
                modality="pixel",
                payload={
                    "direction": "worldmodel",
                    "replay_spec": replay_spec,
                    "frames": spec.get("frames"),
                    "text_prompt": spec.get("text_prompt", ""),
                    "resolution": resolution,
                    "frame_count": frame_count,
                },
                meta={"degraded": degrade},
            )

        # level (default)
        width = int(spec.get("width", 16))
        height = int(spec.get("height", 10))
        if degrade:
            width = max(width, SAFE_MIN_RES)
            height = max(height, SAFE_MIN_RES)
        level_spec = {
            "level_map": spec.get("level_map"),
            "width": width,
            "height": height,
            "entities": spec.get("entities"),
            "theme": spec.get("theme"),
        }
        return Executable(
            modality="pixel",
            payload={
                "direction": "level",
                "level_spec": level_spec,
                "level_map": spec.get("level_map"),
                "text_prompt": spec.get("text_prompt", ""),
                "width": width,
                "height": height,
            },
            meta={"degraded": degrade},
        )


if __name__ == "__main__":
    m = GameMapper()
    lvl_spec = {"direction": "level", "level_map": ["#", "#"], "width": 16, "height": 10,
                "entities": [], "theme": "grass", "text_prompt": "草地关卡"}
    pl = [Primitive("coin", {}, {"game_spec": lvl_spec})]
    g = SubGoal("s", "game", "g", "", [], {})
    e = m.map(pl, g)
    assert e.modality == "pixel" and e.payload["direction"] == "level"
    assert e.payload["width"] == 16 and e.payload["text_prompt"] == "草地关卡"

    wm_spec = {"direction": "worldmodel", "frames": [[[0]]] * 8, "fps": 12,
               "resolution": [4, 4], "action_history": ["right"], "current_action": "right",
               "text_prompt": "角色向右"}
    pw = [Primitive("frame_step", {}, {"game_spec": wm_spec})]
    e2 = m.map(pw, g)
    assert e2.payload["direction"] == "worldmodel"
    # degrade clamps low resolution up
    pw_d = [Primitive("frame_step", {}, {"game_spec": wm_spec, "degrade": True})]
    e3 = m.map(pw_d, g)
    assert e3.meta["degraded"]
    assert e3.payload["resolution"] == [SAFE_MIN_RES, SAFE_MIN_RES] and e3.payload["frame_count"] == 8
    print("[OK] game mapper self-test passed (level + worldmodel + degrade)")
