"""MockThreeDBackbone — deterministic, dependency-free full-3D generator (V4).

Covers the four generative tasks (robot_scene stays on the V1 path):
  - text_to_3d           : text -> single-asset box mesh + semantics
  - image_to_3d          : concept image ref -> box mesh bound to that source
  - pointcloud_completion: sparse cloud -> denser cloud (>= input points)
  - pbr_texture          : base mesh + PBR material (albedo/roughness/metallic)

Determinism: every field is derived from sha256(prompt|task|params) so the same
request yields byte-identical output (contract: reproducible mock).

Retry convergence (mirrors video/game): a `challenge` request is intentionally
BROKEN on retry==0 (non-manifold / faces=0 / fewer points / out-of-range
roughness) so the Critic rejects it (RETRYABLE_QUALITY); on retry>=1 the defect
is repaired and it passes. This exercises the S9->S7 loop for the physical camp.

⚠️ Placeholder geometry only — a hash-scaled box / bbox. Validates the
orchestration kernel, NOT 3D quality. Real quality = TRELLIS/DreamGaussian on Azure.

Pure stdlib. Zero third-party dependencies.
"""

import hashlib

from .backbone_interface import ThreeDBackbone, TASKS
from .scene_objects import descriptors_of

# 12-triangle unit box topology (shared by every asset mesh)
_BOX_FACES = [[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1],
              [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]]


def _seed(prompt: str, config: dict) -> int:
    key = f"{prompt}|{config.get('task')}|{config.get('source_image','')}|{config.get('poly_budget','')}"
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16)


def _bbox(seed: int) -> list:
    """Deterministic, always-positive [sx, sy, sz] in [0.3, 2.0]."""
    return [round(0.3 + (seed >> (i * 8) & 0xFF) / 255.0 * 1.7, 3) for i in range(3)]


def _box_mesh(bbox: list) -> dict:
    sx, sy, sz = [s / 2.0 for s in bbox]
    verts = [[dx * sx, dy * sy, dz * sz]
             for dx in (-1, 1) for dy in (-1, 1) for dz in (-1, 1)]
    return {"vertices": verts, "faces": [list(f) for f in _BOX_FACES]}


class MockThreeDBackbone(ThreeDBackbone):
    def get_info(self) -> dict:
        return {
            "name": "MockThreeDBackbone",
            "version": "0.4.0",
            "license": "internal-mock",
            "capabilities": list(TASKS),
            "note": "placeholder box/bbox geometry; real: TRELLIS/DreamGaussian on Azure",
        }

    def generate(self, prompt: str, config: dict) -> dict:
        task = config.get("task")
        if task not in TASKS:
            raise ValueError(f"unknown/unsupported 3d task '{task}' (expected {TASKS})")
        retry = int(config.get("retry", 0))
        challenge = bool(config.get("challenge", False))
        broken = challenge and retry == 0
        seed = _seed(prompt, config)
        bbox = _bbox(seed)
        mesh = _box_mesh(bbox)
        desc = descriptors_of(prompt)
        semantics = desc["objects"] + desc["colors"] + desc["materials"] + desc["shapes"]

        base = {
            "task": task,
            "representation": "mesh",
            "text_prompt": prompt,
            "semantics": semantics or ["object"],
            "texture": None,
            "mesh": mesh,
            "scene_description": f"{task}: {' '.join(semantics) or 'generic asset'}",
            "refined_times": retry,
            "meta": {"backbone": "mock", "seed": seed % 10_000_000, "poly_budget": config.get("poly_budget")},
        }

        if task == "text_to_3d":
            base["source"] = prompt
            base["geometry"] = _geo(mesh, bbox, broken)

        elif task == "image_to_3d":
            src = config.get("source_image", "concept.png")
            base["source"] = src
            base["geometry"] = _geo(mesh, bbox, broken)
            base["geometry"]["source_ref"] = src  # bound to input image

        elif task == "pointcloud_completion":
            n_in = int(config.get("source_points", 500))
            factor = 0 if broken else (2 + retry)   # broken -> shrinks below input
            n_out = max(1, n_in // 2) if broken else n_in * factor
            base["representation"] = "pointcloud"
            base["source"] = f"pointcloud[{n_in}]"
            base["geometry"] = _geo(mesh, bbox, broken)
            base["geometry"].update({"faces": 0, "input_points": n_in, "output_points": n_out})

        elif task == "pbr_texture":
            base["source"] = prompt
            base["geometry"] = _geo(mesh, bbox, broken=False)  # geometry fine; defect is in texture
            rough = 1.5 if broken else round(0.2 + (seed >> 16 & 0xFF) / 255.0 * 0.6, 3)
            base["texture"] = {
                "albedo": [round((seed >> (i * 4) & 0xF) / 15.0, 3) for i in range(3)],
                "roughness": rough,
                "metallic": round((seed >> 24 & 0xFF) / 255.0, 3),
            }
        return base


def _geo(mesh: dict, bbox: list, broken: bool) -> dict:
    return {
        "vertices": len(mesh["vertices"]),
        "faces": 0 if broken else len(mesh["faces"]),
        "manifold": not broken,
        "bbox": bbox,
    }


if __name__ == "__main__":
    b = MockThreeDBackbone()
    info = b.get_info()
    assert set(info) >= {"name", "version", "license", "capabilities"}

    # determinism
    o1 = b.generate("a red wooden chair", {"task": "text_to_3d"})
    o2 = b.generate("a red wooden chair", {"task": "text_to_3d"})
    assert o1 == o2 and o1["geometry"]["manifold"] and o1["geometry"]["faces"] == 12
    assert "chair" in o1["semantics"]

    # image_to_3d binds source
    oi = b.generate("a chair", {"task": "image_to_3d", "source_image": "chair.png"})
    assert oi["geometry"]["source_ref"] == "chair.png"

    # pointcloud completion grows point count
    oc = b.generate("complete the cloud", {"task": "pointcloud_completion", "source_points": 400})
    assert oc["geometry"]["output_points"] >= oc["geometry"]["input_points"]

    # pbr in range
    op = b.generate("shiny metal helmet", {"task": "pbr_texture"})
    assert 0.0 <= op["texture"]["roughness"] <= 1.0

    # challenge broken on retry0, repaired on retry1
    bad = b.generate("x", {"task": "text_to_3d", "challenge": True, "retry": 0})
    good = b.generate("x", {"task": "text_to_3d", "challenge": True, "retry": 1})
    assert bad["geometry"]["faces"] == 0 and not bad["geometry"]["manifold"]
    assert good["geometry"]["faces"] == 12 and good["geometry"]["manifold"]

    badc = b.generate("y", {"task": "pointcloud_completion", "source_points": 400, "challenge": True, "retry": 0})
    assert badc["geometry"]["output_points"] < badc["geometry"]["input_points"]

    badt = b.generate("z", {"task": "pbr_texture", "challenge": True, "retry": 0})
    assert badt["texture"]["roughness"] > 1.0

    try:
        b.generate("q", {"task": "robot_scene"})
        raise AssertionError("robot_scene must not go through backbone")
    except ValueError:
        pass
    print("[OK] 3d backbone_mock self-test passed (4 tasks + determinism + retry repair)")
