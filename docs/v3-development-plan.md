# four-scene-brain · V3 开发文档（common + game）

> 版本：v1.0-plan ｜ 范围：**V3 = 通用层（冻结）+ game 分支**
> 依据：`common-contract.md`（FROZEN）、`v2-development-plan.md`（像素阵营模式参考）、`v1-development-plan.md`（V1 模式参考）
> 前置：D1–D7 已拍板，common 已 FROZEN，V1+V2 已交付。**common 全程零改动。**
> backbone 候选：**GameGen-O**（契约 §13 预留示例）等，见 `oss-list-v3.md`
> **当前仍为设计文档，未写代码。**

---

## ⚠️ D-V3-1 · 唯一待拍板的设计岔路（先确认再写 oss-list-v3 / hy3-v3 提示词）

契约 §1 把 V3 交付物写为「**游戏闭环（可玩关卡）**」，但 §13 第 5 条把真 backbone 示例写为 **GameGen-O**（腾讯开放世界**游戏视频生成**模型）。两者存在张力：

| 方案 | 语义 | 匹配"可玩关卡" | 匹配"GameGen-O" | mock 可测性 |
|---|---|---|---|---|
| **A. 可玩关卡生成（本稿推荐）** | 文本 → 2D 平台关卡（tile map + 实体），输出可玩 level 文件 | ✅ 直接 | ⚠️ 需 adapter 把视频/描述转成 tile map | ✅ 高（关卡合法性可确定性判定） |
| **B. 交互式 game world model** | 状态帧 + 玩家动作 → 预测下一帧（action-conditioned video，类 OASIS/GameNGen） | ⚠️ "可玩"=可交互推演，非"关卡" | ✅ 直接 | 🟠 中（mock 只能做"动作→换帧"的弱语义） |

> **推荐 A**：直接满足契约"可玩关卡"，且 mock 阶段能做确定性的关卡合法性校验（连通性/边界/实体支撑），闭环验收最有说服力。B 更像"视频分支 + 动作条件"，与 V2 区分度低。
> **请确认 A 还是 B**（或别的解释）。确认后我再产出 `oss-list-v3.md` + `hy3-v3-dev-prompts.md`（两份都依赖该选择）。**以下全部按方案 A 展开。**

---

## 1. V3 目标与范围

**目标**：在冻结内核之上新增 game 分支，跑通「语言指令 → 生成可玩关卡 → Critic 校验 → 交付 level 文件 → 遥测入飞轮」的最小闭环，验证 common 的 write-once-freeze 在像素阵营的**第二个场景**同样成立。

**范围内（V3 做）**
- `branches/game/` 全套适配器：wam(mock)/critic/primitives/mapper/executor/safety_gate/adapter + README
- game payload 结构定死（为将来换真 backbone 做准备）
- SafetyGate 双版本：**可配置开关**（审核模式 / 放行模式），用户运行时选择
- `examples/game_demo` 最小闭环
- 零 diff 验收 + V3 DoD 验收

**范围外（V3 不做）**
- ❌ 真 backbone 接入（上 Azure，V3 仍 mock）
- ❌ 3D 关卡 / 真实游戏引擎（Godot/Unity）集成
- ❌ 跨分支飞轮全量集成（V5）
- ❌ 完整独立 3D 分支（V4）

---

## 2. V3 框架

```
输入(人语言)
   ↓
┌─────────────── common（冻结，v1.0.0，V1+V2 已验证）───────────────┐
│  orchestrator：S1–S14 状态机（不动）                          │
│  registry / memory / flywheel（不动）                          │
└───────────────▲──────────────────────────────────────────────┘
        经接口契约 │（common 对 game 完全无知）
   ┌─────────────┴──────────┐
   │ branches/game（像素）   │
   │ wam(mock)/critic/       │
   │ primitives/mapper/      │
   │ executor(level文件)/     │
   │ safety_gate(双模式)/     │
   │ adapter(防腐层)          │
   └────────────────────────┘
```

