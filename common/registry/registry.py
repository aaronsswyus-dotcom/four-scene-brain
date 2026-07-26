"""Registry / plugin mechanism (common-contract §7, FROZEN).

- A scene package ships its own `register(registry)` function.
- The Orchestrator discovers scenes ONLY via Registry; it NEVER imports branch modules.
- Unregistered target -> KeyError.
- Routing validates `bundle.modality == state.modality` (generic string equality,
  done by the caller/orchestrator; Registry stores and resolves).

Pure stdlib. No scene knowledge.
"""

from dataclasses import dataclass
from typing import Optional

from common.interfaces.abstract import (
    WorldModel,
    Critic,
    PrimitiveLibrary,
    Mapper,
    Executor,
    SafetyGate,
)


@dataclass
class BranchBundle:
    """A scene's full implementation set, submitted once at registration."""

    target: str
    modality: str
    world_model: WorldModel
    critic: Critic
    primitives: PrimitiveLibrary
    mapper: Mapper
    executor: Executor
    safety_gate: Optional[SafetyGate] = None  # physical MUST provide


class Registry:
    """Target -> BranchBundle registration and resolution."""

    def __init__(self) -> None:
        self._bundles: dict = {}

    def register(self, bundle: BranchBundle) -> None:
        if not isinstance(bundle, BranchBundle):
            raise TypeError(f"expected BranchBundle, got {type(bundle).__name__}")
        if not bundle.target or not isinstance(bundle.target, str):
            raise ValueError("BranchBundle.target must be a non-empty string")
        if not bundle.modality or not isinstance(bundle.modality, str):
            raise ValueError("BranchBundle.modality must be a non-empty string")
        # duck-type/ABC validation: every mandatory slot must be a proper implementation
        _checks = (
            ("world_model", bundle.world_model, WorldModel),
            ("critic", bundle.critic, Critic),
            ("primitives", bundle.primitives, PrimitiveLibrary),
            ("mapper", bundle.mapper, Mapper),
            ("executor", bundle.executor, Executor),
        )
        for name, impl, iface in _checks:
            if not isinstance(impl, iface):
                raise TypeError(f"BranchBundle.{name} must implement {iface.__name__}")
        if bundle.safety_gate is not None and not isinstance(bundle.safety_gate, SafetyGate):
            raise TypeError("BranchBundle.safety_gate must implement SafetyGate or be None")
        if bundle.target in self._bundles:
            raise ValueError(f"target '{bundle.target}' already registered")
        self._bundles[bundle.target] = bundle

    def resolve(self, target: str) -> BranchBundle:
        """Unregistered target -> KeyError (contract: fail fast, no fallback)."""
        if target not in self._bundles:
            raise KeyError(
                f"target '{target}' not registered; known targets: {sorted(self._bundles)}"
            )
        return self._bundles[target]

    def targets(self) -> list:
        """Introspection helper (read-only)."""
        return sorted(self._bundles)


if __name__ == "__main__":
    # __main__ self-test with in-file mock implementations (no branch imports)
    from common.interfaces.data_objects import (
        State, SubGoal, Draft, Verification, Primitive, Executable, Delivery, SafetyVerdict,
    )

    class _WM(WorldModel):
        def predict_next_state(self, state: State, goal: SubGoal) -> State:
            return state

    class _CR(Critic):
        def verify(self, draft: Draft, goal: SubGoal) -> Verification:
            return Verification(True, 1.0, "ok")

    class _PL(PrimitiveLibrary):
        def abstract(self, draft: Draft) -> list:
            return [Primitive("noop", {}, {})]

    class _MP(Mapper):
        def map(self, primitives: list, goal: SubGoal) -> Executable:
            return Executable("m", None, {})

    class _EX(Executor):
        def execute(self, executable: Executable) -> Delivery:
            return Delivery("t", None, {})

    class _SG(SafetyGate):
        def check(self, executable: Executable) -> SafetyVerdict:
            return SafetyVerdict.PASS

    r = Registry()
    b = BranchBundle("t1", "m1", _WM(), _CR(), _PL(), _MP(), _EX(), _SG())
    r.register(b)
    assert r.resolve("t1") is b
    assert r.targets() == ["t1"]

    # unregistered -> KeyError
    try:
        r.resolve("nope")
        raise AssertionError("should raise KeyError")
    except KeyError:
        pass

    # duplicate -> ValueError
    try:
        r.register(BranchBundle("t1", "m1", _WM(), _CR(), _PL(), _MP(), _EX()))
        raise AssertionError("should raise ValueError")
    except ValueError:
        pass

    # wrong impl type -> TypeError
    try:
        r.register(BranchBundle("t2", "m1", object(), _CR(), _PL(), _MP(), _EX()))  # type: ignore[arg-type]
        raise AssertionError("should raise TypeError")
    except TypeError:
        pass

    print("[OK] registry self-test passed")
