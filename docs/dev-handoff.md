# four-scene-brain · 开发交接包（粘贴给开发模型 / 新窗口）

> 用法：开发 V1 时，把**本文件 + 4 份核心文档**作为上下文发给开发模型。
> 目标：①防止它重新设计架构；②防止破坏 common 冻结；③按阶段只喂必要上下文，节省积分。

---

## 0. 给开发模型的硬指令（最重要）
- 你是**实现者，不是设计者**。接口 / 数据对象 / 边界**已定稿并冻结**，**禁止重新设计或"顺手优化"架构**。
- 签名一字不改、字段一字不改。凡觉得"这里该改 common"→ **停下来先问**，不要自作主张。

---

## 1. 先读这 4 份（只读，当作法律）
| 文件 | 读它为了 |
|---|---|
| `docs/common-contract.md` | **最高权威**：数据对象 §4、接口 §5、状态机 §6、红线 §10 |
| `docs/v1-development-plan.md` | V1 范围 §1、physical 接口 §4、计划 §5、DoD §7 |
| `docs/oss-integration-and-maintenance.md` | 开源合规 §A、contract test §B1、README 模板 §B3 |
| `docs/engineering-setup.md` | 包名 / pytest / git / 开源选型 |

---

## 2. 不可协商的红线
- 🔴 common 纯 stdlib、零三方依赖；`payload` 不透明；无场景名 / 无模态 if-else；不 import 任何 `branches/`。
- 🔴 接口签名、数据对象字段**一字不改**（只允许 meta 内扩展）。
- 🔴 重试 ≤ `max_retry`；分支异常映射 `FailureKind`，**不穿透 common**。
- 🔴 `SafetyGate` 在 S11→S12 之间；**robot 必须实现**。

---

## 3. 构建顺序（P0→P8，按序，别跳）
```
P0 common/interfaces → P1 registry → P2 orchestrator → P3 memory/flywheel
→ P4 physical base → P5 robot 分支 → P6 3d 分支 → P7 两个 demo → P8 零diff+DoD
```
**P0–P3 是 common，写完即冻结，后面不许回头改。**

---

## 4. 每阶段只喂必要上下文（省积分，不必每次喂整份文档）
| 阶段 | 只喂这些章节 |
|---|---|
| P0 interfaces | common-contract §4 + §5 |
| P1 registry | §7 |
| P2 orchestrator | §6 |
| P3 memory/flywheel | §8 |
| P4–P6 分支 | v1-plan §3+§4 ＋ oss §A/§B |
| P7–P8 验收 | v1-plan §5+§7 |

---

## 5. 验收闸（每阶段必过，挡住即返工）
- 每模块 `__main__` 自测通过；
- **contract test**：反射断言接口签名 / 字段不变（护冻结）；
- P8：**零 diff**（加 mock 场景 common diff 为空）+ V1 DoD 全过。

---

## 6. 交付要求
- 纯 Python 3.13 stdlib；类型注解 + dataclass；
- 每文件 docstring 标注「阵营 / 工序 / 边界」；
- backbone 一律 `backend='mock'` 默认，真主干留可替换口（走 Azure，先过测试门禁）。

---

## 7. 开发模型策略（省钱核心）
- **设计期**：强推理模型一次性梳理（已完成并冻结，不再重复花钱）。
- **开发期**：性价比模型做机械实现即可——因为契约足够细，执行是"翻译"而非"创作"。
- **分层投入**：**P0–P3（common，写一次、错不起）用更稳的模型/更仔细**；**P4–P8（分支 mock/demo，重复性）用性价比模型**。
- **自动闸代替人工复审**：contract test + 零 diff + DoD 自动拦截漂移，**不为返工/复审花积分**。
