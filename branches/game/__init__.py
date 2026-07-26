"""branches.game — pixel-camp game scene plugin (V3, dual-direction).

target='game', modality='pixel'. Backbone is ALL MOCK in V3 (real MarioGPT /
GameGen-O / OASIS go through Azure later, behind adapter.py). SafetyGate is
dual-mode (audit / passthrough). Register via `branches.game.register(registry)`.
"""

from branches.game.adapter import register, build_bundle

__all__ = ["register", "build_bundle"]
