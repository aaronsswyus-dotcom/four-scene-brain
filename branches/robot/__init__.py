"""branches.robot — physical robot scene plugin.

target='robot', modality='physical'. Backbone is ALL MOCK in V1
(real GR00T goes through Azure later, behind adapter.py).
Register via `branches.robot.register(registry)`.
"""

from branches.robot.adapter import register

__all__ = ["register"]
