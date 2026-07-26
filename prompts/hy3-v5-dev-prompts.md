# HY-3 V5 开发启动包（全场景集成 + 跨分支数据飞轮 + 发布）

> 用途：把这份文件 + 指定的上下文文件发给 HY-3，让它按冻结契约开发 V5（把 V1–V4 的全部分支集成到同一内核，跑通跨分支 DAG + 统一飞轮，并完成发布）。
> 前置：V1+V2 已交付；**V3+V4 必须先完成**（V5 复用它们的 game / 完整 3d 分支）。common 零改动。
> **V5 是集成版本，不新建分支、不接新 backbone、不改 common（含 common/flywheel 接口）。** 只新增集成 demo、跨分支聚合视图、集成测试、发布物。

---

## A. 上下文文件清单（发给 HY-3 的文件）

按优先级排序，**前 6 份必读**：

| # | 文件 | 必读级别 | 作用 |
|---|---|---|---|
| 1 | `docs/common-contract.md` | 🔴 必读 | 冻结契约（重点 §6 DAG/State串联、§8 飞轮、§13 接入清单） |
| 2 | `docs/v5-development-plan.md` | 🔴 必读 | V5 范围/跨分支 DAG/统一飞轮/DoD/P0–P5 |
| 3 | `docs/oss-list-v5.md` | 🔴 必读 | 基础设施同接口替换 + 全版本 backbone 接入总览 |
| 4 | `docs/oss-integration-and-maintenance.md` | 🟠 必读 | 开源接入 3 红线 + E1–E6 |
| 5 | `docs/engineering-setup.md` | 🟠 必读 | 工程规范 |
| 6 | `common/orchestrator/` + `common/flywheel/` | 🟠 必读 | 只读理解 DAG/State串联/Telemetry 机制（**不许改**） |
| 7 | `branches/{robot,3d,video,game}/adapter.py` | 🟠 参考 | 各分支 register() 签名（集成时调用） |
| 8 | `examples/{robot_demo,video_demo}.py` | 🟢 参考 | demo 写法模板 |

**发送建议**：先一次性发前 6 份，HY-3 确认理解后再发各分支 adapter 做集成参考。

---

## B. 主提示词（发给 HY-3 的第一条消息）

```
你是 four-scene-brain 项目的实现工程师，不是设计者。所有架构决策已冻结在
common-contract.md 中，你的任务是严格按规范开发 V5：全场景集成 + 跨分支数据飞轮 + 发布。

【你的身份】
- 实现者，不是设计者。所有接口/数据对象/状态机已冻结，不得重新设计。
- 如果你认为 common 需要改动 → 立即停止，向我提问，不要擅自改。

【三条铁律（违反 = 返工）】
1. common 写一次永冻结：你不能改 common/ 任何一行（含 common/flywheel 接口）。
2. 场景即插件：分支之间不直接 import、不共享 payload 结构知识，跨分支只经 common 的
   SubGoal DAG + State 串联（common-contract §6）。
3. 唯一交换语言：common 与各分支之间只交换 common-contract §4/§5 定义的对象与签名。

【V5 范围（集成，不新建分支）】
- 新增 examples/integration_demo.py：≥2 条跨分支复合指令的最小闭环
  （如 3d→robot「生成客厅 3D 场景，让机器人把红杯拿到托盘」；video+game「生成猫视频+可玩关卡」）
- 新增 examples/_flywheel_view.py：跨分支遥测聚合视图（读统一 jsonl，按 branch/kind 分组汇总）
  —— 放 examples/ 侧，不进 common
- 新增 tests/test_integration.py：跨分支 DAG + 统一飞轮 + State 串联
- 发布物：版本号、CHANGELOG 定稿（补 V3/V4/V5）、README 终稿、GitHub Release 说明
- 全量回归：V1–V4 全部测试 + demo 不回归
- common 零改动，零 diff 验收必须通过

【开发顺序（P0–P5）】
严格按 v5-development-plan.md §5 的顺序：
P0 _flywheel_view.py（聚合视图）→ P1 integration_demo.py（跨分支 DAG）→
P2 test_integration.py → P3 全量回归 → P4 发布物 → P5 零 diff 验收

【关键约束】
- common/flywheel 接口不动；聚合视图放 examples/ 侧（读 jsonl，不写回）
- 复合指令的 S4 分解用规则/模板（D1/D3 已拍板），LLM 解析为可选插件
- 复用 V1–V4 各分支的 register()，不新建分支、不接新 backbone
- 纯 Python stdlib，零三方依赖

【质量标准】
- 每个新文件含 __main__ 自测
- demo 必须演示：≥2 条跨分支 DAG + 统一飞轮聚合 + 边界声明
- 全量回归必须通过

现在开始。先告诉我你理解了哪些关键点，然后从 P0 开始。
```

---

## C. P0 任务提示词（HY-3 确认理解后发送）

```
【P0 · examples/_flywheel_view.py：跨分支遥测聚合视图】

任务：实现一个纯 stdlib 工具，读 FileBufferFlywheel 落盘的 jsonl，按 branch/kind 分组汇总。

要求：
1. 实现 aggregate_by_branch(jsonl_path) -> dict：
   - 读 jsonl（每行一个 Telemetry：trace_id/subgoal_id/kind/data/ts）
   - 按 kind（torque/geometry/watch/player/...）分组计数 + 汇总（如各 kind 条数、均分）
   - 返回 {"<kind>": {"count": int, "traces": [...], "avg_score": float|None}, ...}
2. 实现 print_summary(agg)：人类可读的分支汇总打印
3. 不改 common；只读 jsonl，不写回
4. __main__ 自测：造几条假 Telemetry jsonl，验证聚合正确

输出文件：examples/_flywheel_view.py
```

