# four-scene-brain · 文档索引

> 用途：一眼分清**核心契约文件**（必读、冻结、随版本携带）与**过程/背景文档**（可追溯，可不随版本带）。
> 更新：2026-07-26 V1+V2 已交付（common + robot + 3d + video），31/31 测试通过；V3/V4/V5 准备包就绪（HY-3 过夜开发总入口：`prompts/hy3-overnight-master.md`）。

---

## 🟢 核心契约文件（必读 · 冻结 · 随 V1–V5 携带）

| 文件 | 作用 | 何时用 |
|---|---|---|
| **`common-contract.md`** | **通用层唯一权威契约**（思路/框架/边界/接口/数据对象/状态机/接入清单/冻结纪律）。已 FROZEN。 | **V1–V5 全程**；每个版本开发都把它当上下文 |
| **`v1-development-plan.md`** | **V1 开发文档**（common+physical：robot + robot的3D场景；范围/框架/接口/P0–P8/DoD）。 | V1 开发期；V2–V5 参考模式 |
| **`v2-development-plan.md`** | **V2 开发文档**（common+video：payload/接口/DoD/P0–P9/SafetyGate双模式）。 | V2 开发期 |
| **`v3-development-plan.md`** | **V3 开发文档**（common+game **双方向**：level 可玩关卡 + worldmodel 交互式推演；payload/接口/DoD/P0–P9）。✅ **D-V3-1 已拍板（A+B 双方向）**。 | V3 开发期 |
| **`v4-development-plan.md`** | **V4 开发文档**（common+完整独立 3D，物理阵营，多任务：robot_scene/text_to_3d/image_to_3d/pointcloud_completion/pbr_texture；payload/接口/DoD/P0–P9）。 | V4 开发期 |
| **`v5-development-plan.md`** | **V5 开发文档**（全场景集成 + 跨分支数据飞轮 + 发布；不新建分支；DAG/统一飞轮/DoD/P0–P5）。 | V5 开发期（须 V3+V4 先完成） |
| **`oss-integration-and-maintenance.md`** | **开源接入合规 + 可维护性规范**（3 红线、E1–E6、contract test、mock/real、README模板、测试分层、配置外化、变更纪律）。 | 接任何开源框架 / 写代码全程 |
| **`engineering-setup.md`** | **工程规范 + 开源选型**（common纯stdlib、5道测试门禁T1–T5、候选框架清单、包名/pytest/git）。 | 搭环境 / 选型 / 写测试 |
| **`oss-list-v1.md`** | **V1 开源项目清单**（运行时零三方依赖；backbone 候选与处置）。 | V1 启动前 / 选型参考 |
| **`oss-list-v2.md`** | **V2 开源项目清单 + backbone adapter 接口规范**（HunyuanVideo/备选；VideoBackbone 统一接口）。 | V2 启动前 / 选型 + 接口对齐 |
| **`oss-list-v3.md`** | **V3 开源项目清单 + GameBackbone adapter 接口规范**（A 关卡生成 MarioGPT 等 / B 交互式 GameGen-O·OASIS·DIAMOND；方向感知统一接口）。 | V3 启动前 / 选型 + 接口对齐 |
| **`oss-list-v4.md`** | **V4 开源项目清单 + ThreeDBackbone adapter 接口规范**（TRELLIS 主推 / TripoSR·DreamGaussian·Shap-E 备选；任务感知统一接口）。 | V4 启动前 / 选型 + 接口对齐 |
| **`oss-list-v5.md`** | **V5 开源项目清单**（集成版无新 backbone；基础设施同接口替换 Mem0/Azure + 全版本 backbone 接入总览）。 | V5 启动前 / 选型参考 |

> 这 13 份是"真契约"，开发时**只看这 13 份**即可。

---

## 🔵 测试与真模型接入（跨版本通用）

| 文件 | 作用 | 何时用 |
|---|---|---|
| **`acceptance-test-plan.md`** | **V3/V4/V5 验收测试计划**（测试金字塔 + 各版本 DoD 清单 + 全量回归 + 关键测试点）。 | 每版本开发完逐项验收 |
| **`model-integration-runbook.md`** | **真模型接入 + 自动测试 Runbook**（T1–T5 门禁 + mock/real 开关 + 自动测试 + 测试报告模板）。 | mock 全交付后接真 backbone |
| **`phase4-integration-framework.md`** | **阶段四总控设计**（全分支接入框架/seam + 7类失败×5级降级阶梯 + 持续优化飞轮 + 本沙箱T1核查 + 执行路线图 + 执行环境选择 GitHub Actions vs Azure）。 | 阶段四启动前 / 真模型接入总蓝图 |
| **`../prompts/hy3-overnight-master.md`** | **HY-3 过夜主开发包**（V3→V4→V5 依次开发总控 + 测试 + 模型接入 + 报告）。 | HY-3 自主开发总入口 |

### 测试报告（真模型接入实测，按 runbook §5 模板）

| 文件 | 分支 / backbone | 状态 |
|---|---|---|
| `reports/game_mariogpt_report.md` | game / MarioGPT（distilgpt2, CPU, MIT） | ✅ 代码已落地（2026-07-27）；T1/T2/T5 已核查；T3/T4 + 自动测试待 `git push` 后 GitHub Actions `game-real-mariogpt` job 实测 |

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
│   ├── video/                🟢 V2 ✅ 视频分支（全 mock，像素阵营）
│   ├── game/                 #   V3 占位
├── examples/                # robot_demo + 3d_scene_demo
├── tests/                   # 契约测试 + 零 diff 验收 + 边界测试（31 项）
├── prompts/                 # HY-3 开发提示词（方法论追溯）
└── docs/                    # 本索引 + 上述文档
```

**测试**：`python -m pytest tests/ -v` → 31/31 PASS。

---

## 一句话

**开发只带 13 份核心**（contract / v1–v5-plan / oss-maintenance / eng-setup / oss-list-v1–v5）；4 份过程稿留作追溯。新增场景按 `common-contract.md` §13 接入清单走，**全程不改 common**；HY-3 过夜开发从 `prompts/hy3-overnight-master.md` 进。
