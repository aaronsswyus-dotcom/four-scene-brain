# V3 / V4 / V5 验收测试计划（acceptance test plan）

> 用途：HY-3 每完成一个版本，按本文档**逐项验收**；三版本全部完成后做**全量回归**。
> 依据：各版本 `vX-development-plan.md` 的 DoD、`common-contract.md` §9/§10 冻结纪律。
> 原则：**每个版本都要过「单元自测 + 分支测试 + demo 闭环 + 零 diff + DoD 清单」五关**；前一版本不许回归。

---

## 0. 测试金字塔（所有版本通用）

```
        ┌─────────────────────────┐
        │ L4 零 diff 验收（冻结）   │  common/ git diff 必须为空
        ├─────────────────────────┤
        │ L3 DoD 验收（场景闭环）   │  demo 跑通 S1–S14 + retry + SafetyGate
        ├─────────────────────────┤
        │ L2 分支 pytest           │  tests/test_<branch>_branch.py 全绿
        ├─────────────────────────┤
        │ L1 单元 __main__ 自测     │  每个分支文件自带 __main__ 自测
        └─────────────────────────┘
```

**通用测试命令**：
```bash
PY="C:/Users/aaron/.workbuddy/binaries/python/envs/default/Scripts/python.exe"
$PY -m pytest tests/ -v          # L2 全量 pytest
$PY -m tests.test_zero_diff      # L4 零 diff 验收
$PY -m examples.<scene>_demo     # L3 场景闭环 demo
```

**通用通过判据**：全绿 + common 零 diff + 边界声明显式输出。

---

## 1. V3（game · 双方向）验收

### 1.1 测试命令
```bash
$PY -m pytest tests/ -v                 # 含 tests/test_game_branch.py
$PY -m examples.game_demo               # 双方向闭环 demo
$PY -m tests.test_zero_diff             # 零 diff
```

### 1.2 V3 DoD 清单（逐项打勾）
- [ ] `python -m examples.game_demo` 跑通**两个方向**：
  - direction="level"：「生成 2D 平台关卡：草地主题，3 金币，能跳到终点旗帜」→ level JSON + ASCII
  - direction="worldmodel"：「游戏场景：角色向右移动 1 秒」→ replay JSON（帧随动作变化）
- [ ] **重试路径**：level 不可达（起点到不了终点）→ S9 回 S7 → 成功（retries≥1）
- [ ] **SafetyGate 审核**：gore prompt → BLOCK
- [ ] **SafetyGate 放行**：同一 prompt → PASS（双模式可切换）
- [ ] `pytest tests/` 全绿（含新增 game 测试；V1/V2 不回归）
- [ ] `test_zero_diff` 通过，`common/` git diff 为空
- [ ] 两方向共用 `target="game"`，**未新增 target**
- [ ] `branches/game/README.md` 写清双方向 payload + SafetyGate 双模式 + direction 旋钮
- [ ] 边界声明：demo/README 注明「验证编排内核，不证明关卡/推演质量」

### 1.3 V3 关键测试点（Critic 正确性）
| 用例 | 期望 |
|---|---|
| level：无玩家起点 P | Critic 判 fail（STRUCTURAL/RETRYABLE） |
| level：起点到不了终点 | Critic 判 fail → retry |
| level：边界不封闭 / 实体悬空 | Critic 判 fail |
| worldmodel：动作无帧差分 | Critic 判 fail |
| 两方向 theme/scene 与 prompt 对齐 | Critic 软指标给分 |

---

## 2. V4（完整 3D · 多任务）验收

### 2.1 测试命令
```bash
$PY -m pytest tests/ -v                 # 含 tests/test_3d_branch.py（全量任务）
$PY -m examples.3d_full_demo            # 多任务闭环 demo
$PY -m examples.3d_scene_demo           # V1 robot_scene 回归
$PY -m tests.test_zero_diff             # 零 diff
```

### 2.2 V4 DoD 清单（逐项打勾）
- [ ] `python -m examples.3d_full_demo` 跑通**多任务**：
  - task="text_to_3d"：「生成一个红色杯子的 3D 模型」→ 占位 GLB
  - task="image_to_3d"：「概念图 → 3D GLB（一把椅子）」→ 占位 GLB
