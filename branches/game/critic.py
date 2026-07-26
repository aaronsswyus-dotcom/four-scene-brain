"""GameCritic — S9 verification for game (dual-direction dispatch on payload).

Success criteria (v3-plan §4), HARD metrics first:
  direction=="level" (playability):
    - exactly 1 'P' and 1 'G'
    - BFS reachability P -> G (enemies/hazards are passable, only '#' blocks)
    - four borders closed (no leak)
    - no floating entity (each C/E/H has '#' directly below)
    - width in [8,32], height in [6,16]
    SOFT: theme/entity keywords overlap with the prompt
  direction=="worldmodel" (action consistency + frame quality):
    - frames vary across time (non-zero inter-frame diff)
    - the moving block drifts in the CURRENT_ACTION direction (directional diff)
    - fps >= 8, resolution >= [8,8], frame count >= 4
    SOFT: scene_description keywords overlap with the prompt

Failure kinds:
  - malformed payload            -> STRUCTURAL_INFEASIBLE
  - hard metric miss (unreachable / oversize / floating / no-motion / wrong-dir)
                                 -> RETRYABLE_QUALITY (back to S7; WAM refines)
  - zero alignment               -> RETRYABLE_QUALITY

Verification.meta.verification_source records which check decided the verdict
(includes the direction, so telemetry can be grouped later).

Pure stdlib. Zero third-party dependencies.
"""

from branches.game.scene_objects import keywords_of, objects_from_goal
from common.interfaces.abstract import Critic
from common.interfaces.data_objects import Draft, SubGoal, Verification, FailureKind

WALL = "#"
PLAYER = "P"
GOAL = "G"
COIN = "C"
ENEMY = "E"
HAZARD = "H"

MIN_W, MAX_W = 8, 32
MIN_H, MAX_H = 6, 16
_MIN_FPS = 8
_MIN_RES = 8
_MIN_FRAMES = 4

_ACTION_DELTA = {   # (dx_sign, dy_sign) expected for centroid delta
    "right": (+1, 0),
    "left": (-1, 0),
    "up": (0, -1),    # grid row decreases upward
    "down": (0, +1),
}


def _bfs_reachable(grid: list, start, goal) -> bool:
    """4-connected BFS; only WALL blocks. Returns True if goal reachable from start."""
    h, w = len(grid), len(grid[0])
    if grid[start[1]][start[0]] == WALL or grid[goal[1]][goal[0]] == WALL:
        return False
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        if (x, y) == goal:
            return True
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and grid[ny][nx] != WALL:
                seen.add((nx, ny))
                stack.append((nx, ny))
    return False


