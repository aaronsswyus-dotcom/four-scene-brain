"""MockGameBackbone — deterministic mock game backbone (V3 default, dual-direction).

Covers BOTH directions:
  - direction="level": deterministic tile map from sha256(prompt|retry|challenge).
      * exactly 1 P, 1 G; border closed; entities supported (not floating).
      * default -> guaranteed reachable (a carved floor corridor P->G).
      * challenge flag + retry==0 -> a sealed wall makes G unreachable, so the
        orchestrator's S9->S7 retry loop is exercised; retry>=1 re-carves -> reachable.
  - direction="worldmodel": deterministic frame sequence from sha256(prompt|action|retry).
      * a block moves in the current_action direction each frame (non-zero, directional diff).

Real MarioGPT / GameGen-O / OASIS go through Azure later; only a new backbone_*.py
file is added, this interface stays fixed. Pure stdlib. Zero third-party deps.
"""

import hashlib
import random

from branches.game.backbone_interface import GameBackbone
from branches.game.scene_objects import objects_from_goal

DEFAULT_WIDTH = 16
DEFAULT_HEIGHT = 10
DEFAULT_N_COINS = 3
DEFAULT_N_ENEMIES = 2
DEFAULT_N_HAZARDS = 1
DEFAULT_FPS = 12
DEFAULT_RESOLUTION = [16, 12]
DEFAULT_STATE_FRAMES = 8

WALL = "#"
EMPTY = "."
PLAYER = "P"
GOAL = "G"
COIN = "C"
ENEMY = "E"
HAZARD = "H"

_ACTION_VEC = {
    "right": (1, 0),
    "left": (-1, 0),
    "up": (0, -1),     # grid row decreases upward
    "down": (0, 1),
}


def _rng(*parts) -> random.Random:
    h = hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def _grid_to_rows(grid: list) -> list:
    return ["".join(row) for row in grid]


