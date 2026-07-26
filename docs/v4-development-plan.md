# four-scene-brain · V4 开发文档（common + 完整独立 3D · 物理阵营 · 多任务）

> 版本：v1.0-plan ｜ 范围：**V4 = 通用层（冻结）+ `branches/3d` 扩展为全量独立 3D**
> 依据：`common-contract.md`（FROZEN）、`v1-development-plan.md`（物理阵营 + V1-3d 基线）、`v2/v3-development-plan.md`（模式参考）
> 前置：D1–D7 已拍板，common 已 FROZEN，V1+V2 已交付，V3 已就绪。**common 全程零改动。**
> backbone 候选：见 `oss-list-v4.md`（TRELLIS / DreamGaussian / TripoSR / Shap-E 等）
> **当前仍为设计文档，未写代码。**

---

## 0. V4 与 V1-3d 的关系（关键，先读懂）

契约 §1：**V1 的 `branches/3d` 专指「robot 的 3D 作业场景」**（机器人所处物理环境，与 WAM 物理先验强耦合）；**完整独立 3D 归 V4**。因此 V4 不是新建分支，而是**把 `branches/3d` 从"robot 作业场景"扩展为"全量独立 3D"**：

| 能力 | V1-3d（已交付） | V4-3d（本版扩展） |
|---|---|---|
| robot 作业场景（环境） | ✅ `task="robot_scene"` | 保留（向后兼容） |
| 文生 3D（text→3D） | ❌ | ✅ `task="text_to_3d"`（主推） |
| 概念图→3D（image→GLB） | ❌ | ✅ `task="image_to_3d"` |
| 点云补全 | ❌ | ✅ `task="pointcloud_completion"` |
| PBR 材质 | ❌ | ✅ `task="pbr_texture"` |

- **同一 `target="3d"`、同一 `modality="geometry"`**，经 **`adapter.build_bundle(task=...)`** 切换任务（沿用 V2 双模式 / V3 双方向的"构建期旋钮"模式）。
- **物理阵营**：V4-3d 继续与 robot 共享 `PhysicalWorldModelBase`（WAM 物理先验，场景侧可选基类）；文生3D 等生成式任务也复用其物理 State 工具函数。
- **common 零改动**：扩展只发生在 `branches/3d/` 内。

---

## 1. V4 目标与范围

**目标**：把 `branches/3d` 扩展为全量独立 3D，跑通「语言/图像指令 → 生成 3D（mesh/GLB）→ Critic 校验 → 交付 GLB → 遥测入飞轮」的最小闭环（多任务），验证物理阵营第二个分支的扩展同样不动 common。

**范围内（V4 做）**
- `branches/3d/` 扩展：新增 3d 专用 backbone 防腐层（`backbone_interface/backbone_mock`）、wam、critic、primitives、mapper、executor(GLB 导出)、safety_gate(双模式)、adapter(task 旋钮) + README
- 3d payload 结构定死（为将来换真 TRELLIS/DreamGaussian 做准备）
- SafetyGate 双模式（审核/放行）
- `examples/3d_full_demo`：多任务最小闭环（保留 V1 robot_scene 回归）
- 零 diff 验收 + V4 DoD 验收

**范围外（V4 不做）**
- ❌ 真 3D backbone 接入（上 Azure，V4 仍 mock）
- ❌ 实时渲染引擎 / UV 展开 / 骨骼绑定（属下游后处理）
- ❌ 跨分支飞轮全量集成（V5）
- ❌ 改动 robot/video/game 分支（只扩 3d）

---

## 2. V4 框架

```
输入(人语言 / 图像)
   ↓
┌─────────────── common（冻结，v1.0.0，V1+V2 已验证）───────────────┐
│  orchestrator：S1–S14 状态机（不动）                          │
│  registry / memory / flywheel（不动）                          │
└───────────────▲──────────────────────────────────────────────┘
        经接口契约 │（common 对 3d 完全无知）
   ┌─────────────┴──────────────────────────────┐
   │ branches/3d（物理 · geometry · 多任务）      │
   │  共享 PhysicalWorldModelBase（WAM 物理先验） │
   │  task="robot_scene"(V1保留) │ text_to_3d │ image_to_3d │      │
   │       pointcloud_completion │ pbr_texture                │
   │  backbone_interface/backbone_mock/wam/critic/             │
   │  primitives/mapper/executor(GLB)/safety_gate(双模式)/adapter │
   └─────────────────────────────────────────────┘
```

**关键**：common 对 3d 完全无知；任务差异全部走 `payload` + `config`/`meta`，不进 common。

---

## 3. V4 边界

**common 边界**：无场景名、无模态 if/else、不 import 分支、payload 不透明、纯 stdlib、重试 ≤max_retry。**V4 全程不改 common 一行。**

