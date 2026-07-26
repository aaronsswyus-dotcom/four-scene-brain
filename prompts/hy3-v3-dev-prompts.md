# HY-3 V3 开发启动包（game 分支 · 双方向）

> 用途：把这份文件 + 指定的上下文文件发给 HY-3，让它按冻结契约开发 V3 game 分支。
> 前置：V1+V2 已交付并上架 GitHub（common 冻结，robot/3d/video 完成），common 零改动。
> **D-V3-1 已拍板：A（level 可玩关卡）+ B（worldmodel 交互式推演）两个方向都上**，经 `adapter.build_bundle(direction=...)` 切换。
> 与 V2 的关系：game 与 video 同属像素阵营，**video 分支是最近的参考模板**（比 robot 更贴）。

---

## A. 上下文文件清单（发给 HY-3 的文件）

按优先级排序，**前 6 份必读**：

| # | 文件 | 必读级别 | 作用 |
|---|---|---|---|
| 1 | `docs/common-contract.md` | 🔴 必读 | 冻结契约（接口/数据对象/状态机/铁律） |
| 2 | `docs/v3-development-plan.md` | 🔴 必读 | V3 范围/双方向/payload/DoD/P0–P9 |
| 3 | `docs/oss-list-v3.md` | 🔴 必读 | 开源选型 + GameBackbone adapter 接口规范 |
| 4 | `docs/oss-integration-and-maintenance.md` | 🟠 必读 | 开源接入 3 红线 + E1–E6 |
| 5 | `docs/engineering-setup.md` | 🟠 必读 | 工程规范 + 五道门禁 |
| 6 | `branches/video/` 全部文件 | 🟠 参考 | **V2 像素阵营模板**（game 分支照这个模式写） |
| 7 | `branches/robot/` 全部文件 | 🟢 参考 | V1 物理阵营模板（结构参考） |
| 8 | `common/interfaces/data_objects.py` + `abstract.py` | 🟢 参考 | 数据对象 + 8 个抽象接口 |

**发送建议**：先一次性发前 5 份，HY-3 确认理解后再发 `branches/video/` 代码做参考。

---

## B. 主提示词（发给 HY-3 的第一条消息）

```
你是 four-scene-brain 项目的实现工程师，不是设计者。所有架构决策已冻结在
common-contract.md 中，你的任务是严格按规范实现 V3 game 分支（双方向）。

【你的身份】
- 实现者，不是设计者。所有接口/数据对象/状态机已冻结，不得重新设计。
- 如果你认为 common 需要改动 → 立即停止，向我提问，不要擅自改。

【三条铁律（违反 = 返工）】
1. common 写一次永冻结：你只能新增 branches/game/，不能改 common/ 任何一行。
2. 场景即插件：common 不出现 game/GameGen-O 等场景名，一切差异走 payload + meta。
   方向（level/worldmodel）也只走 payload/config/meta，不进 common、不进 orchestrator。
3. 唯一交换语言：common 与 game 分支之间只交换 common-contract §4/§5 定义的对象与签名。

【V3 范围（双方向）】
- 新增 branches/game/ 全套适配器（wam/critic/primitives/mapper/executor/safety_gate/adapter）
- 两个生成方向，经 adapter.build_bundle(direction=...) 切换：
  · direction="level"      可玩 2D 平台关卡（tile map+实体）
  · direction="worldmodel" 交互式推演（状态帧+动作→下一帧）
- backbone 全 mock（真 GameGen-O / OASIS / MarioGPT 后续上 Azure）
- SafetyGate 双模式（audit 内容审核 / passthrough 放行）
- examples/game_demo.py 双方向最小闭环
- 共用一个 target="game"，不新增 target，不破坏"四场景"框架
- common 零改动，零 diff 验收必须通过

【开发顺序（P0–P9）】
严格按 v3-development-plan.md §5 的顺序：
P0 scene_objects.py → P1 backbone_interface.py → P2 backbone_mock.py →
P3 wam.py → P4 critic.py → P5 primitives.py → P6 mapper.py →
P7 executor.py + safety_gate.py → P8 adapter.py → P9 demo + 零 diff 验收

【参考模板】
branches/video/ 是 V2 像素阵营的完整实现，game 分支照这个模式写：
- 文件结构相同（scene_objects/backbone_interface/backbone_mock/wam/critic/
  primitives/mapper/executor/safety_gate/adapter + README）
- 每个文件都有 __main__ 自测
- adapter.py 是防腐层 + register(registry)
- payload 结构写进分支 README
- 区别：game 多了一个 direction 维度（level/worldmodel），统一走 GameBackbone 接口

【开源红线】
- backbone 只在 branches/game/adapter.py 内，不进 common
- wam.py 调 backbone 走 GameBackbone 接口（oss-list-v3.md §4），不直接调 API
- 换方向/换 backbone 只改 adapter.py 参数，其他文件全不动

【质量标准】
- 纯 Python stdlib，零三方依赖
- 每个文件含 __main__ 自测
- demo 必须演示：两个方向各自的 S1–S14 闭环 + 一次 S9 失败重试 + SafetyGate 双模式

现在开始。先告诉我你理解了哪些关键点，然后从 P0 开始。
```

