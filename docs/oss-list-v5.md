# V5 开源项目清单（2026-07-26 · V5 启动前定稿）

> 依据：common-contract §2/§10 红线、`v5-development-plan.md`（集成版，不新建分支）、engineering-setup §2 五道门禁。
> 结论先行：**V5 本机运行时零三方依赖；不引入新场景 backbone（复用 V1–V4）；开源重点在「基础设施同接口替换」与「全版本 backbone 接入总览」。**

---

## 1. V5 本机实际使用（现在就装/用）

| 项目 | 用途 | 层 | 许可 | 状态 |
|---|---|---|---|---|
| Python 3.13 stdlib | 集成 demo + 跨分支聚合视图 | examples/tests | PSF | ✅ 唯一运行时依赖 |
| pytest | 集成测试 + 全量回归 | 仅开发依赖 | MIT | ✅ 已装 |

**就这两项。** V5 不加任何三方运行时依赖。

---

## 2. V5 无新场景 backbone（关键）

V5 是**集成版本**，不新建分支、不接新 backbone。各分支的真 backbone 仍属各自版本（V1 robot→GR00T、V2 video→HunyuanVideo、V3 game→MarioGPT/GameGen-O、V4 3d→TRELLIS），**接入时机与方式统一走 `docs/model-integration-runbook.md`**（HY-3 在 Azure 阶段过 T1–T5 门禁接入）。V5 本版只保证它们能在同一 Registry 下并存路由。

---

## 3. 基础设施类候选（同接口替换，common 零改动）

这些不是场景 backbone，而是 common 已定义接口（Memory/Flywheel/S3 意图）的**可选真实现**，V5 集成时可按需替换（替换不动 common）：

| 能力（common 接口） | V1–V5 默认实现 | 可替换开源/云服务 | 许可 | 替换方式 | 门禁 |
|---|---|---|---|---|---|
| Memory (S6) | InMemoryMemory（dict） | **Mem0**（~30k star，长期记忆） | Apache-2.0 | 实现同一 `Memory` 接口 | T1–T5 |
| Flywheel (S13/S14) | FileBufferFlywheel（jsonl 落盘） | **Azure 回灌管道**（周期蒸馏→各分支 WM） | —（自建） | 实现同一 `Flywheel` 接口 | — |
| S3/S4 意图解析 | 规则/模板（D1 拍板） | **LLM 插件**（可选，如 Azure OpenAI） | 视所选 | Orchestrator 可选注入，非必需 | T1–T5 |
| 跨分支遥测存储 | 本地 jsonl | **Azure Data Lake / Cosmos** | —（云服务） | Flywheel 实现内改存储后端 | — |

**纪律**：以上全是"同接口替换实现"，**绝不改 common 接口签名**；接入前过 T1–T5。

---

## 4. 全版本 backbone 接入总览（V5 统一视图）

| 分支 | 阵营 | 真 backbone（主推/备选） | 接入阶段 | 门禁状态 |
|---|---|---|---|---|
| robot | 物理 | GR00T / （备选） | Azure | ⬜ 未过 T1–T5 |
| 3d | 物理 | TRELLIS / TripoSR / DreamGaussian / Shap-E | Azure | ⬜ 未过 |
| video | 像素 | HunyuanVideo / Wan-2.1 / CogVideoX | Azure | ⬜ 未过 |
| game | 像素 | MarioGPT(A) / GameGen-O·OASIS·DIAMOND(B) | Azure | ⬜ 未过 |

> **接入纪律（全版本统一）**：每个真 backbone 都①只在 `branches/<scene>/adapter.py` 内、②走各自 `XxxBackbone` 防腐层接口、③过 T1–T5 门禁、④先在 Azure 跑通官方 quickstart、⑤接 `model-integration-runbook.md` 的自动测试。V5 集成时这四个分支可各自独立接入、互不阻塞。

---

## 5. 纪律重申

1. 🔴 **V5 零三方运行时依赖**；集成 demo/聚合视图/测试全 stdlib。
2. 🔴 **不新建分支、不接新 backbone**；复用 V1–V4。
3. 🔴 **基础设施替换只换实现、不改接口**（Memory/Flywheel/S3）。
4. 🔴 **common 全程零改动**（含 `common/flywheel`）；跨分支聚合放分支/示例侧。
5. 🔴 **真模型接入统一走 `model-integration-runbook.md`**，过 T1–T5 门禁 + 自动测试。
