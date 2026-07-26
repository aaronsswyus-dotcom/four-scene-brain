"""branches._physical — physical-camp shared layer (scene-side, NOT in common).

robot and V1-3d share the WAM physical prior via PhysicalWorldModelBase.
Imagination layer is shared; execution layers are NOT (torque vs mesh).
"""

from branches._physical.base import PhysicalWorldModelBase, MockWAMPrior

__all__ = ["PhysicalWorldModelBase", "MockWAMPrior"]
