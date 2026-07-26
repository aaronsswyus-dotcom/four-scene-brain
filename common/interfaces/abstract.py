"""Abstract interfaces — The Membrane (common-contract §5, FROZEN, signatures immutable).

Scenes IMPLEMENT these; common only CALLS these. Signatures must not change.

S8 note (D6): generation has NO separate interface. WorldModel.predict_next_state
returns a candidate State; the Orchestrator wraps it into a Draft generically.
Scene-internal "regeneration" (diffusion decode, trajectory refinement) happens
inside S7 or S11.

Pure stdlib. Zero third-party dependencies.
"""

from abc import ABC, abstractmethod

from common.interfaces.data_objects import (
    State,
    SubGoal,
    Draft,
    Verification,
    Primitive,
    Executable,
    Delivery,
    Telemetry,
    SafetyVerdict,
)


class WorldModel(ABC):
    """S7 world imagination -> candidate State (imagination/generation inside)."""

    @abstractmethod
    def predict_next_state(self, state: State, goal: SubGoal) -> State:
        ...


class Critic(ABC):
    """S9 autonomous verification."""

    @abstractmethod
    def verify(self, draft: Draft, goal: SubGoal) -> Verification:
        ...


class PrimitiveLibrary(ABC):
    """S10 primitive abstraction."""

    @abstractmethod
    def abstract(self, draft: Draft) -> list:
        """Returns list[Primitive]."""
        ...


class Mapper(ABC):
    """S11 mapping -> executable."""

    @abstractmethod
    def map(self, primitives: list, goal: SubGoal) -> Executable:
        """primitives: list[Primitive]."""
        ...


class Executor(ABC):
    """S12 execution -> delivery."""

    @abstractmethod
    def execute(self, executable: Executable) -> Delivery:
        ...


class SafetyGate(ABC):
    """Between S11 and S12; physical MUST implement, others may pass-through."""

    @abstractmethod
    def check(self, executable: Executable) -> SafetyVerdict:
        ...


class Memory(ABC):
    """S6 memory read/write."""

    @abstractmethod
    def read(self, query: str, top_k: int = 5) -> list:
        """Returns list[dict]."""
        ...

    @abstractmethod
    def write(self, item: dict) -> None:
        ...


class Flywheel(ABC):
    """S13 recycle + S14 self-improve."""

    @abstractmethod
    def record(self, telemetry: Telemetry) -> None:
        """S13: unified telemetry intake."""
        ...

    @abstractmethod
    def distill(self) -> None:
        """S14: local buffer/flush; cloud feedback loop implements same interface."""
        ...


if __name__ == "__main__":
    # __main__ self-test: abstract classes must NOT be directly instantiable
    import inspect

    abcs = [WorldModel, Critic, PrimitiveLibrary, Mapper, Executor, SafetyGate, Memory, Flywheel]
    for cls in abcs:
        try:
            cls()  # type: ignore[abstract]
            raise AssertionError(f"{cls.__name__} should not be instantiable")
        except TypeError:
            pass

    # signature spot-checks (frozen membrane)
    assert list(inspect.signature(WorldModel.predict_next_state).parameters) == ["self", "state", "goal"]
    assert list(inspect.signature(Critic.verify).parameters) == ["self", "draft", "goal"]
    assert list(inspect.signature(PrimitiveLibrary.abstract).parameters) == ["self", "draft"]
    assert list(inspect.signature(Mapper.map).parameters) == ["self", "primitives", "goal"]
    assert list(inspect.signature(Executor.execute).parameters) == ["self", "executable"]
    assert list(inspect.signature(SafetyGate.check).parameters) == ["self", "executable"]
    assert list(inspect.signature(Memory.read).parameters) == ["self", "query", "top_k"]
    assert inspect.signature(Memory.read).parameters["top_k"].default == 5
    assert list(inspect.signature(Flywheel.record).parameters) == ["self", "telemetry"]
    assert list(inspect.signature(Flywheel.distill).parameters) == ["self"]

    # a minimal concrete impl must be instantiable
    class _WM(WorldModel):
        def predict_next_state(self, state: State, goal: SubGoal) -> State:
            return state

    s = State(modality="physical", payload=None, meta={})
    g = SubGoal(id="x", target="robot", goal="", success_criteria="", depends_on=[], constraints={})
    assert _WM().predict_next_state(s, g) is s
    print("[OK] abstract interfaces self-test passed:", len(abcs), "interfaces")
