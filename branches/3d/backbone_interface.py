"""ThreeDBackbone — anti-corruption interface for full-3D generation (V4).

The ONLY seam through which a real 3D model (TRELLIS / DreamGaussian / TripoSR /
Shap-E via Azure) is ever called. `wam.py` talks to THIS interface, never to a
model API. Swapping the backbone = one new file + one line in adapter.py.

Task-aware: `config` MUST carry `"task"`, one of
    text_to_3d | image_to_3d | pointcloud_completion | pbr_texture
(robot_scene stays on the V1 Scene3DWAM path and does NOT use this backbone).
The returned dict MUST carry `"task"` plus the task-specific fields documented
in branches/3d/README.md.

Pure stdlib. Zero third-party dependencies.
"""

from abc import ABC, abstractmethod

TASKS = ("text_to_3d", "image_to_3d", "pointcloud_completion", "pbr_texture")


class ThreeDBackbone(ABC):
    @abstractmethod
    def generate(self, prompt: str, config: dict) -> dict:
        """prompt: text description. config: dict with required "task" +
        task params (source_image / source_points / poly_budget / retry / seed).
        Returns a dict with "task" + task-specific fields + "meta"."""
        ...

    @abstractmethod
    def get_info(self) -> dict:
        """Backbone card: name / version / license / capabilities."""
        ...


if __name__ == "__main__":
    try:
        ThreeDBackbone()  # type: ignore[abstract]
        raise AssertionError("interface must be abstract")
    except TypeError:
        pass
    assert TASKS == ("text_to_3d", "image_to_3d", "pointcloud_completion", "pbr_texture")
    print("[OK] 3d backbone_interface self-test passed (abstract, task-aware)")
