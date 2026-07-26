# HY-3 V4 开发启动包（完整独立 3D · 物理阵营 · 多任务）

> 用途：把这份文件 + 指定的上下文文件发给 HY-3，让它按冻结契约开发 V4（把 `branches/3d` 从 V1 的 robot 作业场景扩展为全量独立 3D）。
> 前置：V1+V2 已交付并上架 GitHub（common 冻结），common 零改动。V3 可并行/先于 V4 完成（互不依赖）。
> **V4 是物理阵营**：3d 继续与 robot 共享 `PhysicalWorldModelBase`（WAM 物理先验），且**必须保留 V1 的 `task="robot_scene"` 能力不回归**。
> 多任务：`task = robot_scene / text_to_3d / image_to_3d / pointcloud_completion / pbr_texture`，经 `adapter.build_bundle(task=...)` 切换。

---

## A. 上下文文件清单（发给 HY-3 的文件）

按优先级排序，**前 6 份必读**：

| # | 文件 | 必读级别 | 作用 |
|---|---|---|---|
| 1 | `docs/common-contract.md` | 🔴 必读 | 冻结契约（接口/数据对象/状态机/铁律） |
| 2 | `docs/v4-development-plan.md` | 🔴 必读 | V4 范围/多任务/payload/DoD/P0–P9 |
| 3 | `docs/oss-list-v4.md` | 🔴 必读 | 3D 开源选型 + ThreeDBackbone adapter 接口规范 |
| 4 | `docs/oss-integration-and-maintenance.md` | 🟠 必读 | 开源接入 3 红线 + E1–E6 |
| 5 | `docs/engineering-setup.md` | 🟠 必读 | 工程规范 + 五道门禁 |
| 6 | `branches/3d/` 现有全部文件 | 🟠 必读 | **V1 3d 基线（V4 在此扩展，robot_scene 不许回归）** |
| 7 | `branches/_physical/base.py` | 🟠 必读 | PhysicalWorldModelBase（3d WAM 要继承） |
| 8 | `branches/video/` 全部文件 | 🟢 参考 | 分支 backbone 防腐层模式参考（video 已示范 backbone_interface/mock/adapter） |
| 9 | `common/interfaces/data_objects.py` + `abstract.py` | 🟢 参考 | 数据对象 + 8 个抽象接口 |

**发送建议**：先一次性发前 6 份，HY-3 确认理解后再发 video 分支做 backbone 模式参考。

---

## B. 主提示词（发给 HY-3 的第一条消息）

```
你是 four-scene-brain 项目的实现工程师，不是设计者。所有架构决策已冻结在
common-contract.md 中，你的任务是严格按规范开发 V4：把 branches/3d 从 V1 的
robot 作业场景扩展为全量独立 3D（多任务）。

【你的身份】
- 实现者，不是设计者。所有接口/数据对象/状态机已冻结，不得重新设计。
- 如果你认为 common 需要改动 → 立即停止，向我提问，不要擅自改。

【三条铁律（违反 = 返工）】
1. common 写一次永冻结：你只能改/扩 branches/3d/，不能改 common/ 任何一行。
2. 场景即插件：common 不出现 3d/TRELLIS 等场景名，一切差异走 payload + meta。
   任务（task）也只走 payload/config/meta，不进 common、不进 orchestrator。
3. 唯一交换语言：common 与 3d 分支之间只交换 common-contract §4/§5 定义的对象与签名。

【V4 范围（多任务，扩展 branches/3d）】
- 在 branches/3d/ 上扩展，新增 backbone 防腐层（backbone_interface/backbone_mock）
  并扩展现有 wam/critic/primitives/mapper/executor/safety_gate/adapter
- 多任务，经 adapter.build_bundle(task=...) 切换：
  robot_scene(V1保留) / text_to_3d / image_to_3d / pointcloud_completion / pbr_texture
- 物理阵营：3d WAM 继承 branches/_physical/base.py 的 PhysicalWorldModelBase
- backbone 全 mock（真 TRELLIS/TripoSR/DreamGaussian 后续上 Azure）
- SafetyGate 双模式（audit 内容审核 / passthrough 放行）
- examples/3d_full_demo.py 多任务最小闭环
- 仍是 target="3d"，不新增 target
- common 零改动，零 diff 验收必须通过；V1 robot_scene 不回归

【开发顺序（P0–P9）】
严格按 v4-development-plan.md §5 的顺序：
P0 scene_objects.py 扩展 → P1 backbone_interface.py → P2 backbone_mock.py →
P3 wam.py → P4 critic.py → P5 primitives.py → P6 mapper.py →
P7 executor.py + safety_gate.py → P8 adapter.py(+V1回归) → P9 demo + 零 diff 验收

【参考模板】
- branches/3d/ 现有文件是 V1 基线，robot_scene 能力必须保留
- branches/_physical/base.py 的 PhysicalWorldModelBase：3d WAM 继承它
- branches/video/ 的 backbone_interface/backbone_mock/adapter：backbone 防腐层写法参考
- 每个文件都有 __main__ 自测；payload 结构写进分支 README

【开源红线】
- backbone 只在 branches/3d/adapter.py 内，不进 common
- wam.py 调 backbone 走 ThreeDBackbone 接口（oss-list-v4.md §4），不直接调 API
- 换任务/换 backbone 只改 adapter.py 参数，其他文件全不动

【质量标准】
- 纯 Python stdlib，零三方依赖
- 每个文件含 __main__ 自测
- demo 必须演示：text_to_3d 与 image_to_3d 闭环 + 一次 S9 失败重试 + SafetyGate 双模式
  + V1 robot_scene 回归

现在开始。先告诉我你理解了哪些关键点，然后从 P0 开始。
```

