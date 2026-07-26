# four-scene-brain · 开源接入合规与可维护性规范

> 版本：v1.0 ｜ 配套 `common-contract.md`（已冻结）、`engineering-setup.md`
> 两条铁律：①引入的开源项目**必须严格遵循**现有框架/边界/接口；②一切从**后续可维护**出发。

---

## Part A · 开源接入合规策略

### A0. 核心认知
开源模型（GR00T / HunyuanVideo / DreamGaussian / GameGen-O）**不会原生实现我们的接口**。合规不靠"挑守规矩的框架"，而靠**适配器（Adapter）+ 防腐层（ACL）把它们包成守规矩**。

### A1. 三条合规红线（任何引入框架不得违反）
- 🔴 backbone **只出现在 `branches/<scene>/` 内**，绝不进 common、绝不被 orchestrator 直接 import。
- 🔴 backbone 的类型/错误/配置**全部在 adapter 内翻译**成我们的数据对象 / FailureKind，**不外泄**（防腐层）。
- 🔴 **循环控制权归 orchestrator**；backbone 只作纯函数被调用（输入→输出），不得自跑 loop 接管流程。

### A2. "框架没法满足"的情况 → 选项清单（请你拍板）

| 情况 | 选项 | 建议 |
|---|---|---|
| **E1 端到端一把梭**（生成+解码+导出一体，如视频模型直接出 mp4，把 S7/S8/S11/S12 揉一起） | a. adapter 内拆调用：原始输出当 S7 候选，Mapper/Exporter 做薄封装（保骨架完整）<br>b. 该分支 S10/S11 做 no-op 直通（接口满足、内部融合，骨架名存实亡）<br>c. 换能分层的备选 backbone | **a** |
| **E2 自带 runtime loop**（想自己控循环） | a. 只当纯函数调用，循环权留 orchestrator<br>b. 包一层把它的 loop 降级为单步<br>c. 不用它 | **a** |
| **E3 依赖太重/本地跑不了** | a. 放 Azure，本地 adapter 作远程 client（gRPC/REST），接口不变<br>b. 本地 mock/小模型，云端用真的 | **a** |
| **E4 输出形状与 State 不匹配** | a. adapter 防腐层翻译（类型/坐标系/单位）<br>b. 差异是根本性的（如它输出的是成品不是状态）→ 重新归类它的接口角色（它可能该当 Mapper 而非 WorldModel） | **先 a，根本冲突再 b** |
| **E5 许可不合规（商用受限）** | a. 仅研究/内部用，商用换备选<br>b. 联系授权 / 自研该主干（仅 robot WAM 是自研项） | **a** |
| **E6 必须改 backbone 源码才能适配** | a. fork + pin + 最小 patch，记录 patch 清单<br>b. 优先找不改源码的用法（子类/回调/配置）<br>c. 换备选 | **先 b，不得已 a，慎 c** |

> ✅ **2026-07-26 已全部按"建议"列拍板通过。** 后续接开源框架严格按此执行。

---

## Part B · 可维护性补强（开发前最后完善）

### B1. Contract test —— 冻结的技术护栏（最重要）
写一个**接口回归测试**：用反射（`inspect`）断言 common 的接口签名 + 数据对象字段**逐字不变**。任何破坏冻结的改动 → 测试直接红。这是"写一次不改"从"约定"变成"强制"。

### B2. backbone mock / real 开关
每个 adapter 支持 `backend='mock' | 'real'`：
- 本地默认 `mock`（零依赖跑闭环）；
- 云端/接真主干切 `real`（走 Azure / 过门禁的框架）。
切换**不改接口、不改 orchestrator**。

### B3. 分支 README 模板（每个分支必填）
```
- payload 结构（State.payload 字段）
- success_criteria 判定来源
- backbone 选型 + 版本 pin + 许可结论 + 过门禁记录(T1–T5)
- 可重试错误 → FailureKind 映射
- 如何跑本分支 mock 闭环 / 如何切 real
```

### B4. 测试分层金字塔
```
        backbone 探针测试(T5)      ← 接真框架时
       contract test（零diff+签名回归） ← 护冻结
      分支 mock 闭环测试            ← 每分支 S1–S14
     单元测试（数据对象/接口/编排）     ← 最多
```

### B5. 配置外部化
backbone 路径 / Azure endpoint / 许可 token / backend 开关 → 走 **环境变量或 config 文件**，**不入库、不硬编码**（安全 + 可维护）。

### B6. 统一日志 / 遥测
全程 `trace_id` 贯穿（S1–S14），日志格式统一，便于排障与飞轮归因。

### B7. 变更纪律（CONTRIBUTING）
- 改 `common/` 的 PR：必过 **零 diff + contract test + 主版本评审**。
- 改分支：不影响其他分支、不动 common。
- 任何"看似必须改 common" → 先读 common-contract §11。

---

## Part C · 开发前最终状态（全部就绪）

- [x] 架构 / 边界 / 接口 / 版本 / D1–D7 —— **已冻结**
- [x] common 纯 stdlib —— **已定**
- [x] 开源选型 + 5 道测试门禁 —— 已就绪
- [x] 开源接入合规策略（E1–E6 选项）—— **已全按建议拍板（2026-07-26）**
- [x] 可维护性补强（contract test / mock-real 开关 / README 模板 / 测试分层 / 配置外化 / 日志 / 变更纪律）
- [ ] （可选）8 个提示词落盘 `prompts/`
- [ ] 你说"**可以开发代码**" → 从 P0 `common/interfaces` 开工（附带写 B1 contract test 护冻结）

**结论：除 E1–E6 选项待你确认（可一句"全按建议"）与提示词落盘（可选）外，无阻塞项，可随时开工。**
