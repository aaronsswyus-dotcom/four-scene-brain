"""MockVideoBackbone — deterministic mock video backbone (V2 default).

Generates SOLID-COLOR placeholder frames whose color is derived from the prompt
hash (so the same prompt always yields the same "video" — determinism the Critic
can rely on). Real HunyuanVideo/Wan-2.1 go through Azure later; only a new
backbone_*.py file is added, this interface stays fixed.

Retry refinement (mirrors robot WAM's force-drop): the mock starts a target
duration `initial_drift_s` seconds off, and each orchestrator retry converges it
back toward the target. This lets the demo exercise the S9->S7 retry loop.

Pure stdlib. Zero third-party dependencies.
"""

import hashlib

from branches.video.backbone_interface import VideoBackbone
from branches.video.scene_objects import objects_from_goal

DEFAULT_DURATION_S = 5.0
DEFAULT_FPS = 24
DEFAULT_RESOLUTION = [640, 480]
DRIFT_STEP_S = 1.5              # duration error removed per retry
FRAME_SAMPLE_CAP = 12          # cap emitted placeholder frames (keep payload small)


def _color_from_prompt(prompt: str) -> list:
    """Deterministic RGB from prompt hash."""
    h = hashlib.sha256((prompt or "").encode("utf-8")).digest()
    return [h[0], h[1], h[2]]


class MockVideoBackbone(VideoBackbone):
    """Deterministic solid-color mock. Same prompt+config -> identical output."""

    NAME = "mock-video"
    VERSION = "0.2.0"

    def generate(self, prompt: str, config: dict) -> dict:
        cfg = config or {}
        target_duration = float(cfg.get("duration_s", DEFAULT_DURATION_S))
        fps = int(cfg.get("fps", DEFAULT_FPS))
        resolution = list(cfg.get("resolution", DEFAULT_RESOLUTION))
        retry = int(cfg.get("retry", 0))
        initial_drift = float(cfg.get("initial_drift_s", 0.0))

        # retry refinement: converge duration toward target
        drift = max(0.0, initial_drift - retry * DRIFT_STEP_S)
        actual_duration = round(max(0.1, target_duration - drift), 4)

        parsed = objects_from_goal(prompt)
        subjects = parsed["subjects"] or ["subject"]
        actions = parsed["actions"] or ["move"]
        scenes = parsed["scenes"] or ["scene"]
        scene_description = f"{'+'.join(subjects)} {'+'.join(actions)} in {'+'.join(scenes)}"
        camera_motion = parsed["camera"][0]

        # deterministic solid-color placeholder frames (sampled)
        color = _color_from_prompt(prompt)
        n_frames = max(1, int(round(actual_duration * fps)))
        sample = min(n_frames, FRAME_SAMPLE_CAP)
        frames = [{"idx": i, "rgb": color} for i in range(sample)]

        return {
            "frames": frames,
            "frame_count": n_frames,
            "fps": fps,
            "duration_s": actual_duration,
            "resolution": resolution,
            "text_prompt": prompt,
            "scene_description": scene_description,
            "camera_motion": camera_motion,
            "refined_times": retry,
            "meta": {"backbone": self.NAME, "seed": cfg.get("seed"),
                     "color": color, "quality_score": round(0.6 + 0.1 * retry, 4)},
        }

    def get_info(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "license": "N/A (mock)",
            "capabilities": ["text2video-mock", "deterministic", "retry-refine"],
        }


if __name__ == "__main__":
    b = MockVideoBackbone()

    # determinism: same prompt -> same color
    o1 = b.generate("a cat running on the grass", {"duration_s": 5.0})
    o2 = b.generate("a cat running on the grass", {"duration_s": 5.0})
    assert o1["meta"]["color"] == o2["meta"]["color"]
    assert o1["frames"][0]["rgb"] == o2["frames"][0]["rgb"]

    # no drift -> duration hits target exactly
    assert o1["duration_s"] == 5.0
    assert o1["scene_description"].startswith("cat run")
    assert o1["camera_motion"] == "static"

    # drift converges with retries
    d0 = b.generate("cat run grass", {"duration_s": 5.0, "initial_drift_s": 2.0, "retry": 0})
    d1 = b.generate("cat run grass", {"duration_s": 5.0, "initial_drift_s": 2.0, "retry": 1})
    assert d0["duration_s"] == 3.0 and d1["duration_s"] == 4.5   # 5-2.0, 5-0.5
    assert d1["refined_times"] == 1

    assert b.get_info()["name"] == "mock-video"
    print("[OK] video backbone_mock self-test passed")