---

## C. P0 任务提示词（HY-3 确认理解后发送）

```
【P0 · branches/3d/scene_objects.py 扩展：3D 关键词词汇表】

任务：在现有 V1 scene_objects 基础上扩展 3D 生成关键词，供 wam 和 critic 共用。

要求：
1. 保留 V1 robot_scene 相关关键词（不回归）
2. 扩展 3D 生成关键词（双语）：
   - 物体：cup/chair/table/car/robot/杯子/椅子/桌子/车/机器人
   - 材质：metal/wood/plastic/glass/fabric/金属/木/塑料/玻璃/布
   - 属性：red/blue/smooth/rough/transparent/红/蓝/光滑/粗糙/透明
   - 场景元素：walkable/floor/wall/可行走/地板/墙
3. 实现/扩展 objects_from_goal(goal_text) -> dict：
   返回 {"objects": [...], "materials": [...], "attributes": [...], "scene_elements": [...]}
4. __main__ 自测：中英文混合 prompt 都能解析；V1 旧 prompt 仍解析正确

输出文件：branches/3d/scene_objects.py
```

---

## D. P1–P9 阶段提示词（按需逐个发送）

### P1 · backbone_interface.py

```
【P1 · branches/3d/backbone_interface.py：ThreeDBackbone 抽象接口（任务感知）】

任务：定义所有 3d backbone 必须实现的防腐层接口，一个接口覆盖全部任务。

要求：
1. 参考 oss-list-v4.md §4.1 与 branches/video/backbone_interface.py 的模式
2. 实现 ThreeDBackbone(ABC)：
   - generate(prompt, config) -> dict
     · config 必含 "task": robot_scene|text_to_3d|image_to_3d|pointcloud_completion|pbr_texture
     · + 任务参数（source_image/source_pointcloud/representation/poly_budget/retry/seed）
     · 返回 dict 必含 "task" + geometry/semantics/texture/source + "meta"
   - get_info() -> dict（name/version/license/capabilities/tasks）
3. __main__ 自测：抽象类不可实例化 + 各 task 返回 schema 文档化

输出文件：branches/3d/backbone_interface.py
```

### P2 · backbone_mock.py

```
【P2 · branches/3d/backbone_mock.py：Mock 3D backbone（多任务）】

任务：实现确定性 mock backbone，V4 默认，覆盖全部任务。

要求：
1. 实现 Mock3DBackbone(ThreeDBackbone)
2. 用 sha256(prompt+task) 生成确定性 geometry：
   - manifold=True、vertices>0、faces>0、bbox 非退化
   - task=pbr_texture：texture 含 albedo/roughness/metallic ∈ [0,1]
   - task=robot_scene：保持 V1 行为（不回归）
   - retry 时：提升 manifold/语义对齐（模拟细化）
3. scene_description 从 prompt 提取（调 scene_objects.objects_from_goal）
4. __main__ 自测：相同 prompt 相同结果；各 task 都验证；robot_scene 与 V1 一致

输出文件：branches/3d/backbone_mock.py
```

### P3 · wam.py

