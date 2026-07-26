# HY-3 V2 开发启动包（video 分支）

> 用途：把这份文件 + 指定的上下文文件发给 HY-3，让它按冻结契约开发 V2 video 分支。
> 前置：V1 已交付并上架 GitHub（common 冻结，robot + 3d 完成），common 零改动。
> 与 V1 的区别：V1 是物理阵营（robot/3d），V2 是像素阵营（video），不共享 PhysicalWorldModelBase。

---

## A. 上下文文件清单（发给 HY-3 的文件）

按优先级排序，**前 6 份必读**：

| # | 文件 | 必读级别 | 作用 |
|---|---|---|---|
| 1 | `docs/common-contract.md` | 🔴 必读 | 冻结契约（接口/数据对象/状态机/铁律） |
| 2 | `docs/v2-development-plan.md` | 🔴 必读 | V2 范围/接口/payload/DoD/P0–P9 |
| 3 | `docs/oss-list-v2.md` | 🔴 必读 | 开源选型 + backbone adapter 接口规范 |
| 4 | `docs/oss-integration-and-maintenance.md` | 🟠 必读 | 开源接入 3 红线 + E1–E6 |
| 5 | `docs/engineering-setup.md` | 🟠 必读 | 工程规范 + 五道门禁 |
| 6 | `branches/robot/` 全部文件 | 🟠 参考 | V1 分支模板（video 分支照这个模式写） |
| 7 | `common/interfaces/data_objects.py` | 🟢 参考 | 数据对象定义（video 分支要用） |
| 8 | `common/interfaces/abstract.py` | 🟢 参考 | 8 个抽象接口（video 分支要实现） |

**发送建议**：先一次性发前 5 份，HY-3 确认理解后再发 V1 robot 分支代码做参考。

---

## B. 主提示词（发给 HY-3 的第一条消息）

```
你是 four-scene-brain 项目的实现工程师，不是设计者。所有架构决策已冻结在
common-contract.md 中，你的任务是严格按规范实现 V2 video 分支。

【你的身份】
- 实现者，不是设计者。所有接口/数据对象/状态机已冻结，不得重新设计。
- 如果你认为 common 需要改动 → 立即停止，向我提问，不要擅自改。

【三条铁律（违反 = 返工）】
1. common 写一次永冻结：你只能新增 branches/video/，不能改 common/ 任何一行。
2. 场景即插件：common 不出现 video/HunyuanVideo 等场景名，一切差异走 payload + meta。
3. 唯一交换语言：common 与 video 分支之间只交换 common-contract §4/§5 定义的对象与签名。

【V2 范围】
- 新增 branches/video/ 全套适配器（wam/critic/primitives/mapper/executor/safety_gate/adapter）
- backbone 全 mock（真 HunyuanVideo 后续上 Azure）
- SafetyGate 双模式（audit 内容审核 / passthrough 放行）
- examples/video_demo.py 最小闭环
- common 零改动，零 diff 验收必须通过

【开发顺序（P0–P9）】
严格按 v2-development-plan.md §5 的顺序：
P0 scene_objects.py → P1 backbone_interface.py → P2 backbone_mock.py →
P3 wam.py → P4 critic.py → P5 primitives.py → P6 mapper.py →
P7 executor.py + safety_gate.py → P8 adapter.py → P9 demo + 零 diff 验收

【参考模板】
branches/robot/ 是 V1 的完整实现，video 分支照这个模式写：
- 文件结构相同（adapter/critic/primitives/mapper/executor/safety_gate + README）
- 每个文件都有 __main__ 自测
- adapter.py 是防腐层 + register(registry)
- payload 结构写进分支 README

【开源红线】
- backbone 只在 branches/video/adapter.py 内，不进 common
- wam.py 调 backbone 走 VideoBackbone 接口（oss-list-v2.md §4），不直接调 API
- 换 backbone 只改 adapter.py 一行参数，其他文件全不动

【质量标准】
- 纯 Python stdlib，零三方依赖
- 每个文件含 __main__ 自测
- demo 必须演示：S1–S14 闭环 + 一次 S9 失败重试 + SafetyGate 双模式

现在开始。先告诉我你理解了哪些关键点，然后从 P0 开始。
```

---

## C. P0 任务提示词（HY-3 确认理解后发送）