def _verify_level(p: dict, goal: SubGoal) -> Verification:
    required = ("level_map", "width", "height", "entities", "theme", "text_prompt")
    if not isinstance(p, dict) or not all(k in p for k in required):
        return Verification(False, 0.0, "malformed level payload (missing keys)",
                            FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": "level:schema"})

    rows = p["level_map"]
    h = p["height"]
    w = p["width"]
    if not isinstance(rows, list) or len(rows) != h:
        return Verification(False, 0.0, "level_map row count != height",
                            FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": "level:schema"})

    # exactly one P, one G
    ps = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == PLAYER]
    gs = [(x, y) for y, r in enumerate(rows) for x, c in enumerate(r) if c == GOAL]
    if len(ps) != 1 or len(gs) != 1:
        return Verification(False, 0.0, f"expected 1 P and 1 G, got {len(ps)}/{len(gs)}",
                            FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": "level:pg-count"})
    p_pos, g_pos = ps[0], gs[0]

    # borders closed
    if any(rows[0][x] != WALL for x in range(w)) or any(rows[h - 1][x] != WALL for x in range(w)):
        return Verification(False, 0.2, "top/bottom border not closed",
                            FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": "level:border"})
    if any(rows[y][0] != WALL for y in range(h)) or any(rows[y][w - 1] != WALL for y in range(h)):
        return Verification(False, 0.2, "left/right border not closed",
                            FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": "level:border"})

    # reachability (BFS, ignore enemies/hazards)
    if not _bfs_reachable(rows, p_pos, g_pos):
        return Verification(False, 0.3, "goal not reachable from player",
                            FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": "level:reachable"})

    # no floating entity (C/E/H must have '#' directly below)
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in (COIN, ENEMY, HAZARD):
                if y + 1 >= h or rows[y + 1][x] != WALL:
                    return Verification(False, 0.4, f"floating entity '{c}' at ({x},{y})",
                                        FailureKind.RETRYABLE_QUALITY,
                                        meta={"verification_source": "level:floating"})

    # size in range
    if not (MIN_W <= w <= MAX_W and MIN_H <= h <= MAX_H):
        return Verification(False, 0.4, f"size {w}x{h} out of range [{MIN_W},{MAX_W}]x[{MIN_H},{MAX_H}]",
                            FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": "level:size", "width": w, "height": h})

    # SOFT: theme/entity keyword overlap with prompt
    want = keywords_of(goal.goal)
    got = set()
    parsed = objects_from_goal(p.get("text_prompt", goal.goal))
    got.update(parsed["themes"] + parsed["entities"])
    overlap = len(want & got) / len(want) if want else 1.0

    score = round(min(1.0, 0.6 + overlap * 0.4), 4)
    return Verification(True, score, "level playable: 1P/1G, reachable, closed, supported",
                        meta={"verification_source": "level:playability",
                              "reachable": True, "overlap": round(overlap, 4)})


def _centroid(grid: list) -> tuple:
    xs, ys, n = [], [], 0
    for y, row in enumerate(grid):
        for x, v in enumerate(row):
            if v:
                xs.append(x); ys.append(y); n += 1
    return ((sum(xs) / n, sum(ys) / n) if n else (0.0, 0.0)), n


def _verify_worldmodel(p: dict, goal: SubGoal) -> Verification:
    required = ("frames", "fps", "resolution", "current_action", "text_prompt")
    if not isinstance(p, dict) or not all(k in p for k in required):
        return Verification(False, 0.0, "malformed worldmodel payload (missing keys)",
                            FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": "wm:schema"})

    frames = p["frames"]
    if not isinstance(frames, list) or len(frames) < _MIN_FRAMES:
        return Verification(False, 0.0, f"frame count {len(frames) if isinstance(frames, list) else '?'}<{_MIN_FRAMES}",
                            FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": "wm:frame-count"})

    fps = int(p["fps"])
    res = list(p["resolution"])
    if fps < _MIN_FPS:
        return Verification(False, 0.3, f"fps {fps} < {_MIN_FPS}",
                            FailureKind.RETRYABLE_QUALITY, meta={"verification_source": "wm:fps"})
    if len(res) >= 2 and (res[0] < _MIN_RES or res[1] < _MIN_RES):
        return Verification(False, 0.3, f"resolution {res} below {_MIN_RES}",
                            FailureKind.RETRYABLE_QUALITY, meta={"verification_source": "wm:resolution"})

    # inter-frame motion (non-zero diff)
    total_diff = 0
    for a, b in zip(frames, frames[1:]):
        for ra, rb in zip(a, b):
            total_diff += sum(abs(x - y) for x, y in zip(ra, rb))
    if total_diff == 0:
        return Verification(False, 0.3, "frames show no motion",
                            FailureKind.RETRYABLE_QUALITY, meta={"verification_source": "wm:no-motion"})

    # directional consistency: centroid drifts in current_action direction
    action = str(p["current_action"])
    exp = _ACTION_DELTA.get(action)
    if exp is None:
        return Verification(False, 0.3, f"unknown action '{action}'",
                            FailureKind.RETRYABLE_QUALITY, meta={"verification_source": "wm:action"})
    c0, n0 = _centroid(frames[0])
    c1, n1 = _centroid(frames[-1])
    if n0 == 0 or n1 == 0:
        return Verification(False, 0.3, "no block present in frames",
                            FailureKind.RETRYABLE_QUALITY, meta={"verification_source": "wm:empty"})
    dx = c1[0] - c0[0]
    dy = c1[1] - c0[1]
    if (exp[0] != 0 and dx * exp[0] <= 0) or (exp[1] != 0 and dy * exp[1] <= 0):
        return Verification(False, 0.3, f"motion not in '{action}' direction (dx={dx:.1f},dy={dy:.1f})",
                            FailureKind.RETRYABLE_QUALITY, meta={"verification_source": "wm:direction"})

    # SOFT: scene_description overlap with prompt
    want = keywords_of(goal.goal)
    got = set(objects_from_goal(p.get("text_prompt", goal.goal))["themes"])
    overlap = len(want & got) / len(want) if want else 1.0

    score = round(min(1.0, 0.6 + overlap * 0.4), 4)
    return Verification(True, score, "worldmodel: frames move in action direction",
                        meta={"verification_source": "wm:action-consistency",
                              "motion": total_diff, "overlap": round(overlap, 4)})


class GameCritic(Critic):
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        p = draft.payload or {}
        direction = (p or {}).get("direction")
        if direction == "level":
            return _verify_level(p, goal)
        if direction == "worldmodel":
            return _verify_worldmodel(p, goal)
        return Verification(False, 0.0, f"unknown game direction '{direction}'",
                            FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": "direction"})


if __name__ == "__main__":
    from branches.game.backbone_mock import MockGameBackbone
    c = GameCritic()
    b = MockGameBackbone()

    # ---- level: good map passes ----
    lvl = b.generate("草地关卡 3 金币 终点旗帜", {"direction": "level", "n_coins": 3})
    g = SubGoal("sg", "game", "草地关卡 3 金币 终点旗帜", "", [],
                {"direction": "level", "n_coins": 3})
    v = c.verify(Draft("pixel", lvl, {}), g)
    assert v.passed and v.meta["verification_source"] == "level:playability", v

    # ---- level: sealed (unreachable) fails with RETRYABLE_QUALITY ----
    sealed = b.generate("challenge", {"direction": "level", "challenge": True, "retry": 0})
    v2 = c.verify(Draft("pixel", sealed, {}), g)
    assert not v2.passed and v2.failure_kind is FailureKind.RETRYABLE_QUALITY
    assert v2.meta["verification_source"] == "level:reachable", v2

    # ---- level: malformed ----
    assert c.verify(Draft("pixel", {"nope": 1}, {}), g).failure_kind is FailureKind.STRUCTURAL_INFEASIBLE

    # ---- worldmodel: good passes ----
    wm = b.generate("角色向右移动", {"direction": "worldmodel", "action": "right"})
    gw = SubGoal("sg", "game", "角色向右移动", "", [], {"direction": "worldmodel", "action": "right"})
    vw = c.verify(Draft("pixel", wm, {}), gw)
    assert vw.passed and vw.meta["verification_source"] == "wm:action-consistency", vw

    # ---- worldmodel: unknown action fails ----
    wm_bad = dict(wm, current_action="spin")
    vwb = c.verify(Draft("pixel", wm_bad, {}), gw)
    assert not vwb.passed and vwb.failure_kind is FailureKind.RETRYABLE_QUALITY
    print("[OK] game critic self-test passed (level + worldmodel + dispatch)")