```
【P3 · branches/3d/wam.py：3dWAM（继承 PhysicalWorldModelBase）】

任务：实现/扩展 3d 分支的 WorldModel，内部调用 backbone。

要求：
1. 继承 branches/_physical/base.py 的 PhysicalWorldModelBase（复用 WAM 物理先验）
2. 实现 3dWAM：
   - __init__(backbone: ThreeDBackbone, task: str = "text_to_3d")
   - predict_next_state(state, goal) -> State：
     · 从 goal.goal 提取 text_prompt；从 goal.constraints 提取 task 及任务参数（默认值）
     · 调用 self.backbone.generate(prompt, config)（config 含 task）
     · 包装成 State(modality="geometry", payload=backbone_output, meta={..., "task": task})
3. __main__ 自测：mock backbone 注入，各 task 的 predict 都返回正确 payload

输出文件：branches/3d/wam.py
```

### P4 · critic.py

```
【P4 · branches/3d/critic.py：3dCritic（按 task 分派）】

任务：实现 3D 内容校验，按 payload["task"] 分派标准。

要求：
1. 参考 branches/video/critic.py 的分派模式
2. 实现 3dCritic(Critic)：
   - 通用几何硬指标：manifold=True、vertices>0、faces>0、bbox 非退化
   - 任务专属：
     · text_to_3d：semantics 与 goal.goal 关键词重叠
     · image_to_3d：source 引用与 geometry 绑定一致
     · pointcloud_completion：补全点数 ≥ 输入，无 NaN/越界
     · pbr_texture：texture 含 albedo/roughness/metallic ∈ [0,1]
     · robot_scene：可行走性 + 几何保真（V1 标准，不回归）
   - 判定来源写入 Verification.meta.verification_source（含 task）
3. __main__ 自测：各 task 达标/不达标都验证

输出文件：branches/3d/critic.py
```

### P5 · primitives.py

```
【P5 · branches/3d/primitives.py：3dPrimitiveLibrary】

任务：实现 3D 基元抽象（按 task 分派）。

要求：
1. 定义基元：extrude（拉伸）/smooth（平滑）/weld（焊接）/texture（贴图）/walkable（可行走区）
2. 实现 3dPrimitiveLibrary(PrimitiveLibrary)：
   - abstract(draft) -> list[Primitive]，按 draft.payload["task"] 分派
3. __main__ 自测：各 task 都验证

输出文件：branches/3d/primitives.py
```

### P6 · mapper.py

```
【P6 · branches/3d/mapper.py：3dMapper】

任务：实现基元 → 3d Executable 映射。

要求：
1. 实现 3dMapper(Mapper)：
   - map(primitives, goal) -> Executable
   - payload 含 glb_spec（representation/geometry/texture/task）
2. __main__ 自测：各 task 都验证

输出文件：branches/3d/mapper.py
```

### P7 · executor.py + safety_gate.py

```
【P7 · branches/3d/executor.py + safety_gate.py】

任务：实现 GLB 输出 + 双模式 SafetyGate。

executor.py 要求：
1. 实现 3dExecutor(Executor)：写 output/3d/model_<hash>.glb（纯 stdlib 最小合法 GLB 头 JSON+BIN chunk）
2. Delivery.meta 带 telemetry_kind="geometry"
3. __main__ 自测：验证 GLB 头合法

safety_gate.py 要求：
1. 实现 3dSafetyGate(SafetyGate)，支持双模式：
   - mode="audit"（默认）：text_prompt 含 NSFW/版权角色关键词 → BLOCK；
     geometry 顶点数过低 / bbox 退化 → DEGRADE
   - mode="passthrough"：直接 PASS
2. __init__(mode="audit")
3. __main__ 自测：两种模式都验证
4. 注意：正常 3D 题材（"骷髅摆件/武器模型"）≠ NSFW，关键词列表保守，宁可漏不可错杀

输出文件：branches/3d/executor.py + branches/3d/safety_gate.py
```

### P8 · adapter.py（+ V1 回归）

