"""MarioGPT backbone adapter — REAL integration (Phase 4, game-A primary).

distilgpt2 (~82M) fine-tuned on SMB levels. CPU-runnable. MIT license.
Install:  pip install mario-gpt   (pulls torch + transformers + Pillow)

API verified against official repo (shyamsn97/mario-gpt, NeurIPS 2023):
    from mario_gpt import MarioLM
    lm = MarioLM()                                  # default lm_path="distilgpt2"
    out = lm.sample(
        prompts=["many pipes, many enemies, some blocks, high elevation"],
        num_steps=1400,    # columns; row count is fixed at 14 (SMB height)
        temperature=2.0,
        use_tqdm=False,
    )
    out.level          # List[str], one row per element
    out.img            # PIL.Image
    out.run_astar()    # playability verifier (needs Java 8+)

LAZY IMPORT: importing this module does NOT pull torch/transformers. Only
generate() does, so mock-first tests stay fast and dependency-free. The
adapter.py `_make_backbone("mariogpt")` returns this class; if mario_gpt is
not installed, the FIRST generate() call raises ImportError with a clear
message — mock tests are unaffected.

ANTI-CORRUPTION LAYER: MarioGPT emits SMB tile chars on a 14-row grid (X S - ?
o E B | [ ] etc.). We (1) crop to requested width x height, (2) normalize tiles
to our schema (# . P G C E H), (3) force exactly 1 PLAYER + 1 GOAL, (4) force
closed borders, (5) carve a guaranteed floor corridor so BFS reachability holds.
Output matches MockGameBackbone's level schema exactly -> GameCritic and
GameSafetyGate stay unchanged; common/ stays at zero diff.

direction="worldmodel" raises NotImplementedError (MarioGPT is level-only).
For worldmodel, use backbone='mock' until backbone_gamegen.py / backbone_oasis.py
land.

Pure stdlib at import time. Only generate() pulls mario_gpt/torch.
Lives ONLY in branches/game/ (never common). Wired in via adapter._make_backbone("mariogpt").
"""

import hashlib
import random

from branches.game.backbone_interface import GameBackbone

STATUS = "real"
NOTE = ("MarioGPT real integration (Phase 4). CPU-runnable via distilgpt2 (~82M). "
        "mario_gpt is lazily imported at first generate() call; mock tests unaffected.")

# ---- tile schema (must match MockGameBackbone / GameCritic exactly) ----
WALL = "#"
EMPTY = "."
PLAYER = "P"
GOAL = "G"
COIN = "C"
ENEMY = "E"
HAZARD = "H"

# ---- SMB tile (MarioGPT output) -> our schema. Conservative: unknown -> EMPTY.
#      Source: VGLC SMB charset + mario_gpt/simulator/simulator.py observations.
_SMB_TO_OUR = {
    "X": WALL,        # solid block / ground
    "S": PLAYER,      # player spawn (we'll relocate to a controlled position)
    "o": COIN,        # coin
    "E": ENEMY,       # goomba
    "g": ENEMY,       # green koopa
    "k": ENEMY,       # red koopa
    "B": HAZARD,      # bullet bill launcher
    "b": HAZARD,      # bullet bill body
    # everything else (- ? Q | [ ] < > = ( ) % ...) -> EMPTY
}

DEFAULT_WIDTH = 16
DEFAULT_HEIGHT = 10
DEFAULT_TEMPERATURE = 2.0


