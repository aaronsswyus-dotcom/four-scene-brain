"""branches/3d scene object vocabulary — shared by WAM and Critic.

Extracted so Critic's required-object check does NOT depend on the WAM
implementation (which will be swapped for a real backbone behind the adapter).

V1 (robot_scene) uses `objects_from_goal` for the required-object check.
V4 (full 3D: text_to_3d / image_to_3d / ...) adds generative vocabulary
(objects + colors + materials + shapes) via `keywords_of` / `descriptors_of`.
Both are ADDITIVE — V1 helpers below are unchanged.
"""

# (multilingual keywords, canonical_object_name)
_KNOWN_OBJECTS = (
    (("table", "桌"), "table"),
    (("cup", "杯"), "cup"),
    (("tray", "托盘"), "tray"),
    (("sofa", "沙发"), "sofa"),
    (("door", "门"), "door"),
    (("shelf", "架"), "shelf"),
)

# ---- V4 generative vocabulary (text/image -> 3D) --------------------------
# extra objects common in single-asset generation (not scene furniture)
_GEN_OBJECTS = (
    (("chair", "椅"), "chair"),
    (("mug", "马克杯"), "mug"),
    (("vase", "花瓶"), "vase"),
    (("robot", "机器人"), "robot"),
    (("car", "车", "汽车"), "car"),
    (("bottle", "瓶"), "bottle"),
    (("lamp", "灯"), "lamp"),
    (("helmet", "头盔"), "helmet"),
    (("statue", "雕像", "摆件"), "statue"),
)
_COLORS = (
    (("red", "红"), "red"), (("green", "绿"), "green"), (("blue", "蓝"), "blue"),
    (("yellow", "黄"), "yellow"), (("black", "黑"), "black"), (("white", "白"), "white"),
    (("wooden", "wood", "木"), "wood"),
)
_MATERIALS = (
    (("metal", "金属", "metallic"), "metal"), (("wood", "木", "wooden"), "wood"),
    (("plastic", "塑料"), "plastic"), (("ceramic", "陶瓷"), "ceramic"),
    (("glass", "玻璃"), "glass"), (("stone", "石"), "stone"),
)
_SHAPES = (
    (("round", "圆"), "round"), (("square", "方"), "square"),
    (("tall", "高"), "tall"), (("small", "小"), "small"), (("large", "大"), "large"),
)


def objects_from_goal(goal_text: str) -> list:
    """Parse known object names from a goal text (lowercased keyword match)."""
    text = goal_text.lower()
    found = [name for keys, name in _KNOWN_OBJECTS if any(k in text for k in keys)]
    return found or ["floor"]


def _match(table, text):
    return {name for keys, name in table if any(k in text for k in keys)}


def descriptors_of(text: str) -> dict:
    """V4: parse objects/colors/materials/shapes for generative tasks."""
    t = (text or "").lower()
    objs = _match(_KNOWN_OBJECTS, t) | _match(_GEN_OBJECTS, t)
    return {
        "objects": sorted(objs),
        "colors": sorted(_match(_COLORS, t)),
        "materials": sorted(_match(_MATERIALS, t)),
        "shapes": sorted(_match(_SHAPES, t)),
    }


def keywords_of(text: str) -> set:
    """V4: flat set of all recognised descriptors (for text-3D alignment)."""
    d = descriptors_of(text)
    return set(d["objects"]) | set(d["colors"]) | set(d["materials"]) | set(d["shapes"])


if __name__ == "__main__":
    # V1 (unchanged)
    assert objects_from_goal("table and cup") == ["table", "cup"]
    assert objects_from_goal("沙发和门") == ["sofa", "door"]
    assert objects_from_goal("nothing here") == ["floor"]
    # V4 generative
    d = descriptors_of("a red wooden chair")
    assert "chair" in d["objects"] and "red" in d["colors"] and "wood" in d["materials"]
    assert keywords_of("小的金属花瓶") >= {"vase", "metal", "small"}
    print("[OK] scene_objects self-test passed (V1 + V4 vocab)")
