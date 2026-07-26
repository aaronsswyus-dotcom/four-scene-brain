# four-scene-brain · V3 开发文档（common + game · 双方向）

> 版本：v1.1-plan ｜ 范围：**V3 = 通用层（冻结）+ game 分支（两个生成方向）**
> 依据：`common-contract.md`（FROZEN）、`v2-development-plan.md`（像素阵营模式参考）、`v1-development-plan.md`（V1 模式参考）
> 前置：D1–D7 已拍板，common 已 FROZEN，V1+V2 已交付。**common 全程零改动。**
> backbone 候选：见 `oss-list-v3.md`（方向 A 关卡生成 / 方向 B 交互式 world model 分开选型）
> **当前仍为设计文档，未写代码。**

---

## ✅ D-V3-1 · 已拍板（2026-07-26）：A、B 两个方向都上

契约 §1 把 V3 交付物写为「游戏闭环（可玩关卡）」，§13 又引用 GameGen-O（游戏**视频**生成模型）。曾存在张力，现拍板：**两个方向都实现**，作为 `branches/game/` 的**两个生成方向（direction）**：

| 方向 | 语义 | payload 主轴 | Critic 主轴 | 真 backbone 倾向 |
|---|---|---|---|---|
| **A · level（可玩关卡）** | 文本 → 2D 平台关卡（tile map+实体），输出可玩 level 文件 | `level_map/entities/theme` | 可玩性（连通/边界/支撑） | 关卡生成模型 |
| **B · worldmodel（交互式推演）** | 状态帧 + 玩家动作 → 预测下一帧（action-conditioned video，类 GameGen-O/OASIS） | `frames/action_history/current_action` | 动作一致性 + 帧质量 | GameGen-O / OASIS |

**结构决定**：**一个 `branches/game/`、一个 `target="game"`、一套 5+1 接口**，两个方向经 **`adapter.build_bundle(direction="level"|"worldmodel")`** 切换（沿用 V2 SafetyGate 双模式同款"构建期旋钮"模式）。demo 用两个 registry 演示两个方向。**不新增 target、不破坏"四场景"框架、common 零改动。**

---

## 1. V3 目标与范围

**目标**：在冻结内核之上新增 game 分支，跑通「语言指令 → 生成可玩关卡 / 交互式推演 → Critic 校验 → 交付 → 遥测入飞轮」的最小闭环（两个方向各一条），验证 common 的 write-once-freeze 在像素阵营的**第二个场景**同样成立。

**范围内（V3 做）**
- `branches/game/` 全套适配器：wam(mock)/critic/primitives/mapper/executor/safety_gate/adapter + README
- game payload 结构定死（**双方向各一套**，为将来换真 backbone 做准备）
- SafetyGate 双版本：**可配置开关**（审核模式 / 放行模式），用户运行时选择
- `examples/game_demo`：两个方向的最小闭环
- 零 diff 验收 + V3 DoD 验收

**范围外（V3 不做）**
- ❌ 真 backbone 接入（上 Azure，V3 仍 mock）
- ❌ 3D 关卡 / 真实游戏引擎（Godot/Unity）集成 / 真实玩家输入回环
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
   ┌─────────────┴──────────────────────┐
   │ branches/game（像素 · 双方向）       │
   │  direction="level"      │ direction="worldmodel" │
   │  level payload/critic   │ frames+action payload/critic │
   │  ── 共享 ──             │
   │  scene_objects / GameBackbone 接口(方向感知) / │
   │  wam / primitives / mapper / executor / safety_gate(双模式) / adapter │
   └────────────────────────┘
