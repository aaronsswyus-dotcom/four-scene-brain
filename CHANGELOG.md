# Changelog · 变更日志

All notable changes to **four-scene-brain** are documented here.
本项目的所有重要变更都会记录在此文件。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)；版本号遵循 [SemVer](https://semver.org/lang/zh-CN/) 的近似约定。

> 注：V1–V5 是"**组合（combination）**"标签而非严格语义版本；`common/` 冻结内核版本恒为 `1.0.0`（见 `docs/common-contract.md` §1 打包纪律）。

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
| V3 | common + game | 像素 | 🔵 准备中（可玩关卡） |
| V4 | common + 完整独立 3D | 物理 | ⬜ Planned |
| V5 | 全场景集成 + 跨分支数据飞轮 | — | ⬜ Planned |

> 每个版本 = 独立的「common（冻结）+ 场景包」端到端项目；`common/` 全程零改动。
