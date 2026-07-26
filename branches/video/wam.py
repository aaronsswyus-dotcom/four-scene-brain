"""VideoWAM — S7 imagination for video (pixel camp, backbone behind adapter).

Unlike robot/3d (physical camp), video does NOT inherit PhysicalWorldModelBase:
its priors are pixel/temporal, not force/geometry. It implements WorldModel
directly and delegates the actual "imagination" to an injected VideoBackbone.

Branch-frozen State.payload (see README.md):
    frames / frame_count / fps / duration_s / resolution / text_prompt
    scene_description / camera_motion / refined_times / meta

Retry refinement is delegated to the backbone: the orchestrator sets
state.meta['retry']; VideoWAM forwards it (plus the sub-goal's
constraints['initial_drift_s']) so the mock converges duration toward target.

Pure stdlib. Zero third-party dependencies.
"""

from branches.video.backbone_interface import VideoBackbone
from branches.video.backbone_mock import (
    MockVideoBackbone, DEFAULT_DURATION_S, DEFAULT_FPS, DEFAULT_RESOLUTION,
)
from common.interfaces.abstract import WorldModel
from common.interfaces.data_objects import State, SubGoal


class VideoWAM(WorldModel):
    """Video world model. Real HunyuanVideo (Azure) replaces the backbone via adapter."""

    def __init__(self, backbone: VideoBackbone = None) -> None:
        self.backbone = backbone or MockVideoBackbone()

    def predict_next_state(self, state: State, goal: SubGoal) -> State:
        c = goal.constraints or {}
        config = {
            "duration_s": float(c.get("duration_s", DEFAULT_DURATION_S)),
            "fps": int(c.get("fps", DEFAULT_FPS)),
            "resolution": list(c.get("resolution", DEFAULT_RESOLUTION)),
            "seed": c.get("seed"),
            "retry": int((state.meta or {}).get("retry", 0)),
            "initial_drift_s": float(c.get("initial_drift_s", 0.0)),
        }
        output = self.backbone.generate(goal.goal, config)
        return State(modality="pixel", payload=output, meta=dict(state.meta or {}))


if __name__ == "__main__":
    wm = VideoWAM()  # defaults to MockVideoBackbone
    s = State("pixel", None, {"trace_id": "t"})
    g = SubGoal("sg-1", "video", "a cat running on the grass, zoom in",
                "duration/fps/resolution + alignment", [], {"duration_s": 5.0})
    out = wm.predict_next_state(s, g)
    p = out.payload
    assert out.modality == "pixel"
    assert set(p) >= {"frames", "fps", "duration_s", "resolution", "text_prompt",
                      "scene_description", "camera_motion", "refined_times"}
    assert p["duration_s"] == 5.0 and p["camera_motion"] == "zoom"
    assert p["scene_description"].startswith("cat run")

    # retry converges duration (backbone refinement forwarded from state.meta)
    g2 = SubGoal("sg-1", "video", "cat run grass", "", [],
                 {"duration_s": 5.0, "initial_drift_s": 2.0})
    s0 = State("pixel", None, {"trace_id": "t", "retry": 0})
    s1 = State("pixel", None, {"trace_id": "t", "retry": 1})
    assert wm.predict_next_state(s0, g2).payload["duration_s"] == 3.0
    assert wm.predict_next_state(s1, g2).payload["duration_s"] == 4.5
    print("[OK] video wam self-test passed")
