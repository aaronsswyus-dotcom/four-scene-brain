# four-scene-brain · V2 开发文档（common + video）

> 版本：v1.0-plan ｜ 范围：**V2 = 通用层（冻结）+ video 分支**
> 依据：`common-contract.md`（FROZEN）、`v1-development-plan.md`（V1 模式参考）
> 前置：D1–D7 已拍板，common 已 FROZEN，V1 已交付。**common 全程零改动。**
> backbone 候选：**HunyuanVideo**（腾讯自研，10k+ star，Hunyuan Community License）
> **当前仍为设计文档，未写代码。**

---

## 1. V2 目标与范围

**目标**：在 V1 冻结内核之上，新增 video 分支，跑通「语言指令 → 生成视频 → Critic 校验 → 交付 mp4 → 遥测入飞轮」的最小闭环，验证 common 的 write-once-freeze 在像素阵营同样成立。

**范围内（V2 做）**
- `branches/video/` 全套适配器：wam(mock)/critic/primitives/mapper/executor/safety_gate/adapter + README
- video payload 结构定死（为将来换真 HunyuanVideo 做准备）
- SafetyGate 双版本：**可配置开关**（审核模式 / 放行模式），用户运行时选择
- `examples/video_demo` 最小闭环
- 零 diff 验收 + V2 DoD 验收

**范围外（V2 不做）**
- ❌ 真 HunyuanVideo 接入（上 Azure，V2 仍 mock）
- ❌ 视频后处理/编辑（归后续版本）
- ❌ 跨分支飞轮全量集成（V5）
- ❌ game / 完整 3D 分支（V3/V4）

---

## 2. V2 框架

```
输入(人语言)
   ↓
┌─────────────── common（冻结，v1.0.0，V1 已验证）───────────────┐
│  orchestrator：S1–S14 状态机（不动）                          │
│  registry / memory / flywheel（不动）                          │
└───────────────▲──────────────────────────────────────────────┘
        经接口契约 │（common 对 video 完全无知）
   ┌─────────────┴──────────┐
   │ branches/video（像素）  │
   │ wam(mock)/critic/       │
   │ primitives/mapper/      │
   │ executor(mp4输出)/       │
   │ safety_gate(双模式)/     │
   │ adapter(防腐层)          │
   └────────────────────────┘
```

**关键**：common 对 video 完全无知；video 不共享 robot/3d 的 PhysicalWorldModelBase（像素阵营，物理先验不同）。video 分支独立实现全部 5+1 接口。

---

## 3. V2 边界

**common 边界**：无场景名、无模态 if/else、不 import 分支、payload 不透明、纯 stdlib、重试 ≤max_retry。**V2 全程不改 common 一行。**

**video 专属边界**：
1. **SafetyGate 双模式**：`safety_gate(mode="audit")` 做内容审核，`safety_gate(mode="passthrough")` 直接放行。adapter 内可配置，default=audit。
2. **内容生成 vs 内容审核分离**：Critic 管「视频质量」（duration/fps/分辨率/语义对齐），SafetyGate 管「内容合规」（NSFW/暴力/版权关键词）。两者不混淆。
3. **mock 不证明视频质量**：V2 mock 生成的是占位帧，验证编排闭环，不验证视频质量。真质量靠 HunyuanVideo on Azure。
4. **本地只缓冲不训**：S14 仍走 FileBufferFlywheel 落盘。

---

## 4. V2 接口

**通用接口（冻结，V1 已验证，V2 原样使用）**：
`WorldModel / Critic / PrimitiveLibrary / Mapper / Executor / SafetyGate / Memory / Flywheel` + 全部数据对象 + 枚举。

**video 分支 payload 结构（分支冻结，写进分支 README）**：

```
frames:        list[list[list[int]]]  # 帧数组 [T][H][W][C]，mock 用纯色帧
fps:           int                    # 帧率（默认 24）
duration_s:    float                  # 时长（秒）
text_prompt:   str                    # 文本描述（驱动生成）
resolution:    [width, height]        # 分辨率
# mock 附加：scene_description / camera_motion / refined_times
```

**video Critic 成功标准**：
- **duration + fps + resolution 达标**（硬指标优先）：duration 在目标 ±20% 内，fps ≥ 目标值，resolution ≥ 目标值
- **text-video 语义对齐**（软指标次之）：mock 检查 text_prompt 与 scene_description 关键词重叠度
- 判定来源写入 `Verification.meta.verification_source`

**video SafetyGate（双模式）**：