---

## C. P0 任务提示词（HY-3 确认理解后发送）

```
【P0 · branches/game/scene_objects.py：游戏关键词词汇表（双方向共用）】

任务：实现游戏场景的关键词解析模块，供 wam 和 critic 共用。

要求：
1. 参考 branches/video/scene_objects.py 与 branches/3d/scene_objects.py 的模式
2. 定义游戏场景的关键词词汇表（双语）：
   - 主题：grass/desert/ice/cave/sky/草地/沙漠/冰原/洞穴/天空
   - 实体：coin/enemy/player/goal/hazard/金币/敌人/玩家/终点/陷阱
   - 动作：run/jump/left/right/attack/跑/跳/左移/右移/攻击
   - 关卡元素：platform/gap/spike/flag/平台/缺口/尖刺/旗帜
3. 实现 objects_from_goal(goal_text) -> dict 函数：
   - 返回 {"themes": [...], "entities": [...], "actions": [...], "elements": [...]}
   - 用关键词匹配（lower + in）
4. __main__ 自测：中英文混合 prompt 都能解析

输出文件：branches/game/scene_objects.py
```

---

## D. P1–P9 阶段提示词（按需逐个发送）

### P1 · backbone_interface.py

```
【P1 · branches/game/backbone_interface.py：GameBackbone 抽象接口（方向感知）】

任务：定义所有 game backbone 必须实现的防腐层接口，一个接口覆盖两个方向。

要求：
1. 参考 oss-list-v3.md §4.1 的接口定义
2. 实现 GameBackbone(ABC)：
   - generate(prompt, config) -> dict
     · config 必含 "direction": "level" | "worldmodel"
     · level: theme/width/height/n_coins/n_enemies/retry/seed
     · worldmodel: action/state_frames/fps/resolution/retry/seed
     · 返回 dict 必含 "direction" + 方向专属字段 + "meta"
   - get_info() -> dict（name/version/license/capabilities/directions）
3. __main__ 自测：抽象类不可实例化 + 两个 direction 的返回 schema 文档化

输出文件：branches/game/backbone_interface.py
```

### P2 · backbone_mock.py

```
【P2 · branches/game/backbone_mock.py：Mock 游戏 backbone（双方向）】

任务：实现确定性的 mock backbone，V3 默认使用，覆盖两个方向。

要求：
1. 实现 MockGameBackbone(GameBackbone)
2. direction="level"：用 sha256(prompt) 生成确定性 tile map：
   - 保证恰好 1 个 P、1 个 G，且起点可达终点
   - 四周边界封闭，实体不悬空
   - retry 时（config 有 retry）：提升可达性/可玩性（模拟细化）
3. direction="worldmodel"：用 sha256(prompt+action) 生成确定性帧序列：
   - 帧随 action 产生非零且方向合理的差分
   - retry 时：提升动作一致性
4. scene_description 从 prompt 提取（调 scene_objects.objects_from_goal）
5. __main__ 自测：相同 prompt 生成相同结果；两个 direction 都验证

输出文件：branches/game/backbone_mock.py
```

### P3 · wam.py