```

**关键**：common 对 game 完全无知；game **不**共享 robot/3d 的 `PhysicalWorldModelBase`（像素阵营），独立实现全部 5+1 接口；方向差异全部走 `payload` + `config`/`meta`，不进 common。

---

## 3. V3 边界

**common 边界**：无场景名、无模态 if/else、不 import 分支、payload 不透明、纯 stdlib、重试 ≤max_retry。**V3 全程不改 common 一行。**

**game 专属边界**：
1. **双方向经 adapter 旋钮**：`build_bundle(direction=...)` 选方向；不在 common、不在 orchestrator 出现方向分支——方向只存在于 game 分支内部（payload/config/meta）。
2. **SafetyGate 双模式**：`safety_gate(mode="audit")` 内容审核，`safety_gate(mode="passthrough")` 放行，default=audit。
3. **关卡质量/推演质量 vs 内容合规分离**：Critic 管「达标」（可玩性 / 动作一致性），SafetyGate 管「合规」（gore/explicit）。不混淆。
4. **mock 不证明质量**：V3 mock 生成确定性占位（tile map / 换帧），验证编排闭环，不证明关卡好玩或推演逼真。真质量靠真 backbone on Azure。
5. **本地只缓冲不训**：S14 仍走 FileBufferFlywheel 落盘。

---

## 4. V3 接口

**通用接口（冻结，V1+V2 已验证，V3 原样使用）**：
`WorldModel / Critic / PrimitiveLibrary / Mapper / Executor / SafetyGate / Memory / Flywheel` + 全部数据对象 + 枚举。

**统一 GameBackbone 接口（防腐层，方向感知；不进 common）**：

```python
class GameBackbone(ABC):
    def generate(self, prompt: str, config: dict) -> dict:
        # config 必含 "direction": "level" | "worldmodel"
        #   level:      theme / width / height / n_coins / n_enemies / retry / seed
        #   worldmodel: action / state_frames / fps / resolution / retry / seed
        # 返回 dict 必含 "direction" + 方向专属字段 + "meta"
    def get_info(self) -> dict: ...
