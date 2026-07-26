"""branches/game scene keyword vocabulary — shared by mock backbone / WAM / Critic.

Parses a free-text game prompt into four buckets (game-specific, NOT video):
    themes   — visual biome        (grass/desert/ice/cave/sky/...)
    entities — things in the level  (coin/enemy/player/goal/hazard/...)
    actions  — player verbs        (run/jump/left/right/attack/...)
    elements — level geometry      (platform/gap/spike/flag/...)

Extracted so the Critic's semantic-alignment check does NOT depend on the WAM
implementation (which is swapped for a real backbone behind the adapter).
Bilingual (EN + 中文) keyword matching, lowercase substring.

Pure stdlib. Zero third-party dependencies.
"""

# (multilingual keywords, canonical_name)
_THEMES = (
    (("grass", "草地", "草"), "grass"),
    (("desert", "沙漠"), "desert"),
    (("ice", "冰原", "冰"), "ice"),
    (("cave", "洞穴"), "cave"),
    (("sky", "天空", "天"), "sky"),
)
_ENTITIES = (
    (("coin", "金币", "coins"), "coin"),
    (("enemy", "敌人", "enemies"), "enemy"),
    (("player", "玩家", "players"), "player"),
    (("goal", "终点", "旗帜", "flag", "goals", "flags"), "goal"),
    (("hazard", "陷阱", "hazards"), "hazard"),
)
_ACTIONS = (
    (("run", "跑", "奔"), "run"),
    (("jump", "跳"), "jump"),
    (("left", "左移", "向左"), "left"),
    (("right", "右移", "向右"), "right"),
    (("attack", "攻击", "打"), "attack"),
)
_ELEMENTS = (
    (("platform", "平台", "platforms"), "platform"),
    (("gap", "缺口", "gaps"), "gap"),
    (("spike", "尖刺", "spikes"), "spike"),
    (("flag", "旗帜"), "flag"),
)

_BUCKETS = (
    ("themes", _THEMES),
    ("entities", _ENTITIES),
    ("actions", _ACTIONS),
    ("elements", _ELEMENTS),
)


def objects_from_goal(goal_text: str) -> dict:
    """Parse a prompt into {themes, entities, actions, elements} keyword lists.

    Empty buckets are returned as empty lists (never None).
    """
    text = (goal_text or "").lower()
    out = {}
    for bucket, table in _BUCKETS:
        out[bucket] = [name for keys, name in table if any(k in text for k in keys)]
    return out


def keywords_of(goal_text: str) -> set:
    """Flatten all recognized canonical keywords into a set (for alignment scoring)."""
    parsed = objects_from_goal(goal_text)
    flat = set()
    for bucket in ("themes", "entities", "actions", "elements"):
        flat.update(parsed[bucket])
    return flat


if __name__ == "__main__":
    a = objects_from_goal("生成一个 2D 平台关卡：草地主题，3 个金币，能跳到终点旗帜")
    assert "grass" in a["themes"] and "coin" in a["entities"] and "flag" in a["elements"]
    assert "jump" in a["actions"]

    b = objects_from_goal("A desert level with enemies and spikes, run right and attack")
    assert "desert" in b["themes"] and "enemy" in b["entities"]
    assert "run" in b["actions"] and "spike" in b["elements"]

    c = objects_from_goal("nothing recognizable here")
    assert c["themes"] == [] and c["entities"] == [] and c["actions"] == [] and c["elements"] == []

    assert "coin" in keywords_of("草地 金币 跳跃 平台")
    print("[OK] game scene_objects self-test passed")
