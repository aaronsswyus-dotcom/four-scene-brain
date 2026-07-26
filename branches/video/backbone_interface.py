"""VideoBackbone — the ANTI-CORRUPTION LAYER for video generation (oss-list-v2 §4.1).

Every video backbone (mock now; HunyuanVideo / Wan-2.1 / CogVideoX on Azure later)
MUST implement this interface. The rest of the branch (wam/critic/primitives/...)
talks ONLY to this interface, NEVER to a raw backbone API. Swapping backbones is a
one-line change in adapter.py; nothing else in the branch or in common moves.

Pure stdlib. Zero third-party dependencies.
"""

from abc import ABC, abstractmethod


class VideoBackbone(ABC):
    """Unified video-generation adapter interface."""

    @abstractmethod
    def generate(self, prompt: str, config: dict) -> dict:
        """Generate a video from a text prompt.

        Args:
            prompt: free-text description of the desired video.
            config: {
                "duration_s":  float,          # target duration (seconds)
                "fps":         int,            # target frames per second
                "resolution":  [w, h],         # target resolution
                "seed":        int | None,     # determinism seed
                "retry":       int,            # orchestrator retry count (refinement)
                "initial_drift_s": float,      # mock-only: duration error to converge away
            }

        Returns (unified schema — all backbones normalize to this):
            {
                "frames":            list,     # placeholder frame data [T] (mock: solid colors)
                "fps":               int,
                "duration_s":        float,
                "resolution":        [w, h],
                "text_prompt":       str,
                "scene_description": str,      # backbone's scene understanding
                "camera_motion":     str,      # backbone's camera description
                "refined_times":     int,      # how many refinement passes happened
                "meta":              dict,     # backbone-specific extras
            }
        """
        ...

    @abstractmethod
    def get_info(self) -> dict:
        """Return backbone metadata: name / version / license / capabilities."""
        ...


if __name__ == "__main__":
    import inspect

    # abstract class must NOT be directly instantiable
    try:
        VideoBackbone()  # type: ignore[abstract]
        raise AssertionError("VideoBackbone should not be instantiable")
    except TypeError:
        pass

    # frozen signatures
    assert list(inspect.signature(VideoBackbone.generate).parameters) == ["self", "prompt", "config"]
    assert list(inspect.signature(VideoBackbone.get_info).parameters) == ["self"]

    # a minimal concrete impl must be instantiable
    class _Impl(VideoBackbone):
        def generate(self, prompt, config):
            return {}
        def get_info(self):
            return {"name": "_impl"}

    assert _Impl().get_info()["name"] == "_impl"
    print("[OK] video backbone_interface self-test passed")
