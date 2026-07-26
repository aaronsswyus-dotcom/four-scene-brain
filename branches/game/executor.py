"""GameExecutor — S12 execution: write a level / replay artifact (no real engine).

Pure stdlib. Emits:
  - direction=="level":     output/game/level_<hash>.json  (spec)
                             + output/game/level_<hash>.txt  (ASCII render)
  - direction=="worldmodel": output/game/replay_<hash>.json (frames + action trajectory)

This is a MOCK artifact — it proves the delivery/telemetry path, NOT game quality.
Real levels/replays come from MarioGPT / GameGen-O on Azure later.

Delivery.meta carries telemetry_kind='game' + telemetry_data (contract §8: the
scene fills kind/data, common stores).

Pure stdlib. Zero third-party dependencies.
"""

import hashlib
import json
import time
from pathlib import Path

from common.interfaces.abstract import Executor
from common.interfaces.data_objects import Executable, Delivery

OUTPUT_DIR = Path("output/game")


class GameExecutor(Executor):
    def execute(self, executable: Executable) -> Delivery:
        p = executable.payload or {}
        direction = p.get("direction", "level")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        if direction == "worldmodel":
            return self._execute_worldmodel(p)

        # ---- level ----
        level_map = p.get("level_map") or []
        spec = {
            "direction": "level",
            "level_map": level_map,
            "width": p.get("width"),
            "height": p.get("height"),
            "entities": p.get("entities"),
            "theme": p.get("theme"),
            "text_prompt": p.get("text_prompt", ""),
        }
        prompt = p.get("text_prompt", "")
        name = f"level_{hashlib.sha1(prompt.encode('utf-8')).hexdigest()[:8]}"
        json_path = OUTPUT_DIR / f"{name}.json"
        txt_path = OUTPUT_DIR / f"{name}.txt"
        json_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        ascii_render = "\n".join(level_map)
        txt_path.write_text(
            f"theme: {spec['theme']}\nsize: {spec['width']}x{spec['height']}\n"
            f"prompt: {prompt}\n\n{ascii_render}\n", encoding="utf-8")

        return Delivery(
            target="game",
            artifact={"level_json": str(json_path), "ascii_txt": str(txt_path),
                      "width": spec["width"], "height": spec["height"],
                      "theme": spec["theme"], "placeholder": True},
            meta={
                "telemetry_kind": "game",
                "telemetry_data": {
                    "direction": "level",
                    "width": spec["width"], "height": spec["height"],
                    "theme": spec["theme"], "placeholder": True,
                    "executed_at": time.time(),
                },
            },
        )

    def _execute_worldmodel(self, p: dict) -> Delivery:
        spec = {
            "direction": "worldmodel",
            "frames": p.get("frames"),
            "fps": (p.get("replay_spec") or {}).get("fps"),
            "resolution": p.get("resolution"),
            "frame_count": p.get("frame_count"),
            "action_history": (p.get("replay_spec") or {}).get("action_history"),
            "current_action": (p.get("replay_spec") or {}).get("current_action"),
            "text_prompt": p.get("text_prompt", ""),
        }
        prompt = p.get("text_prompt", "")
        name = f"replay_{hashlib.sha1(prompt.encode('utf-8')).hexdigest()[:8]}"
        path = OUTPUT_DIR / f"{name}.json"
        path.write_text(json.dumps(spec, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return Delivery(
            target="game",
            artifact={"replay_json": str(path), "frame_count": spec["frame_count"],
                      "resolution": spec["resolution"], "placeholder": True},
            meta={
                "telemetry_kind": "game",
                "telemetry_data": {
                    "direction": "worldmodel",
                    "frame_count": spec["frame_count"], "resolution": spec["resolution"],
                    "current_action": spec["current_action"], "placeholder": True,
                    "executed_at": time.time(),
                },
            },
        )


if __name__ == "__main__":
    ex = GameExecutor()
    lvl = Executable("pixel", {"direction": "level", "level_map": ["####", "#P.G#", "####"],
                               "width": 4, "height": 3, "entities": [], "theme": "grass",
                               "text_prompt": "草地关卡"}, {})
    d = ex.execute(lvl)
    assert d.target == "game" and d.meta["telemetry_kind"] == "game"
    from pathlib import Path as _P
    assert _P(d.artifact["level_json"]).exists() and _P(d.artifact["ascii_txt"]).exists()

    wm = Executable("pixel", {"direction": "worldmodel", "frames": [[[0]]] * 8,
                              "resolution": [16, 12], "frame_count": 8,
                              "replay_spec": {"fps": 12, "action_history": ["right"],
                                              "current_action": "right"},
                              "text_prompt": "角色向右"}, {})
    d2 = ex.execute(wm)
    assert d2.target == "game" and _P(d2.artifact["replay_json"]).exists()
    print(f"[OK] game executor self-test passed -> {d.artifact['ascii_txt']} + {d2.artifact['replay_json']}")