def _level_map(prompt: str, config: dict) -> dict:
    w = int(config.get("width", DEFAULT_WIDTH))
    h = int(config.get("height", DEFAULT_HEIGHT))
    n_coins = int(config.get("n_coins", DEFAULT_N_COINS))
    n_enemies = int(config.get("n_enemies", DEFAULT_N_ENEMIES))
    n_hazards = int(config.get("n_hazards", DEFAULT_N_HAZARDS))
    challenge = bool(config.get("challenge", False))
    retry = int(config.get("retry", 0))

    rng = _rng(prompt, retry, "challenge" if challenge else "")

    grid = [[EMPTY for _ in range(w)] for _ in range(h)]
    # border closed
    for x in range(w):
        grid[0][x] = WALL
        grid[h - 1][x] = WALL
    for y in range(h):
        grid[y][0] = WALL
        grid[y][w - 1] = WALL
    # floor (walkable row is h-3, floor is h-2)
    floor_row = h - 2
    for x in range(1, w - 1):
        grid[floor_row][x] = WALL

    p_pos = (1, h - 3)
    g_pos = (w - 2, h - 3)
    wall_col = w // 2

    # a few sparse platforms (rows 1..h-4) for visual variety
    for _ in range(max(1, h // 3)):
        py = rng.randint(1, h - 4)
        px = rng.randint(2, w - 3)
        grid[py][px] = WALL

    # carve a guaranteed floor corridor (row h-3) P.x -> G.x, plus a 1-cell gap
    # at wall_col. MUST happen BEFORE placing P/G so it does not erase them.
    for x in range(p_pos[0], g_pos[0] + 1):
        grid[floor_row - 1][x] = EMPTY
    grid[floor_row - 1][wall_col] = EMPTY

    # place P and G on the now-cleared corridor
    grid[p_pos[1]][p_pos[0]] = PLAYER
    grid[g_pos[1]][g_pos[0]] = GOAL

    # candidate supported cells ('.' with '#' below), excluding P/G
    supported = [
        (x, y) for y in range(1, h - 2) for x in range(1, w - 1)
        if grid[y][x] == EMPTY and grid[y + 1][x] == WALL
        and (x, y) not in (p_pos, g_pos)
    ]
    rng.shuffle(supported)
    entities = []
    placed = set()
    for ch, n in ((COIN, n_coins), (ENEMY, n_enemies), (HAZARD, n_hazards)):
        for _ in range(n):
            if not supported:
                break
            x, y = supported.pop()
            if (x, y) in placed:
                continue
            grid[y][x] = ch
            placed.add((x, y))
            entities.append({"type": ch, "x": x, "y": y})

    if challenge and retry == 0:
        # seal a full vertical wall -> G unreachable until a retry re-carves
        for y in range(1, h - 1):
            grid[y][wall_col] = WALL

    rows = _grid_to_rows(grid)
    theme = config.get("theme") or (objects_from_goal(prompt)["themes"] or ["grass"])[0]
    parsed = objects_from_goal(prompt)
    scene_description = " ".join(parsed["themes"] + parsed["actions"]) or "game scene"
    return {
        "direction": "level",
        "level_map": rows,
        "width": w,
        "height": h,
        "entities": [{"type": PLAYER, "x": p_pos[0], "y": p_pos[1]},
                     {"type": GOAL, "x": g_pos[0], "y": g_pos[1]}] + entities,
        "theme": theme,
        "text_prompt": prompt,
        "scene_description": scene_description,
        "refined_times": retry,
        "meta": {"backbone": "mock-game", "challenge": challenge,
                 "seed": config.get("seed")},
    }


def _worldmodel_frames(prompt: str, config: dict) -> dict:
    fps = int(config.get("fps", DEFAULT_FPS))
    res = list(config.get("resolution", DEFAULT_RESOLUTION))
    gw = max(8, min(int(res[0]), 16))
    gh = max(8, min(int(res[1]), 12))
    t_frames = int(config.get("state_frames", DEFAULT_STATE_FRAMES))
    action = str(config.get("action", "right"))
    retry = int(config.get("retry", 0))

    vec = _ACTION_VEC.get(action, (1, 0))
    rng = _rng(prompt, action, retry)
    cx, cy = gw // 2, gh // 2
    step = 1 + retry  # retry -> stronger, clearer motion

    frames = []
    for t in range(t_frames):
        nx = max(0, min(gw - 1, cx + vec[0] * step * t))
        ny = max(0, min(gh - 1, cy + vec[1] * step * t))
        g = [[0 for _ in range(gw)] for _ in range(gh)]
        g[ny][nx] = 1
        frames.append(g)

    parsed = objects_from_goal(prompt)
    scene_description = " ".join(parsed["themes"] + parsed["actions"]) or "game scene"
    return {
        "direction": "worldmodel",
        "frames": frames,
        "fps": fps,
        "resolution": [gw, gh],
        "action_history": [action] * t_frames,
        "current_action": action,
        "text_prompt": prompt,
        "scene_description": scene_description,
        "refined_times": retry,
        "meta": {"backbone": "mock-game", "step": step, "seed": config.get("seed")},
    }


class MockGameBackbone(GameBackbone):
    """Deterministic dual-direction mock. Same prompt+config -> identical output."""

    NAME = "mock-game"
    VERSION = "0.2.0"

    def generate(self, prompt: str, config: dict) -> dict:
        cfg = config or {}
        direction = cfg.get("direction", "level")
        if direction == "level":
            return _level_map(prompt, cfg)
        if direction == "worldmodel":
            return _worldmodel_frames(prompt, cfg)
        raise ValueError(f"unknown game direction '{direction}' (expected level|worldmodel)")

    def get_info(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "license": "N/A (mock)",
            "capabilities": ["level-mock", "worldmodel-mock", "deterministic", "retry-refine"],
            "directions": ["level", "worldmodel"],
        }


if __name__ == "__main__":
    b = MockGameBackbone()

    # ---- level: determinism + reachable by default ----
    o1 = b.generate("草地关卡 3 金币 终点旗帜", {"direction": "level", "n_coins": 3})
    o2 = b.generate("草地关卡 3 金币 终点旗帜", {"direction": "level", "n_coins": 3})
    assert o1["level_map"] == o2["level_map"]
    assert o1["level_map"][o1["height"] - 3].count(PLAYER) == 1
    assert o1["level_map"][o1["height"] - 3].count(GOAL) == 1
    # default reachable: P and G on the same floor corridor row
    prow = o1["level_map"][o1["height"] - 3]
    assert PLAYER in prow and GOAL in prow

    # ---- level: challenge+retry0 unreachable, retry>=1 reachable ----
    sealed = b.generate("challenge level", {"direction": "level", "challenge": True, "retry": 0})
    wall_col = sealed["width"] // 2
    assert sealed["level_map"][sealed["height"] - 3][wall_col] == WALL  # sealed
    reopened = b.generate("challenge level", {"direction": "level", "challenge": True, "retry": 1})
    assert reopened["level_map"][reopened["height"] - 3][wall_col] == EMPTY  # gap carved

    # ---- worldmodel: frames move in action direction ----
    wm = b.generate("角色向右移动", {"direction": "worldmodel", "action": "right"})
    assert wm["direction"] == "worldmodel" and len(wm["frames"]) == DEFAULT_STATE_FRAMES
    f0, f1 = wm["frames"][0], wm["frames"][-1]
    # find centroid of the moving block
    def _centroid(g):
        xs, ys, n = [], [], 0
        for y, row in enumerate(g):
            for x, v in enumerate(row):
                if v:
                    xs.append(x); ys.append(y); n += 1
        return (sum(xs) / n, sum(ys) / n) if n else (0, 0)
    c0, c1 = _centroid(f0), _centroid(f1)
    assert c1[0] > c0[0]  # moved right
    assert b.get_info()["name"] == "mock-game"
    print("[OK] game backbone_mock self-test passed (level + worldmodel + retry)")
