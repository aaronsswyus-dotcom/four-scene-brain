# Contributing to four-scene-brain

Thanks for your interest! This project's defining rule is the **frozen common kernel** — new scenes plug in WITHOUT touching `common/`. This guide tells you how.

## TL;DR — adding a new scene (V2/V3/V4 style)

1. Read [`docs/common-contract.md`](docs/common-contract.md) end-to-end. It is the **only authoritative contract** and is FROZEN.
2. Copy an existing branch (e.g. `branches/robot/`) as a template → `branches/<your_scene>/`.
3. Pick your `target` (free string, e.g. `video`) and `modality` (e.g. `pixel`).
4. Implement the 5+1 interfaces: `WorldModel` / `Critic` / `PrimitiveLibrary` / `Mapper` / `Executor` / `SafetyGate` (physical & content-sensitive scenes MUST).
5. Define your `State.payload` structure and `success_criteria` — document them in your branch's `README.md`, NOT in common.
6. Backbone default = mock. Real backbone goes in `adapter.py` ONLY, behind the T1–T5 gates in [`docs/engineering-setup.md`](docs/engineering-setup.md) §2.
7. Ship a `register(registry)` function in `adapter.py`.
8. Write `examples/<your_scene>_demo.py` — a minimal S1–S14 closed loop.
9. Run the freeze acceptance: **`common/` git diff must be empty** after adding your scene (see `tests/test_zero_diff.py`).
10. If you think you MUST modify `common/` → STOP. Re-read [`docs/common-contract.md`](docs/common-contract.md) §11 (freeze discipline). If `payload`/`meta`/a new implementation can't solve it, open an issue first — do NOT silently change common.

## The 3 Iron Laws (do not break)

1. **Write-once-forever**: `common/` is frozen after merge. New scenes only add `branches/<scene>/`.
2. **Scenes-as-plugins**: no scene/backbone names, no modality if/else in common. All differences ride opaque `payload` + extensible `meta`.
3. **Single exchange language**: common ↔ branches exchange ONLY the objects/signatures in [`docs/common-contract.md`](docs/common-contract.md) §4/§5.

## Development setup

```bash
# Python 3.13+ required (managed runtime recommended)
# common/ is pure stdlib — zero third-party runtime deps

# Optional: pytest for the test suite
pip install pytest
python -m pytest tests/ -v          # 23 tests
python -m tests.test_contract       # contract: interfaces/fields/enums immutable
python -m tests.test_zero_diff      # zero-diff: mock5 plug-in, common untouched
```

## Branch layout template

```
branches/<your_scene>/
├── __init__.py          # exports register()
├── README.md            # payload structure, success criteria, safety notes
├── adapter.py           # anti-corruption layer + register(registry); backbone switch
├── wam.py               # WorldModel impl (or another name)
├── critic.py            # Critic impl
├── primitives.py        # PrimitiveLibrary impl
├── mapper.py            # Mapper impl
├── executor.py          # Executor impl (deliver the artifact)
└── safety_gate.py       # SafetyGate impl (physical/content scenes MUST)
```

## Open-source integration rules (E1–E6)

When wiring a real backbone (e.g. HunyuanVideo, GameGen-O):

- Backbones live ONLY inside `branches/<scene>/adapter.py` (anti-corruption layer).
- Adapters translate everything to/from the common interface contract.
- The orchestration loop stays with `common/orchestrator` — backbones NEVER call back into common.
- Pass `docs/engineering-setup.md` §2 T1–T5 gates BEFORE integration: license → health → isolated install → official quickstart → interface probe.

## Pull request checklist

- [ ] `python -m pytest tests/` all green
- [ ] `python -m tests.test_zero_diff` passes (common git diff empty)
- [ ] Your branch has its own `README.md` documenting payload structure
- [ ] `examples/<your_scene>_demo.py` runs end-to-end (S1–S14)
- [ ] One S9 failure → retry path is demonstrated
- [ ] Telemetry carries `trace_id`
- [ ] Boundary declaration: "mock verifies orchestration, not real-world feasibility"

## Reporting issues

- Bugs in `common/` → label `common` (treat as freeze-affecting; needs version bump review).
- Bugs in a branch → label with the branch name (e.g. `robot`, `3d`).
- New scene proposal → label `proposal`; describe target/modality/backbone candidate.

## License

By contributing, you agree your contributions are licensed under Apache-2.0 (see [LICENSE](LICENSE)).
