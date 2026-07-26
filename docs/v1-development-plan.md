# four-scene-brain · V1 开发文档（common + physical：robot + 3d）

> 版本：v1.0-plan ｜ 范围：**V1 = 通用层 + 物理阵营（robot + 3d）**
> 依据：`common-contract.md`（冻结基线）、`boundaries.md`、`pre-dev-gap-analysis.md`
> 前置：D1–D7 已拍板（2026-07-26），common 已 **FROZEN**，本计划生效。**当前仍为设计文档，未写代码。**

---

## 1. V1 目标与范围

**目标**：交付一个本机可跑的端到端最小闭环——**通用编排内核 + 物理阵营两个分支（robot、3d）**，验证「大脑=编排器」成立 + 数据飞轮转起来。

**范围内（V1 做）**
- 完整 `common/`（interfaces / orchestrator / registry / memory / flywheel）——**冻结级质量**。
- `branches/robot/`（含 SafetyGate）全套适配器，**backbone 全 mock**。
- `branches/3d/` 的 **robot 作业场景**部分（机器人所处/操作的物理环境；**不是所有 3D 场景**，全量 3D 归 V4），backbone 全 mock。
- 场景侧共享基类 `PhysicalWorldModelBase`（robot 与 V1-3d 共享 WAM 物理先验）。
- `examples/robot_demo` + `examples/3d_scene_demo`（robot 作业场景）两个最小闭环。
- 零 diff 验收 + V1 DoD 验收。

**范围外（V1 不做）**
- ❌ 完整独立 3D 场景（文生3D / 概念图→GLB / 点云补全 / PBR）——归 **V4**。
- ❌ video / game 分支——归 **V2 / V3**。
- ❌ 真实 backbone（GR00T / DreamGaussian）——上 Azure，属后续。
- ❌ 真实硬件手驱动（S12 用零力矩 mock）。
- ❌ 跨分支飞轮全量集成（V5）。
- ❌ 真实训练（本地只缓冲）。

---

## 2. V1 整体框架

```
输入(人语言/自观) 
   ↓
┌─────────────── common（冻结内核，modality-agnostic）───────────────┐
│  orchestrator：S1输入→S2编码→S3意图→S4分解(DAG)→S5路由            │
│                →S7想象→S8包装→S9校验→S10基元→S11映射→SafetyGate   │
│                →S12执行→S13回收→S14自改进                          │
│  registry：BranchBundle 注册/解析   memory/flywheel：内存实现      │
└───────────────▲──────────────────────────▲────────────────────────┘
        经接口契约 │                          │ 经接口契约
   ┌─────────────┴──────────┐   ┌───────────┴────────────┐
   │ branches/robot（物理）  │   │ branches/3d（物理）     │
   │ 共享 PhysicalWorldModelBase（WAM 物理先验，场景侧）  │
   │ wam/critic/primitives  │   │ adapter/critic/         │
   │ /mapper/executor/      │   │ primitives/mapper/      │
   │ safety_gate/adapter    │   │ exporter(/safety_gate)  │
   └────────────────────────┘   └─────────────────────────┘
```

**关键**：common 对 robot/3d 完全无知；robot 与 V1-3d 之间**只共享 `PhysicalWorldModelBase`**（物理想象层），执行层各自实现（robot=关节力矩，3d=mesh 操作）。**V1 的 3d = robot 的作业场景（环境），不是通用 3D 生成。**

---

## 3. V1 边界

**common 边界**（详见 common-contract §2/§12）：无场景名、无模态 if/else、不 import 分支、payload 不透明、纯 stdlib、重试 ≤max_retry。

**physical 专属边界**：
1. **SafetyGate 必须**：robot 在 S11→S12 之间强制 `SafetyGate.check`（哪怕 mock 直接放行也要有这个钩子）；3d 可用 pass-through。
2. **sim2real 声明**：mock 物理态"假设可达"≠ 物理可行。V1 只验证编排内核 + 接口 + 飞轮，**不证明物理正确**——写进验收。
3. **共享到想象层，不共享执行层**：robot/3d 的 WAM 物理先验共享；执行（力矩 vs mesh）各自实现。
4. **顺序依赖先落地**：robot 复合指令（开门→推车）依赖 SubGoal DAG + State 串联（common-contract §6）。
5. **本地只缓冲不训**：S14 在 V1 仅落盘/缓冲 Telemetry。

---

## 4. V1 接口

**通用接口（冻结，见 common-contract §4/§5，V1 原样实现）**：
`WorldModel / Critic / PrimitiveLibrary / Mapper / Executor / SafetyGate / Memory / Flywheel` + 数据对象 `State/SubGoal(DAG)/Intent/Draft/Verification/Primitive/Executable/Delivery/Telemetry/RunMetrics/FailureKind/SafetyVerdict`。

