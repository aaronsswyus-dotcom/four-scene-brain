# four-scene-brain · 文档索引

> 用途：一眼分清**核心契约文件**（必读、冻结、随版本携带）与**过程/背景文档**（可追溯，可不随版本带）。
> 更新：2026-07-26 V1 已交付（common + robot + 3d），47/47 测试通过；V2 规划已出（video 分支）。

---

## 🟢 核心契约文件（必读 · 冻结 · 随 V1–V5 携带）

| 文件 | 作用 | 何时用 |
|---|---|---|
| **`common-contract.md`** | **通用层唯一权威契约**（思路/框架/边界/接口/数据对象/状态机/接入清单/冻结纪律）。已 FROZEN。 | **V1–V5 全程**；每个版本开发都把它当上下文 |
| **`v1-development-plan.md`** | **V1 开发文档**（common+physical：robot + robot的3D场景；范围/框架/接口/P0–P8/DoD）。 | V1 开发期；V2–V5 参考模式 |
| **`v2-development-plan.md`** | **V2 开发文档**（common+video：payload/接口/DoD/P0–P9/SafetyGate双模式）。 | V2 开发期 |
| **`oss-integration-and-maintenance.md`** | **开源接入合规 + 可维护性规范**（3 红线、E1–E6、contract test、mock/real、README模板、测试分层、配置外化、变更纪律）。 | 接任何开源框架 / 写代码全程 |
| **`engineering-setup.md`** | **工程规范 + 开源选型**（common纯stdlib、5道测试门禁T1–T5、候选框架清单、包名/pytest/git）。 | 搭环境 / 选型 / 写测试 |
| **`oss-list-v1.md`** | **V1 开源项目清单**（运行时零三方依赖；backbone 候选与处置）。 | V1 启动前 / 选型参考 |
| **`oss-list-v2.md`** | **V2 开源项目清单 + backbone adapter 接口规范**（HunyuanVideo/备选；VideoBackbone 统一接口）。 | V2 启动前 / 选型 + 接口对齐 |

> 这 7 份是"真契约"，开发时**只看这 7 份**即可。

---

## 🟠 过程 / 背景文档（可追溯 · 已被核心文件吸收）

| 文件 | 作用 | 现状 |
|---|---|---|
| `scheme.md` | 最早的整体开发文档（目录/开源内容/环境评估/最小闭环） | 背景；内容已被 common-contract + v1-plan 覆盖 |
| `boundaries.md` | 三层职责边界 + 接口契约 + 决策矩阵 | 背景；已并入 common-contract |
| `pre-dev-gap-analysis.md` | 完备性缺口分析（G1–G6、physical注意项、Checklist） | 背景；G1–G6 已并入 common-contract 数据模型 |
| `dev-handoff.md` | HY-3 开发交接包（实现者非设计者/禁止重设计 + P0→P8 顺序） | V1 开发过程产物；保留作方法论追溯 |

> 这 4 份是"过程稿"，记录了推演过程，**保留作追溯**。

---

## V1 代码结构（已交付）

```
four-scene-brain/
├── common/                  🟢 冻结内核（纯 stdlib，v1.0.0）
│   ├── interfaces/          #   数据对象 + 8 抽象接口
│   ├── orchestrator/        #   S1–S14 状态机
│   ├── registry/            #   BranchBundle 插件机制
│   ├── memory/              #   InMemoryMemory
│   └── flywheel/            #   FileBufferFlywheel
├── branches/
│   ├── _physical/           #   物理阵营 WAM 共享基类
│   ├── robot/               🟢 V1 ✅ 全 mock
│   ├── 3d/                  🟢 V1 ✅ robot 作业场景
│   ├── video/ game/         #   V2/V3 占位
├── examples/                # robot_demo + 3d_scene_demo
├── tests/                   # 契约测试 + 零 diff 验收 + 边界测试（23 项）
├── prompts/                 # HY-3 开发提示词（方法论追溯）
└── docs/                    # 本索引 + 上述文档
```

**测试**：`python -m pytest tests/ -v` → 23/23 PASS；全量回归 47/47。

---

## 一句话

**开发只带 7 份核心**（contract / v1-plan / v2-plan / oss-maintenance / eng-setup / oss-list-v1 / oss-list-v2）；4 份过程稿留作追溯。新增场景按 `common-contract.md` §13 接入清单走，**全程不改 common**。
