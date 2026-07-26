# HY-3 开发启动包（four-scene-brain · V1）

> 用法：新开开发会话，把下面 **A. 上下文文件**（5 份）作为附件/上下文发给 HY-3，再依次粘贴 **B. 主提示词 → C. P0 任务 → 后续 P1–P8**。
> 目的：让 HY-3 当"实现工程师"照 frozen spec 翻译，**不重新设计**，省钱不返工。

---

## A. 需要发给 HY-3 的上下文文件（5 份，只读）

| 文件 | 作用 |
|---|---|
| `docs/dev-handoff.md` | 交接包总纲（红线/顺序/验收闸） |
| `docs/common-contract.md` | **最高权威**：数据对象§4 / 接口§5 / 状态机§6 / 红线§10 |
| `docs/v1-development-plan.md` | V1 范围§1 / physical 接口§4 / 计划§5 / DoD§7 |
| `docs/oss-integration-and-maintenance.md` | 开源合规§A / contract test§B1 / README模板§B3 |
| `docs/engineering-setup.md` | 包名 / pytest / git / 开源选型 / 模型策略§5 |

---

## B. 主提示词（开发会话第一段先粘贴）

```
你是 four-scene-brain 的【实现工程师】，不是设计者。本项目的架构、接口、数据对象、边界已全部定稿并【冻结】，写在随附的 4 份契约文档里。你的唯一职责：严格按 spec，用 Python 3.13 纯标准库把代码实现出来，禁止重新设计或"顺手优化"架构。

先通读这 4 份（只读，当作法律）：
1. docs/common-contract.md —— 最高权威（数据对象§4 / 接口§5 / 状态机§6 / 红线§10）
2. docs/v1-development-plan.md —— V1 范围§1 / physical接口§4 / 计划§5 / DoD§7
3. docs/oss-integration-and-maintenance.md —— 开源合规§A / contract test§B1 / README模板§B3
4. docs/engineering-setup.md —— 包名 / pytest / git / 选型

铁律（违反即返工）：
- common 纯 stdlib、零三方依赖；payload 不透明；无场景名 / 无模态 if-else；不 import 任何 branches/
- 接口签名、数据对象字段【一字不改】（只允许 meta 内扩展）
- 重试 ≤ max_retry；分支异常映射 FailureKind，不穿透 common
- SafetyGate 在 S11→S12 之间；robot 必须实现
- 每个 .py：类型注解 + dataclass + docstring（标注阵营/工序/边界）+ __main__ 自测
- backbone 一律 backend='mock' 默认，真主干留可替换口（走 Azure，先过测试门禁）

如果你觉得"这里该改 common"，【停下来问我】，不要自作主张。
确认读完并理解后，只回复"已就绪"，等我发 P0 任务。
```

---

## C. P0 任务提示词（第一段活）

