# four-scene-brain · 框架统一与边界设定（Framework Contract）

> 版本：v0.1（开发前边界基线）。本文件在写任何代码前冻结"谁拥有什么、绝不做什么"。
> 适用：所有 `common/` 与 `branches/` 的实现都必须服从本契约。

---

## 0. 一句话原则（所有争议的裁判）

**大脑 = 编排器（Orchestrator，modality-agnostic）；小脑 = 四分支适配器（modality-specific）；接口契约是两者之间唯一的膜。**
任何"这段逻辑该放哪"的争论，都回到这一条裁决。

---

## 1. 三层职责边界（最重要的边界）

| 层 | 归属 | 拥有什么 | 绝不做什么 | 关键接口 |
|---|---|---|---|---|
| **编排层 Orchestrator**（大脑） | 自研 | 驱动 9 工序、意图解析、路由决策、重试控制、遥测聚合 | 不生成任何模态内容、不解析 State.payload、不 import 分支模态库 | 调 `WorldModel` / `Critic` |
| **分支层 Branch**（小脑） | 自研适配器 + 开源主干 | 模态专属实现：世界想象、生成、校验、基元、映射、执行 | 不做路由、不跨分支调用、不决定重试 | 实现 `WorldModel` / `Critic` / `PrimitiveLibrary` / `Mapper` / `Executor` |
| **支撑层 Memory / Flywheel** | 自研封装 | 横切：记忆读写、遥测回收、自改进缓冲 | 不参与单工序决策、不路由 | `Memory` / `Flywheel` |

---

## 2. 接口契约（边界的数据膜，field 级）

```python
@dataclass
class State:
    modality: str        # 'physical' | 'sim' | 'geometry' | 'pixel'
    payload: object      # 对编排层不透明（opaque）
    meta: dict

@dataclass
class SubGoal:
    goal: str
    success_criteria: str

@dataclass
class Draft:
    modality: str
    payload: object

@dataclass
class Verification:
    passed: bool
    score: float
    reason: str
    meta: dict

# 三大接口（四分支各自实现，零改动插入）
WorldModel.predict_next_state(state: State, goal: SubGoal) -> State      # S7
Critic.verify(draft: Draft, goal: SubGoal) -> Verification                # S9
PrimitiveLibrary.abstract(draft: Draft) -> list[Primitive]                # S10

# 小脑链路补充
Mapper.map(primitives: list[Primitive]) -> Executable                     # S11
Executor.execute(executable: Executable) -> Delivery                      # S12
```

**边界结论**：编排层只认识 `State/SubGoal/Verification` 的字段，从不认识 `payload` 的内部结构。

---

## 3. 工序归属矩阵（S1–S14，谁拥有谁）

| 工序 | 拥有者 | 边界说明 |
|---|---|---|
| S1 输入 | Orchestrator | 接人语言 / 机器自观 |
| S2 编码 | Orchestrator | **模态在此定型**（文本/状态向量/几何/帧 → State.modality） |
| S3 意图 | Orchestrator | 产出 `target ∈ {robot, game, 3d, video}` |
| S4 分解 | Orchestrator | 产出 `SubGoal[]` |
| S5 路由 | Orchestrator | 经 Registry 选分支 |
| S6 记忆 | Memory（横切） | 最小闭环用内存 mock |
| S7 世界想象 | **Branch.WorldModel**（被大脑调用） | 同模态推进，返回假设态 |
| S8 生成 | **Branch**（主干/生成器） | 模态专属 |
| S9 校验 | **Branch.Critic**（被大脑调用） | 返回 Verification |
| S10 基元 | **Branch.PrimitiveLibrary** | 抽象生成物 |
| S11 映射 | **Branch.Mapper** | → Executable |
| S12 执行 | **Branch.Executor** | → Delivery |
| S13 回收 | Flywheel（横切） | 统一 Telemetry |
| S14 自改进 | Flywheel（横切） | 本地缓冲 / 云端回灌 |

**关键边界流**：编排层在 S2/S5 后持有"类型化但内容不透明"的 State；从 **S7 起把执行权交给分支**；S9 结果回到编排层决定是否重试。

---

## 4. 状态对象与模态边界

- `State.modality ∈ {physical, sim, geometry, pixel}`，S2 定型后**不再跨模态转换**（S7 在同模态内推进）。
- 编排层对 `payload` 一律 opaque：不解析、不假设结构。
- `payload` 结构**只在分支内定义**；分支必须经 `meta`/`__repr__` 提供可被编排层记录的摘要（供 S13 遥测）。
- 两个阵营可共享可选基类（见 §10），但**接口签名永远统一**。