```

**方向 A（level）payload 结构（分支冻结，写进分支 README）**：
```
direction:     "level"
level_map:     list[str]     # '#'=地面, '.'=空, 'P'=玩家起点, 'E'=敌人, 'C'=金币, 'H'=陷阱, 'G'=终点
width/height:  int
entities:      list[dict]    # {type, x, y}
theme:         str
text_prompt:   str
frames:        list[str]     # ASCII 渲染预览
# mock 附加：scene_description / refined_times
```

**方向 B（worldmodel）payload 结构（分支冻结，写进分支 README）**：
```
direction:     "worldmodel"
frames:        list[list[list[int]]]  # [T][H][W][C]
fps:           int
resolution:    [width, height]
action_history: list[str]
current_action: str                    # 本次玩家动作（left/right/jump/…）
text_prompt:   str
# mock 附加：scene_description / refined_times
```

**game Critic 成功标准（按 payload["direction"] 分派）**：
- **方向 A 可玩性（硬指标优先）**：恰好 1 个 `P`、恰好 1 个 `G`；**起点可达终点**（BFS 连通，忽略敌人）；四周边界封闭；实体不悬空；尺寸在目标范围（如 8–32 列 × 6–16 行）。软指标：`theme` 与 prompt 关键词重叠。
- **方向 B 动作一致性 + 帧质量（硬指标优先）**：`frames` 随 `current_action` 产生确定性变化（mock 校验动作→帧差非零且方向合理）；fps/resolution 达标；帧间相干性。软指标：scene_description 与 prompt 关键词重叠。
- 判定来源写入 `Verification.meta.verification_source`（含 direction 标记）。

**game SafetyGate（双模式，对两方向通用）**：

| 模式 | 检查 | 结果 |
|---|---|---|
| `audit`（默认） | text_prompt 含 gore/explicit 关键词 | BLOCK |
| `audit` | level 尺寸越界 / worldmodel 分辨率过低或帧数过少 | DEGRADE |
| `audit` | 一切正常 | PASS |
| `passthrough` | 无检查 | PASS |

**game Executor（按 direction 分派）**：
- A：写 `output/game/level_<hash>.json`（tile map+entities）+ `.txt`（ASCII 渲染）。
- B：写 `output/game/replay_<hash>.json`（帧序列+动作轨迹占位）。

---

## 5. V3 开发计划（阶段拆解）

> 顺序即依赖；每阶段带自测。纯 stdlib，零三方依赖。common 零改动。

| 阶段 | 产出 | 验收 |
|---|---|---|
| **P0 game 关键词** | `branches/game/scene_objects.py`（主题/实体/动作/陷阱/镜头 关键词，双语） | 关键词解析自测 |
| **P1 GameBackbone 接口** | `branches/game/backbone_interface.py`（方向感知 `generate`/`get_info`） | 抽象不可实例化自测 |
| **P2 Mock backbone** | `branches/game/backbone_mock.py`（**双方向**确定性生成；retry 提升可达性/动作一致性） | 相同 prompt 相同结果自测 |
| **P3 game WAM** | `branches/game/wam.py`（GameWAM 调 backbone，传 direction） | predict_next_state 自测 |
| **P4 game Critic** | `branches/game/critic.py`（**双方向**分派校验） | verify 自测 |
| **P5 game Primitives** | `branches/game/primitives.py`（level: platform/gap/enemy/coin/hazard/goal；worldmodel: frame_step/action_apply） | abstract 自测 |
| **P6 game Mapper** | `branches/game/mapper.py`（基元 → 方向 Executable） | map 自测 |
| **P7 Executor + SafetyGate** | `branches/game/executor.py`（level JSON+ASCII / replay JSON）+ `safety_gate.py`（双模式） | execute/check 自测 |
| **P8 game Adapter** | `branches/game/adapter.py` + `register()`（`direction` 旋钮） | 注册自测 |
| **P9 Demo + 零 diff** | `examples/game_demo.py`（双方向）+ `tests/test_zero_diff.py` 加 game | common git diff 为空 |

**冻结纪律**：P0–P8 是 game 分支内部；P9 是验收，不通过不许合入。

---

## 6. V3 依赖

- **运行时**：Python 3.13（托管），**仅用标准库**。
- **开发依赖**：pytest（已装）。
- **不装**：任何大模型 / GPU 依赖（V3 全 mock）。
- **真 backbone**：方向 A/B 分开选型（`oss-list-v3.md`），走 Azure，接入前过 `engineering-setup.md` §2 五道门禁。

---

## 7. V3 验收 DoD

1. **level 最小闭环**：输入「生成一个 2D 平台关卡：草地主题，3 个金币，能跳到终点旗帜」→ S1–S14 → 输出 level JSON + ASCII 渲染 + 带 trace_id 的 Telemetry。
2. **worldmodel 最小闭环**：输入「游戏场景：角色向右移动 1 秒」→ S1–S14 → 输出 replay JSON（帧随动作变化）+ 带 trace_id 的 Telemetry。
3. **重试路径**：演示一次 S9 失败（level 不可达：起点到不了终点）→ 回 S7 → 成功。
4. **SafetyGate 审核模式**：含 gore 关键词的 prompt → BLOCK。
5. **SafetyGate 放行模式**：同一 prompt → PASS（验证双模式可切换）。
6. **零 diff 验收**：`tests/test_zero_diff.py` 通过，`common/` git diff 为空。
7. **RunMetrics**：输出成功率 / 重试次数 / 各 Critic 分（含 direction）。
8. **边界声明**：README 注明「验证编排内核，不证明关卡/推演质量」。

---

## 8. V3 风险与红线

- 🔴 game 分支泄漏逻辑到 common → 冻结失败（零 diff 测试兜底）。
- 🔴 game payload 没定死 → 将来换真 backbone 要重构（P0/P4 定死规避）。
- 🔴 方向分支写进 common/orchestrator → 违反铁律 2（方向只走 payload/config/meta）。
- 🟠 误把 mock 关卡/推演质量当真 → DoD 第 8 条声明规避。
- 🔴 SafetyGate 审核误伤正常游戏语境（"打僵尸/战斗/怪物"≠ gore）→ 关键词列表保守，宁可漏不可错杀。
- 🟠 双方向使分支体量约≈1.5 个 V2 分支 → 共享 scene_objects/backbone 接口/adapter 骨架以控量。

---

## 9. V3 与 V1/V2 的差异对比

| 维度 | V1（robot + 3d） | V2（video） | V3（game · 双方向） |
|---|---|---|---|
| 阵营 | 物理（physical） | 像素（pixel） | 像素（pixel） |
| 共享基类 | PhysicalWorldModelBase | 无（独立实现） | 无（独立实现） |
| 交付物 | 机器人闭环 + 3D 作业场景 | mp4 占位 | **level 文件 + replay 文件（双方向）** |
| 方向/模式 | — | SafetyGate 双模式 | **生成方向双轨（level/worldmodel）+ SafetyGate 双模式** |
| Critic 标准 | force-torque 阈值 | duration/fps/resolution | **A 可玩性 / B 动作一致性 + 语义对齐** |
| payload | pose/twist/wrench/joint_state | frames/fps/duration/text_prompt/resolution | **A: level_map/entities/theme ｜ B: frames/action_history/current_action** |
| backbone | GR00T / DreamGaussian | HunyuanVideo / Wan-2.1 | A 关卡生成 / B GameGen-O、OASIS |
| 跨分支 DAG | robot → 3d | video 独立 | game 独立（V5 再集成） |
