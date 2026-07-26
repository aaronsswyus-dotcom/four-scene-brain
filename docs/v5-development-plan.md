# four-scene-brain · V5 开发文档（全场景集成 + 跨分支数据飞轮 + 发布）

> 版本：v1.0-plan ｜ 范围：**V5 = common（冻结）+ 全部四个分支（robot/game/3d/video）集成**
> 依据：`common-contract.md`（FROZEN）、`v1–v4-development-plan.md`
> 前置：D1–D7 已拍板，common 已 FROZEN，**V1+V2 已交付，V3+V4 须先于 V5 完成**（本版依赖它们的 branch）。**common 全程零改动。**
> 性质：**集成版本，不新建分支**。复用 V1–V4 的全部分支，做「跨分支 DAG + 统一飞轮 + 发布」。
> **当前仍为设计文档，未写代码。**

---

## 0. V5 与前四版的关系

V1–V4 各自是「common + 单场景（或单阵营）」的独立端到端项目；**V5 把它们装回同一个编排内核**，验证「大脑=编排器」的终局命题：**一个冻结内核同时驱动四个场景，且跨场景数据汇入同一飞轮**。

| 版本 | 交付 | V5 复用 |
|---|---|---|
| V1 | robot + 3d(robot场景) | robot 分支、3d 分支（robot_scene） |
| V2 | video | video 分支 |
| V3 | game（双方向） | game 分支 |
| V4 | 完整 3D（多任务） | 3d 分支（全量任务） |
| **V5** | **集成 + 跨分支飞轮 + 发布** | 上述全部 + 集成 demo/测试/发布 |

---

## 1. V5 目标与范围

**目标**：在一个进程内注册全部四个分支，跑通**跨分支复合指令（DAG）**，把各分支 Telemetry 汇入**统一飞轮**并按分支聚合蒸馏，最后完成**版本发布**。验证：冻结内核多场景并发驱动 + 跨分支数据飞轮闭环。

**范围内（V5 做）**
- `examples/integration_demo.py`：跨分支复合指令最小闭环（≥2 条，跨≥2 分支）
- `common/flywheel` **不动**；V5 只在**分支侧/示例侧**做跨分支遥测聚合视图（读统一缓冲、按 branch 分组、汇总）
- 跨分支集成测试 `tests/test_integration.py`
- 发布物：版本号、CHANGELOG 定稿、README 终稿、GitHub Release 说明
- 零 diff 验收 + V5 DoD 验收

**范围外（V5 不做）**
- ❌ 新建任何分支（复用 V1–V4）
- ❌ 真 backbone / 真硬件（仍全 mock，真接入走 `model-integration-runbook.md`）
- ❌ 改动 common（零改动；飞轮跨分支聚合在分支/示例侧做，不动 `common/flywheel` 接口）
- ❌ 真实云端训练（S14 本地缓冲；云端回灌走同接口，Azure 阶段）

---

## 2. V5 框架

```
一条复合人语言指令（跨场景）
   ↓
┌──────────────── common（冻结，v1.0.0）────────────────┐
│  S3 意图 → S4 分解出跨场景 SubGoal DAG                 │
│  S5 路由（同一 Registry 解析 robot/game/3d/video）     │
│  S6 State 串联（前序分支输出 → 后序分支输入上下文）     │
│  S13 统一回收 Telemetry（各分支 kind 不同，common 只存）│
│  S14 统一蒸馏                                          │
└───────▲──────────▲──────────▲──────────▲──────────────┘
        │          │          │          │
   robot(物理)  3d(物理)   video(像素)  game(像素)
        └──────┬───┴──────────┴────┬─────┘
               │  统一飞轮缓冲（jsonl）│
               └─→ 跨分支聚合视图（V5 新增，分支/示例侧）─→ 按 branch 分组/汇总
```

**关键**：common 早已支持 DAG + State 串联 + 统一 Telemetry（S6/S13）。V5 几乎不改代码，只**新增集成 demo + 跨分支聚合视图 + 集成测试 + 发布物**。

---

## 3. V5 边界

**common 边界**：全程零改动（含 `common/flywheel` 接口）。跨分支聚合视图放 `examples/` 或 `branches/` 侧工具，**不进 common**。

**集成专属边界**：
1. **跨分支只经 DAG + State 串联**：分支之间不直接 import / 不共享 payload 结构知识；一切经 common 的 SubGoal/State 机制（common-contract §6）。
2. **统一飞轮不改接口**：各分支 Telemetry `kind` 不同（torque/geometry/watch/player），common 只存；V5 聚合视图按 `kind`/`branch` 分组，不写回。
3. **mock 不证明端到端真实**：V5 验证集成与飞轮闭环，不证明任一分支真实质量。
4. **发布不破坏冻结**：版本发布只动文档/标签，不动 common 接口。

---

## 4. V5 接口

**通用接口（冻结，V1–V4 已验证，V5 原样使用）**：全部数据对象 + 8 接口。**V5 不新增 common 接口。**