---

## 5. 路由与复合指令边界

- **单一 SubGoal → 唯一分支**，绝不跨分支。
- 复合指令由 S4 拆成多个 `SubGoal`，**各自独立路由**到不同分支。
- `target` 为显式枚举 `{robot, game, 3d, video}`，**不允许 auto/unknown**。
- Registry 是唯一注册点；分支通过 `register(registry)` 上线，**未注册即不可路由**。

---

## 6. 失败回退 / 重试边界

- `S9 passed=False` → 编排层决定回退层级：
  - **局部失败**（细节/分数不达标）→ 回 **S7** 重想象（同 SubGoal）。
  - **结构性失败**（目标不可达）→ 回 **S4** 重新分解。
- `max_retry` 由编排层持有（默认 3），**超出即返回失败 + reason，绝不无限循环**。
- 重试上下文（上次 `Verification.reason`）回灌给 S7 / S4。

---

## 7. 数据飞轮边界（S13–S14）

- **S13 回收** = 遥测聚合 → 统一 `Telemetry`：
  - robot: 力矩/触觉 ｜ game: 玩家行为 ｜ 3d: 几何误差 ｜ video: 观看质量
- **S14 自改进** = 两档：
  - **本地最小闭环**：仅缓冲/落盘（经验积累），**不重训**。
  - **云端（Azure）**：周期性回灌各分支 WM（GR00T / GameGen-O / …），"推理即训练"。
- **边界红线**：本机飞轮**只写不训**；任何真实训练永远上云。

---

## 8. 自研 vs 组装边界

| 类别 | 内容 |
|---|---|
| **自研** | 编排器 + 3 接口 + Memory 封装 + Flywheel + Robot WAM |
| **组装**（只适配，不写真代码到本机） | 四分支 backbone（GR00T / GameGen-O / DreamGaussian / HunyuanVideo）+ 3D/视频读写库 |

**原则**：一切"模态生成能力"来自开源主干；一切"决策 / 契约 / 飞轮"自研。

---

## 9. 依赖与运行边界

- **本地最小闭环**：仅 Python 3.13 标准库（dataclasses/abc/typing/json/enum/asyncio），零三方依赖，全 mock 主干。
- **真实生成**：Azure / GPU 机，装各 backbone 依赖。
- **边界红线**：本机**禁止 pip 装大模型**；主干一律远程 / 可插拔（adapter 内默认 mock）。

---

## 10. 阵营共享边界

| 阵营 | 分支 | 共享先验 | 可选基类 |
|---|---|---|---|
| **物理阵营** | robot, 3d | WAM 物理先验（WAM 复用度最高） | `PhysicalWorldModelBase` |
| **像素阵营** | game, video | 生成式 WM 家族 | `PixelWorldModelBase` |

**边界**：共享基类只承载"先验 / 工具函数"，**接口签名仍统一为 `WorldModel`**，不引入第二个接口。

---

## 11. 待你拍板的核心决策（Decision Matrix）

| # | 核心问题 | 选项 | 推荐默认 |
|---|---|---|---|
| **D1** | 编排器形态 | A. LLM 驱动 agent ／ B. 规则状态机 | **B（v0 规则状态机）**，LLM 可选作 S3/S4 解析器 |
| **D2** | S7 语义 | A. 返回假设态 State ／ B. 直接生成成品 | **A**：想象归想象，生成归 S8 |
| **D3** | 跨分支复合指令 | A. 允许 ／ B. 禁止 | **A**：S4 拆 SubGoal 各自路由 |
| **D4** | S14 重训时机 | A. 在线梯度 ／ B. 周期回灌 | **B**：本地只缓冲，云端周期回灌 |
| **D5** | Critic 自由度 | A. 统一签名+分支自定义 criteria ／ B. 全统一标准 | **A** |

---

## 12. 边界红线（实现时逐条检查）

- 🔴 编排层**不得 import** 任何分支的模态库。
- 🔴 分支**不得跨分支调用**。
- 🔴 `payload` 结构**只在分支内定义**。
- 🔴 失败**不得无限重试**（≤max_retry）。
- 🔴 本地**不得触发真实训练**。
- 🔴 `target` **不得为 unknown/auto**。
- 🔴 真实 backbone 一律 **adapter 内可替换 + 默认 mock**。
