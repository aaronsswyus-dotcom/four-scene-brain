# four-scene-brain · 整体开发文档（方案 / Scheme）

> 状态：规划文档 v0.1（尚未开始写代码）。
> 定位：复用现成开源模型填满四分支，只自研「通用主干的编排层 + 统一接口 + 跨分支数据飞轮」。
> 核心命题：**大脑 = 编排器（Orchestrator）**，组装而非重训。

---

## 0. 一句话结论（环境可运行性）

| 层 | 能否在本机跑 | 说明 |
|---|---|---|
| 编排层 + 接口契约 + 四分支适配器（**mock 主干**） | ✅ 能，纯 Python 标准库即可 | 这是项目的"大脑"，也是自研重点 |
| 真实开源主干（GR00T / GameGen-O / DreamGaussian / HunyuanVideo） | ❌ 不能（本机无 NVIDIA GPU，需 CUDA + 大显存 + 长下载） | 走 Azure 云端推理/训练，本机只留适配接口 |
| Mem0 本地记忆封装 | ⚠️ 可选 | 最小闭环用内存版 mock 即可，零三方依赖 |
| **最小闭环** | ✅ 能跑通 | 全 mock 主干 → CPU 上端到端验证 9 工序闭环 |

**结论**：本机可以跑"最小闭环"（编排 + 接口 + 全 mock 适配器），用来验证架构与数据飞轮；真实生成能力需上云（Azure）或在带 GPU 的机器上插主干。这恰好印证了项目设计——**先让大脑闭环跑起来，主干可插拔后补**。

---

## 1. 项目背景与闭环

**定位**：four-scene-brain = 一个统一编排大脑，把"人语言 / 机器自观"输入路由到四个世界模型分支（机器人 / 游戏 / 3D / 视频），各自生成后由 Critic 校验，遥测回灌形成数据飞轮。

**主闭环**：
```
输入(人语言/机器自观) → 大脑决策 → 小脑执行 → 交付结果 → 数据回灌大脑(自改进)
```

**大脑/小脑/编排 ↔ 9 工序（S1–S14）映射**
- 编排 S5 ｜ 大脑 S2–S4 编码/意图/分解 + S7 世界想象 + S9 自主校验 ｜ 记忆 S6 ｜ 小脑 S8 生成 + S10 基元 + S11 映射 + S12 执行 ｜ 飞轮 S13–S14

**两个自然聚类**
- **物理阵营 {机器人, 3D}**：共享 WAM 物理先验，WAM 复用度最高。
- **像素阵营 {游戏, 视频}**：共用生成式 WM 家族，视频物理约束最松、最易出金流。

**接口契约（四分支零改动插入的基石）**
```python
WorldModel.predict_next_state(state, goal) -> State   # S7 世界想象
Critic.verify(draft, goal) -> Verification            # S9 自主校验
PrimitiveLibrary.abstract(draft) -> Primitive[]        # S10 基元抽象
```

**流水线**：FAB5（录入提示词 → 生成运行时）→ 微软 Azure（推理/训练/飞轮）→ GitHub（发布）。

---

## 2. 待开发目录结构（含职责 + 开发状态）

```
four-scene-brain/
├── common/                      # 通用主干（自研核心，四场景共享）
│   ├── interfaces/              # 【自研】WorldModel / Critic / PrimitiveLibrary 抽象基类 + State/Draft/SubGoal 状态对象
│   ├── orchestrator/            # 【自研】9 工序 pipeline + Registry(分支注册) + Hooks(工序钩子)
│   ├── memory/                  # 【自研封装】Mem0 本地封装（最小闭环可先用内存 mock）
│   └── flywheel/                # 【自研】S13 回收 + S14 自改进（推理即训练回灌）
│
├── branches/                    # 四分支适配器（各自实现接口，调开源主干）
│   ├── robot/                   # 物理阵营：wam(WorldModel) / critic / primitives / mapper(手部DOF) / adapter(注册)
│   ├── game/                    # 像素阵营：adapter(WorldModel) / critic / primitives / mapper / runtime / README
│   ├── 3d/                      # 物理阵营：adapter(WorldModel) / critic / primitives / mapper(Mesh) / exporter(GLB) / README
│   └── video/                   # 像素阵营：adapter(WorldModel) / critic / primitives / mapper(扩散) / exporter(mp4) / README
│
├── examples/                    # 【自研】跑通闭环的 demo（每分支一个最小可跑样例）
├── prompts/                     # 8 个完整提示词（见第 3 节，按 orchestrator→接口→四分支→用户指令 顺序）
└── docs/                        # scheme.md（本文件）+ 后续架构/许可细节
```

**开发状态标记**
- 🔴 未开始　🟠 设计中　🟢 可跑（mock）
- `common/interfaces` 🔴｜`common/orchestrator` 🔴｜`common/memory` 🔴｜`common/flywheel` 🔴
- `branches/*` 🔴（均先以 mock 主干落地，再换真主干）
- `examples/` 🔴｜`prompts/` 🟢（提示词已就绪，待落盘）｜`docs/scheme.md` 🟢（本文件）

