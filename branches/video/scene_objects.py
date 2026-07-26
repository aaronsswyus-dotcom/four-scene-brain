"""branches/video scene keyword vocabulary — shared by mock backbone / WAM / Critic.

Parses a free-text video prompt into four buckets:
    actions  — verbs of motion       (run/jump/fly/...)
    subjects — who/what is acting     (cat/dog/person/car/...)
    scenes   — where it happens       (grass/road/sky/...)
    camera   — camera language        (zoom/pan/tilt/static/...)

Extracted so the Critic's semantic-alignment check does NOT depend on the WAM
implementation (which is swapped for a real backbone behind the adapter).
Bilingual (EN + 中文) keyword matching, lowercase substring.

Pure stdlib. Zero third-party dependencies.
"""

# (multilingual keywords, canonical_name)
_ACTIONS = (
    (("run", "跑", "奔"), "run"),
    (("jump", "跳"), "jump"),
    (("walk", "走"), "walk"),
    (("fly", "飞"), "fly"),
    (("swim", "游"), "swim"),
    (("dance", "舞", "跳舞"), "dance"),
)
_SUBJECTS = (
    (("cat", "猫"), "cat"),
    (("dog", "狗"), "dog"),
    (("person", "man", "woman", "人"), "person"),
    (("car", "车"), "car"),
    (("bird", "鸟"), "bird"),
    (("robot", "机器人"), "robot"),
)
_SCENES = (
    (("grass", "meadow", "草地", "草"), "grass"),
    (("road", "street", "马路", "路"), "road"),
    (("sky", "天空", "天"), "sky"),
    (("water", "sea", "river", "水", "海"), "water"),
    (("room", "indoor", "房间", "室内"), "room"),
    (("city", "城市"), "city"),
)
_CAMERA = (
    (("zoom", "拉近", "推近"), "zoom"),
    (("pan", "平移"), "pan"),
    (("tilt", "倾斜"), "tilt"),
    (("static", "fixed", "固定"), "static"),
)

_BUCKETS = (
    ("actions", _ACTIONS),
    ("subjects", _SUBJECTS),
    ("scenes", _SCENES),
    ("camera", _CAMERA),
)


def objects_from_goal(goal_text: str) -> dict:
    """Parse a prompt into {actions, subjects, scenes, camera} keyword lists.

    Empty buckets are returned as empty lists (never None). If no camera word is
    found, camera defaults to ['static'] so downstream always has a motion.
    """
    text = (goal_text or "").lower()
    out = {}
    for bucket, table in _BUCKETS:
        out[bucket] = [name for keys, name in table if any(k in text for k in keys)]
    if not out["camera"]:
        out["camera"] = ["static"]
    return out


def keywords_of(goal_text: str) -> set:
    """Flatten all recognized canonical keywords into a set (for alignment scoring)."""
    parsed = objects_from_goal(goal_text)
    flat = set()
    for bucket in ("actions", "subjects", "scenes"):   # camera excluded from alignment
        flat.update(parsed[bucket])
    return flat


if __name__ == "__main__":
    a = objects_from_goal("a cat running on the grass, camera zoom in")
    assert a["subjects"] == ["cat"] and a["actions"] == ["run"]
    assert a["scenes"] == ["grass"] and a["camera"] == ["zoom"]

    b = objects_from_goal("一只狗在马路上奔跑")
    assert b["subjects"] == ["dog"] and b["actions"] == ["run"] and b["scenes"] == ["road"]
    assert b["camera"] == ["static"]  # no camera word -> default static

    c = objects_from_goal("nothing recognizable here")
    assert c["subjects"] == [] and c["actions"] == [] and c["camera"] == ["static"]

    assert keywords_of("cat run grass") == {"cat", "run", "grass"}
    print("[OK] video scene_objects self-test passed")