```
【P0 · branches/video/scene_objects.py：视频关键词词汇表】

任务：实现视频场景的关键词解析模块，供 wam 和 critic 共用。

要求：
1. 参考 branches/3d/scene_objects.py 的模式
2. 定义视频场景的关键词词汇表：
   - 动作：run/jump/walk/fly/swim/跑/跳/走/飞/游
   - 主体：cat/dog/person/car/bird/猫/狗/人/车/鸟
   - 场景：grass/road/sky/water/room/草地/马路/天空/水/房间
   - 镜头：zoom/pan/tilt/static/拉近/平移/倾斜/固定
3. 实现 objects_from_goal(goal_text) -> dict 函数：
   - 返回 {"actions": [...], "subjects": [...], "scenes": [...], "camera": [...]}
   - 用关键词匹配（lower + in）
4. __main__ 自测：中英文混合 prompt 都能解析

输出文件：branches/video/scene_objects.py
```

---

## D. P1–P9 阶段提示词（按需逐个发送）

### P1 · backbone_interface.py

```
【P1 · branches/video/backbone_interface.py：VideoBackbone 抽象接口】

任务：定义所有 video backbone 必须实现的防腐层接口。

要求：
1. 参考 oss-list-v2.md §4.1 的接口定义
2. 实现 VideoBackbone(ABC)：
   - generate(prompt, config) -> dict（返回 frames/fps/duration/resolution/scene_description/camera_motion/meta）
   - get_info() -> dict（返回 name/version/license/capabilities）
3. __main__ 自测：抽象类不可实例化

输出文件：branches/video/backbone_interface.py
```

### P2 · backbone_mock.py

```
【P2 · branches/video/backbone_mock.py：Mock 视频 backbone】

任务：实现确定性的 mock backbone，V2 默认使用。

要求：
1. 实现 MockVideoBackbone(VideoBackbone)
2. generate() 返回：
   - frames: 纯色帧数组（用 prompt 的 hash 值决定颜色，保证确定性）
   - fps/duration/resolution: 从 config 读取或默认值
   - scene_description: 从 prompt 提取（调 scene_objects.objects_from_goal）
   - camera_motion: 从 prompt 提取镜头关键词
3. retry 时（config 里有 retry 标记）：提升 quality_score（模拟细化）
4. __main__ 自测：相同 prompt 生成相同结果

输出文件：branches/video/backbone_mock.py
```

### P3 · wam.py

```
【P3 · branches/video/wam.py：VideoWAM（WorldModel 实现）】

任务：实现 video 分支的 WorldModel，内部调用 backbone。

要求：
1. 参考 branches/robot/wam.py 的模式
2. 实现 VideoWAM(WorldModel)：
   - __init__(backbone: VideoBackbone)
   - predict_next_state(state, goal) -> State：
     - 从 goal.goal 提取 text_prompt
     - 从 goal.constraints 提取 duration/fps/resolution（默认值）
     - 调用 self.backbone.generate(prompt, config)
     - 包装成 State(modality="pixel", payload=backbone_output)
3. __main__ 自测：mock backbone 注入，predict 返回正确 payload

输出文件：branches/video/wam.py
```

### P4 · critic.py

```
【P4 · branches/video/critic.py：VideoCritic】

任务：实现视频质量校验。

要求：
1. 参考 branches/robot/critic.py 的模式
2. 实现 VideoCritic(Critic)：
   - 硬指标优先：duration 在目标 ±20% 内，fps ≥ 目标，resolution ≥ 目标
   - 软指标次之：text-video 语义对齐（scene_description 与 goal.goal 关键词重叠）
   - 判定来源写入 Verification.meta.verification_source
3. __main__ 自测：达标/不达标两种情况

输出文件：branches/video/critic.py
```

### P5 · primitives.py

```
【P5 · branches/video/primitives.py：VideoPrimitiveLibrary】

任务：实现视频基元抽象。

要求：
1. 定义视频基元：cut（剪辑）/fade（淡入淡出）/overlay（叠加）/zoom（缩放）
2. 实现 VideoPrimitiveLibrary(PrimitiveLibrary)：
   - abstract(draft) -> list[Primitive]
   - 从 draft.payload 的 scene_description 推导基元序列
3. __main__ 自测

输出文件：branches/video/primitives.py
```

### P6 · mapper.py

```
【P6 · branches/video/mapper.py：VideoMapper】

任务：实现基元 → 视频 Executable 映射。

要求：
1. 实现 VideoMapper(Mapper)：
   - map(primitives, goal) -> Executable
   - payload 包含 video_spec（时长/帧率/分辨率/基元序列）
2. __main__ 自测

输出文件：branches/video/mapper.py
```

