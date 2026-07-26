"""Scene3DCritic — S9 verification for branches/3d (multi-task dispatch).

Dispatches on payload["task"] (absent -> "robot_scene", the V1 default):
  - robot_scene (V1, UNCHANGED): walkability + geometric fidelity + text-scene
    alignment. Thresholds via goal.constraints (min_fidelity, default 0.7).
  - text_to_3d / image_to_3d / pointcloud_completion / pbr_texture (V4):
    generic geometry hard-gate (manifold / vertices>0 / non-degenerate bbox;
    mesh tasks also need faces>0) + task-specific check.

HARD miss -> RETRYABLE_QUALITY (back to S7); malformed -> STRUCTURAL_INFEASIBLE.
Verification.meta.verification_source records the deciding check (incl. task).
"""

from common.interfaces.abstract import Critic
from common.interfaces.data_objects import Draft, SubGoal, Verification, FailureKind

from .scene_objects import objects_from_goal as _objects_from_goal
from .scene_objects import keywords_of as _keywords_of

DEFAULT_MIN_FIDELITY = 0.7
_GEN_TASKS = ("text_to_3d", "image_to_3d", "pointcloud_completion", "pbr_texture")


def _verify_robot_scene(p: dict, goal: SubGoal) -> Verification:
    if "representation" not in p or "semantics" not in p:
        return Verification(False, 0.0, "malformed 3d payload",
                            FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": "schema"})
    sem = p["semantics"]
    checks = {}

    # 1) walkability
    need_walk = any(k in goal.goal.lower() for k in ("walk",)) or "行走" in goal.goal or "通行" in goal.goal
    checks["walkable"] = (not need_walk) or bool(sem.get("walkable"))

    # 2) geometric fidelity
    min_fid = float(goal.constraints.get("min_fidelity", DEFAULT_MIN_FIDELITY))
    fidelity = float(p.get("fidelity", 0.0))
    checks["fidelity"] = fidelity >= min_fid

    # 3) text-scene alignment: required objects present
    required = set(_objects_from_goal(goal.goal)) - {"floor"}
    present = set(sem.get("objects", []))
    checks["alignment"] = required <= present

    passed = all(checks.values())
    score = round((0.34 * checks["walkable"] + 0.33 * checks["fidelity"]
                   + 0.33 * checks["alignment"]) * min(1.0, max(fidelity, 0.5) + 0.2), 4)
    reason = "; ".join(f"{k}={'ok' if v else 'FAIL'}" for k, v in checks.items())
    return Verification(
        passed, score, reason,
        FailureKind.NONE if passed else FailureKind.RETRYABLE_QUALITY,
        meta={"verification_source": "walkable+fidelity+alignment",
              "fidelity": fidelity, "required_objects": sorted(required)},
    )


def _geometry_gate(p: dict, task: str, need_faces: bool) -> Verification | None:
    """Shared generative hard-gate; returns a failing Verification or None."""
    geo = p.get("geometry")
    if not isinstance(geo, dict):
        return Verification(False, 0.0, "missing geometry", FailureKind.STRUCTURAL_INFEASIBLE,
                            meta={"verification_source": f"{task}:schema"})
    if not geo.get("manifold", False):
        return Verification(False, 0.3, "non-manifold geometry", FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": f"{task}:manifold"})
    if int(geo.get("vertices", 0)) <= 0:
        return Verification(False, 0.2, "no vertices", FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": f"{task}:vertices"})
    if need_faces and int(geo.get("faces", 0)) <= 0:
        return Verification(False, 0.3, "no faces (degenerate mesh)", FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": f"{task}:faces"})
    bbox = geo.get("bbox") or []
    if len(bbox) < 3 or any(float(d) <= 0 for d in bbox[:3]):
        return Verification(False, 0.3, f"degenerate bbox {bbox}", FailureKind.RETRYABLE_QUALITY,
                            meta={"verification_source": f"{task}:bbox"})
    return None


def _verify_generative(p: dict, goal: SubGoal) -> Verification:
    task = p["task"]
    need_faces = task != "pointcloud_completion"
    gate = _geometry_gate(p, task, need_faces)
    if gate is not None:
        return gate
    geo = p["geometry"]

    # task-specific
    if task == "pointcloud_completion":
        if int(geo.get("output_points", 0)) < int(geo.get("input_points", 0)):
            return Verification(False, 0.3, "completion produced fewer points than input",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": "pointcloud_completion:point-count"})
    elif task == "image_to_3d":
        if not str(geo.get("source_ref", "")).strip():
            return Verification(False, 0.3, "output not bound to any source image",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": "image_to_3d:source-binding"})
    elif task == "pbr_texture":
        tex = p.get("texture") or {}
        for ch in ("albedo", "roughness", "metallic"):
            if ch not in tex:
                return Verification(False, 0.3, f"texture missing '{ch}'",
                                    FailureKind.RETRYABLE_QUALITY,
                                    meta={"verification_source": "pbr_texture:channels"})
        vals = list(tex["albedo"]) + [tex["roughness"], tex["metallic"]]
        if any(not (0.0 <= float(v) <= 1.0) for v in vals):
            return Verification(False, 0.3, "PBR channel out of [0,1]",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": "pbr_texture:range"})

    # SOFT: text-3D semantic alignment (skip for image/pointcloud which aren't text-driven)
    overlap = 1.0
    if task in ("text_to_3d", "pbr_texture"):
        want = _keywords_of(goal.goal)
        got = set(p.get("semantics", []))
        overlap = len(want & got) / len(want) if want else 1.0
        if want and overlap == 0.0:
            return Verification(False, 0.4, "zero semantic alignment with prompt",
                                FailureKind.RETRYABLE_QUALITY,
                                meta={"verification_source": f"{task}:alignment"})

    score = round(min(1.0, 0.6 + overlap * 0.4), 4)
    return Verification(True, score, f"{task}: geometry valid + task check ok",
                        meta={"verification_source": f"{task}:ok", "overlap": round(overlap, 4)})


class Scene3DCritic(Critic):
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        p = draft.payload or {}
        if not isinstance(p, dict):
            return Verification(False, 0.0, "malformed 3d payload",
                                FailureKind.STRUCTURAL_INFEASIBLE,
                                meta={"verification_source": "schema"})
        task = p.get("task", "robot_scene")
        if task in _GEN_TASKS:
            return _verify_generative(p, goal)
        return _verify_robot_scene(p, goal)


if __name__ == "__main__":
    c = Scene3DCritic()

    # ---- robot_scene (V1, unchanged) ----
    g = SubGoal("s", "3d", "walkable living room with table and cup", "", [], {})
    good = Draft("geometry", {
        "representation": "mesh", "fidelity": 0.9,
        "semantics": {"objects": ["table", "cup"], "walkable": True},
    }, {})
    assert c.verify(good, g).passed
    low = Draft("geometry", {
        "representation": "mesh", "fidelity": 0.4,
        "semantics": {"objects": ["table", "cup"], "walkable": True},
    }, {})
    v2 = c.verify(low, g)
    assert not v2.passed and v2.failure_kind is FailureKind.RETRYABLE_QUALITY
    missing = Draft("geometry", {
        "representation": "mesh", "fidelity": 0.9,
        "semantics": {"objects": ["table"], "walkable": True},
    }, {})
    assert not c.verify(missing, g).passed  # cup missing -> alignment FAIL
    assert c.verify(Draft("geometry", {}, {}), g).failure_kind is FailureKind.STRUCTURAL_INFEASIBLE

    # ---- generative (V4) ----
    from .backbone_mock import MockThreeDBackbone
    b = MockThreeDBackbone()
    gt = SubGoal("s", "3d", "a red wooden chair", "", [], {})
    assert c.verify(Draft("geometry", b.generate("a red wooden chair", {"task": "text_to_3d"}), {}), gt).passed

    # broken text_to_3d -> RETRYABLE (no faces)
    bad = b.generate("x", {"task": "text_to_3d", "challenge": True, "retry": 0})
    vb = c.verify(Draft("geometry", bad, {}), SubGoal("s", "3d", "x", "", [], {}))
    assert not vb.passed and vb.failure_kind is FailureKind.RETRYABLE_QUALITY

    # pointcloud shrink -> fail
    badc = b.generate("y", {"task": "pointcloud_completion", "source_points": 400, "challenge": True, "retry": 0})
    assert not c.verify(Draft("geometry", badc, {}), SubGoal("s", "3d", "y", "", [], {})).passed

    # pbr out-of-range -> fail
    badt = b.generate("shiny metal helmet", {"task": "pbr_texture", "challenge": True, "retry": 0})
    assert not c.verify(Draft("geometry", badt, {}), SubGoal("s", "3d", "shiny metal helmet", "", [], {})).passed

    # good pbr passes
    okt = b.generate("shiny metal helmet", {"task": "pbr_texture"})
    assert c.verify(Draft("geometry", okt, {}), SubGoal("s", "3d", "shiny metal helmet", "", [], {})).passed
    print("[OK] 3d critic self-test passed (robot_scene V1 + 4 generative tasks)")