```
【P8 · branches/3d/adapter.py：防腐层 + 注册（task 旋钮）+ V1 回归】

任务：实现 3d 分支的唯一入口，并确保 V1 robot_scene 不回归。

要求：
1. 参考 branches/video/adapter.py 的模式
2. 实现 build_bundle(task="text_to_3d", backbone="mock", safety_mode="audit") -> BranchBundle：
   - task=robot_scene|text_to_3d|image_to_3d|pointcloud_completion|pbr_texture
   - backbone="mock"：用 Mock3DBackbone；backbone="trellis-azure"/"triposr-azure"/"dreamgaussian-azure"：raise NotImplementedError（T1–T5 未过）
   - safety_mode="audit"/"passthrough"：传给 3dSafetyGate
3. 实现 register(registry, task="text_to_3d", backbone="mock", safety_mode="audit")
4. __main__ 自测：各 task 注册成功 + 双模式切换
5. **回归**：跑 examples/3d_scene_demo（V1）+ 相关测试，确认 robot_scene 行为不变

输出文件：branches/3d/adapter.py
```

### P9 · demo + 零 diff 验收

```
【P9 · examples/3d_full_demo.py + 零 diff 验收】

任务：实现 3d 多任务最小闭环 demo + 验证 common 零改动。

demo 要求：
1. 参考 examples/video_demo.py 的模式
2. 演示：
   - text_to_3d 闭环：「生成一个红色杯子的 3D 模型」→ 占位 GLB
   - image_to_3d 闭环：「概念图 → 3D GLB（一把椅子）」→ 占位 GLB
   - S9 失败重试：geometry 退化（faces=0/非 manifold）→ 回 S7 → 成功
   - SafetyGate 审核模式：版权角色 prompt → BLOCK
   - SafetyGate 放行模式：同一 prompt → PASS
   - V1 robot_scene 回归：再跑一次 V1 场景确认不变
3. 输出 RunMetrics + flywheel 路径 + 边界声明

零 diff 验收要求：
1. 运行 python -m tests.test_zero_diff
2. 确认 common/ git diff 为空
3. 失败 → 说明 3d 扩展泄漏到 common，必须修复

输出文件：examples/3d_full_demo.py
```

---

## E. 纠偏话术（HY-3 跑偏时用）

| 情况 | 纠偏话术 |
|---|---|
| HY-3 想改 common | "common 已冻结，不能改。如果你认为必须改，先停下来告诉我原因。" |
| HY-3 把 task 分支写进 common/orchestrator | "任务只走 payload/config/meta，common 不出现 text_to_3d 等字样。" |
| HY-3 想在 wam.py 直接调 TRELLIS API | "backbone 只能通过 ThreeDBackbone 接口调用，参考 backbone_mock.py 的模式。" |
| HY-3 删除/破坏 V1 robot_scene | "V1 robot_scene 必须保留，task='robot_scene' 行为不许变，P8 有回归检查。" |
| HY-3 不继承 PhysicalWorldModelBase | "3d 是物理阵营，WAM 要继承 branches/_physical/base.py 的 PhysicalWorldModelBase。" |
| HY-3 想新增 target | "仍是 target='3d'，扩展不新建分支。" |
| HY-3 忘了 __main__ 自测 | "每个文件都要有 __main__ 自测，参考 branches/video/ 的文件。" |
| HY-3 想装第三方库 | "V4 纯 stdlib，零三方依赖。backbone 全 mock。" |

---

## F. 省钱提醒

- **一次性发上下文**：前 6 份文件一次发完。
- **分阶段验收**：每个 P 阶段完成后先跑自测，通过了再发下一阶段。
- **用 video 分支做 backbone 参考**：backbone_interface/backbone_mock/adapter 的写法 video 已示范。
- **V1 回归早做**：P8 的 robot_scene 回归别拖到最后，扩展时随时跑 V1 demo。
- **卡住就问**：HY-3 卡住超过 3 轮 → 停下来汇报，你来决策。

---

## G. V4 DoD 验收清单（全部完成后检查）

- [ ] `python -m examples.3d_full_demo` 跑通多任务场景（text_to_3d + image_to_3d + retry + 双模式 + V1 回归）
- [ ] `python -m pytest tests/` 全绿（含新增 3d 全量测试 + V1 不回归）
- [ ] `python -m tests.test_zero_diff` 通过，common git diff 为空
- [ ] `branches/3d/README.md` 写清多任务 payload 结构 + SafetyGate 双模式 + task 旋钮
- [ ] SafetyGate 双模式可切换（audit/passthrough）
- [ ] V1 robot_scene 能力保留（demo + 测试不回归）
- [ ] 仍是 target="3d"，未新增 target
- [ ] 边界声明：README 注明「验证编排内核，不证明 3D 质量」
- [ ] git commit + push 到 GitHub
