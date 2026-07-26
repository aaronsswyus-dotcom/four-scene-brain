# four-scene-brain · 完备性缺口分析 + physical 闭环注意项 + 开发前清单

> 版本：v0.1（接 boundaries.md，作为开发前冻结的补充基线）。
> 结论先行：**架构骨架是完整的**（三层 + 接口 + S1–S14 + 飞轮都对），但冻结前有 6 个真缺口要补；
> 先做「通用 + physical」闭环时，安全与 sim2real 是最容易翻车的两处。

---

## Q1 · 架构完备性评估（还缺什么）

骨架完整 ≠ 可直接写码。以下 6 处按 🔴必补 / 🟠建议补 / 🟢可后补 分级。

### 🔴 必补（直接影响接口冻结）

**G1 · SubGoal 结构化不足（最关键缺口）**
当前 `SubGoal = {goal, success_criteria}` 两个字符串，撑不起复合指令与路由。物理指令天然有**顺序依赖**（"开门→把推车推进房间"），必须能表达 SubGoal 之间的 DAG。补成：
```
SubGoal:
  id: str                # 唯一标识，供遥测 trace
  target: str            # 'robot'|'game'|'3d'|'video'
  goal: str
  success_criteria: str
  depends_on: list[str]  # 前置 SubGoal id（顺序依赖）
  constraints: dict      # 模态无关约束（超时/资源/安全级别）
  priority: int = 0
```

**G2 · 错误/异常 taxonomy 缺失**
S9 失败只说了"回 S7 或 S4"，但没说清**哪些错可重试、哪些必须终止、哪些要降级**。补 `FailureKind`：
```
RETRYABLE_QUALITY      # 生成质量差 → 回 S7
STRUCTURAL_INFEASIBLE  # 目标物理不可达 → 回 S4
HARDWARE_OFFLINE       # 不可重试 → 终止
LICENSE_BLOCKED        # 不可重试 → 终止/降级到备选 backbone
TIMEOUT                # 可重试有限次
```
`Verification.meta` 里必须带 `failure_kind`，重试决策才有依据。

**G3 · trace/session 贯穿缺失**
S1–S14 现在没有一条贯穿的 `trace_id`，飞轮 S13 回收的数据无法归因到"哪一次闭环、哪一个 SubGoal"。补：`trace_id`（每次闭环唯一）+ `session_id`（跨指令会话），写进 State.meta 与所有 Telemetry。

### 🟠 建议补

**G4 · 执行模型（async/sync）未定**
复合指令多个 SubGoal 是串行还是并行？**物理分支必须串行**（机械手不能同时做两件事）；游戏/视频将来可能并行。建议 v0 同步实现，但接口签名预留 `async` 口子（避免日后推倒）。

**G5 · SafetyGate 钩子（physical 硬约束）**
机器人不能无限力矩、不能撞人。在 **S11→S12 之间**插一个 `SafetyGate.check(executable) -> SafetyVerdict`，最小闭环也要有这个 hook（哪怕 mock 直接放行）。这正对应你写过的 CBF_Safety_Bus / Edge_HardRT。

**G6 · 全局闭环度量缺失**
S9 只有单条 score，没有"这次闭环整体好不好 / 任务成功率"的度量。飞轮要喂数据，需要 `RunMetrics`（成功率、平均重试、耗时、各 Critic 分）——这也是可验证命题，方便你尽调式判断"架构是否成立"。

### 🟢 可后补
- **G7** 接口版本字段（`schema_version` 入 meta，FAB5/Azure 阶段才需要）。
- **G8** Human-in-the-loop / 自观 watcher（"看到地上有物体就捡起"的触发机制，v0 先手动触发）。

---

## Q2 · 先做「通用 + physical」闭环，要注意什么

physical 阵营 = robot + 3d（共享 WAM 物理先验）。重点 6 条：

1. **WAM 是唯一自研主干，也是最大难点。** 其余三个主干都是开源组装，唯独 Robot WAM 要自研。最小闭环先 mock 物理态，但**现在就要把 State.payload 的物理表示定好**（SE(3) 位姿 / twist 速度 / wrench 力 / contact），否则将来换真 GR00T 要重构。

2. **物理 Critic 比像素阵营难得多。** "抓到了吗 / 杯稳吗"要有判定来源——**优先 force-torque 阈值**，视觉确认次之。mock 时可假设成功，但接口要预留 `verification_source` 字段。

3. **安全是 physical 独有硬约束，不能省。** 即便最小闭环是"零力矩 mock 指令"，S11→S12 之间的 SafetyGate 钩子必须存在（见 G5）。这是 physical 和像素阵营最大的区别。

4. **sim2real 边界要写进 DoD。** mock 物理态"假设可达"与真实差距巨大。**最小闭环只验证"大脑编排 + 接口 + 飞轮"，不证明物理可行性**——这条必须在验收标准里明说，避免误以为跑通=物理可行。

5. **robot 与 3d 共享到哪一层要想清楚。** 共享的是**物理想象层（PhysicalWorldModelBase 的 WAM 先验）**，不是执行层：robot 执行=关节力矩，3d 执行=mesh 操作。做闭环时先抽象到想象层，执行层各自实现。

6. **顺序依赖先落地（呼应 G1）。** "开门→推车"这类强顺序指令是 physical 常态，SubGoal DAG 不解决，physical 闭环就跑不了复合指令。

---

## Q3 · 边界已做好，正式开发前清单（Checklist）

按顺序逐项打勾，全部完成再放行写码：

- [ ] **C1 冻结 SubGoal 结构化 schema（G1）** — 含 id/target/depends_on
- [ ] **C2 冻结 FailureKind taxonomy（G2）** — 可重试 vs 终止 vs 降级
- [ ] **C3 trace_id / session_id 贯穿设计（G3）**
- [ ] **C4 定执行模型：v0 sync，接口留 async 口子（G4）**
- [ ] **C5 加 SafetyGate 钩子（G5，physical 必须）**
- [ ] **C6 定义 RunMetrics（G6）**
- [ ] **C7 拍板 D1–D5**（见 boundaries.md §11，尚未确认）
- [ ] **C8 定代码规范**：零三方依赖、纯 stdlib、每模块 `__main__` 自测、目录 `__init__.py` 规划
- [ ] **C9 定"跑通"验收标准 DoD**（见下）
- [ ] **C10 选第一条 demo 指令**：建议 robot「用灵巧手把桌上红杯拿到托盘」

### 最小 physical 闭环 DoD（建议）
1. 输入 `用灵巧手把桌上红杯拿到托盘`（含 SubGoal DAG：抓杯→移动→放置）。
2. 走完 S1–S14，输出 `Delivery`（零力矩 mock Executable）+ 带 trace_id 的 `Telemetry`。
3. 演示一次 **S9 失败 → 回 S7 重试 → 成功**（验证重试边界）。
4. 全程零三方依赖，`python` 直接可跑。
5. 声明边界：验证大脑编排，**不证明物理可行性**。

---

## 与 boundaries.md 的关系
本文件是 boundaries.md 的**补充基线**：G1–G6 是对接口契约的增量，Q2/Q3 是落地指引。你确认后，我把 G1–G6 合并回 boundaries.md 的接口契约，并更新 D1–D5 的拍板结果。