**场景侧扩展（在 branches/，不进 common）**：

`PhysicalWorldModelBase`（robot/3d 共享的可选基类）：承载 WAM 物理先验与物理 State 工具函数，仍实现统一 `WorldModel` 接口。

**robot 的 physical `State.payload` 结构**（写进分支 README，本机现在定死以便将来换真 GR00T）：
```
pose: SE3        # 位置+朝向
twist: 速度       # 线速度+角速度
wrench: 力/力矩
contact: 接触信息
joint_state: 各关节角/力矩（灵巧手 DOF）
```
- robot Critic 成功判定：**force-torque 阈值优先**，视觉确认次之（`Verification.meta.verification_source`）。
- robot SafetyGate：力矩上限 / 关节限位 / 禁撞区（mock 也留接口）。

**3d 的 geometry `State.payload` 结构**：
```
representation: gaussians | pointcloud | mesh
semantics: 语义标注
```
- 3d Critic（V1 场景向）：可行走性 + 几何保真 + 文本-场景对齐（如「含桌面/杯子/可通行」）。
- 3d Exporter：占位 GLB（robot 作业场景）。

---

## 5. V1 开发计划（阶段拆解）

> 顺序即依赖；每阶段带自测。纯 stdlib，零三方依赖。

| 阶段 | 产出 | 验收 |
|---|---|---|
| **P0 通用数据对象+接口** | `common/interfaces/`：§4 数据对象 + §5 abc，含 `__main__` 自测 | 实例化、抽象不可直接实例化 |
| **P1 Registry** | `common/registry/`：BranchBundle + register/resolve | 注册/解析/未注册报错 |
| **P2 Orchestrator** | `common/orchestrator/`：S1–S14 状态机（DAG 拓扑 + State 串联 + 重试 + SafetyGate + 异常映射） | 用假分支跑通路由/重试 |
| **P3 Memory+Flywheel** | `common/memory/`（InMemory）+ `common/flywheel/`（落盘缓冲） | 读写/record/distill 自测 |
| **P4 Physical 共享基类** | `branches/_physical/base.py`（PhysicalWorldModelBase + 物理 State 工具） | robot/3d 可继承 |
| **P5 robot 分支** | `branches/robot/`：wam(mock)/critic/primitives/mapper/executor(零力矩mock)/safety_gate/adapter | 注册成功 |
| **P6 3d 分支** | `branches/3d/`：adapter(mock)/critic/primitives/mapper/exporter(占位GLB)/safety_gate | 注册成功 |
| **P7 两个 demo** | `examples/robot_demo` + `examples/3d_scene_demo` | 各自 S1–S14 跑通 |
| **P8 冻结验收** | 零 diff 测试（加 mock 第3场景，common diff 为空）+ V1 DoD | 全过 |

**先行冻结**：P0–P3 是 common，质量要求最高，写完即冻结，P5–P8 不许回头改。

---

## 6. V1 依赖

- **运行时**：Python 3.13（托管），**仅用标准库**（dataclasses/abc/typing/enum/json/asyncio）。
- **开发依赖**：`pytest`（测试用，不进 common 运行期）。
- **不装**：任何大模型 / GPU 依赖（v1 全 mock）。
- **真 backbone**：GR00T / DreamGaussian 走 Azure（后续，接入前过 `engineering-setup.md` §2 测试门禁）。
- 详细开源选型与工程规范见 `docs/engineering-setup.md`。

---

## 7. V1 验收 DoD

1. **robot 最小闭环**：输入「用灵巧手把桌上红杯拿到托盘」（含 DAG：抓杯→移动→放置）→ 走完 S1–S14 → 输出零力矩 mock `Delivery` + 带 trace_id 的 `Telemetry`。
2. **3d 最小闭环（robot 作业场景）**：输入「生成机器人作业的客厅场景：可行走，含桌子和桌上红杯」→ 走完 S1–S14 → 输出占位 GLB `Delivery`。
3. **重试路径**：演示一次 S9 失败 → 回 S7 → 成功。
4. **SafetyGate**：robot 演示一次 BLOCK（如力矩超限被拦）。
5. **零 diff 验收**：临时加 mock 场景，`common/` git diff 为空。
6. **RunMetrics**：输出成功率 / 重试次数 / 各 Critic 分。
7. **边界声明**：README 注明「验证编排内核，不证明物理可行性」。

---

## 8. V1 风险与红线

- 🔴 common 泄漏场景逻辑 → 冻结失败（零 diff 测试兜底）。
- 🔴 robot WAM 物理 payload 没定死 → 将来换真 GR00T 要重构（P4 定死规避）。
- 🟠 误把 mock 物理可行当真 → DoD 第 7 条声明规避。
- 🔴 本地装大模型 → 违反依赖红线。
