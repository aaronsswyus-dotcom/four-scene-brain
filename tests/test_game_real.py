"""Real backbone integration tests for the game branch (MarioGPT, Phase 4).

DEFAULT-SKIP: these tests pull distilgpt2 (~82M) and run actual neural-network
inference on CPU (~30-90s per generate() call). They are skipped unless the
env var FOURSCENE_REAL_TESTS=1 is set, so the default CI / mock test run stays
fast and dependency-free.

To run locally:
    pip install mario-gpt
    FOURSCENE_REAL_TESTS=1 python -m pytest tests/test_game_real.py -v

To run on GitHub Actions:
    The .github/workflows/phase4-tests.yml 'game-real-mariogpt' job sets
    FOURSCENE_REAL_TESTS=1 and installs mario-gpt on every push to main +
    on workflow_dispatch.

Red lines (per docs/model-integration-runbook.md §6):
    - Real backbone only lives in branches/game/ (never common/).
    - Common stays at zero diff (test_zero_diff.py guards this).
    - Credentials never enter the repo (MarioGPT needs no credentials).
    - These tests never block the mock CI (default skip).
"""

import os
import unittest

from branches.game.backbone_mariogpt import MarioGPTBackbone
from branches.game.critic import GameCritic
from branches.game.safety_gate import GameSafetyGate
from common.interfaces.data_objects import Draft, SubGoal


@unittest.skipUnless(os.getenv("FOURSCENE_REAL_TESTS") == "1",
                     "real backbone tests disabled; set FOURSCENE_REAL_TESTS=1 "
                     "and `pip install mario-gpt` to enable")
class TestMarioGPTRealBackbone(unittest.TestCase):
    """Phase 4 real integration: MarioGPT (distilgpt2, CPU, MIT)."""

    @classmethod
    def setUpClass(cls):
        # one shared backbone instance; distilgpt2 weights load on first generate()
        cls.backbone = MarioGPTBackbone()
        cls.info = cls.backbone.get_info()

    def test_1_generate_schema(self):
        """generate() returns a dict matching MockGameBackbone's level schema.

        GameCritic._verify_level requires: level_map / width / height / entities
        / theme / text_prompt. We assert all are present and self-consistent.
        """
        out = self.backbone.generate(
            "草地关卡 3 金币 终点旗帜",
            {"direction": "level", "width": 16, "height": 10, "n_coins": 3, "seed": 42},
        )
        self.assertEqual(out["direction"], "level")
        self.assertIsInstance(out["level_map"], list)
        self.assertEqual(len(out["level_map"]), 10, "row count must equal height")
        self.assertEqual(out["width"], 16)
        self.assertEqual(out["height"], 10)
        self.assertIsInstance(out["entities"], list)
        self.assertIn("theme", out)
        self.assertEqual(out["text_prompt"], "草地关卡 3 金币 终点旗帜")
        self.assertIn("meta", out)
        self.assertEqual(out["meta"]["backbone"], "mariogpt")
        # each row must be a string of length == width
        for row in out["level_map"]:
            self.assertIsInstance(row, str)
            self.assertEqual(len(row), 16, f"row width mismatch: {row!r}")
        # anti-corruption layer guarantees 1 PLAYER + 1 GOAL
        types = [e["type"] for e in out["entities"]]
        self.assertEqual(types.count("P"), 1, "exactly one PLAYER required")
        self.assertEqual(types.count("G"), 1, "exactly one GOAL required")

    def test_2_determinism_seed(self):
        """Same seed + same prompt -> same level_map.

        MarioGPT sampling randomness is controlled by torch.manual_seed. With
        a fixed seed and identical inputs, output must be bit-identical. We use
        a moderate temperature (0.8) to keep generation stable but non-degenerate.
        """
        cfg = {"direction": "level", "width": 14, "height": 8, "seed": 7,
               "temperature": 0.8}
        out1 = self.backbone.generate("pipes and enemies", cfg)
        out2 = self.backbone.generate("pipes and enemies", cfg)
        self.assertEqual(out1["level_map"], out2["level_map"],
                         "same seed must produce identical level_map")

    def test_3_critic_integration(self):
        """Real MarioGPT output feeds GameCritic; the pipeline must produce a
        Verification object (we do NOT assert pass/fail score, only that the
        flow completes and returns a structured verdict).

        The anti-corruption layer in backbone_mariogpt.py forces 1P/1G, closed
        borders, and a carved floor corridor -> BFS reachability should hold ->
        Critic should PASS. But we only assert the verdict is well-formed, so
        this test does not break if a future MarioGPT version emits an unusual
        level that triggers RETRYABLE_QUALITY.
        """
        from common.interfaces.data_objects import Verification, FailureKind

        out = self.backbone.generate(
            "草地关卡",
            {"direction": "level", "width": 16, "height": 10, "seed": 99},
        )
        critic = GameCritic()
        draft = Draft(modality="pixel", payload=out, meta={"trace_id": "test-real"})
        goal = SubGoal(
            subgoal_id="sg-real-1", target="game",
            goal="草地关卡", summary="", predecessors=[],
            constraints={"direction": "level", "n_coins": 3},
        )
        verdict = critic.verify(draft, goal)
        self.assertIsInstance(verdict, Verification)
        self.assertIsInstance(verdict.passed, bool)
        self.assertIsInstance(verdict.score, float)
        self.assertIn("verification_source", verdict.meta)
        # if it failed, the failure_kind must be a known enum value
        if not verdict.passed:
            self.assertIn(verdict.failure_kind, list(FailureKind))

    def test_4_safety_gate(self):
        """SafetyGate must BLOCK on gore prompts and PASS on normal prompts,
        regardless of which backbone produced the payload. The text_prompt
        field is what the gate inspects, and MarioGPT echoes it verbatim.
        """
        gate = GameSafetyGate(mode="audit")

        # BLOCK: gore keyword in text_prompt
        out_bad = self.backbone.generate(
            "gore massacre level",
            {"direction": "level", "width": 16, "height": 10, "seed": 1},
        )
        from common.interfaces.data_objects import Executable, SafetyVerdict
        exe_bad = Executable(modality="pixel", payload=out_bad,
                             meta={"trace_id": "test-real"})
        self.assertIs(gate.check(exe_bad), SafetyVerdict.BLOCK,
                      "gore prompt must BLOCK even from real backbone")

        # PASS: normal prompt + in-range size
        out_ok = self.backbone.generate(
            "草地关卡 3 金币 终点旗帜",
            {"direction": "level", "width": 16, "height": 10, "seed": 2},
        )
        exe_ok = Executable(modality="pixel", payload=out_ok,
                            meta={"trace_id": "test-real"})
        self.assertIs(gate.check(exe_ok), SafetyVerdict.PASS,
                      "normal prompt with in-range size must PASS")

    def test_5_worldmodel_raises(self):
        """MarioGPT is level-only; asking for worldmodel must raise
        NotImplementedError (not silently produce wrong-shaped output)."""
        with self.assertRaises(NotImplementedError):
            self.backbone.generate("x", {"direction": "worldmodel"})

    def test_6_get_info_contract(self):
        """get_info() must report status='real' and MIT license (T1 gate evidence)."""
        self.assertEqual(self.info["status"], "real")
        self.assertEqual(self.info["name"], "mariogpt")
        self.assertTrue(self.info["license"].startswith("MIT"),
                        f"T1 license gate: expected MIT, got {self.info['license']!r}")
        self.assertEqual(self.info["directions"], ["level"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