**关键**：common 对 game 完全无知；game **不**共享 robot/3d 的 `PhysicalWorldModelBase`（像素阵营，物理先验不同），独立实现全部 5+1 接口。

---

## 3. V3 边界

**common 边界**：无场景名、无模态 if/else、不 import 分支、payload 不透明、纯 stdlib、重试 ≤max_retry。**V3 全程不改 common 一行。**

**game 专属边界**：
1. **SafetyGate 双模式**：`safety_gate(mode="audit")` 做内容审核，`safety_gate(mode="passthrough")` 直接放行。adapter 内可配置，default=audit。
2. **关卡质量 vs 内容合规分离**：Critic 管「关卡可玩性/达标」（连通性/边界/尺寸/语义对齐），SafetyGate 管「内容合规」（gore/explicit 关键词）。两者不混淆。
3. **mock 不证明关卡质量**：V3 mock 生成的是占位关卡（确定性 tile map），验证编排闭环，不验证关卡好玩程度。真质量靠真 backbone on Azure。
4. **本地只缓冲不训**：S14 仍走 FileBufferFlywheel 落盘。

---

## 4. V3 接口

**通用接口（冻结，V1+V2 已验证，V3 原样使用）**：
`WorldModel / Critic / PrimitiveLibrary / Mapper / Executor / SafetyGate / Memory / Flywheel` + 全部数据对象 + 枚举。

**game 分支 payload 结构（分支冻结，写进分支 README）**：

```
level_map:     list[str]          # 关卡网格行：'#'=地面, '.'=空, 'P'=玩家起点,
                                  #   'E'=敌人, 'C'=金币, 'H'=尖刺/陷阱, 'G'=终点旗帜
width:         int                # 关卡宽（列数）
height:        int                # 关卡高（行数）
entities:      list[dict]         # {type: 'enemy'|'coin'|'hazard', x, y}
theme:         str                # 关卡主题（grass/desert/ice/cave…）
text_prompt:   str                # 文本描述（驱动生成）
frames:        list[list[str]]    # 渲染预览（mock 用 ASCII 渲染行）
# mock 附加：scene_description / refined_times
```

**game Critic 成功标准**：
- **可玩性 + 尺寸硬指标（优先）**：
  - 恰好 1 个玩家起点 `P`、恰好 1 个终点 `G`
  - **起点可到达终点**（BFS 连通性，忽略敌人）
  - 四周边界封闭（外圈为 `#`）
  - 实体不悬空（`E/C/H` 下方为 `#` 或 `G`）
  - 尺寸在目标范围内（如 8–32 列 × 6–16 行）
- **text-level 语义对齐（次之）**：`theme` 与 `text_prompt` 关键词重叠
- 判定来源写入 `Verification.meta.verification_source`

**game SafetyGate（双模式）**：

| 模式 | 检查 | 结果 |
|---|---|---|
| `audit`（默认） | text_prompt 含 gore/explicit 关键词 | BLOCK |
| `audit` | 关卡尺寸越界（过小/过大） | DEGRADE |
| `audit` | 一切正常 | PASS |
| `passthrough` | 无检查 | PASS |

**game Executor**：输出可玩关卡文件（纯 stdlib：写 `output/game/level_<hash>.json`（tile map + entities）+ `.txt`（ASCII 渲染预览））。

---

## 5. V3 开发计划（阶段拆解）

> 顺序即依赖；每阶段带自测。纯 stdlib，零三方依赖。common 零改动。

