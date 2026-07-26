"""GamePrimitiveLibrary — S10 primitive abstraction for game (dual-direction).

Primitives (editing/composition units), dispatched by payload["direction"]:
    level:      platform / gap / enemy / coin / hazard / goal
    worldmodel: frame_step / action_apply

Because the frozen Mapper.map(primitives, goal) signature does NOT receive the
draft/payload, the full game spec (level data / replay data) is stashed in EVERY
primitive's meta under 'game_spec'. The orchestrator's degraded re-map copies
primitive meta, so the spec survives the SafetyGate DEGRADE path.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import PrimitiveLibrary
from common.interfaces.data_objects import Draft, Primitive

WALL = "#"
PLAYER = "P"
GOAL = "G"
COIN = "C"
ENEMY = "E"
HAZARD = "H"

_LEVEL_SPEC_KEYS = ("level_map", "width", "height", "entities", "theme", "text_prompt")
_WM_SPEC_KEYS = ("frames", "fps", "resolution", "action_history", "current_action", "text_prompt")


def _spec_from_payload(p: dict, keys) -> dict:
    return {k: p.get(k) for k in keys}


def _scan_level(rows: list) -> dict:
    """Count entity / structure primitives present in a level map."""
    counts = {"coin": 0, "enemy": 0, "hazard": 0, "goal": 0, "platform": 0, "gap": 0}
    h = len(rows)
    for y, r in enumerate(rows):
        plat_run = 0
        for x, c in enumerate(r):
            if c == COIN:
                counts["coin"] += 1
            elif c == ENEMY:
                counts["enemy"] += 1
            elif c == HAZARD:
                counts["hazard"] += 1
            elif c == GOAL:
                counts["goal"] += 1
            elif c == WALL and 0 < y < h - 1:   # interior wall => platform segment
                plat_run += 1
        if plat_run >= 2:
            counts["platform"] += 1
    return counts


class GamePrimitiveLibrary(PrimitiveLibrary):
    def abstract(self, draft: Draft) -> list:
        p = draft.payload or {}
        direction = p.get("direction")
        subgoal_id = (draft.meta or {}).get("subgoal_id")

        if direction == "level":
            spec = _spec_from_payload(p, _LEVEL_SPEC_KEYS)
            rows = p.get("level_map") or []
            counts = _scan_level(rows)
            prims = []
            for kind, n in (("coin", counts["coin"]), ("enemy", counts["enemy"]),
                            ("hazard", counts["hazard"]), ("goal", counts["goal"]),
                            ("platform", counts["platform"])):
                for i in range(max(1, n)):   # at least one structural primitive
                    prims.append(Primitive(
                        kind=kind, params={"index": i, "count": n},
                        meta={"subgoal_id": subgoal_id, "game_spec": spec}))
            return prims

        if direction == "worldmodel":
            spec = _spec_from_payload(p, _WM_SPEC_KEYS)
            frames = p.get("frames") or []
            action = p.get("current_action", "right")
            return [
                Primitive(kind="frame_step", params={"steps": max(0, len(frames) - 1)},
                          meta={"subgoal_id": subgoal_id, "game_spec": spec}),
                Primitive(kind="action_apply", params={"action": action},
                          meta={"subgoal_id": subgoal_id, "game_spec": spec}),
            ]

        # unknown direction -> single noop so the pipeline still completes
        return [Primitive(kind="noop", params={}, meta={"subgoal_id": subgoal_id})]


if __name__ == "__main__":
    lib = GamePrimitiveLibrary()
    lvl = {"direction": "level", "level_map": ["########", "#P..C.G#", "#.##....#",
                                              "#C..E..H#", "########"],
           "width": 8, "height": 5, "entities": [], "theme": "grass",
           "text_prompt": "草地关卡"}
    pl = lib.abstract(Draft("pixel", lvl, {"subgoal_id": "sg-1"}))
    kinds = [p.kind for p in pl]
    assert "coin" in kinds and "enemy" in kinds and "hazard" in kinds and "goal" in kinds
    assert all(p.meta["game_spec"]["level_map"] == lvl["level_map"] for p in pl)

    wm = {"direction": "worldmodel", "frames": [[[0]]] * 8, "fps": 12,
          "resolution": [16, 12], "action_history": ["right"] * 8,
          "current_action": "right", "text_prompt": "角色向右移动"}
    pw = lib.abstract(Draft("pixel", wm, {"subgoal_id": "sg-2"}))
    assert [p.kind for p in pw] == ["frame_step", "action_apply"]
    assert pw[1].params["action"] == "right"
    assert all(p.meta["game_spec"]["current_action"] == "right" for p in pw)
    print("[OK] game primitives self-test passed (level + worldmodel)")
