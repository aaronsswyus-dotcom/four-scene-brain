"""3d adapter — anti-corruption layer + registration (contract §13, E1-E6).

V1 scope: robot-job-scene ONLY (full 3D belongs to V4; common unchanged then).
Backbone default MOCK; real DreamGaussian/TRELLIS via Azure later, wired ONLY
here after T1-T5 gates.

Import note: package dir is 'branches/3d' (digit prefix). Load this module via
    importlib.import_module('branches.3d.adapter')
Intra-package imports below are RELATIVE, which works fine.
"""

from common.registry.registry import Registry, BranchBundle

from .wam import Scene3DWAM
from .critic import Scene3DCritic
from .primitives import Scene3DPrimitiveLibrary
from .mapper import Scene3DMapper
from .exporter import Scene3DExporter
from .safety_gate import Scene3DSafetyGate

TARGET = "3d"
MODALITY = "geometry"


def build_bundle(backbone: str = "mock", output_dir: str = "output/3d") -> BranchBundle:
    """backbone: 'mock' (V1) | 'dreamgaussian-azure' (future, T1-T5 gated)."""
    if backbone != "mock":
        raise NotImplementedError(
            f"backbone '{backbone}' not integrated yet; V1 is mock-only")
    return BranchBundle(
        target=TARGET,
        modality=MODALITY,
        world_model=Scene3DWAM(),
        critic=Scene3DCritic(),
        primitives=Scene3DPrimitiveLibrary(),
        mapper=Scene3DMapper(),
        executor=Scene3DExporter(output_dir),
        safety_gate=Scene3DSafetyGate(),
    )


def register(registry: Registry, backbone: str = "mock", output_dir: str = "output/3d") -> None:
    registry.register(build_bundle(backbone, output_dir))


if __name__ == "__main__":
    r = Registry()
    register(r)
    b = r.resolve(TARGET)
    assert b.modality == MODALITY and b.safety_gate is not None
    try:
        build_bundle("dreamgaussian-azure")
        raise AssertionError("non-mock backbone should raise")
    except NotImplementedError:
        pass
    print("[OK] 3d adapter/registration self-test passed")
