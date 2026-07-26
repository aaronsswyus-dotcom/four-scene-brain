"""VideoMapper — S11 mapping: primitives -> video Executable (mp4 spec).

The frozen signature is map(primitives, goal); the video spec travels inside
primitives[0].meta['video_spec'] (stashed by VideoPrimitiveLibrary). The
resulting Executable.payload carries text_prompt / resolution / duration_s so
the SafetyGate (which only sees the Executable) can audit content and enforce
safe bounds.

DEGRADE path (SafetyGate): when any primitive meta carries degrade=True, the
spec is CLAMPED UP to safe minimums (>=240p, >=0.5s). This is the one bounded
degraded re-map the orchestrator performs before re-checking SafetyGate.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import Mapper
from common.interfaces.data_objects import SubGoal, Executable, Primitive

SAFE_MIN_RESOLUTION = [320, 240]   # 240p floor
SAFE_MIN_DURATION_S = 0.5


class VideoMapper(Mapper):
    def map(self, primitives: list, goal: SubGoal) -> Executable:
        spec = {}
        if primitives:
            spec = dict((primitives[0].meta or {}).get("video_spec", {}) or {})
        degrade = any((p.meta or {}).get("degrade") for p in primitives)

        resolution = list(spec.get("resolution") or SAFE_MIN_RESOLUTION)
        duration = float(spec.get("duration_s") or SAFE_MIN_DURATION_S)
        if degrade:
            resolution = [max(resolution[0], SAFE_MIN_RESOLUTION[0]),
                          max(resolution[1], SAFE_MIN_RESOLUTION[1])]
            duration = max(duration, SAFE_MIN_DURATION_S)

        sequence = [{"primitive": p.kind, "params": p.params} for p in primitives]
        video_spec = {
            "duration_s": round(duration, 4),
            "fps": spec.get("fps"),
            "resolution": resolution,
            "frame_count": spec.get("frame_count"),
            "camera_motion": spec.get("camera_motion"),
            "primitive_sequence": [p.kind for p in primitives],
        }
        return Executable(
            modality="pixel",
            payload={
                "video_spec": video_spec,
                "sequence": sequence,
                "text_prompt": spec.get("text_prompt", ""),   # SafetyGate content audit
                "scene_description": spec.get("scene_description", ""),
                "resolution": resolution,                     # SafetyGate bounds check
                "duration_s": round(duration, 4),
            },
            meta={"degraded": degrade},
        )


if __name__ == "__main__":
    m = VideoMapper()
    spec = {"duration_s": 5.0, "fps": 24, "resolution": [640, 480],
            "text_prompt": "a cat running on the grass", "scene_description": "cat run in grass",
            "camera_motion": "zoom", "frame_count": 120}
    prims = [Primitive("cut", {}, {"video_spec": spec}),
             Primitive("zoom", {"zoom_factor": 1.5}, {"video_spec": spec}),
             Primitive("fade", {"fade_ms": 300}, {"video_spec": spec})]
    g = SubGoal("s", "video", "g", "", [], {})
    e = m.map(prims, g)
    assert e.modality == "pixel" and not e.meta["degraded"]
    assert e.payload["text_prompt"] == "a cat running on the grass"
    assert e.payload["video_spec"]["primitive_sequence"] == ["cut", "zoom", "fade"]
    assert e.payload["resolution"] == [640, 480]

    # degrade clamps low resolution/duration UP to safe floor
    low = {"duration_s": 0.2, "fps": 24, "resolution": [160, 120],
           "text_prompt": "x", "scene_description": "y", "camera_motion": "static"}
    prims_d = [Primitive("cut", {}, {"video_spec": low, "degrade": True})]
    e2 = m.map(prims_d, g)
    assert e2.meta["degraded"]
    assert e2.payload["resolution"] == [320, 240] and e2.payload["duration_s"] == 0.5
    print("[OK] video mapper self-test passed")