- [ ] **重试路径**：geometry 退化（faces=0 / 非 manifold）→ S9 回 S7 → 成功
- [ ] **SafetyGate 审核**：版权角色 prompt → BLOCK
- [ ] **SafetyGate 放行**：同一 prompt → PASS
- [ ] **V1 robot_scene 回归**：`examples/3d_scene_demo` + 相关测试仍通过
- [ ] `pytest tests/` 全绿（含新增 3d 全量测试；V1/V2/V3 不回归）
- [ ] `test_zero_diff` 通过，`common/` git diff 为空
- [ ] 仍是 `target="3d"`，**未新增 target**
- [ ] 3d WAM 继承 `PhysicalWorldModelBase`
- [ ] `branches/3d/README.md` 写清多任务 payload + SafetyGate 双模式 + task 旋钮
- [ ] 边界声明：注明「验证编排内核，不证明 3D 质量」

### 2.3 V4 关键测试点（Critic 正确性）
| 用例 | 期望 |
|---|---|
| 通用：faces=0 / 非 manifold / bbox 退化 | Critic 判 fail |
| text_to_3d：semantics 与 prompt 不对齐 | 软指标扣分 |
| image_to_3d：source 引用与 geometry 不绑定 | Critic 判 fail |
| pointcloud_completion：补全点数 < 输入 | Critic 判 fail |
| pbr_texture：缺 albedo/roughness/metallic 或越界 | Critic 判 fail |
| robot_scene：V1 标准（可行走/保真） | 不回归 |

---

## 3. V5（全场景集成 + 跨分支飞轮）验收

### 3.1 测试命令
```bash
$PY -m pytest tests/ -v                 # 含 tests/test_integration.py + 全量回归
$PY -m examples.integration_demo        # 跨分支 DAG demo
$PY -m tests.test_zero_diff             # 零 diff（含全部分支注册）
```

### 3.2 V5 DoD 清单（逐项打勾）
- [ ] `python -m examples.integration_demo` 跑通 **≥2 条跨分支 DAG**：
  - 3d→robot：「生成客厅 3D 场景，让机器人把红杯拿到托盘」（State 串联，depends_on 生效）
  - video+game：「生成猫奔跑视频 + 可玩平台关卡」
- [ ] **统一飞轮**：≥2 分支 Telemetry 落同一 jsonl；`aggregate_by_branch` 按 kind 分组正确
- [ ] `pytest tests/` 全绿（含 test_integration + V1–V4 全量回归）
- [ ] `test_zero_diff` 通过，`common/` git diff 为空
- [ ] **未新建分支、未接新 backbone、未改 common/flywheel 接口**
- [ ] 全部 demo 跑通不回归（robot/3d_scene/video/game/3d_full/integration）
- [ ] 发布物就绪：版本号 + CHANGELOG（V1–V5）+ README 终稿 + Release 说明
- [ ] 边界声明：注明「验证集成与跨分支飞轮，不证明单分支真实质量」

### 3.3 V5 关键测试点
| 用例 | 期望 |
|---|---|
| 3d→robot：robot 依赖 3d 输出（State 串联） | depends_on 生效，顺序正确 |
| 跨分支 Telemetry：多 kind 入同一 jsonl | 分组计数正确 |
| 注册全部分支后 | common 零 diff |
| 单分支闭环（各分支独立） | 不回归 |

---

## 4. 三版本全量回归（V3+V4+V5 都完成后）

```bash
$PY -m pytest tests/ -v     # 期望：V1(23) + V2(8) + V3(?) + V4(?) + V5(?) 全绿
$PY -m tests.test_zero_diff # common 零 diff
# 逐个跑通所有 demo：
for d in robot_demo 3d_scene_demo video_demo game_demo 3d_full_demo integration_demo; do
  $PY -m examples.$d || echo "FAIL: $d"
done
```

**总通过判据**：
1. 全量 pytest 绿（V1/V2 不回归，V3/V4/V5 新增全绿）。
2. 所有 demo 跑通。
3. `common/` git diff 为空（三个版本全程未改 common）。
4. 各版本边界声明齐全。

---

## 5. 失败处理

- 任何一关不过 → **停下来汇报**，不要带病进下一版本。
- common 出现 diff → 说明场景泄漏，回读 `common-contract.md` §11 冻结纪律，用 payload/meta/新实现解决，不改 common。
- 前一版本回归 → 先修回归再推进新版本。
- 记录每个版本的实际测试计数与结果，填入 `model-integration-runbook.md` 的测试报告模板对应栏目。
