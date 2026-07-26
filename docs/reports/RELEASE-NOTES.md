# four-scene-brain — Release Notes (V1–V5)

> 版本标签：V1–V5 是"组合（combination）"标签；`common/` 冻结内核版本恒为 **v1.0.0**（write-once-freeze）。
> 交付性质：**全 mock backbone**。验证编排内核 + 接口契约 + 跨分支 DAG + 统一数据飞轮，**不证明任一分支的真实质量**。

---

## 能力矩阵（5 版本）

| 版本 | 阵营 | 交付能力 | 关键机制 | 测试 |
|---|---|---|---|---|
| **V1** | 物理 | robot + 3d(robot 作业场景) | 冻结 common 内核（S1–S14）、DAG、S9 重试、SafetyGate、零 diff 验收 | 23 |
| **V2** | 像素 | video | 像素阵营首验、SafetyGate 双模式、mp4 占位、防腐层 backbone | +8 → 31 |
| **V3** | 像素 | game（双方向） | 一个 target 承载 level + worldmodel 两方向、双模式安全门 | +17 → 48 |
| **V4** | 物理 | 完整 3D（多任务） | 一个 target 覆盖 text/image_to_3d + 点云补全 + PBR；V1 robot_scene 字节级不变 | +17 → 65 |
| **V5** | — | 全场景集成 + 跨分支飞轮 + 发布 | 四分支同注册、跨分支复合指令 DAG（3d→robot 串联）、统一飞轮聚合视图 | +7 → **72** |

**全量：72/72 pytest PASS；6 个 demo 全绿；`common/` 全程零 diff。**

---

## 终局命题验证（V5）

一条冻结内核（`common/`，纯 stdlib，v1.0.0）同时驱动四个场景，跨场景 Telemetry 汇入同一飞轮：

- **跨分支 DAG（物理阵营）**：「生成机器人作业客厅 3D 场景 → 机器人把红杯拿到托盘」→ `[3d(robot_scene), robot depends_on 3d]`，State 串联，两 SubGoal 全成功。
- **跨分支复合（像素阵营）**：「猫奔跑视频 + 可玩平台关卡」→ `[video, game]`，独立 SubGoal 全成功。
- **统一飞轮**：四分支 Telemetry（kind = torque/geometry/video/game）落入同一 jsonl，聚合视图按 branch 分组输出 count / trace / avg_score。

## 三条铁律（全程守住）

1. **写一次永冻结**：`common/`（含 `common/flywheel` 接口）自 V1 起零改动，V2–V5 只加 `branches/<scene>/` 与 `examples/`。
2. **场景即插件**：分支之间不直接 import，只经 SubGoal DAG + State 串联交互；common 无场景名/模态 if-else。
3. **唯一交换语言**：common ↔ 分支只交换 `docs/common-contract.md` §4/§5 定义的数据对象与签名。

## 边界声明

- 全 mock：真 GR00T / DreamGaussian / HunyuanVideo / TRELLIS 走 Azure，接入前过 `docs/engineering-setup.md` §2 T1–T5 门禁。
- V5 证明**集成与跨分支飞轮闭环**，不证明单分支真实质量或物理可行性（sim2real / 画质缺口）。

## 快速验证

```bash
python -m pytest tests/ -v          # 72 tests
python -m examples.integration_demo # 跨分支 DAG + 统一飞轮聚合
python -m tests.test_zero_diff      # common git diff 为空
```

## Commits (release chain)

`c4cf23e`(V1) → `5b0f93a` → `5e691d2` → `dc19316` → `1c635db`(V2) → `f407548` → `1c6843d`(V3) → `df189f4`(V4) → `2350d80`(V5)
