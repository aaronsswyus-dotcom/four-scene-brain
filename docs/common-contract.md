# four-scene-brain · 通用层契约（Common Contract · 冻结基线）

> 版本：v1.0-**FROZEN**（2026-07-26 拍板生效）｜ 适用范围：V1–V5 全部版本
> 本文件是**通用层（common/）的唯一权威参考**。V2/V3/V4/V5 开发时**只允许读它，不允许改 common/**。
> 与 boundaries.md / pre-dev-gap-analysis.md 一致；G1–G6 缺口已并入本契约的数据模型。

---

## 0. 一句话定位 + 三条铁律

**通用层 = 编排内核（modality-agnostic kernel），对四场景完全无知；场景 = 通过 Registry 插入的插件。**

- **铁律 1 · 写一次，永冻结**：common/ 合入后，V2/V3/V4 开发只允许新增 `branches/<scene>/`，**common/ 零改动**。
- **铁律 2 · 场景即插件**：common/ **不出现**任何场景名、backbone 名、模态 if/else；一切场景差异经 `payload`（不透明）+ `meta`（可扩展 dict）承载。
- **铁律 3 · 唯一交换语言**：common 与各场景之间只交换本文件 §4 定义的数据对象、§5 定义的接口签名。

---

## 1. 版本战略与打包

五个版本（V1–V4 为单场景，V5 为全场景集成），每个都是「common（冻结、pin 版本）+ 场景包」的**独立端到端项目**：

| 版本 | 组合 | 场景包 | 阵营 | 交付物 |
|---|---|---|---|---|
| **V1** | common + physical | `branches/robot` + `branches/3d`（仅 robot 作业场景） | 物理 | 机器人闭环 + robot 的 3D 作业场景 |
| **V2** | common + video | `branches/video` | 像素 | 视频闭环（mp4，金流场景） |
| **V3** | common + game | `branches/game` | 像素 | 游戏闭环（可玩关卡） |
| **V4** | common + 3d（完整独立） | `branches/3d`（全量 3D） | 物理 | 独立 3D 场景（文生3D / 概念图→GLB / 点云补全 / PBR） |
| **V5** | 全场景集成 | common + 全部分支 | — | 跨分支数据飞轮 + 发布 |

> 说明（2026-07-26 定稿）：**共 5 个版本**。**V1 的 3d 专指「robot 的 3D 作业场景」**（机器人所处/操作的物理环境，与 WAM 物理先验强耦合），**不是所有 3D 场景**；完整独立的 3D 能力归 **V4**。robot 与 V1-3d 经 `PhysicalWorldModelBase`（场景侧可选基类，不在 common 内核）共享 WAM 物理先验。`branches/3d` 在 V1 先交付 robot 场景部分，V4 扩为全量 3D——**common 始终不变**。

**打包纪律**：`common/` 自带 `__version__`（如 1.0.0）；每个版本 pin 同一个 common 版本号。发现 common bug 时只升补丁号且**接口向后兼容**，绝不为新场景改接口。

---

## 2. 通用的范围边界（在 / 绝不在 common）

| ✅ 必须在 common（冻结） | ❌ 绝不在 common |
|---|---|
| 数据对象（§4） | 任何场景名 / backbone 名（GR00T、HunyuanVideo…） |
| 接口抽象（§5） | 任何 `if modality == ...` / `if target == ...` |
| Orchestrator 状态机（§6） | 任何 payload 结构知识 |
| Registry 插件机制（§7） | 任何场景专属 success criteria |
| Memory / Flywheel 机制（§8） | 任何真实生成逻辑 / 硬件驱动 |
| FailureKind / SafetyVerdict 枚举 | 任何三方重依赖（v1 纯 stdlib） |

**判据**：凡"换个场景就要改"的代码，一律不在 common。

---

## 3. 通用模块划分与职责

```
common/
├── interfaces/    # 数据对象(§4) + 抽象接口(§5)：唯一交换语言
├── orchestrator/  # S1–S14 状态机 + DAG 拓扑 + 重试 + 遥测聚合（§6）
├── registry/      # BranchBundle 注册与解析（§7）
├── memory/        # S6 记忆读写机制（接口 + 内存实现）（§8）
└── flywheel/      # S13 回收 + S14 自改进缓冲（§8）
```

- `interfaces` 与 `registry` 是**冻结核心**；`orchestrator` 依赖它们，不含场景逻辑。
- `memory`/`flywheel` 提供**默认内存实现**（最小闭环零依赖），真 Mem0 / 云端实现走同接口替换。

---

## 4. 数据对象全集（The Language · field 级 · 冻结）

> 设计要点：`payload` 一律 opaque；`meta: dict` 是唯一扩展口（含 trace_id/session_id/schema_version）。**common 永不为新场景加字段。**

```python
# ---- 路由/模态：自由字符串，由场景注册时声明；common 仅透传与相等校验 ----
# 已知约定（非 enum，保证冻结）：modality ∈ {physical, sim, geometry, pixel}
#                              target   ∈ {robot, game, 3d, video}

@dataclass
class State:
    modality: str
    payload: object                 # opaque，场景自定义
    meta: dict                      # trace_id / session_id / schema_version / ...

@dataclass
class SubGoal:                      # G1：结构化 + DAG
    id: str
    target: str                     # 路由键
    goal: str
    success_criteria: str
    depends_on: list[str]           # 前置 SubGoal id（顺序依赖 → DAG）
    constraints: dict               # 模态无关约束（timeout_s / safety_level / ...）
    priority: int = 0

@dataclass
class Intent:                       # S3 产物
    raw: str
    source: str                     # 'human' | 'self_observe'
    subgoals: list[SubGoal]

@dataclass
class Draft:
    modality: str
    payload: object                 # opaque
    meta: dict

class FailureKind(Enum):            # G2：错误 taxonomy（冻结枚举，属"语言"）
    NONE = "none"
    RETRYABLE_QUALITY = "retryable_quality"      # 回 S7
    STRUCTURAL_INFEASIBLE = "structural_infeasible"  # 回 S4
    HARDWARE_OFFLINE = "hardware_offline"        # 终止
    LICENSE_BLOCKED = "license_blocked"          # 终止/降级
    TIMEOUT = "timeout"                          # 有限重试

@dataclass
class Verification:
    passed: bool
    score: float
    reason: str
    failure_kind: FailureKind = FailureKind.NONE
    meta: dict = None

@dataclass
class Primitive:
    kind: str                       # 场景自定义：grasp/place/attack/wall/cut...
    params: dict
    meta: dict

@dataclass
class Executable:
    modality: str
    payload: object                 # 关节力矩 / 引擎指令 / mesh / 像素帧
    meta: dict

@dataclass
class Delivery:
    target: str
    artifact: object                # 最终交付物（路径/句柄/描述）
    meta: dict

@dataclass
class Telemetry:                    # G3：带 trace_id，S13 统一回收
    trace_id: str
    subgoal_id: str
    kind: str                       # 'torque'|'player'|'geometry'|'watch'|...
    data: dict
    ts: float

@dataclass
class RunMetrics:                   # G6：全局闭环度量（可验证命题）
    trace_id: str
    success: bool
    retries: int
    duration_s: float
    critic_scores: list[float]
    meta: dict = None

class SafetyVerdict(Enum):          # G5
    PASS = "pass"
    DEGRADE = "degrade"
    BLOCK = "block"
```

---

## 5. 接口全集（The Membrane · 签名 · 冻结）

> 场景只**实现**这些接口；common 只**调用**这些接口。签名一字不改。

```python
class WorldModel(ABC):              # S7 世界想象 → 返回候选 State（想象/生成在内）
    @abstractmethod
    def predict_next_state(self, state: State, goal: SubGoal) -> State: ...

class Critic(ABC):                  # S9 自主校验
    @abstractmethod
    def verify(self, draft: Draft, goal: SubGoal) -> Verification: ...

class PrimitiveLibrary(ABC):        # S10 基元抽象
    @abstractmethod
    def abstract(self, draft: Draft) -> list[Primitive]: ...

class Mapper(ABC):                  # S11 映射 → 可执行
    @abstractmethod
    def map(self, primitives: list[Primitive], goal: SubGoal) -> Executable: ...

class Executor(ABC):                # S12 执行 → 交付
    @abstractmethod
    def execute(self, executable: Executable) -> Delivery: ...

class SafetyGate(ABC):              # S11→S12 之间；physical 必须实现，其余可默认放行
    @abstractmethod
    def check(self, executable: Executable) -> SafetyVerdict: ...

class Memory(ABC):                  # S6
    @abstractmethod
    def read(self, query: str, top_k: int = 5) -> list[dict]: ...
    @abstractmethod
    def write(self, item: dict) -> None: ...

class Flywheel(ABC):                # S13 + S14
    @abstractmethod
    def record(self, telemetry: Telemetry) -> None: ...   # S13
    @abstractmethod
    def distill(self) -> None: ...                        # S14（本地缓冲/云端回灌）
```

**S8 的定位（关键设计决定）**：S8"生成"不单独设接口。`WorldModel.predict_next_state` 返回的候选 State，由 **Orchestrator 通用包装成 Draft**（`Draft.modality=state.modality, Draft.payload=state.payload`），**不含场景知识**。场景内"重生成"（如扩散解码、动作轨迹细化）发生在 S7 内部或 S11 映射里。
> ⚠️ 这与 D2（想象/生成分离）的折中：想象 API 是 `predict_next_state`，"生成"被分布到 S7 内部 + S10 抽象 + S11 映射。请你确认这一融合是否接受（见 §12 新增决策 D6）。

---

## 6. 编排器工作机制（S1–S14 状态机）

`Orchestrator(registry, memory, flywheel, max_retry=3).run(raw_input, source) -> RunMetrics`

1. **S1 输入**：接收 `raw_input` + `source`（human/self_observe），生成 `trace_id`。
2. **S2 编码**：把输入编码为初始 `State`（模态由后续路由分支决定，此处仅承载原始表示）。
3. **S3 意图**：解析为 `Intent`（v0 用规则/模板解析；LLM 解析为可选插件）。
4. **S4 分解**：产出 `SubGoal[]`，按 `depends_on` 做 **DAG 拓扑排序**（复合指令串/并行由 DAG 决定）。
5. 对每个 SubGoal（按拓扑序，physical 串行）：
   - **S5 路由**：`registry.resolve(subgoal.target)` → `BranchBundle`；未注册 → 直接失败。
   - **S6 记忆**：`memory.read(...)` 取上下文。
   - **S7 想象**：`world_model.predict_next_state(state, subgoal)` → candidate State。
   - **S8 包装**：State → Draft（通用）。
   - **S9 校验**：`critic.verify(draft, subgoal)`。
     - passed=False → 按 `failure_kind`：RETRYABLE_QUALITY/TIMEOUT → 回 S7；STRUCTURAL_INFEASIBLE → 回 S4 重分解；HARDWARE_OFFLINE/LICENSE_BLOCKED → 终止。**retry 计数 ≤ max_retry，超出返回失败。**
   - **S10 基元**：`primitives.abstract(draft)` → Primitive[]。
   - **S11 映射**：`mapper.map(primitives, subgoal)` → Executable。
   - **SafetyGate**：`safety_gate.check(executable)`；BLOCK → 终止，DEGRADE → 降级重映射。
   - **S12 执行**：`executor.execute(executable)` → Delivery。
   - **S13 回收**：`flywheel.record(Telemetry(...))`。
6. **S14 自改进**：`flywheel.distill()`（本地缓冲；云端回灌）。
7. 汇总 `RunMetrics` 返回。

**State 跨 SubGoal 串联（DAG）**：存在 `depends_on` 依赖时，前序 SubGoal 执行后的 State/观察作为后序 SubGoal 的输入上下文（如 robot「开门→推车」：开门后的世界态喂给推车）。Orchestrator 负责按拓扑序传递 State，**不解析其 payload**。

**分支异常 → FailureKind 映射**：Orchestrator 对分支接口调用一律 try/except；异常映射为 FailureKind（超时→TIMEOUT、硬件→HARDWARE_OFFLINE、许可→LICENSE_BLOCKED、其余→RETRYABLE_QUALITY），再按上述重试/终止规则处理。**分支异常不穿透 common。**

**并发模型（G4）**：v0 **同步**实现；接口签名天然可包 `async`，升级不破坏契约。

---

## 7. 注册 / 插件机制（场景零改动接入）

```python
@dataclass
class BranchBundle:                 # 一个场景的全套实现，注册时一次性提交
    target: str
    modality: str
    world_model: WorldModel
    critic: Critic
    primitives: PrimitiveLibrary
    mapper: Mapper
    executor: Executor
    safety_gate: SafetyGate | None = None   # physical 必须提供

class Registry:
    def register(self, bundle: BranchBundle) -> None: ...
    def resolve(self, target: str) -> BranchBundle: ...   # 未注册 → KeyError
```

- 场景包自带 `register(registry)` 函数；**Orchestrator 只经 Registry 发现场景，绝不 import 场景模块**。
- 路由时校验 `bundle.modality == state.modality`（通用字符串相等校验）。

---

## 8. 飞轮与记忆（通用机制）

- **Memory（S6）**：接口 + 默认 `InMemory` 实现（dict 存储）。真 Mem0 封装实现同接口替换，common 不变。
- **Flywheel（S13/S14）**：
  - S13 `record`：统一收 Telemetry（robot 力矩 / game 玩家 / 3d 几何 / video 观看质量——**kind/data 由场景填，common 只存**）。
  - S14 `distill`：默认实现=落盘/缓冲（**本地只写不训**）；云端回灌实现走同接口（Azure 周期回灌各分支 WM）。

---

## 9. "写一次不改"的保证机制 + 零 diff 验收

**为什么敢冻结**：
1. 场景差异只走 `payload`（opaque）+ `meta`（dict）→ common 永不加字段。
2. `target/modality` 是自由字符串、Registry 注册 → common 零场景枚举/硬编码。
3. Orchestrator 只经 Registry 发现场景 → 新增场景不动 orchestrator。

**零 diff 验收测试（冻结就绪判据）**：
> 临时实现一个**全新的 mock 场景**（随便编一个 target，如 `mock5`），要求：
> (a) 只新增 `branches/mock5/` 一个包；
> (b) `common/` **git diff 为空**；
> (c) 能注册并被 orchestrator 路由跑通。
> 三者全过 ⇒ common 真正 write-once；任何一项要改 common ⇒ 说明契约还有场景泄漏，必须回补。

---

## 10. 通用层质量红线与验收 DoD

**红线**：
- 🔴 common 无任何场景/backbone 字符串、无模态 if/else。
- 🔴 common 不 import 任何 `branches/`。
- 🔴 接口签名与数据对象字段一字不改（只允许 meta 内扩展）。
- 🔴 v1 纯 stdlib，零三方依赖。
- 🔴 重试 ≤ max_retry，绝不无限循环；未注册 target 直接失败。

**通用层 DoD（V1 放行前）**：
1. §4/§5 全部对象与接口实现，含 `__main__` 自测。
2. Orchestrator 跑通一条 physical 指令 S1–S14（含 DAG、一次 S9 失败重试、SafetyGate）。
3. **零 diff 验收测试通过（§9）**。
4. 输出带 trace_id 的 Telemetry + RunMetrics。
5. 声明边界：验证编排内核，不证明单场景物理可行性。

---

## 11. 冻结纪律（common 变更规则）

- 允许：升补丁号修 bug（接口向后兼容）、meta 内新增约定键、`Memory`/`Flywheel` 新增**实现**（不改接口）。
- 禁止：改 §4 字段、改 §5 签名、在 common 加场景逻辑、为新场景开口子。
- 任何"看似必须改 common"的需求 → 先问：能否用 `payload`/`meta`/新实现解决？能 ⇒ 不改；不能 ⇒ 升级 **common 主版本** 并全版本回归（极慎重）。

---

## 12. D1–D7 拍板结果（2026-07-26 · 全部采纳推荐 · 契约冻结）

| # | 决策点 | 推荐 |
|---|---|---|
| D1 | 编排器形态 | B 规则状态机 v0（LLM 作 S3/S4 可选插件） |
| D2 | S7/S8 语义 | **D6 融合方案**（见 §5：predict 返回候选，S8 通用包装，生成分布到 S7内部/S10/S11） |
| D3 | 跨分支复合指令 | A 允许（SubGoal DAG 各自路由） |
| D4 | S14 重训 | B 周期回灌（本地只缓冲） |
| D5 | Critic 自由度 | A 统一签名 + 场景自定义 criteria |
| **D6** | S8 是否单独设 Generator 接口 | **否**（保持 3 主接口 + Mapper/Executor/SafetyGate，S8 通用包装） |
| **D7** | modality/target 用自由字符串而非 enum | **是**（保证冻结；类型安全靠 Registry 校验） |

> ✅ **2026-07-26 已全部按推荐拍板通过，本契约正式 FROZEN。** V1（common + physical）可放行开发；V2–V5 严格按 §13 接入，不得改 common。后续若必须动 common，走 §11 主版本升级流程。

---

## 13. 新场景接入清单（V2/V3/V4 作者按此执行，禁止改 common）

> 本契约是**通用层唯一权威参考**。开发 V2/V3/V4 时，把本文件作为上下文，严格按下列步骤接入，**全程不得修改 `common/`**。

1. **复制模板**：以 `branches/_template`（或现有分支）为底，新建 `branches/<scene>/`。
2. **定 target / modality**：选定本场景的路由键与模态字符串（如 video→`pixel`）。
3. **实现 5+1 接口**：`WorldModel` / `Critic` / `PrimitiveLibrary` / `Mapper` / `Executor`，按需加 `SafetyGate`（physical 必须，video 可用于内容审核）。
4. **定义场景私有结构**：本场景 `State.payload` 结构与 `success_criteria` 写进**分支 README**，不进 common。
5. **backbone 默认 mock**：真主干（HunyuanVideo/GameGen-O…）在 adapter 内可替换，默认 mock；真实推理走 Azure。
6. **写 `register(registry)`**：把 `BranchBundle` 注册进 Registry。
7. **写 `examples/<scene>_demo`**：该场景最小闭环。
8. **零 diff 验收（§9）**：`common/` git diff 必须为空，否则说明有场景泄漏，回补契约。
9. **跑该场景 DoD**：S1–S14 + 一次 S9 失败重试 + 带 trace_id 的 Telemetry/RunMetrics。

> 任一环节让你觉得"非改 common 不可" → 先读 §11 冻结纪律：能用 payload/meta/新实现解决就不改；不能才升级 common 主版本。