| 阶段 | 产出 | 验收 |
|---|---|---|
| **P0 game 关键词** | `branches/game/scene_objects.py`（主题/实体/动作/陷阱关键词词汇表） | 关键词解析自测 |
| **P1 GameBackbone 接口** | `branches/game/backbone_interface.py`（`generate`/`get_info` 防腐层） | 抽象不可实例化自测 |
| **P2 Mock backbone** | `branches/game/backbone_mock.py`（确定性 tile map，retry 提升可达性） | 相同 prompt 相同关卡自测 |
| **P3 game WAM** | `branches/game/wam.py`（GameWAM 调 backbone） | predict_next_state 自测 |
| **P4 game Critic** | `branches/game/critic.py`（可玩性 + 语义对齐） | verify 自测 |
| **P5 game Primitives** | `branches/game/primitives.py`（platform/gap/enemy/coin/hazard/goal 基元） | abstract 自测 |
| **P6 game Mapper** | `branches/game/mapper.py`（基元 → 关卡 Executable） | map 自测 |
| **P7 Executor + SafetyGate** | `branches/game/executor.py`（level JSON+ASCII）+ `safety_gate.py`（双模式） | execute/check 自测 |
| **P8 game Adapter** | `branches/game/adapter.py` + `register()` | 注册自测 |
| **P9 Demo + 零 diff** | `examples/game_demo.py` + `tests/test_zero_diff.py` 加 game 场景 | common git diff 为空 |

**冻结纪律**：P0–P8 是 game 分支内部，质量要求低于 common 但高于临时脚本；P9 是验收，不通过不许合入。

---

## 6. V3 依赖

- **运行时**：Python 3.13（托管），**仅用标准库**。
- **开发依赖**：pytest（已装）。
- **不装**：任何大模型 / GPU 依赖（V3 全 mock）。
- **真 backbone**：GameGen-O / OASIS 等走 Azure（接入前过 `engineering-setup.md` §2 五道门禁；选型见 `oss-list-v3.md`）。

---

## 7. V3 验收 DoD

1. **game 最小闭环**：输入「生成一个 2D 平台关卡：草地主题，3 个金币，能跳到终点旗帜」→ 走完 S1–S14 → 输出占位 level JSON + ASCII 渲染 + 带 trace_id 的 Telemetry。
2. **重试路径**：演示一次 S9 失败（关卡不可达：起点到不了终点）→ 回 S7 → 成功。
3. **SafetyGate 审核模式**：含 gore 关键词的 prompt → BLOCK。
4. **SafetyGate 放行模式**：同一 prompt → PASS（验证双模式可切换）。
5. **零 diff 验收**：`tests/test_zero_diff.py` 通过，`common/` git diff 为空。
6. **RunMetrics**：输出成功率 / 重试次数 / 各 Critic 分。
7. **边界声明**：README 注明「验证编排内核，不证明关卡质量」。

---

## 8. V3 风险与红线

- 🔴 game 分支泄漏逻辑到 common → 冻结失败（零 diff 测试兜底）。
- 🔴 game payload 没定死 → 将来换真 backbone 要重构（P0 定死规避）。
- 🟠 误把 mock 关卡质量当真 → DoD 第 7 条声明规避。
- 🔴 SafetyGate 审核模式误伤正常 prompt（如"打僵尸"这类正常游戏语境）→ 关键词列表要保守，宁可漏不可错杀；游戏语境的"战斗/怪物"≠ gore，需谨慎区分。
- 🟠 D-V3-1 若改判为方案 B（world model）→ payload/Critic/backbone 全要重定，须在写代码前拍板。

---

## 9. V3 与 V1/V2 的差异对比

| 维度 | V1（robot + 3d） | V2（video） | V3（game） |
|---|---|---|---|
| 阵营 | 物理（physical） | 像素（pixel） | 像素（pixel） |
| 共享基类 | PhysicalWorldModelBase | 无（独立实现） | 无（独立实现） |
| 交付物 | 机器人闭环 + 3D 作业场景 | mp4 占位 | **可玩 level 文件（JSON+ASCII）** |
| SafetyGate | 单模式（力矩/限位） | 双模式（内容审核） | 双模式（内容审核） |
| Critic 标准 | force-torque 阈值优先 | duration/fps/resolution 达标优先 | **可玩性（连通/边界/支撑）+ 语义对齐** |
| payload | pose/twist/wrench/joint_state | frames/fps/duration/text_prompt/resolution | **level_map/entities/theme/text_prompt/frames** |
| backbone | GR00T / DreamGaussian | HunyuanVideo / Wan-2.1 | GameGen-O / OASIS（待定 D-V3-1） |
| 跨分支 DAG | robot → 3d | video 独立 | game 独立（V5 再集成） |