```
【P3 · branches/game/wam.py：GameWAM（WorldModel 实现）】

任务：实现 game 分支的 WorldModel，内部调用 backbone。

要求：
1. 参考 branches/video/wam.py 的模式（不继承 PhysicalWorldModelBase，直接实现 WorldModel）
2. 实现 GameWAM(WorldModel)：
   - __init__(backbone: GameBackbone, direction: str = "level")
   - predict_next_state(state, goal) -> State：
     · 从 goal.goal 提取 text_prompt；从 goal.constraints 提取 direction 及方向参数（默认值）
     · 调用 self.backbone.generate(prompt, config)（config 含 direction）
     · 包装成 State(modality="pixel", payload=backbone_output, meta={..., "direction": direction})
3. __main__ 自测：mock backbone 注入，两个 direction 的 predict 都返回正确 payload

输出文件：branches/game/wam.py
```

### P4 · critic.py

```
【P4 · branches/game/critic.py：GameCritic（双方向分派）】

任务：实现游戏内容校验，按 payload["direction"] 分派标准。

要求：
1. 参考 branches/video/critic.py 的模式
2. 实现 GameCritic(Critic)：
   - direction="level"（可玩性，硬指标优先）：
     · 恰好 1 个 P、1 个 G；起点可达终点（BFS，忽略敌人）；四周边界封闭；实体不悬空；尺寸在目标范围
     · 软指标：theme 与 goal.goal 关键词重叠
   - direction="worldmodel"（动作一致性 + 帧质量）：
     · frames 随 current_action 有非零且方向合理的差分；fps/resolution 达标；帧间相干
     · 软指标：scene_description 与 goal.goal 关键词重叠
   - 判定来源写入 Verification.meta.verification_source（含 direction）
3. __main__ 自测：两个 direction 的达标/不达标都验证

输出文件：branches/game/critic.py
```

### P5 · primitives.py

```
【P5 · branches/game/primitives.py：GamePrimitiveLibrary】

任务：实现游戏基元抽象（按 direction 分派）。

要求：
1. 定义基元：
   - level: platform（平台）/gap（缺口）/enemy（敌人）/coin（金币）/hazard（陷阱）/goal（终点）
   - worldmodel: frame_step（帧步进）/action_apply（动作施加）
2. 实现 GamePrimitiveLibrary(PrimitiveLibrary)：
   - abstract(draft) -> list[Primitive]，按 draft.payload["direction"] 分派
   - level：从 level_map 推导基元序列；worldmodel：从 frames+action 推导
3. __main__ 自测：两个 direction 都验证

输出文件：branches/game/primitives.py
```

### P6 · mapper.py

```
【P6 · branches/game/mapper.py：GameMapper】

任务：实现基元 → 游戏 Executable 映射。

要求：
1. 实现 GameMapper(Mapper)：
   - map(primitives, goal) -> Executable
   - payload 按 direction 含 level_spec（tile map/尺寸/实体）或 replay_spec（帧序列/动作轨迹/分辨率/帧率）
2. __main__ 自测：两个 direction 都验证

输出文件：branches/game/mapper.py
```

### P7 · executor.py + safety_gate.py

```
【P7 · branches/game/executor.py + safety_gate.py】

任务：实现游戏输出 + 双模式 SafetyGate。

executor.py 要求：
1. 实现 GameExecutor(Executor)，按 direction 分派：
   - level：写 output/game/level_<hash>.json（tile map+entities）+ .txt（ASCII 渲染）
   - worldmodel：写 output/game/replay_<hash>.json（帧序列+动作轨迹占位）
2. Delivery.meta 带 telemetry_kind="game"
3. __main__ 自测：两个 direction 的落盘文件都验证

safety_gate.py 要求：
1. 实现 GameSafetyGate(SafetyGate)，支持双模式：
   - mode="audit"（默认）：text_prompt 含 gore/explicit 关键词 → BLOCK；
     level 尺寸越界 / worldmodel 分辨率过低或帧数过少 → DEGRADE
   - mode="passthrough"：直接 PASS
2. __init__(mode="audit")
3. __main__ 自测：两种模式都验证
4. 注意：正常游戏语境（"打僵尸/战斗/怪物"）≠ gore，关键词列表要保守，宁可漏不可错杀

输出文件：branches/game/executor.py + branches/game/safety_gate.py
```

### P8 · adapter.py

