"""GameBackbone — the ANTI-CORRUPTION LAYER for game generation (oss-list-v3 §4.1).

Every game backbone (mock now; MarioGPT / GameGen-O / OASIS on Azure later) MUST
implement this ONE interface, which covers BOTH generation directions:
    - direction="level"      -> playable 2D platformer tile map (+ entities)
    - direction="worldmodel" -> action-conditioned frame sequence (interactive sim)

The rest of the branch (wam/critic/primitives/...) talks ONLY to this interface,
NEVER to a raw backbone API. Swapping backbones is a one-line change in
adapter.py; nothing else in the branch or in common moves.

Pure stdlib. Zero third-party dependencies.
"""

from abc import ABC, abstractmethod


class GameBackbone(ABC):
    """Unified, direction-aware game-generation adapter interface."""

    @abstractmethod
    def generate(self, prompt: str, config: dict) -> dict:
        """Generate game content from a text prompt.

        Args:
            prompt: free-text description of the desired level / scene.
            config: {
                "direction": "level" | "worldmodel"   # REQUIRED routing key
                # level:
                #   theme / width / height / n_coins / n_enemies / n_hazards
                #   / challenge / seed / retry
                # worldmodel:
                #   action / fps / resolution / state_frames / seed / retry
            }

        Returns (unified schema — all backbones normalize to this):
            {
                "direction": "level" | "worldmodel",
                # direction=="level":
                #   level_map / width / height / entities / theme / text_prompt
                #   / scene_description / refined_times / meta
                # direction=="worldmodel":
                #   frames / fps / resolution / action_history / current_action
                #   / text_prompt / scene_description / refined_times / meta
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
        GameBackbone()  # type: ignore[abstract]
        raise AssertionError("GameBackbone should not be instantiable")
    except TypeError:
        pass

    # frozen signatures
    assert list(inspect.signature(GameBackbone.generate).parameters) == ["self", "prompt", "config"]
    assert list(inspect.signature(GameBackbone.get_info).parameters) == ["self"]

    # a minimal concrete impl must be instantiable
    class _Impl(GameBackbone):
        def generate(self, prompt, config):
            return {"direction": config["direction"]}
        def get_info(self):
            return {"name": "_impl"}

    assert _Impl().get_info()["name"] == "_impl"
    print("[OK] game backbone_interface self-test passed")
