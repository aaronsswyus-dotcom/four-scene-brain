# four-scene-brain · 工程规范与开源选型（开发前最后一补）

> 版本：v1.0 ｜ 配合 `common-contract.md`（已冻结）、`v1-development-plan.md` 使用
> 回应两条新规：①开发尽量用 GitHub 热门开源框架；②**先测试，再使用**。

---

## 1. 开源选型总原则

- 项目哲学 = **组装而非自研**：能用热门开源就不手写。
- **唯一例外 = common（冻结内核）**：为保"写一次不改"，common **运行期只用 Python 标准库**，不引三方框架（依赖越少，冻结越稳）。
- 三方框架只用在三层：**场景 backbone**（GR00T/DreamGaussian/HunyuanVideo/GameGen-O）、**支撑库**（Mem0/trimesh/OpenCV…）、**开发工具链**（pytest…）。

> 取舍（**2026-07-26 已定**）：**common 内核纯 stdlib**，不引三方框架（保冻结）；热门框架只用在场景 backbone / 支撑库 / 工具链（pytest），**不进 common 运行期**。开源接入合规与可维护性详见 `docs/oss-integration-and-maintenance.md`。

---

## 2. 测试门禁（任何框架一律"先测后用"）

一个框架要进项目，必须依次过 5 道关，**任一不过即换备选**：

| 关 | 内容 | 通过标准 |
|---|---|---|
| **T1 许可核查** | 商用许可合规性 | 合规；GR00T=NVIDIA 许可、HunyuanVideo/GameGen-O 见 repo，不合规仅研究用或淘汰 |
| **T2 健康度** | GitHub stars / 维护活跃度 / 最近提交 / issue 响应 | 活跃维护、社区认可 |
| **T3 隔离安装** | 独立 venv 安装 | 不污染主环境、无依赖冲突 |
| **T4 官方 quickstart** | 跑框架自带 hello-world/quickstart | 能跑通 |
| **T5 接口探针** | 包一层我们的接口（如 WorldModel）写最小集成测试 | 探针通过，记入选型表 |

---

## 3. 候选框架清单（待过门禁）

**四分支 backbone（默认 mock，真主干走 Azure；接入前必须过 §2 门禁）**

| 分支 | 首选 | 备选 | 许可风险 |
|---|---|---|---|
| robot (WAM) | GR00T | OpenVLA、LeRobot | ⚠ NVIDIA 商用需审 |
| 3d | DreamGaussian | threestudio、InstantMesh | 见 repo |
| video | HunyuanVideo | Wan2.1、CogVideoX、LTX、SVD | ⚠ 需核查 |
| game | GameGen-O | GameGen-X、Oasis | ⚠ 见 repo |

**支撑 / 工具**

| 用途 | 候选 | 备注 |
|---|---|---|
| 记忆 | Mem0 | common 只留接口，真 Mem0 是场景侧实现 |
| 3d 读写 | trimesh / pygltflib / USD-Python | 导 GLB/USD |
| 视频读写 | imageio-ffmpeg / OpenCV | 导 mp4 |
| 测试 | **pytest** | 开发依赖，不进 common 运行期 |
| schema(可选) | pydantic | **不进 common**；场景侧可用 |

---

## 4. 工程规范（lock）

- **包名**：`four_scene_brain`（仓库名 four-scene-brain）。
- **目录**：各包补 `__init__.py`；`common/` 自带 `__version__`。
- **测试**：`pytest`（开发依赖）跑单元/集成；**每个模块仍保留 `__main__` 自测**（最小闭环零依赖可跑）。
- **git**：`git init` + `.gitignore`（`__pycache__/`、`venv/`、`artifacts/`、大模型权重）；分支模型 `main` + `feat/*`。
- **代码风格**：类型注解 + dataclass + docstring（标注阵营/工序/边界）；接口签名与 common-contract 一字不差。

---

## 5. 开发模型策略（省钱 + 防漂移，2026-07-26 定）

- **设计期**：强推理模型一次性梳理（已完成并冻结，**不再重复花钱**）。
- **开发期**：性价比模型做机械实现（契约够细，执行是"翻译"不是"创作"）。
- **分层投入**：**P0–P3（common，写一次、错不起）用更稳的模型**；**P4–P8（分支 mock/demo，重复性）用性价比模型**。
- **自动闸代替人工复审**：contract test + 零 diff + DoD 自动拦截漂移，**不为返工/复审花积分**。
- **交接包**：开发时把 `docs/dev-handoff.md` + 4 份核心文档发给开发模型，**禁止它重新设计**。

---

## 6. 开发前最终 Checklist

- [x] D1–D7 拍板（**已冻结**，2026-07-26）
- [x] 通用层契约 + 边界 + V1 开发文档（已就绪）
- [x] **common 保持纯 stdlib**（已定，2026-07-26）
- [x] 开源接入合规（E1–E6）+ 开发模型策略（已定，2026-07-26）
- [ ] **工程规范落地**：git init / 包名 / pytest / `.gitignore`（开工第一步顺手做）
- [ ] **backbone 选型表**：V1 本地全 mock，只需 pytest；真 backbone 在 Azure / V2+ 阶段过 §2 门禁后逐个接入
- [ ] （可选）8 个提示词落盘 `prompts/` 或录 FAB5
- [ ] 你说"**可以开发代码**" → 从 P0 `common/interfaces` 开工

---

## 7. 结论

架构、边界、接口、版本、决策、开发模型策略**已全部冻结**；工程规范与开源门禁本文补齐。**唯一可选小项是"8 个提示词是否现在落盘"（不阻塞）**——你说"可以开发代码"即可从 P0 开工。