```
【P8 · branches/game/adapter.py：防腐层 + 注册（direction 旋钮）】

任务：实现 game 分支的唯一入口。

要求：
1. 参考 branches/video/adapter.py 的模式
2. 实现 build_bundle(direction="level", backbone="mock", safety_mode="audit") -> BranchBundle：
   - direction="level" / "worldmodel"：传给 GameWAM/GameCritic
   - backbone="mock"：用 MockGameBackbone；backbone="gamegen-azure"/"oasis-azure"/"mariogpt-azure"：raise NotImplementedError（T1–T5 门禁未过）
   - safety_mode="audit" / "passthrough"：传给 GameSafetyGate
3. 实现 register(registry, direction="level", backbone="mock", safety_mode="audit")
4. __main__ 自测：两个 direction 注册成功 + 双模式切换

输出文件：branches/game/adapter.py
```

### P9 · demo + 零 diff 验收

```
【P9 · examples/game_demo.py + 零 diff 验收】

任务：实现 game 双方向最小闭环 demo + 验证 common 零改动。

demo 要求：
1. 参考 examples/video_demo.py 的模式
2. 演示（用两个 registry 或两次 register 切换 direction）：
   - level 正常闭环：「生成一个 2D 平台关卡：草地主题，3 个金币，能跳到终点旗帜」→ level JSON + ASCII
   - worldmodel 正常闭环：「游戏场景：角色向右移动 1 秒」→ replay JSON（帧随动作变化）
   - S9 失败重试：level 不可达（起点到不了终点）→ 回 S7 → 成功
   - SafetyGate 审核模式：gore prompt → BLOCK
   - SafetyGate 放行模式：同一 prompt → PASS
3. 输出 RunMetrics + flywheel 路径 + 边界声明

零 diff 验收要求：
1. 运行 python -m tests.test_zero_diff
2. 确认 common/ git diff 为空
3. 如果失败 → 说明 game 分支有逻辑泄漏到 common，必须修复

输出文件：examples/game_demo.py
```

---

## E. 纠偏话术（HY-3 跑偏时用）

| 情况 | 纠偏话术 |
|---|---|
| HY-3 想改 common | "common 已冻结，不能改。如果你认为必须改，先停下来告诉我原因。" |
| HY-3 把 direction 分支写进 common/orchestrator | "方向只走 payload/config/meta，common 不出现 level/worldmodel 字样。" |
| HY-3 想在 wam.py 直接调 GameGen-O API | "backbone 只能通过 GameBackbone 接口调用，参考 backbone_mock.py 的模式。" |
| HY-3 只做一个方向 | "V3 是双方向（level + worldmodel），两个都要，经 adapter 的 direction 旋钮切换。" |
| HY-3 想新增 target（如 game_wm） | "两个方向共用一个 target='game'，不新增 target，不破坏四场景框架。" |
| HY-3 忘了 __main__ 自测 | "每个文件都要有 __main__ 自测，参考 branches/video/ 的文件。" |
| HY-3 想装第三方库 | "V3 纯 stdlib，零三方依赖。backbone 全 mock。" |

---

## F. 省钱提醒

- **一次性发上下文**：前 5 份文件一次发完，避免 HY-3 反复问你要文件浪费积分。
- **分阶段验收**：每个 P 阶段完成后先跑自测，通过了再发下一阶段提示词。
- **用 V2 video 做参考**：branches/video/ 是像素阵营完整模板，让 HY-3 照着写，减少返工。
- **双方向控量**：scene_objects/backbone 接口/adapter 骨架共享，只有 payload/critic/executor 按 direction 分派，别让 HY-3 写两套完全独立的代码。
- **卡住就问**：HY-3 卡住超过 3 轮 → 让它停下来汇报问题，你来决策。

---

## G. V3 DoD 验收清单（全部完成后检查）

- [ ] `python -m examples.game_demo` 跑通两个方向的场景（level + worldmodel）
- [ ] `python -m pytest tests/` 全绿（含新增 game 测试）
- [ ] `python -m tests.test_zero_diff` 通过，common git diff 为空
- [ ] `branches/game/README.md` 写清双方向 payload 结构 + SafetyGate 双模式 + direction 旋钮
- [ ] SafetyGate 双模式可切换（audit/passthrough）
- [ ] 两个方向共用一个 target="game"，未新增 target
- [ ] 边界声明：README 注明「验证编排内核，不证明关卡/推演质量」
- [ ] git commit + push 到 GitHub