---

## 3. 用到的开源内容清单（组装而非自研）

### 3.1 四分支"世界模型"主干（默认 backbone，可替换）

| 分支 | 默认主干 | 许可风险 | 备选（同接口可换） |
|---|---|---|---|
| 机器人 (WAM) | **NVIDIA GR00T** | ⚠ 商用需审 NVIDIA 许可 | OpenVLA、LeRobot |
| 游戏 (sim) | **GameGen-O** | ⚠ 见其 repo 许可 | GameGen-X、Oasis |
| 3D (3DGS/NeRF) | **DreamGaussian** | 相对友好（见 repo） | threestudio、InstantMesh |
| 视频 (像素/时序) | **HunyuanVideo** | ⚠ 许可需核查 | Wan2.1、CogVideoX、LTX、SVD |

> 这些主干**不写进本机代码**，只在 `branches/*/adapter.py` 里以"可替换 backbone"形式引用（默认 mock，真主干走 Azure）。

### 3.2 支撑型开源（本机/云端都可能用到）

| 用途 | 组件 | 备注 |
|---|---|---|
| 记忆封装 | **Mem0** | 本地封装；最小闭环可用内存 mock 替代 |
| 3D 资产读写 | trimesh / pygltflib / USD-Python | 导出 GLB/USD/FBX |
| 视频读写 | imageio-ffmpeg / OpenCV | 导出 mp4、占位短片 |
| 3DGS/NeRF 运行时 | nerfstudio（可选） | 真 3D 主干上云时 |
| Schema 校验 | pydantic（可选） | 接口对象可用 dataclass 替代，零依赖 |
| 云端训练/推理 | 微软 Azure ML | 真主干推理与飞轮回灌 |

### 3.3 运行时依赖评估

- **最小闭环（mock 主干）**：仅 Python 3.13 标准库（`dataclasses` / `abc` / `typing` / `json` / `enum` / `asyncio`）→ **本机零安装即可跑**。
- **接真主干**：需对应 CUDA 环境 + 各主干依赖（通常在 Azure 或 GPU 机器完成）。

---

## 4. 最小可运行闭环（本机版）

**目标**：不依赖任何 GPU / 大模型，纯标准库跑通 S1→S14 全工序，证明"大脑=编排器"成立。

**以机器人分支为例的最小闭环**：
1. **S1 输入**：人语言指令 `"用灵巧手把桌上的红色杯子拿到托盘里"`
2. **S2 编码**：文本 → 结构化表示
3. **S3 意图**：`target = robot`
4. **S4 分解**：`SubGoal[] = [抓红色杯子, 放到托盘]`
5. **S5 路由**：Registry 选 `RobotWorldModel`
6. **S6 记忆**：内存版 mock 记忆（不依赖 Mem0 联网）
7. **S7 世界想象**：`RobotWorldModel.predict_next_state(state, sub_goal)` → **mock 物理态**（假设可达，返回占位 State）
8. **S8 生成**：动作轨迹（mock 序列）
9. **S9 校验**：`RobotCritic.verify(draft, sub_goal)` → `passed=True, score=0.9`（mock 成功检测）
10. **S10 基元**：`RobotPrimitives.abstract` → `[grasp, place]`
11. **S11 映射**：`HandMapper.map` → 关节角 / **零力矩 mock Executable**
12. **S12 执行**：mock 执行器打印指令（不接真实硬件手）
13. **S13 回收**：记录遥测（力矩/触觉占位）
14. **S14 自改进**：遥测回灌（mock 写入飞轮缓冲）

> 四分支的"最小闭环"结构完全一致，只是 S7–S12 的材质不同：游戏=mock 关卡 JSON、3D=占位 GLB、视频=占位 mp4。
> **关键点**：S9 校验失败可回退 S4/S7 重做（≤max_retry），这层逻辑本机即可验证。

---

## 5. 开发阶段建议（待你授权后执行）

| 阶段 | 内容 | 产出 |
|---|---|---|
| P0 接口契约 | `common/interfaces` 三个 abc + 状态对象 | 零依赖、可单测 |
| P1 编排器 | `common/orchestrator` pipeline + Registry + Hooks | 能跑路由 |
| P2 分支 mock | 四分支适配器（全 mock 主干）+ `examples/` 最小闭环 | 本机端到端跑通 |
| P3 记忆/飞轮 | `common/memory` + `common/flywheel` | S13–S14 可用 |
| P4 接真主干 | Azure 上替换 backbone（GR00T/GameGen-O/...） | 真实生成能力 |
| P5 发布 | GitHub 发布 + FAB5 提示词固化 | 可复用 |

---

## 6. 风险提示

- 🔴 **许可**：GR00T / HunyuanVideo 商用需审；GameGen-O 见 repo。本机只 mock，规避风险；接真主干前必须走许可核查。
- 🟠 **环境**：本机无 GPU，真实生成务必上云；不要试图在本机 pip 装大模型。
- 🟢 **架构**：接口契约稳定后，四分支可并行推进，互不阻塞。
