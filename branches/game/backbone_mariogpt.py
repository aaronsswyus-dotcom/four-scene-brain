"""MarioGPT backbone adapter stub (V3 placeholder, oss-list-v3 §4.3).

Direction A 主推 (oss-list-v3 §2). MarioGPT (shyamsn97, text→2D platformer tile
map, SMB style) is the primary level-generation backbone. It is the only open
option that directly emits a 2D platform tile map.

Real integration goes through Azure AFTER engineering-setup §2 T1–T5 gates pass
(license / commercial terms / output-format controllability). Until then every
call raises NotImplementedError — the contract shape is defined but nothing is
falsely "working".

This is the "V3 只做接口定义" deliverable: a concrete subclass of GameBackbone
that documents direction A's primary backbone without pulling any real dependency
into the repo.

Pure stdlib. Zero third-party dependencies. Lives ONLY in branches/game/
(never common). The adapter wires it in via `backbone="mariogpt-azure"`.
"""

from branches.game.backbone_interface import GameBackbone

STATUS = "stub"
NOTE = ("NotImplementedError until Azure T1-T5 gates pass (oss-list-v3 §4.3). "
        "Use backbone='mock' for the dual-direction mock.")


class MarioGPTBackbone(GameBackbone):
    """Direction A 主推 (oss-list-v3 §2). Stub until Azure T1-T5 gates pass.

    MarioGPT is level-oriented → natural direction "level".
    """

    NAME = "mariogpt"
    VERSION = "0.0.0-stub"
    DIRECTIONS = ["level", "worldmodel"]

    def generate(self, prompt: str, config: dict) -> dict:
        raise NotImplementedError(
            f"{self.NAME} backbone is not integrated yet. {NOTE}")

    def get_info(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "license": "TBD (T1 gate: research code, verify commercial usability)",
            "capabilities": [],
            "directions": self.DIRECTIONS,
            "status": STATUS,
            "note": NOTE,
        }


if __name__ == "__main__":
    b = MarioGPTBackbone()
    assert isinstance(b, GameBackbone)
    assert b.get_info()["status"] == STATUS
    try:
        b.generate("x", {"direction": "level"})
        raise AssertionError("stub must raise NotImplementedError on generate()")
    except NotImplementedError:
        pass
    print("[OK] game backbone_mariogpt stub self-test passed (raises until Azure T1-T5)")
