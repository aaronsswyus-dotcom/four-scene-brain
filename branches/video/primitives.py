"""VideoPrimitiveLibrary — S10 primitive abstraction for video.

Video primitives (editing/compositing units):
    cut      — hard scene change
    fade     — fade in/out transition
    overlay  — composite a subject over a scene
    zoom     — camera zoom move

The sequence is derived from the backbone's scene_description + camera_motion.
Because the frozen Mapper.map(primitives, goal) signature does NOT receive the
draft/payload, the full video spec (duration/fps/resolution/text_prompt/
scene_description) is stashed in EVERY primitive's meta under 'video_spec'. The
orchestrator's degraded re-map copies primitive meta, so the spec survives the
SafetyGate DEGRADE path.

Pure stdlib. Zero third-party dependencies.
"""

from common.interfaces.abstract import PrimitiveLibrary
from common.interfaces.data_objects import Draft, Primitive

_SPEC_KEYS = ("duration_s", "fps", "resolution", "text_prompt",
              "scene_description", "camera_motion", "frame_count")


def _spec_from_payload(p: dict) -> dict:
    return {k: p.get(k) for k in _SPEC_KEYS}


class VideoPrimitiveLibrary(PrimitiveLibrary):
    def abstract(self, draft: Draft) -> list:
        p = draft.payload or {}
        spec = _spec_from_payload(p)
        subgoal_id = (draft.meta or {}).get("subgoal_id")
        camera = str(p.get("camera_motion", "static"))

        # base editing sequence: always open with a cut, close with a fade;
        # multi-part scene_description ('a+b in c') adds an overlay; camera zoom
        # contributes a zoom primitive.
        seq = ["cut"]
        desc = str(p.get("scene_description", ""))
        if "+" in desc or " in " in desc:
            seq.append("overlay")
        if camera == "zoom":
            seq.append("zoom")
        seq.append("fade")

        prims = []
        for i, kind in enumerate(seq):
            params = {"order": i, "camera_motion": camera}
            if kind == "zoom":
                params["zoom_factor"] = 1.5
            if kind == "fade":
                params["fade_ms"] = 300
            prims.append(Primitive(
                kind=kind,
                params=params,
                meta={"subgoal_id": subgoal_id, "video_spec": spec},
            ))
        return prims


if __name__ == "__main__":
    lib = VideoPrimitiveLibrary()
    d = Draft("pixel", {
        "duration_s": 5.0, "fps": 24, "resolution": [640, 480],
        "text_prompt": "a cat running on the grass, zoom in",
        "scene_description": "cat run in grass", "camera_motion": "zoom",
        "frame_count": 120,
    }, {"subgoal_id": "sg-1"})
    prims = lib.abstract(d)
    kinds = [p.kind for p in prims]
    assert kinds == ["cut", "overlay", "zoom", "fade"], kinds
    # spec is carried in every primitive's meta (for the signature-limited Mapper)
    assert all(p.meta["video_spec"]["duration_s"] == 5.0 for p in prims)
    assert all(p.meta["subgoal_id"] == "sg-1" for p in prims)
    assert prims[2].params["zoom_factor"] == 1.5

    # no zoom / no composite marker -> minimal sequence
    d2 = Draft("pixel", {"duration_s": 2.0, "fps": 24, "resolution": [640, 480],
                         "scene_description": "single shot", "camera_motion": "static"},
               {"subgoal_id": "sg-2"})
    assert [p.kind for p in lib.abstract(d2)] == ["cut", "fade"]

    # composite scene ('... in ...') adds overlay even without zoom
    d3 = Draft("pixel", {"duration_s": 2.0, "fps": 24, "resolution": [640, 480],
                         "scene_description": "cat run in grass", "camera_motion": "static"},
               {"subgoal_id": "sg-3"})
    assert [p.kind for p in lib.abstract(d3)] == ["cut", "overlay", "fade"]
    print("[OK] video primitives self-test passed")
