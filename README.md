# four-scene-brain

[English](#english) ｜ [中文](#中文)

---

<a id="english"></a>

## English

A **modality-agnostic orchestration core** that routes language or machine-state inputs to robot / game / 3d / video branches, validates outputs with critics, and feeds telemetry into a data flywheel.

**Scope**: common orchestration backbone + stable interface contracts + cross-branch telemetry flywheel. Scene capabilities are integrated as branch plugins via adapters (no backbone hard-coding in core).

### Current Status — V1 Delivered

| Version | Combination | Status |
|---|---|---|
| **V1** | common + robot + 3d (robot job scene) | ✅ **This repo** |
| V2 | + video | Planned |
| V3 | + game | Planned |
| V4 | + complete standalone 3D | Planned |
| V5 | Full integration + cross-branch flywheel | Planned |

**Boundary statement**: V1 validates the orchestration kernel, interface contracts, and flywheel flow — NOT real-world physical feasibility. All backbones are mock (real GR00T / DreamGaussian go through Azure later, behind T1–T5 gates in `docs/engineering-setup.md`).

### Highlights

- **Frozen core**: `common/` is written once, never modified for new scenes.
- **Plugin architecture**: new scenes only add `branches/<scene>/`, common stays untouched (verified by zero-diff acceptance test).
- **Unified exchange contract**: strict data objects + abstract interfaces (see `docs/common-contract.md`).
- **Observable loop**: every run emits trace_id-tagged Telemetry → local flywheel buffer.

### Quick Start (Python 3.13, zero third-party runtime deps)

```bash
# robot minimal loop: DAG (grasp→move→place) + S9 retry + SafetyGate BLOCK/DEGRADE
python -m examples.robot_demo

# 3d minimal loop: robot-workspace living room → placeholder GLB + cross-branch DAG
python -m examples.3d_scene_demo

# Freeze acceptance
python -m tests.test_contract     # reflection contract test: interfaces/fields/enums immutable
python -m tests.test_zero_diff    # zero-diff: plug in mock5 scene, common git diff stays empty

# Full test suite (optional, requires pytest)
pip install pytest
python -m pytest tests/ -v         # 23 tests, ~0.5s
```

### Three Iron Laws

1. **Write-once-forever**: after `common/` is merged, new scenes only add `branches/<scene>/`.
2. **Scenes-as-plugins**: no scene/backbone names, no modality if/else in common — differences ride opaque `payload` + extensible `meta`.
3. **Single exchange language**: common ↔ branches exchange ONLY the objects/signatures defined in `docs/common-contract.md` §4/§5.

### Structure

```
common/               # frozen kernel (pure stdlib, v1.0.0)
├── interfaces/       #   data objects + 8 abstract interfaces
├── orchestrator/     #   S1–S14 state machine (DAG/retry/SafetyGate/exception mapping)
├── registry/         #   BranchBundle plugin register/resolve
├── memory/           #   InMemoryMemory (default S6)
└── flywheel/         #   FileBufferFlywheel (S13/S14, local buffer only)
branches/
├── _physical/        #   physical-camp shared WAM prior base (scene-side)
├── robot/            #   V1 ✅ robot branch (mock, zero-torque executor)
├── 3d/               #   V1 ✅ robot-job-scene (placeholder GLB export)
├── video/ game/      #   V2/V3 placeholders
examples/             # two minimal closed-loop demos
tests/                # contract test + zero-diff acceptance + edge cases
docs/                 # frozen contract + design docs (see docs/README.md)
```

**Authoritative contract**: `docs/common-contract.md` (v1.0-FROZEN).

---

<a id="中文"></a>

## 中文

一个**模态无关的编排内核**，把人类语言/机器自观输入路由到 robot / game / 3d / video 四类场景分支，生成内容经 Critic 校验后，遥测汇入数据飞轮。

**自研范围**：通用主干编排层 + 统一接口契约 + 跨分支数据飞轮；场景能力通过插件化分支接入（防腐层封装 backbone，内核不绑死任何模型）。

### 当前状态：V1 已交付

| 版本 | 组合 | 状态 |
|---|---|---|
| **V1** | common + robot + 3d（robot 作业场景） | ✅ **本仓库当前版本** |
| V2 | + video | 计划 |
| V3 | + game | 计划 |
| V4 | + 完整独立 3D | 计划 |
| V5 | 全场景集成 + 跨分支飞轮 | 计划 |

**⚠️ 边界声明（V1 DoD #7）**：V1 验证的是编排内核 + 接口契约 + 数据飞轮，**不证明单场景物理可行性**。所有 backbone 均为 mock（真 GR00T / DreamGaussian 后续走 Azure，接入前过 `docs/engineering-setup.md` §2 五道门禁）。mock 的"假设可达"≠ 真实物理可达（sim2real 缺口）。

### 核心特性

- **冻结主干**：`common/` 写一次、长期稳定，新场景不侵入内核。
- **场景插件化**：新增场景只扩展 `branches/<scene>/`，common 零改动（零 diff 验收测试自动拦截）。
- **统一交换语言**：通过标准数据对象与抽象接口通信（`docs/common-contract.md` §4/§5）。
- **可观测闭环**：每次运行输出带 trace_id 的 Telemetry → 本地飞轮缓冲。

### 快速开始（Python 3.13，零三方运行时依赖）

```bash
# robot 最小闭环：复合 DAG（抓杯→移动→放置）+ S9 重试 + SafetyGate BLOCK/DEGRADE
python -m examples.robot_demo

# 3d 最小闭环：机器人作业客厅场景 → 占位 GLB + 跨分支 DAG（3d→robot）
python -m examples.3d_scene_demo

# 冻结验收
python -m tests.test_contract     # 反射契约测试：接口/字段/枚举一字不改
python -m tests.test_zero_diff    # 零 diff 验收：新增 mock5 场景，common 零改动

# 完整测试套件（可选，需装 pytest）
pip install pytest
python -m pytest tests/ -v         # 23 个测试，约 0.5 秒
```

### 三条铁律

1. **写一次，永冻结**：common 合入后零改动，新场景只加 `branches/<scene>/`。
2. **场景即插件**：common 无场景名/backbone 名/模态 if/else，差异全走 opaque payload + meta。
3. **唯一交换语言**：common 与场景之间只交换 `docs/common-contract.md` §4/§5 定义的对象与签名。

### 结构

```
common/               # 冻结内核（纯 stdlib，v1.0.0）
├── interfaces/       #   数据对象 + 8 个抽象接口
├── orchestrator/     #   S1–S14 状态机（DAG/重试/SafetyGate/异常映射）
├── registry/         #   BranchBundle 插件注册与解析
├── memory/           #   InMemoryMemory（S6 默认实现）
└── flywheel/         #   FileBufferFlywheel（S13/S14，本地只缓冲不训）
branches/
├── _physical/        #   物理阵营共享 WAM 先验基类（场景侧，非 common）
├── robot/            #   V1 ✅ 机器人分支（全 mock，零力矩执行）
├── 3d/               #   V1 ✅ robot 作业场景（占位 GLB 导出）
├── video/ game/      #   V2/V3 占位
examples/             # 两个最小闭环 demo
tests/                # 契约测试 + 零 diff 验收 + 边界测试
docs/                 # 冻结契约与全部设计文档（见 docs/README.md 索引）
```

**权威契约**：`docs/common-contract.md`（v1.0-FROZEN）。

---

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add new scene branches (V2/V3/V4) without touching the frozen common kernel.