### P7 · executor.py + safety_gate.py

```
【P7 · branches/video/executor.py + safety_gate.py】

任务：实现视频输出 + 双模式 SafetyGate。

executor.py 要求：
1. 实现 VideoExecutor(Executor)
2. execute() 输出占位 mp4 文件（纯 stdlib：写最小合法 mp4 头 + 帧数据占位）
3. Delivery.meta 带 telemetry_kind="video"
4. __main__ 自测：验证 mp4 头合法

safety_gate.py 要求：
1. 实现 VideoSafetyGate(SafetyGate)，支持双模式：
   - mode="audit"（默认）：检查 NSFW/暴力/版权关键词 → BLOCK；分辨率过低/时长过短 → DEGRADE
   - mode="passthrough"：直接 PASS
2. __init__(mode="audit")
3. __main__ 自测：两种模式都验证

输出文件：branches/video/executor.py + branches/video/safety_gate.py
```

### P8 · adapter.py

```
【P8 · branches/video/adapter.py：防腐层 + 注册】

任务：实现 video 分支的唯一入口。

要求：
1. 参考 branches/robot/adapter.py 的模式
2. 实现 build_bundle(backbone="mock", safety_mode="audit") -> BranchBundle：
   - backbone="mock"：用 MockVideoBackbone
   - backbone="hunyuan-azure"：raise NotImplementedError（T1–T5 门禁未过）
   - safety_mode="audit" / "passthrough"：传给 VideoSafetyGate
3. 实现 register(registry, backbone="mock", safety_mode="audit")
4. __main__ 自测：注册成功 + 双模式切换

输出文件：branches/video/adapter.py
```

### P9 · demo + 零 diff 验收

```
【P9 · examples/video_demo.py + 零 diff 验收】

任务：实现 video 最小闭环 demo + 验证 common 零改动。

demo 要求：
1. 参考 examples/robot_demo.py 的模式
2. 演示 4 个场景：
   - 正常闭环：「生成一个 5 秒的视频：一只猫在草地上奔跑」→ 占位 mp4
   - S9 失败重试：duration 不达标 → 回 S7 → 成功
   - SafetyGate 审核模式：NSFW prompt → BLOCK
   - SafetyGate 放行模式：同一 prompt → PASS
3. 输出 RunMetrics + flywheel 路径 + 边界声明

零 diff 验收要求：
1. 运行 python -m tests.test_zero_diff
2. 确认 common/ git diff 为空
3. 如果失败 → 说明 video 分支有逻辑泄漏到 common，必须修复

输出文件：examples/video_demo.py
```

---

## E. 纠偏话术（HY-3 跑偏时用）

| 情况 | 纠偏话术 |
|---|---|
| HY-3 想改 common | "common 已冻结，不能改。如果你认为必须改，先停下来告诉我原因。" |
| HY-3 想在 wam.py 直接调 HunyuanVideo API | "backbone 只能通过 VideoBackbone 接口调用，参考 backbone_mock.py 的模式。" |
| HY-3 忘了 __main__ 自测 | "每个文件都要有 __main__ 自测，参考 branches/robot/ 的文件。" |
| HY-3 跳过 SafetyGate 双模式 | "SafetyGate 必须支持 audit/passthrough 双模式，adapter 内可配置。" |
| HY-3 想装第三方库 | "V2 纯 stdlib，零三方依赖。backbone 全 mock。" |

---

## F. 省钱提醒

- **一次性发上下文**：前 5 份文件一次发完，避免 HY-3 反复问你要文件浪费积分。
- **分阶段验收**：每个 P 阶段完成后先跑自测，通过了再发下一阶段提示词，避免一口气写完发现全错。
- **用 V1 robot 做参考**：branches/robot/ 是完整模板，让 HY-3 照着写，减少返工。
- **卡住就问**：HY-3 卡住超过 3 轮 → 让它停下来汇报问题，你来决策，不要让它硬写。

---

## G. V2 DoD 验收清单（全部完成后检查）

- [ ] `python -m examples.video_demo` 跑通 4 个场景
- [ ] `python -m pytest tests/` 全绿（含新增 video 测试）
- [ ] `python -m tests.test_zero_diff` 通过，common git diff 为空
- [ ] `branches/video/README.md` 写清 payload 结构 + SafetyGate 双模式
- [ ] SafetyGate 双模式可切换（audit/passthrough）
- [ ] 边界声明：README 注明「验证编排内核，不证明视频质量」
- [ ] git commit + push 到 GitHub