**3d 专属边界**：
1. **多任务经 adapter 旋钮**：`build_bundle(task=...)` 选任务；任务分支只在 3d 分支内部（payload/config/meta）。
2. **物理阵营共享到想象层**：与 robot 共享 `PhysicalWorldModelBase`（WAM 先验 + 物理 State 工具）；执行层（GLB 导出）各自实现。
3. **生成质量 vs 内容合规分离**：Critic 管「几何达标/保真/语义对齐」，SafetyGate 管「内容合规」（NSFW/版权角色）。不混淆。
4. **mock 不证明 3D 质量**：V4 mock 生成占位 mesh/GLB（确定性），验证编排闭环，不证明几何质量。真质量靠真 backbone on Azure。
5. **向后兼容**：`task="robot_scene"` 必须与 V1 行为一致（V1 demo/测试不回归）。
6. **本地只缓冲不训**：S14 仍走 FileBufferFlywheel。

---

## 4. V4 接口

**通用接口（冻结，V1+V2 已验证，V4 原样使用）**：
`WorldModel / Critic / PrimitiveLibrary / Mapper / Executor / SafetyGate / Memory / Flywheel` + 全部数据对象 + 枚举。

**场景侧共享基类（在 branches/，不进 common）**：`PhysicalWorldModelBase`（robot/3d 共享，V1 已建，V4 复用）。

**统一 3DBackbone 接口（防腐层，任务感知；不进 common）**：

```python
class ThreeDBackbone(ABC):
    def generate(self, prompt: str, config: dict) -> dict:
        # config 必含 "task": "robot_scene"|"text_to_3d"|"image_to_3d"|
        #                    "pointcloud_completion"|"pbr_texture"
        #   + 任务参数（source_image/source_pointcloud/resolution/poly_budget/retry/seed）
        # 返回 dict 必含 "task" + 任务专属字段 + "meta"
    def get_info(self) -> dict: ...
```

**3d payload 结构（分支冻结，写进分支 README；多任务）**：
```
task:           str                 # robot_scene | text_to_3d | image_to_3d | pointcloud_completion | pbr_texture
representation: str                 # gaussians | pointcloud | mesh | glb
geometry:       dict                # mock: {"vertices": int, "faces": int, "manifold": bool, "bbox": [...]}
semantics:      list[str]           # 语义标注（red cup / table / walkable / ...）
texture:        dict | None         # task=pbr_texture 时: {"albedo": ..., "roughness": ..., "metallic": ...}
source:         str                 # 文本 prompt 或 输入图像/点云占位引用
text_prompt:    str
# mock 附加：scene_description / refined_times
```

**3d Critic 成功标准（按 payload["task"] 分派）**：
- **通用几何硬指标**：`geometry.manifold=True`、`vertices>0`、`faces>0`、`bbox` 非退化（三轴尺寸>0）。
- **任务专属**：
  - text_to_3d：text-3D 语义对齐（semantics 与 prompt 关键词重叠）
  - image_to_3d：source 一致性（mock 校验 source 引用与输出 geometry 绑定）
  - pointcloud_completion：补全后点数 ≥ 输入点数，无 NaN/越界
  - pbr_texture：texture 含 albedo/roughness/metallic 且在 [0,1]
  - robot_scene：可行走性 + 几何保真（V1 标准，保持不回归）
- 判定来源写入 `Verification.meta.verification_source`（含 task）。

**3d SafetyGate（双模式）**：

| 模式 | 检查 | 结果 |
|---|---|---|
| `audit`（默认） | text_prompt 含 NSFW/版权角色关键词 | BLOCK |
| `audit` | geometry 顶点数低于下限 / bbox 退化 | DEGRADE |
| `audit` | 一切正常 | PASS |
| `passthrough` | 无检查 | PASS |

**3d Executor**：输出 GLB 占位文件（纯 stdlib：写最小合法 GLB 头 JSON+BIN chunk 到 `output/3d/model_<hash>.glb`）。

---

## 5. V4 开发计划（阶段拆解）

> 顺序即依赖；每阶段带自测。纯 stdlib，零三方依赖。common 零改动。`branches/3d/` 在 V1 基础上扩展（新增 backbone 层 + 多任务），不删 V1 robot_scene 能力。

