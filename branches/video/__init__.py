"""branches.video — pixel-camp video scene plugin (V2).

target='video', modality='pixel'. Backbone is ALL MOCK in V2 (real HunyuanVideo /
Wan-2.1 go through Azure later, behind adapter.py). SafetyGate is dual-mode
(audit / passthrough). Register via `branches.video.register(registry)`.
"""

from branches.video.adapter import register

__all__ = ["register"]