def _normalize_smb_level(smb_str: str, width: int, height: int,
                         rng: random.Random, n_coins: int = 3) -> list:
    """Convert raw MarioGPT SMB string -> our grid (list of str rows).

    The MarioGPT grid is fixed at 14 rows tall; num_steps controls columns.
    We crop to (width, height) and standardize so GameCritic's hard checks pass:
    1. take first `height` rows; pad/truncate each to `width` cols
    2. map SMB chars -> our schema (unknown -> EMPTY)
    3. force closed borders (all WALL on 4 edges)
    4. clear any P/G from raw mapping; place our own
    5. solid floor at row height-2; walkable corridor at row height-3
    6. PLAYER at (1, height-3), GOAL at (width-2, height-3) -> BFS reachable
    7. scatter up to n_coins on supported cells (above floor) for richness
    """
    raw_rows = smb_str.replace("\r", "").split("\n")
    grid = []
    for r in raw_rows[:height]:
        row = [_SMB_TO_OUR.get(c, EMPTY) for c in r[:width]]
        row = row + [EMPTY] * (width - len(row))
        grid.append(row)
    while len(grid) < height:
        grid.append([EMPTY] * width)

    # closed borders
    for x in range(width):
        grid[0][x] = WALL
        grid[height - 1][x] = WALL
    for y in range(height):
        grid[y][0] = WALL
        grid[y][width - 1] = WALL

    # clear any P/G that came from raw mapping; we place our own
    for y in range(height):
        for x in range(width):
            if grid[y][x] in (PLAYER, GOAL):
                grid[y][x] = EMPTY

    # solid floor + walkable corridor (guarantees BFS reachability)
    floor_row = height - 2
    walk_row = floor_row - 1
    for x in range(1, width - 1):
        grid[floor_row][x] = WALL
        grid[walk_row][x] = EMPTY

    # place PLAYER and GOAL on the walkable corridor
    grid[walk_row][1] = PLAYER
    grid[walk_row][width - 2] = GOAL

    # scatter coins on supported cells (cell above floor, excluding P/G columns)
    supported = [(x, walk_row - 1) for x in range(2, width - 2)]
    rng.shuffle(supported)
    for x, y in supported[:n_coins]:
        if 0 < y < height - 1 and grid[y][x] == EMPTY:
            grid[y][x] = COIN

    return ["".join(row) for row in grid]


def _entities_from_rows(rows: list) -> list:
    out = []
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in (PLAYER, GOAL, COIN, ENEMY, HAZARD):
                out.append({"type": ch, "x": x, "y": y})
    return out


def _translate_prompt(prompt: str) -> str:
    """Best-effort translate free-text prompt -> MarioGPT descriptor format.

    MarioGPT was trained on prompts like:
      "many pipes, many enemies, some blocks, high elevation"
      "no pipes, many enemies, some blocks, low elevations"
    We do keyword matching on the user's free text; unknown -> neutral default.
    """
    p = (prompt or "").lower()
    parts = []
    if "pipe" in p or "管道" in p:
        parts.append("many pipes")
    if "enemy" in p or "enemies" in p or "敌人" in p or "怪" in p:
        parts.append("many enemies")
    else:
        parts.append("no enemies")
    if "block" in p or "砖" in p:
        parts.append("some blocks")
    if "coin" in p or "金币" in p:
        parts.append("some coins")
    if "high" in p or "高" in p:
        parts.append("high elevation")
    elif "low" in p or "低" in p:
        parts.append("low elevation")
    else:
        parts.append("medium elevation")
    return ", ".join(parts)


