"""GameGen-O backbone adapter stub (V3 placeholder, oss-list-v3 §4.3).

Real GameGen-O (Tencent, research preview) integration goes through Azure AFTER
engineering-setup §2 T1–T5 gates pass (license / open-weights / health /
quickstart / interface probe). Until then every call raises NotImplementedError
so the CONTRACT SHAPE is defined but nothing is falsely "working".

This is the "V3 只做接口定义" deliverable: a concrete subclass of GameBackbone
that documents direction B's primary backbone (open-world game video generation)
without pulling any real dependency into the repo.

Pure stdlib. Zero third-party dependencies. Lives ONLY in branches/game/
(never common). The adapter wires it in via `backbone="gamegen-azure"`.
"""

from branches.game.backbone_interface import GameBackbone

STATUS = "stub"
NOTE = ("NotImplementedError until Azure T1-T5 gates pass (oss-list-v3 §4.3). "
        "Use backbone='mock' for the dual-direction mock.")


class GameGenOBackbone(GameBackbone):
    """Direction B 主推 (oss-list-v3 §2). Stub until Azure T1-T5 gates pass.

    GameGen-O is primarily worldmodel-oriented (open-world game VIDEO generation),
    so its natural direction is "worldmodel"; the schema below reserves both so the
    adapter can route either way once the real backbone lands.
    """

    NAME = "gamegen-o"
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
    b = GameGenOBackbone()
    assert isinstance(b, GameBackbone)
    assert b.get_info()["status"] == STATUS
    try:
        b.generate("x", {"direction": "worldmodel"})
        raise AssertionError("stub must raise NotImplementedError on generate()")
    except NotImplementedError:
        pass
    print("[OK] game backbone_gamegen stub self-test passed (raises until Azure T1-T5)")
