"""common.interfaces — The Language + The Membrane (FROZEN).

Re-exports all data objects (contract §4) and abstract interfaces (§5).
This is the ONLY exchange language between common and branches.
"""

from common.interfaces.data_objects import (
    State,
    SubGoal,
    Intent,
    Draft,
    FailureKind,
    Verification,
    Primitive,
    Executable,
    Delivery,
    Telemetry,
    RunMetrics,
    SafetyVerdict,
)
from common.interfaces.abstract import (
    WorldModel,
    Critic,
    PrimitiveLibrary,
    Mapper,
    Executor,
    SafetyGate,
    Memory,
    Flywheel,
)

__all__ = [
    # data objects (§4)
    "State",
    "SubGoal",
    "Intent",
    "Draft",
    "FailureKind",
    "Verification",
    "Primitive",
    "Executable",
    "Delivery",
    "Telemetry",
    "RunMetrics",
    "SafetyVerdict",
    # abstract interfaces (§5)
    "WorldModel",
    "Critic",
    "PrimitiveLibrary",
    "Mapper",
    "Executor",
    "SafetyGate",
    "Memory",
    "Flywheel",
]
