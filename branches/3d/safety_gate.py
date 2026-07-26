"""Scene3DSafetyGate — content-compliance gate for 3d (DUAL MODE, V4).

Separation of concerns: the Critic judges GEOMETRY/TASK quality; this gate
judges CONTENT COMPLIANCE + resource sanity.

Modes (configurable in adapter.build_bundle):
  - "audit" (default):
      * text_prompt contains NSFW / copyrighted-character keyword  -> BLOCK
        (hard; degraded re-map cannot fix it -> stays BLOCK)
      * mesh spec absurdly large (> MAX_VERTICES)                    -> BLOCK
        (mock resource guard, kept from V1)
      * geometry vertex count below floor / bbox degenerate          -> DEGRADE
        (degraded re-map clamps up to safe floor -> re-check PASSES)
      * otherwise                                                    -> PASS
  - "passthrough":
      * no checks                                                    -> PASS

check() reads only Executable.payload (never the raw prompt), so the Mapper puts
text_prompt / total_vertices / geometry there. Keyword list is CONSERVATIVE
("rather miss than false-block": "骷髅摆件/skeleton figurine" is a normal 3D
subject and is NOT blocked).

V1 compatibility: Scene3DSafetyGate() defaults to audit mode and keeps the
total_vertices BLOCK, so the V1 pass-through-with-sanity-bound behaviour holds.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import SafetyGate
from common.interfaces.data_objects import Executable, SafetyVerdict

MAX_VERTICES = 1_000_000
MIN_VERTICES = 8

# Conservative: only unambiguous non-compliant subjects. Normal skulls/monsters ok.
_BLOCK = ("nsfw", "裸露", "explicit", "porn", "gore", "血腥",
          "mickey mouse", "米老鼠", "copyrighted character", "版权角色")


class Scene3DSafetyGate(SafetyGate):
    def __init__(self, mode: str = "audit") -> None:
        if mode not in ("audit", "passthrough"):
            raise ValueError(f"unknown safety mode '{mode}' (expected audit|passthrough)")
        self.mode = mode

    def check(self, executable: Executable) -> SafetyVerdict:
        if self.mode == "passthrough":
            return SafetyVerdict.PASS

        p = executable.payload or {}

        # content compliance (only when a prompt is present, i.e. generative tasks)
        text = str(p.get("text_prompt", "")).lower()
        for term in _BLOCK:
            if term in text:
                return SafetyVerdict.BLOCK

        # resource guard (V1 behaviour, kept)
        if int(p.get("total_vertices", 0)) > MAX_VERTICES:
            return SafetyVerdict.BLOCK

        # geometry sanity -> degradable (only for generative payloads carrying geometry)
        geo = p.get("geometry")
        if isinstance(geo, dict):
            bbox = geo.get("bbox") or []
            degenerate_bbox = len(bbox) >= 3 and any(float(d) <= 0 for d in bbox[:3])
            if int(geo.get("vertices", 0)) < MIN_VERTICES or degenerate_bbox:
                return SafetyVerdict.DEGRADE

        return SafetyVerdict.PASS


if __name__ == "__main__":
    g = Scene3DSafetyGate()  # default audit

    # V1 behaviour preserved
    assert g.check(Executable("geometry", {"total_vertices": 100}, {})) is SafetyVerdict.PASS
    assert g.check(Executable("geometry", {"total_vertices": 2_000_000}, {})) is SafetyVerdict.BLOCK

    # V4 content BLOCK
    blk = Executable("geometry", {"task": "text_to_3d", "text_prompt": "a nsfw statue",
                                  "total_vertices": 8, "geometry": {"vertices": 8, "bbox": [1, 1, 1]}}, {})
    assert g.check(blk) is SafetyVerdict.BLOCK

    # V4 geometry DEGRADE
    deg = Executable("geometry", {"task": "text_to_3d", "text_prompt": "a chair",
                                  "total_vertices": 0, "geometry": {"vertices": 0, "bbox": [1, 1, 1]}}, {})
    assert g.check(deg) is SafetyVerdict.DEGRADE

    # normal generative asset PASS
    ok = Executable("geometry", {"task": "text_to_3d", "text_prompt": "a red chair",
                                 "total_vertices": 8, "geometry": {"vertices": 8, "bbox": [1, 1, 1]}}, {})
    assert g.check(ok) is SafetyVerdict.PASS

    # skull figurine is NOT blocked (conservative list)
    skull = Executable("geometry", {"task": "text_to_3d", "text_prompt": "a skeleton figurine 骷髅摆件",
                                    "total_vertices": 8, "geometry": {"vertices": 8, "bbox": [1, 1, 1]}}, {})
    assert g.check(skull) is SafetyVerdict.PASS

    # passthrough
    assert Scene3DSafetyGate("passthrough").check(blk) is SafetyVerdict.PASS
    try:
        Scene3DSafetyGate("bogus")
        raise AssertionError("bad mode should raise")
    except ValueError:
        pass
    print("[OK] 3d safety_gate self-test passed (V1 guard + audit/passthrough)")
