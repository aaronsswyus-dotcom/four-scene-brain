# four-scene-brain · 文档索引（README）

> 用途：一眼分清**核心契约文件**（必读、冻结、随版本携带）与**过程/背景文档**（可追溯，可不随版本带）。
> 更新：2026-07-26（D1–D7 与 E1–E6 均已拍板，common 纯 stdlib 已定）。

---

## 🟢 核心契约文件（必读 · 冻结 · 随 V1–V5 携带）

| 文件 | 作用 | 何时用 |
|---|---|---|
| **`common-contract.md`** | **通用层唯一权威契约**（思路/框架/边界/接口/数据对象/状态机/接入清单/冻结纪律）。已 FROZEN。 | **V1–V5 全程**；每个版本开发都把它当上下文 |
| **`v1-development-plan.md`** | **V1 开发文档**（common+physical：robot + robot的3D场景；范围/框架/接口/P0–P8/DoD）。 | **V1 开发期** |
| **`oss-integration-and-maintenance.md`** | **开源接入合规 + 可维护性规范**（3 红线、E1–E6、contract test、mock/real、README模板、测试分层、配置外化、变更纪律）。 | **接任何开源框架 / 写代码全程** |
| **`engineering-setup.md`** | **工程规范 + 开源选型**（common纯stdlib、5道测试门禁T1–T5、候选框架清单、包名/pytest/git）。 | **搭环境 / 选型 / 写测试** |

> 这 4 份是"真契约"，开发时**只看这 4 份**即可。

---

## 🟠 过程 / 背景文档（可追溯 · 已被核心文件吸收）

| 文件 | 作用 | 现状 |
|---|---|---|
| `scheme.md` | 最早的整体开发文档（目录/开源内容/环境评估/最小闭环） | 背景；内容已被 common-contract + v1-plan 覆盖 |
| `boundaries.md` | 三层职责边界 + 接口契约 + 决策矩阵 | 背景；已并入 common-contract |
| `pre-dev-gap-analysis.md` | 完备性缺口分析（G1–G6、physical注意项、Checklist） | 背景；G1–G6 已并入 common-contract 数据模型 |

> 这 3 份是"过程稿"，记录了推演过程，**保留作追溯**；不必随版本携带，如嫌多可日后归档到 `docs/_archive/`。

---

## 目录速览（当前只有文档，代码未开工）

```
four-scene-brain/
├── docs/
│   ├── README.md                        ← 本索引
│   ├── common-contract.md               🟢 核心（冻结）
│   ├── v1-development-plan.md           🟢 核心
│   ├── oss-integration-and-maintenance.md 🟢 核心
│   ├── engineering-setup.md             🟢 核心
│   ├── scheme.md                        🟠 背景
│   ├── boundaries.md                    🟠 背景
│   └── pre-dev-gap-analysis.md          🟠 背景
├── common/  branches/  examples/  prompts/   ← 空骨架，待开发
```

---

## 一句话
**开发只带 4 份核心**（contract / v1-plan / oss-maintenance / eng-setup）；3 份过程稿留作追溯。等你说"可以开发代码"，从 P0 `common/interfaces` 开工。
