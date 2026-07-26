"""branches/3d scene object vocabulary — shared by WAM and Critic.

Extracted so Critic's required-object check does NOT depend on the WAM
implementation (which will be swapped for a real backbone behind the adapter).
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


def objects_from_goal(goal_text: str) -> list:
    """Parse known object names from a goal text (lowercased keyword match)."""
    text = goal_text.lower()
    found = [name for keys, name in _KNOWN_OBJECTS if any(k in text for k in keys)]
    return found or ["floor"]


if __name__ == "__main__":
    assert objects_from_goal("table and cup") == ["table", "cup"]
    assert objects_from_goal("沙发和门") == ["sofa", "door"]
    assert objects_from_goal("nothing here") == ["floor"]
    print("[OK] scene_objects self-test passed")