**V5 新增（分支/示例侧，不进 common）**：
- **跨分支聚合视图**（纯 stdlib 工具函数，如 `examples/_flywheel_view.py`）：
  ```python
  def aggregate_by_branch(telemetry_jsonl_path) -> dict:
      # 读 FileBufferFlywheel 落盘的 jsonl，按 branch/kind 分组
      # 返回 {"robot": {...counts/scores...}, "video": {...}, ...}
  ```
- **集成 demo 的复合指令解析**：v0 仍用规则/模板把跨场景指令拆成多 SubGoal（D1/D3 已拍板，LLM 解析为可选插件）。

**跨分支 DAG 示例（State 串联）**：
```
指令：「生成机器人作业的客厅 3D 场景，然后让机器人把桌上红杯拿到托盘」
S4 分解 → [SubGoal#1 target="3d"(robot_scene), SubGoal#2 target="robot" depends_on=#1]
S5 路由 → 3d 分支产出客厅场景 State → S6 作为 robot 的输入上下文
S7–S13 各分支闭环 → 统一 Telemetry → S14 蒸馏
```

---

## 5. V5 开发计划（阶段拆解）

> 顺序即依赖；每阶段带自测。纯 stdlib，零三方依赖。common 零改动。

| 阶段 | 产出 | 验收 |
|---|---|---|
| **P0 跨分支聚合视图** | `examples/_flywheel_view.py`（读 jsonl 按 branch/kind 分组汇总） | 聚合自测 |
| **P1 集成 demo** | `examples/integration_demo.py`：≥2 条跨分支复合指令（3d→robot、video+game） | 各 DAG 跑通 S1–S14 |
| **P2 集成测试** | `tests/test_integration.py`：跨分支 DAG + 统一飞轮 + State 串联 | pytest 通过 |
| **P3 全量回归** | 跑 V1–V4 全部测试 + demo | 全绿 |
| **P4 发布物** | 版本号、CHANGELOG 定稿（补 V3/V4/V5）、README 终稿、Release 说明 | 文档一致 |
| **P5 零 diff 验收** | `tests/test_zero_diff.py`（含全部分支） | common git diff 为空 |

**冻结纪律**：P0–P2 是集成本体；P3–P5 是验收 + 发布，不通过不许发布。

---

## 6. V5 依赖

- **运行时**：Python 3.13（托管），**仅用标准库**。
- **开发依赖**：pytest（已装）。
- **前置**：V3、V4 分支已交付（本版复用）。若 V3/V4 未完成，V5 只能先做"已有分支"的集成子集。
- **不装**：任何大模型 / GPU 依赖（V5 全 mock）。
- **基础设施（可选，Azure 阶段）**：Mem0（Memory 同接口替换）、Azure 飞轮回灌管道（Flywheel 同接口替换）——见 `oss-list-v5.md`。

---

## 7. V5 验收 DoD

1. **跨分支 DAG（3d→robot）**：输入「生成机器人作业的客厅 3D 场景，然后让机器人把桌上红杯拿到托盘」→ 2 个 SubGoal 按 DAG 串联 → 都成功 + 带 trace_id 的 Telemetry。
2. **跨分支（video+game）**：输入「生成一段猫奔跑的视频，再生成一个可玩平台关卡」→ 2 个 SubGoal → 都成功。
3. **统一飞轮**：≥2 分支的 Telemetry 落同一 jsonl，聚合视图按 branch 分组输出各分支计数/均分。
4. **全量回归**：V1–V4 全部测试 + demo 通过（不回归）。
5. **零 diff 验收**：`common/` git diff 为空。
6. **RunMetrics**：复合指令输出成功率 / 重试次数 / 各分支 Critic 分。
7. **发布**：版本号 + CHANGELOG（V1–V5）+ README 终稿 + GitHub Release 说明就绪。
8. **边界声明**：README 注明「验证集成与跨分支飞轮，不证明单分支真实质量」。

---

## 8. V5 风险与红线

- 🔴 为集成改动 common → 冻结失败（零 diff 兜底）。跨分支只经 DAG + State，不改 common。
- 🔴 分支间直接共享 payload / import → 违反铁律 3（只经 common 交换对象）。
- 🔴 跨分支聚合写进 common/flywheel → 改接口（必须放分支/示例侧）。
- 🟠 V3/V4 未完成就硬上 V5 → 先做已有分支的集成子集，V3/V4 到位后补全。
- 🟠 发布改动接口 → 发布只动文档/标签。

---

## 9. V5 与前版差异对比

| 维度 | V1–V4（单场景/阵营） | V5（集成） |
|---|---|---|
| 新增分支 | robot/3d/video/game | **无（复用全部）** |
| 核心命题 | 单场景闭环 + 冻结 | **多场景并发 + 跨分支飞轮 + 发布** |
| DAG | 分支内 / robot↔3d(V1) | **跨任意分支（3d→robot、video+game…）** |
| 飞轮 | 单分支缓冲 | **统一缓冲 + 跨分支聚合视图** |
| 代码量 | 各分支适配器 | **集成 demo + 聚合视图 + 测试 + 发布物（common 零改动）** |