| 阶段 | 产出 | 验收 |
|---|---|---|
| **P0 3d 关键词扩展** | `branches/3d/scene_objects.py` 扩：物体/材质/场景/属性关键词（双语） | 关键词解析自测 |
| **P1 3DBackbone 接口** | `branches/3d/backbone_interface.py`（任务感知 `generate`/`get_info`） | 抽象不可实例化自测 |
| **P2 Mock 3D backbone** | `branches/3d/backbone_mock.py`（多任务确定性几何；retry 提升 manifold/对齐） | 相同 prompt 相同结果自测 |
| **P3 3d WAM 扩展** | `branches/3d/wam.py`（继承 PhysicalWorldModelBase，调 backbone，传 task） | predict_next_state 自测 |
| **P4 3d Critic 扩展** | `branches/3d/critic.py`（按 task 分派：几何达标 + 任务对齐） | verify 自测 |
| **P5 3d Primitives 扩展** | `branches/3d/primitives.py`（mesh 基元：extrude/smooth/texture/weld） | abstract 自测 |
| **P6 3d Mapper 扩展** | `branches/3d/mapper.py`（基元 → 3d Executable，含 GLB spec） | map 自测 |
| **P7 3d Executor + SafetyGate** | `branches/3d/executor.py`（GLB 占位）+ `safety_gate.py`（双模式） | execute/check 自测 |
| **P8 3d Adapter 扩展** | `branches/3d/adapter.py` + `register()`（`task` 旋钮） | 注册自测 + V1 robot_scene 回归 |
| **P9 Demo + 零 diff** | `examples/3d_full_demo.py`（多任务）+ `tests/test_zero_diff.py` 加 3d 全量 | common git diff 为空 |

**冻结纪律**：P0–P8 是 3d 分支内部；P9 是验收，不通过不许合入。**V1 robot_scene 不得回归。**

---

## 6. V4 依赖

- **运行时**：Python 3.13（托管），**仅用标准库**。
- **开发依赖**：pytest（已装）。
- **不装**：任何大模型 / GPU 依赖（V4 全 mock）。
- **真 backbone**：TRELLIS / DreamGaussian / TripoSR / Shap-E 走 Azure（接入前过 `engineering-setup.md` §2 五道门禁；选型见 `oss-list-v4.md`）。

---

## 7. V4 验收 DoD

1. **text_to_3d 最小闭环**：输入「生成一个红色杯子的 3D 模型」→ S1–S14 → 输出占位 GLB + 带 trace_id 的 Telemetry。
2. **image_to_3d 最小闭环**：输入「概念图 → 3D GLB（一把椅子）」→ S1–S14 → 输出占位 GLB。
3. **重试路径**：演示一次 S9 失败（geometry 退化：faces=0 / 非 manifold）→ 回 S7 → 成功。
4. **SafetyGate 审核模式**：含版权角色关键词 prompt → BLOCK。
5. **SafetyGate 放行模式**：同一 prompt → PASS（验证双模式可切换）。
6. **V1 robot_scene 回归**：`examples/3d_scene_demo` 与相关测试仍通过。
7. **零 diff 验收**：`tests/test_zero_diff.py` 通过，`common/` git diff 为空。
8. **RunMetrics**：输出成功率 / 重试次数 / 各 Critic 分（含 task）。
9. **边界声明**：README 注明「验证编排内核，不证明 3D 质量」。

---

## 8. V4 风险与红线

- 🔴 3d 分支泄漏逻辑到 common → 冻结失败（零 diff 测试兜底）。
- 🔴 3d payload 没定死 → 将来换真 TRELLIS 要重构（P0/P4 定死规避）。
- 🔴 任务分支写进 common/orchestrator → 违反铁律 2（任务只走 payload/config/meta）。
- 🔴 扩展破坏 V1 robot_scene → P8 回归兜底（V1 能力不许丢）。
- 🟠 误把 mock 3D 质量当真 → DoD 第 9 条声明规避。
- 🔴 SafetyGate 审核误伤正常 prompt（"骷髅摆件"这类正常 3D 题材）→ 关键词列表保守，宁可漏不可错杀。

---

## 9. V4 与 V1/V2/V3 的差异对比

| 维度 | V1（robot+3d） | V2（video） | V3（game 双方向） | V4（完整 3D 多任务） |
|---|---|---|---|---|
| 阵营 | 物理 | 像素 | 像素 | **物理** |
| 共享基类 | PhysicalWorldModelBase | 无 | 无 | **PhysicalWorldModelBase（复用）** |
| 分支动作 | 新建 robot+3d | 新建 video | 新建 game | **扩展 3d（V1→全量）** |
| 任务/方向 | — | — | 双方向（level/worldmodel） | **多任务（robot_scene/text/image/pointcloud/pbr）** |
| payload | pose/twist/wrench | frames/fps/duration | level_map / frames+action | **geometry/semantics/texture/task** |
| Critic | force-torque | duration/fps/res | 可玩性/动作一致性 | **几何达标 + 任务对齐** |
| Executor | 零力矩/GLB占位 | mp4 | level JSON / replay | **GLB 占位** |
| backbone | GR00T/DreamGaussian | HunyuanVideo | MarioGPT/GameGen-O | **TRELLIS/DreamGaussian/TripoSR** |
