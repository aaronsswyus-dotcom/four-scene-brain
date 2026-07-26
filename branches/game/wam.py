"""GameWAM — S7 imagination for game (pixel camp, backbone behind adapter).

Like video (pixel camp), game does NOT inherit PhysicalWorldModelBase: its priors
are tile/agent-based, not force/geometry. It implements WorldModel directly and
delegates the actual "imagination" to an injected GameBackbone.

The generation direction ("level" | "worldmodel") is decided per-sub-goal: the
bundle default (set at register time) is overridden by goal.constraints["direction"]
if present. The orchestrator's retry counter is forwarded as config["retry"] so the
mock backbone can refine (level reachability / worldmodel motion coherence).

Pure stdlib. Zero third-party dependencies.
"""

from branches.game.backbone_interface import GameBackbone
from branches.game.backbone_mock import MockGameBackbone
from common.interfaces.abstract import WorldModel
from common.interfaces.data_objects import State, SubGoal


class GameWAM(WorldModel):
    """Game world model. Real MarioGPT / GameGen-O (Azure) replaces the backbone."""

    def __init__(self, backbone: GameBackbone = None, direction: str = "level") -> None:
        self.backbone = backbone or MockGameBackbone()
        self.direction = direction

    def predict_next_state(self, state: State, goal: SubGoal) -> State:
        c = goal.constraints or {}
        direction = str(c.get("direction", self.direction))
        retry = int((state.meta or {}).get("retry", 0))
        config = {"direction": direction, "retry": retry, "seed": c.get("seed")}

        if direction == "level":
            config.update({
                "theme": c.get("theme"),
                "width": c.get("width", 16),
                "height": c.get("height", 10),
                "n_coins": c.get("n_coins", 3),
                "n_enemies": c.get("n_enemies", 2),
                "n_hazards": c.get("n_hazards", 1),
                "challenge": c.get("challenge", False),
            })
        elif direction == "worldmodel":
            config.update({
                "action": c.get("action", "right"),
                "fps": c.get("fps", 12),
                "resolution": list(c.get("resolution", [16, 12])),
                "state_frames": c.get("state_frames", 8),
            })
        else:
            raise ValueError(f"unknown game direction '{direction}'")

        output = self.backbone.generate(goal.goal, config)
        meta = dict(state.meta or {})
        meta["direction"] = direction
        return State(modality="pixel", payload=output, meta=meta)


if __name__ == "__main__":
    # level direction
    wm = GameWAM(direction="level")
    s = State("pixel", None, {"trace_id": "t", "subgoal_id": "sg-1"})
    g = SubGoal("sg-1", "game", "草地关卡 3 金币 终点旗帜", "", [],
                {"direction": "level", "n_coins": 3})
    out = wm.predict_next_state(s, g)
    p = out.payload
    assert out.modality == "pixel" and out.meta["direction"] == "level"
    assert p["direction"] == "level" and p["level_map"] and p["theme"]

    # worldmodel direction (override bundle default)
    wm2 = GameWAM(direction="level")  # default level, but constraint switches
    g2 = SubGoal("sg-2", "game", "角色向右移动", "", [],
                 {"direction": "worldmodel", "action": "right"})
    out2 = wm2.predict_next_state(s, g2)
    assert out2.payload["direction"] == "worldmodel"
    assert out2.payload["current_action"] == "right"

    # retry forwarded
    s_retry = State("pixel", None, {"trace_id": "t", "subgoal_id": "sg-3", "retry": 1})
    g3 = SubGoal("sg-3", "game", "草地关卡", "", [],
                 {"direction": "level", "challenge": True})
    assert wm.predict_next_state(s_retry, g3).payload["refined_times"] == 1
    print("[OK] game wam self-test passed")