```
【P0 · common/interfaces：数据对象 + 抽象接口】
严格按 common-contract §4 + §5 实现，放在 common/interfaces/ 下。

数据对象（@dataclass）：State / SubGoal / Intent / Draft / Verification / Primitive / Executable / Delivery / Telemetry / RunMetrics
枚举（Enum）：FailureKind / SafetyVerdict
抽象接口（ABC + @abstractmethod）：WorldModel / Critic / PrimitiveLibrary / Mapper / Executor / SafetyGate / Memory / Flywheel（签名与 §5 一字不差）

要求：
- 纯 stdlib（dataclasses / abc / typing / enum）；可变默认值用 field(default_factory=...)
- 抽象类不可直接实例化；数据类可实例化
- 每文件 __main__ 自测：实例化各数据类 + 断言抽象类实例化抛 TypeError
- 附 contract test 雏形：用 inspect 反射断言各接口方法签名与 §5 一致

输出：common/interfaces/ 下的完整 .py（用 ```python 分隔并标注文件名）+ 你跑 __main__ 的结果。
```

---

## D. 后续阶段提示词（P1–P8，逐个发）

**P1 · common/registry**
```
按 §7 实现 BranchBundle(@dataclass) + Registry(register/resolve)。resolve 未注册 target 抛 KeyError；register 校验 bundle.modality 非空。__main__ 自测：注册假 bundle→resolve 成功；resolve 未知 target→KeyError。输出完整 .py + 自测结果。
```

**P2 · common/orchestrator**
```
按 §6 实现 Orchestrator(registry, memory, flywheel, max_retry=3).run(raw_input, source)->RunMetrics。含 trace_id、S3 规则解析(留 LLM 插件口)、S4 SubGoal DAG 拓扑排序、S5 路由、S7–S14 全流程、SafetyGate、分支异常→FailureKind、State 跨 SubGoal 串联。modality-agnostic，不 import branches/，无场景 if-else。__main__ 自测：注册 mock 假分支，跑通一条指令 S1–S14 + 一次 S9 失败重试。输出完整 .py + 自测结果。
```

**P3 · common/memory + common/flywheel**
```
按 §8 实现 InMemory(dict) + Flywheel 落盘/缓冲实现，接口与 §5 一致；本地只缓冲不训；Telemetry 带 trace_id。__main__ 自测：read/write + record/distill。输出完整 .py + 自测结果。
```

**P4 · branches/_physical/base.py（场景侧共享基类，不进 common）**
```
按 v1-plan §4 实现 PhysicalWorldModelBase(WorldModel) + 物理 State 工具。robot payload schema：pose(SE3)/twist/wrench/contact/joint_state。仍实现统一 WorldModel 接口。__main__ 自测：robot/3d 可继承、能构造物理 State。输出完整 .py + 自测结果。
```

**P5 · branches/robot**
```
按 v1-plan §3/§4 实现：wam(RobotWorldModel, backbone='mock') / critic(RobotCritic, force-torque 优先) / primitives(RobotPrimitives) / mapper(HandMapper→零力矩 Executable) / executor(mock) / safety_gate(必须：力矩上限+关节限位+禁撞区) / adapter.register。全 mock；docstring 标物理阵营。__main__ 自测：注册进 Registry。输出完整 .py + 自测结果。
```

**P6 · branches/3d（仅 robot 作业场景，不做全量 3D）**
```
实现 adapter(ThreeDWorldModel, backbone='mock') / critic(可行走性+几何保真+文本-场景对齐) / primitives / mapper(MeshMapper) / exporter(占位 GLB) / safety_gate(pass-through) / adapter.register。docstring 标物理阵营。__main__ 自测：注册 + 输出占位 GLB。输出完整 .py + 自测结果。
```

**P7 · examples/robot_demo + examples/3d_scene_demo**
```
各跑通 S1–S14。robot：输入"用灵巧手把桌上红杯拿到托盘"（DAG：抓杯→移动→放置）→零力矩 Delivery+带 trace_id 的 Telemetry；演示一次 S9 失败→回 S7→成功 + 一次 SafetyGate BLOCK。3d：输入"生成机器人作业的客厅场景：可行走，含桌子和桌上红杯"→占位 GLB。输出 demo 脚本 + 运行结果。
```

**P8 · 冻结验收**
```
零 diff 测试 + V1 DoD（v1-plan §7 七条）。零 diff：临时加 mock5 场景，common/ git diff 必须为空。输出：contract test 结果 + 零 diff 证明 + RunMetrics（成功率/重试/各 Critic 分）。
```

---

## E. 纠偏话术（HY-3 一旦乱改就发）
```
停下来。你刚改动了 common 的接口/字段，或加入了场景逻辑——这违反冻结契约。请回退该改动，严格按 common-contract §4/§5 原样实现。只允许 meta 内扩展，不允许改签名/字段。
```

---

## F. 省钱提醒
- 每个阶段**只附该阶段需要的章节**（见 dev-handoff §4），不必每次发全部 4 份。
- P0–P3（common）建议用较稳模型；P4–P8 可用性价比模型。
- 每阶段跑 `__main__` 自测 + contract test，挡住即返工，不人工复审。
