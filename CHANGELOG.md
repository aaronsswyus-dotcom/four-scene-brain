# Changelog · 变更日志

All notable changes to **four-scene-brain** are documented here.
本项目的所有重要变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号遵循 [SemVer](https://semver.org/lang/zh-CN/) 的近似约定。

> 注：V1–V5 是"**组合（combination）**"标签而非严格语义版本；`common/` 冻结内核版本恒为 `1.0.0`（见 `docs/common-contract.md` §1 打包纪律）。

---

## [V5.0.0] — 2026-07-26

**全场景集成 + 跨分支数据飞轮 + 发布**。这是"大脑 = 编排器"终局命题的验证：**一个冻结内核同时驱动四个场景（robot/3d/video/game），且跨场景 Telemetry 汇入同一飞轮**。集成版本，**不新建分支、不接新 backbone、不改 common**。

### Added / 新增
- **`examples/_flywheel_view.py`** — 跨分支遥测聚合视图（纯 stdlib，读 FileBufferFlywheel 落盘 jsonl，按 `kind`→`branch` 分组：`torque`→robot / `geometry`→3d / `video`→video / `game`→game；输出 count / 唯一 trace / avg_score）。**只读不写回，放 examples/ 侧，不进 common**。
- **`examples/integration_demo.py`** — 四分支注册到同一 Registry，跑通 2 条跨分支复合指令：
  - **A（3d→robot，State 串联 DAG）**：「生成机器人作业客厅 3D 场景，再让机器人把红杯拿到托盘」→ `[3d(robot_scene), robot depends_on 3d]`。
  - **B（video+game，像素阵营）**：「生成猫奔跑视频 + 可玩平台关卡」→ `[video, game]`。
  - S4 分解用规则/模板（关键词→target/depends_on），**不接 LLM**（D1/D3：LLM 解析为可选插件）；末尾打印跨分支飞轮聚合视图。
- **`tests/test_integration.py`**（7 pytest）：跨分支 DAG + depends_on 强制排序 + 像素复合 + 统一飞轮聚合 + 单分支不回归 + 四 target 同注册 + 集成后 `common/` git diff 为空。

### Changed / 变更
- `README.md`：状态表 V1–V5 全标 ✅ 已交付；Quick Start 补 `game_demo` / `3d_full_demo` / `integration_demo`；测试数 → **72**。
- 全量测试 **72/72 PASS**（V1–V4 65 + V5 集成 7）；全部 6 个 demo 不回归。

### 边界声明 / Boundary
- V5 验证**集成与跨分支飞轮闭环**（冻结内核多场景并发驱动 + Telemetry 汇同一缓冲），**不证明任一分支的真实质量**（全 mock backbone）。
- **`common/`（含 `common/flywheel` 接口）零改动**（git diff 为空，零 diff 验收通过）。分支之间不直接 import，只经 SubGoal DAG + State 串联交互。

> 相关 commits：`2350d80`（V5 集成 + 跨分支飞轮 + 发布）。

---

## [V4.0.0] — 2026-07-26

新增 **完整独立 3D 分支（多任务，全 mock）**。在 V1 的"3d = robot 作业场景"之上扩展为**完整 3D 生成家族**，且 **V1 `robot_scene` 路径保持字节级不变**（零回归）。

### Added / 新增
- **`branches/3d/` 扩展为多任务**（`target="3d"`，`modality="geometry"`，一个 target 通过 `adapter.build_bundle(task=...)` 旋钮覆盖任务族）：
  - `robot_scene`（V1，backbone-free 内联路径，**未改一行**）｜`text_to_3d`｜`image_to_3d`｜`pointcloud_completion`｜`pbr_texture`。
  - `backbone_interface.py` — **`ThreeDBackbone` 统一接口**（`generate(prompt, config)` 携带 `task`）；`backbone_mock.py` — `MockThreeDBackbone`（`sha256` 确定性、按 task 分派、`challenge` 首轮产坏结果、retry 修复）。
  - `wam.py` / `critic.py` / `mapper.py` / `primitives.py` / `exporter.py` / `safety_gate.py` — 全部按 `payload.get("task")` 分派（默认 `robot_scene`），V1 路径原样保留；`Scene3DWAM` 复用物理阵营 `PhysicalWorldModelBase`。
  - `safety_gate.py` **双模式**：`audit`（text_prompt NSFW/版权 → BLOCK；顶点超限 → BLOCK；退化几何 → DEGRADE）/ `passthrough`。
- **`examples/3d_full_demo.py`**：8 场景（4 生成任务 + retry 修复 + audit BLOCK + passthrough PASS + V1 robot_scene 回归）。
- **`tests/test_3d_branch.py`**（17 pytest）：4 生成闭环 + retry + 全任务共享一 target + 安全审核/放行/V1 顶点守卫 + 防腐层确定性 + 拒绝 robot_scene 走 backbone + Critic 各任务正确性 + V1 不回归。

### Changed / 变更
- 全量测试 **65/65 PASS**（48 V1–V3 + 17 V4）。

### 边界声明 / Boundary
- V4 验证多任务 3D 在同一 target 下的插件化扩展 + 冻结契约，**不证明几何真实质量**（全 mock）。真 TRELLIS / DreamGaussian / TripoSR / Shap-E 走 Azure，接入前过 T1–T5 门禁。
- **`common/` 零改动**（零 diff 验收通过）；V1 `robot_scene` 交付物字节级一致（无回归）。

> 相关 commits：`df189f4`（V4 完整 3D 多任务）。

---

## [V3.0.0] — 2026-07-26

新增 **game 分支（像素阵营，双方向，全 mock）**。像素阵营第二次验证冻结内核，且首次演示**一个 target 承载两个生成方向**。

### Added / 新增
- **`branches/game/`（双方向，`target="game"`，`modality="pixel"`）**：通过 `adapter.build_bundle(direction=...)` 切换：
  - **方向 A（level）**：文本 → 2D 平台跳跃关卡瓦片图（可通关性判定）。
  - **方向 B（worldmodel）**：state+action → 帧序列（像素世界模型）。
  - `wam.py` / `critic.py` / `primitives.py` / `mapper.py` / `executor.py` 全部按 `direction` 分派；**不继承** `PhysicalWorldModelBase`（像素阵营独立）。
  - `safety_gate.py` **双模式**（audit：血腥/NSFW/版权 → BLOCK；越界 → DEGRADE / passthrough）。
  - `backbone_interface.py` / `backbone_mock.py` — `GameBackbone` 防腐层 + 确定性 mock。
- **`examples/game_demo.py`**：level / worldmodel / retry / audit BLOCK / passthrough PASS 场景。
- **`tests/test_game_branch.py`**（17 pytest）：双方向正常闭环 + retry + 双方向共享一 target + 安全双模式 + 防腐层确定性 + Critic 各方向正确性。

### Changed / 变更
- 全量测试 **48/48 PASS**（31 V1–V2 + 17 V3）。

### 边界声明 / Boundary
- V3 验证像素阵营双方向在同一 target 下插件化 + 冻结契约，**不证明可玩性/画面质量**（全 mock 占位）。
- **`common/` 零改动**（零 diff 验收通过）。

> 相关 commits：`1c6843d`（V3 game 双方向分支）。

---

## [V2.0.0] — 2026-07-26

新增 **video 分支（像素阵营，全 mock）**。这是 common 冻结内核 "write-once-freeze" 承诺在**像素阵营**的第一次验证。

### Added / 新增
- **`branches/video/`（12 文件）**：
  - `wam.py` — `VideoWAM`：直接实现 `WorldModel`（**不**继承物理阵营 `PhysicalWorldModelBase`，像素先验不同）。
  - `critic.py` — `VideoCritic`：duration/fps/resolution 硬指标达标 + text-video 语义对齐（判定来源写入 `Verification.meta.verification_source`）。
  - `primitives.py` — 视频基元 `cut/fade/overlay/zoom`；`mapper.py` — 基元 → 视频 `Executable`。
  - `executor.py` — `VideoExecutor`：纯 stdlib 写最小合法 mp4（ISO-BMFF `ftyp`+`mdat`）占位。
  - `safety_gate.py` — `VideoSafetyGate` **双模式**：`audit` 内容审核（NSFW/暴力/版权 → BLOCK；<240p/<0.5s → DEGRADE）/ `passthrough` 放行，运行时切换。
  - `scene_objects.py` — 中英双语视频关键词（动作/主体/场景/镜头）。
  - `backbone_interface.py` — **`VideoBackbone` 统一 adapter 接口**（`generate`/`get_info`），`backbone_mock.py` — 确定性 mock（`sha256(prompt)` 纯色帧，retry 收敛 duration）。
  - `adapter.py` — 防腐层 + `register(registry)`。
- **`examples/video_demo.py`**：5 场景（正常闭环 / S9 retry 收敛 / audit BLOCK / passthrough PASS / DEGRADE→夹紧→PASS）。
- **`tests/test_video_branch.py`**：8 个 pytest（正常/retry/audit/passthrough/degrade/防腐层/确定性/双模式切换）。
- **`pyproject.toml` + `.vscode/settings.json`**：pytest `pythonpath` + VSCode Test Explorer 开箱即绿。

### Changed / 变更
- `README.md` / `docs/README.md`：V2 由 "Planned" → "✅ 已交付"；测试数 23 → 31；Quick Start 加 video demo。
- 全量测试 **31/31 PASS**（23 V1 + 8 V2）。

### 边界声明 / Boundary
- V2 验证编排内核 + 接口契约 + 数据飞轮在**像素阵营**同样成立，**不证明视频质量**。mock 生成纯色占位帧；真 HunyuanVideo / Wan-2.1 后续走 Azure，接入前过 `docs/engineering-setup.md` §2 T1–T5 门禁。
- **`common/` 零改动**（git diff 为空，零 diff 验收通过）。

> 相关 commits：`a3fc2ae`（V2 文档）→ `1c635db`（V2 代码）→ `f407548`（状态修正 + 测试配置）。

---

## [V1.0.0] — 2026-07-26

**common 冻结内核 + robot + 3d（robot 作业场景）**，物理阵营首发。契约 `docs/common-contract.md` v1.0-**FROZEN**。

### Added / 新增
- **`common/`（纯 stdlib，零三方运行时依赖）**：`interfaces`（数据对象 + 8 抽象接口）、`orchestrator`（S1–S14 状态机：DAG 拓扑 / S9 重试 / SafetyGate / 异常映射）、`registry`、`memory`、`flywheel`。
- **`branches/robot/`**（全 mock，零力矩执行器）；**`branches/3d/`**（robot 作业场景，占位 GLB 导出）；**`branches/_physical/`** 物理阵营共享 WAM 先验基类。
- **`examples/`**：`robot_demo.py`（抓杯→移动→放置 DAG + S9 重试 + SafetyGate BLOCK/DEGRADE）、`3d_scene_demo.py`。
- **`tests/`**：契约测试（反射断言接口/字段/枚举一字不改）+ **零 diff 验收**（新增 mock5 场景，`common/` git diff 为空）+ 边界测试。
- 文档：`common-contract.md` / `v1-development-plan.md` / `oss-integration-and-maintenance.md` / `engineering-setup.md` + bilingual `README.md` + Apache-2.0 `LICENSE` + `CONTRIBUTING.md`。

### 边界声明 / Boundary
- V1 验证编排内核 + 接口契约 + 数据飞轮，**不证明单场景物理可行性**（sim2real 缺口）。所有 backbone 均为 mock。
- 测试 **23/23 PASS**（contract test 6/6、零 diff 通过）。

> 相关 commits：`c4cf23e`（V1 base）→ `5b0f93a`（V1 验收）→ `5e691d2`（P1 修复 + 边界测试）→ `dc19316`（bilingual README + LICENSE + CONTRIBUTING）。

---

## Roadmap / 路线图

| 版本 | 组合 | 阵营 | 状态 |
|---|---|---|---|
| V1 | common + robot + 3d（robot 作业场景） | 物理 | ✅ 已交付 |
| V2 | common + video | 像素 | ✅ 已交付（全 mock） |
| V3 | common + game（双方向） | 像素 | ✅ 已交付（全 mock） |
| V4 | common + 完整独立 3D（多任务） | 物理 | ✅ 已交付（全 mock） |
| V5 | 全场景集成 + 跨分支数据飞轮 + 发布 | — | ✅ 已交付（全 mock） |

> 每个版本 = 独立的「common（冻结）+ 场景包」端到端项目；`common/` 全程零改动。