| 模式 | 检查 | 结果 |
|---|---|---|
| `audit`（默认） | text_prompt 含 NSFW/暴力/版权关键词 | BLOCK |
| `audit` | 分辨率过低（<240p）或时长过短（<0.5s） | DEGRADE |
| `audit` | 一切正常 | PASS |
| `passthrough` | 无检查 | PASS |

**video Executor**：输出 mp4 占位文件（纯 stdlib：用 json+struct 写最小合法 mp4 头 + 帧数据占位）。

---

## 5. V2 开发计划（阶段拆解）

> 顺序即依赖；每阶段带自测。纯 stdlib，零三方依赖。common 零改动。

| 阶段 | 产出 | 验收 |
|---|---|---|
| **P0 video payload 结构** | `branches/video/scene_objects.py`（视频关键词词汇表）+ payload 结构定义 | 关键词解析自测 |
| **P1 video WAM** | `branches/video/wam.py`（mock 视频世界模型） | predict_next_state 自测 |
| **P2 video Critic** | `branches/video/critic.py`（duration/fps/resolution + 语义对齐） | verify 自测 |
| **P3 video Primitives** | `branches/video/primitives.py`（cut/fade/overlay 基元） | abstract 自测 |
| **P4 video Mapper** | `branches/video/mapper.py`（基元 → 视频 Executable） | map 自测 |
| **P5 video SafetyGate** | `branches/video/safety_gate.py`（双模式） | audit/passthrough 自测 |
| **P6 video Executor** | `branches/video/executor.py`（mp4 占位输出） | execute 自测 |
| **P7 video Adapter** | `branches/video/adapter.py` + `register()` | 注册自测 |
| **P8 video Demo** | `examples/video_demo.py` | S1–S14 跑通 + 重试 + SafetyGate |
| **P9 零 diff 验收** | `tests/test_zero_diff.py` 加 video 场景验证 | common git diff 为空 |

**冻结纪律**：P0–P7 是 video 分支内部，质量要求低于 common 但高于临时脚本；P8–P9 是验收，不通过不许合入。

---

## 6. V2 依赖

- **运行时**：Python 3.13（托管），**仅用标准库**。
- **开发依赖**：pytest（已装）。
- **不装**：任何大模型 / GPU 依赖（V2 全 mock）。
- **真 backbone**：HunyuanVideo 走 Azure（接入前过 `engineering-setup.md` §2 五道门禁）。

---

## 7. V2 验收 DoD

1. **video 最小闭环**：输入「生成一个 5 秒的视频：一只猫在草地上奔跑」→ 走完 S1–S14 → 输出占位 mp4 + 带 trace_id 的 Telemetry。
2. **重试路径**：演示一次 S9 失败（duration 不达标）→ 回 S7 → 成功。
3. **SafetyGate 审核模式**：含 NSFW 关键词的 prompt → BLOCK。
4. **SafetyGate 放行模式**：同一 prompt → PASS（验证双模式可切换）。
5. **零 diff 验收**：`tests/test_zero_diff.py` 通过，`common/` git diff 为空。
6. **RunMetrics**：输出成功率 / 重试次数 / 各 Critic 分。
7. **边界声明**：README 注明「验证编排内核，不证明视频质量」。

---

## 8. V2 风险与红线

- 🔴 video 分支泄漏逻辑到 common → 冻结失败（零 diff 测试兜底）。
- 🔴 video payload 没定死 → 将来换真 HunyuanVideo 要重构（P0 定死规避）。
- 🟠 误把 mock 视频质量当真 → DoD 第 7 条声明规避。
- 🔴 SafetyGate 审核模式误伤正常 prompt → 关键词列表要保守，宁可漏不可错杀。

---

## 9. V2 与 V1 的差异对比

| 维度 | V1（robot + 3d） | V2（video） |
|---|---|---|
| 阵营 | 物理（physical） | 像素（pixel） |
| 共享基类 | PhysicalWorldModelBase（WAM 先验） | 无（独立实现） |
| SafetyGate | 单模式（力矩/限位/禁撞区） | 双模式（审核/放行） |
| Critic 标准 | force-torque 阈值优先 | duration/fps/resolution 达标优先 |
| Executor | 零力矩 mock | mp4 占位文件 |
| payload | pose/twist/wrench/contact/joint_state | frames/fps/duration/text_prompt/resolution |
| 跨分支 DAG | robot → 3d（物理场景 → 机器人操作） | video 独立（V5 再集成） |