class MarioGPTBackbone(GameBackbone):
    """Direction A primary (Phase 4 real). Level-only; worldmodel raises.

    Instantiation is cheap (no model load). The distilgpt2 weights are pulled
    on first generate() call (lazy). CPU is fine; CUDA is auto-used if available.
    """

    NAME = "mariogpt"
    VERSION = "0.1.0-real"
    DIRECTIONS = ["level"]  # MarioGPT is level-only

    def __init__(self, lm_path: str = "distilgpt2", tokenizer_path: str = "distilgpt2"):
        self._lm_path = lm_path
        self._tokenizer_path = tokenizer_path
        self._lm = None  # lazy

    def _ensure_lm(self):
        if self._lm is not None:
            return self._lm
        try:
            from mario_gpt import MarioLM  # lazy import
        except ImportError as e:
            raise ImportError(
                "mario_gpt not installed. Install with:  pip install mario-gpt  "
                "(pulls torch + transformers + Pillow). "
                "Or use backbone='mock' for dependency-free tests."
            ) from e
        self._lm = MarioLM(lm_path=self._lm_path, tokenizer_path=self._tokenizer_path)
        return self._lm

    def generate(self, prompt: str, config: dict) -> dict:
        cfg = config or {}
        direction = cfg.get("direction", "level")
        if direction != "level":
            raise NotImplementedError(
                f"MarioGPT is level-only (got direction='{direction}'). "
                "Use backbone='mock' for worldmodel, or wait for backbone_gamegen.py "
                "/ backbone_oasis.py real integration."
            )

        width = int(cfg.get("width", DEFAULT_WIDTH))
        height = int(cfg.get("height", DEFAULT_HEIGHT))
        n_coins = int(cfg.get("n_coins", 3))
        seed = cfg.get("seed")
        retry = int(cfg.get("retry", 0))
        temperature = float(cfg.get("temperature", DEFAULT_TEMPERATURE))

        # clamp size to GameCritic's allowed range [8,32]x[6,16] so SafetyGate
        # does not DEGRADE on size
        width = max(8, min(32, width))
        height = max(6, min(16, height))

        # control determinism via torch RNG (model weights are fixed; sampling
        # randomness comes from torch). If torch import fails, generation still
        # runs non-deterministically.
        if seed is not None:
            try:
                import torch
                torch.manual_seed(int(seed))
            except ImportError:
                pass

        lm = self._ensure_lm()
        smb_prompt = _translate_prompt(prompt)

        # num_steps controls columns (SMB row count is fixed at 14). Ask for
        # at least `width` columns so we have enough material to crop from.
        num_steps = max(width, 14)

        try:
            out = lm.sample(
                prompts=[smb_prompt],
                num_steps=num_steps,
                temperature=temperature,
                use_tqdm=False,
            )
        except Exception as e:
            raise RuntimeError(f"MarioGPT sample() failed: {e}") from e

        # out.level is documented as List[str] (one row per element); be tolerant
        level_field = getattr(out, "level", None)
        if isinstance(level_field, (list, tuple)):
            smb_str = "\n".join(str(r) for r in level_field)
        elif isinstance(level_field, str):
            smb_str = level_field
        else:
            smb_str = str(level_field) if level_field is not None else ""

        rng = random.Random(int.from_bytes(
            hashlib.sha256(f"{prompt}|{seed}|{retry}".encode("utf-8")).digest()[:8], "big"))
        rows = _normalize_smb_level(smb_str, width, height, rng, n_coins=n_coins)
        entities = _entities_from_rows(rows)

        return {
            "direction": "level",
            "level_map": rows,
            "width": width,
            "height": height,
            "entities": entities,
            "theme": cfg.get("theme") or "smb",
            "text_prompt": prompt,
            "scene_description": prompt,
            "refined_times": retry,
            "meta": {
                "backbone": self.NAME,
                "version": self.VERSION,
                "smb_prompt": smb_prompt,
                "seed": seed,
                "temperature": temperature,
                "num_steps": num_steps,
                "raw_smb_level": smb_str,
            },
        }

    def get_info(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "license": "MIT (mario-gpt) + Apache 2.0 (distilgpt2 weights)",
            "capabilities": ["level-generation", "cpu-runnable", "seed-deterministic",
                             "text-conditioned"],
            "directions": self.DIRECTIONS,
            "status": STATUS,
            "note": NOTE,
            "lm_path": self._lm_path,
        }


if __name__ == "__main__":
    b = MarioGPTBackbone()
    info = b.get_info()

    # contract shape
    assert isinstance(b, GameBackbone)
    assert info["status"] == STATUS
    assert info["name"] == "mariogpt"
    assert info["license"].startswith("MIT")
    assert info["directions"] == ["level"]

    # worldmodel direction always raises NotImplementedError (MarioGPT is level-only)
    try:
        b.generate("x", {"direction": "worldmodel"})
        raise AssertionError("worldmodel should raise NotImplementedError")
    except NotImplementedError:
        pass

    # generate() without mario_gpt installed -> ImportError with helpful message
    # (if mario_gpt IS installed, the call proceeds and we just check schema)
    try:
        out = b.generate("草地关卡 3 金币", {"direction": "level", "width": 16, "height": 10})
        # if we get here, mario_gpt is installed; verify schema
        assert out["direction"] == "level"
        assert isinstance(out["level_map"], list) and len(out["level_map"]) == 10
        assert out["width"] == 16 and out["height"] == 10
        assert out["text_prompt"] == "草地关卡 3 金币"
        assert any(e["type"] == "P" for e in out["entities"])
        assert any(e["type"] == "G" for e in out["entities"])
    except ImportError as e:
        assert "mario_gpt not installed" in str(e), f"unexpected ImportError: {e}"

    print("[OK] game backbone_mariogpt real self-test passed "
          "(lazy import + direction guard + schema)")