---

## D. P1–P5 阶段提示词（按需逐个发送）

### P1 · integration_demo.py

```
【P1 · examples/integration_demo.py：跨分支复合指令最小闭环】

任务：实现 ≥2 条跨分支复合指令的端到端 demo。

要求：
1. 参考 examples/video_demo.py 的模式；一个 Registry 注册多个分支
2. 复合指令 A（3d→robot，State 串联）：
   「生成机器人作业的客厅 3D 场景，然后让机器人把桌上红杯拿到托盘」
   → S4 分解出 [3d SubGoal, robot SubGoal(depends_on 3d)] → 按 DAG 串联 → 都成功
3. 复合指令 B（video+game，并行/串行）：
   「生成一段猫奔跑的视频，再生成一个可玩平台关卡」
   → [video SubGoal, game SubGoal] → 都成功
4. 每条输出 RunMetrics + 各分支 Critic 分 + 统一 Telemetry 路径
5. S4 分解用规则/模板（关键词 → target/depends_on），不接 LLM
6. 末尾调 _flywheel_view.aggregate_by_branch 打印跨分支汇总
7. 边界声明：验证集成与跨分支飞轮，不证明单分支真实质量
8. __main__ 自测：两条 DAG 都跑通

输出文件：examples/integration_demo.py
```

### P2 · test_integration.py

```
【P2 · tests/test_integration.py：跨分支集成测试】

任务：写跨分支集成的 pytest。

要求：
1. 测跨分支 DAG：3d→robot 复合指令，两个 SubGoal 都成功，robot 的 depends_on 生效（State 串联）
2. 测统一飞轮：跑 ≥2 分支后，jsonl 含 ≥2 种 kind 的 Telemetry，aggregate_by_branch 分组正确
3. 测零 diff：注册全部分支后，common/ git diff 为空（可复用 tests/test_zero_diff.py 的机制）
4. 测不回归：robot/video/3d/game 各自单分支闭环仍通过
5. __main__ 自测 + pytest 都可跑

输出文件：tests/test_integration.py
```

### P3 · 全量回归

```
【P3 · 全量回归】

任务：确认 V1–V4 全部能力不回归。

要求：
1. python -m pytest tests/ 全绿（含 V1/V2/V3/V4 全部测试 + 新集成测试）
2. 跑通全部 demo：robot_demo / 3d_scene_demo / video_demo / game_demo / 3d_full_demo / integration_demo
3. 任何一个失败 → 先修复再进 P4
```

### P4 · 发布物

```
【P4 · 发布物】

任务：准备 V5 发布。

要求：
1. 版本号：common 恒 1.0.0（冻结内核不变）；V5 作为组合版本记录
2. CHANGELOG.md 定稿：补 V3.0.0 / V4.0.0 / V5.0.0 三个条目（仿 V1/V2 格式）
3. README.md 终稿：状态表 V1–V5 全标已交付；Quick Start 补 game/3d_full/integration demo
4. GitHub Release 说明草稿（含 5 版本能力矩阵 + 边界声明 + 测试数）
5. 不改任何代码，只动文档/标签
```

### P5 · 零 diff 验收

```
【P5 · 零 diff 验收】

任务：验证 common 全程零改动。

要求：
1. 运行 python -m tests.test_zero_diff（含全部分支注册）
2. 确认 common/ git diff 为空
3. 失败 → 说明集成有泄漏，必须修复
```

---

## E. 纠偏话术（HY-3 跑偏时用）

| 情况 | 纠偏话术 |
|---|---|
| HY-3 想改 common（含 flywheel 接口） | "common 已冻结，跨分支聚合放 examples/ 侧，不改 common。" |
| HY-3 让分支互相 import / 共享 payload | "分支只经 common 的 SubGoal DAG + State 串联交互，不直接 import。" |
| HY-3 想新建分支或接新 backbone | "V5 是集成版，复用 V1–V4，不新建分支、不接新 backbone。" |
| HY-3 用 LLM 做 S4 分解 | "S4 分解用规则/模板（已拍板），LLM 只是可选插件，先不接。" |
| HY-3 想装第三方库 | "V5 纯 stdlib，零三方依赖。" |
| HY-3 跳过全量回归 | "P3 全量回归必须过，任何一个 demo/测试失败先修复。" |

---

## F. 省钱提醒

- **一次性发上下文**：前 6 份一次发完。
- **复用现有 demo/测试**：integration 测试尽量复用 test_zero_diff / 各分支 demo 的机制。
- **先通一条 DAG**：先把 3d→robot 跑通，再加 video+game，别一次全写。
- **卡住就问**：HY-3 卡住超过 3 轮 → 停下来汇报。

---

## G. V5 DoD 验收清单（全部完成后检查）

- [ ] `python -m examples.integration_demo` 跑通 ≥2 条跨分支 DAG（3d→robot、video+game）
- [ ] 跨分支聚合视图正确（aggregate_by_branch 按 kind 分组）
- [ ] `python -m pytest tests/` 全绿（含 test_integration + 全量回归）
- [ ] `python -m tests.test_zero_diff` 通过，common git diff 为空
- [ ] 全部 demo 跑通不回归（robot/3d_scene/video/game/3d_full/integration）
- [ ] CHANGELOG 补 V3/V4/V5 条目；README 状态表 V1–V5 全标已交付
- [ ] 边界声明：README 注明「验证集成与跨分支飞轮，不证明单分支真实质量」
- [ ] git commit + tag + push 到 GitHub，准备 Release
