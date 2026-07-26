"""OASIS backbone adapter stub (V3 placeholder, oss-list-v3 §4.3).

Direction B 备选 (oss-list-v3 §2). OASIS (etched-ai, Minecraft interactive world
model, open weights) is the fallback when GameGen-O fails the Azure T1–T5 gates.

Real integration goes through Azure AFTER engineering-setup §2 T1–T5 gates pass.
Until then every call raises NotImplementedError — the contract shape is defined
but nothing is falsely "working".

This is the "V3 只做接口定义" deliverable: a concrete subclass of GameBackbone
that documents direction B's alternative backbone without pulling any real
dependency into the repo.

Pure stdlib. Zero third-party dependencies. Lives ONLY in branches/game/
(never common). The adapter wires it in via `backbone="oasis-azure"`.
"""

from branches.game.backbone_interface import GameBackbone

STATUS = "stub"
NOTE = ("NotImplementedError until Azure T1-T5 gates pass (oss-list-v3 §4.3). "
        "Use backbone='mock' for the dual-direction mock.")


class OASISBackbone(GameBackbone):
    """Direction B 备选 (oss-list-v3 §2). Stub until Azure T1-T5 gates pass.

    OASIS is interactive-world-model oriented → natural direction "worldmodel".
    """

    NAME = "oasis"
    VERSION = "0.0.0-stub"
    DIRECTIONS = ["worldmodel", "level"]

    def generate(self, prompt: str, config: dict) -> dict:
        raise NotImplementedError(
            f"{self.NAME} backbone is not integrated yet. {NOTE}")

    def get_info(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "license": "TBD (T1 gate: verify commercial usability)",
            "capabilities": [],
            "directions": self.DIRECTIONS,
            "status": STATUS,
            "note": NOTE,
        }


if __name__ == "__main__":
    b = OASISBackbone()
    assert isinstance(b, GameBackbone)
    assert b.get_info()["status"] == STATUS
    try:
        b.generate("x", {"direction": "worldmodel"})
        raise AssertionError("stub must raise NotImplementedError on generate()")
    except NotImplementedError:
        pass
    print("[OK] game backbone_oasis stub self-test passed (raises until Azure T1-T5)")
