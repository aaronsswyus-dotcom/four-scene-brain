# branches/game — 游戏分支（V3 · 全 mock · 双方向）

> target=`game` ｜ modality=`pixel` ｜ backbone：V3 全 mock，真 MarioGPT / GameGen-O / OASIS 走 Azure（接入前过 engineering-setup §2 T1–T5 门禁）
> ⚠️ **边界声明**：V3 验证编排内核 + 接口 + 飞轮在**像素阵营第二个场景**同样成立，**不证明关卡好玩或推演逼真**。mock 生成的是确定性占位网格，真质量靠真模型 on Azure。

## 阵营差异（vs robot/3d）

game 属**像素阵营**，与 video 同营，**不继承** `PhysicalWorldModelBase`（物理先验不适用），独立实现全部接口。backbone 通过 `GameBackbone` 防腐层接入，换真模型只改 `adapter.py` 一行。

## 双方向（D-V3-1）：一个 target，两种生成

game **共享唯一 target=`game`**，用 `direction` 旋钮在 **build 期**选择生成方向 —— **绝不引入新 target，绝不进 common/orchestrator**：

| direction | 输入 → 输出 | 类比 |
|---|---|---|
| `level`（默认） | 文本 → 2D 平台关卡瓦片图（P/G/金币/敌人/陷阱） | 「文生关卡」MarioGPT |
| `worldmodel` | 状态 + 动作 → 帧序列（动作条件推演） | 「可玩世界模型」OASIS/GameGen |

切换：`register(reg, direction="worldmodel")` 或 `build_bundle(direction=...)`。

## State.payload 结构（分支冻结，为将来换真模型定死）

**direction=`level`：**
```
direction:         "level"
level_map:         list[str]  # 瓦片行，'#'墙 '.'空 'P'玩家 'G'终点 'C'金币 'E'敌人 'H'陷阱
width, height:     int        # 网格尺寸（[8,32] x [6,16]）
entities:          dict       # 各实体坐标/数量
theme:             str        # 主题（grass/cave/sky...）
text_prompt:       str        # 文本描述（驱动生成）
scene_description: str        # backbone 场景理解
refined_times:     int        # 重试细化次数
meta:              dict       # backbone 附加（seed 等）
```

**direction=`worldmodel`：**
```
direction:         "worldmodel"
frames:            list[grid] # 帧序列，每帧 0/1 网格（mock：一个方块按动作平移）
fps:               int        # 帧率（默认 12）
resolution:        [w, h]     # 分辨率（默认 [16,12]）
action_history:    list       # 历史动作
current_action:    str        # 当前动作（right/left/up/down）
text_prompt:       str
scene_description: str
refined_times:     int
meta:              dict
```

## 成功判定（Critic，按 direction 分派，硬指标优先）

**direction=`level`（可玩性）：**
- 恰好 1 个 `P`、1 个 `G`
- BFS 可达性：P → G 可达（敌人/陷阱可穿过，只有 `#` 挡路）
- 四周边界闭合（不漏）
- 无悬空实体（每个 C/E/H 正下方须为 `#`）
- 尺寸 width∈[8,32]、height∈[6,16]
- 软指标：theme/entity 关键词与 prompt 重叠

**direction=`worldmodel`（动作一致性 + 帧质量）：**
- 帧数 ≥ 4、fps ≥ 8、resolution ≥ [8,8]
- 帧间存在非零差异（有运动）
- 质心沿 `current_action` 方向漂移（方向一致性）
- 软指标：scene_description 与 prompt 重叠

判定来源写入 `Verification.meta.verification_source`（如 `level:reachable` / `wm:direction`），带 direction 便于飞轮分组。
硬指标未过 → `RETRYABLE_QUALITY`（回 S7，WAM 细化重试）；结构损坏/未知 direction → `STRUCTURAL_INFEASIBLE`。

## SafetyGate（双模式，adapter 内可配置）

| 模式 | 检查 | 结果 |
|---|---|---|
| `audit`（默认） | text_prompt 含 gore/血腥/explicit 等关键词 | **BLOCK**（降级 re-map 修不了，保持 BLOCK） |
| `audit` | level 尺寸越界 / worldmodel 分辨率<[8,8] 或帧<4 | **DEGRADE**（降级 re-map 钳制到安全下限 → 重检 PASS） |
| `audit` | 一切正常 | PASS |
| `passthrough` | 无检查 | PASS |

> **内容质量 vs 内容合规分离**：Critic 管质量（可玩/一致），SafetyGate 管合规。关键词表保守（宁可漏不可错杀）——「打僵尸/战斗/怪物」等正常游戏语境**不**算 gore。

## Backbone 接入（防腐层）

`wam.py` 只通过 `GameBackbone.generate(prompt, config)` 调 backbone，**不直接调任何模型 API**。config 必带 `"direction"`，返回 dict 必带 `"direction"` + 该方向字段。
- `backbone="mock"`（V3 默认）→ `MockGameBackbone`（确定性网格；level 用 sha256 布图 + 走廊可达，worldmodel 方块按动作平移；retry 收敛）
- `backbone="mariogpt-azure"` / `"gamegen-azure"` / `"oasis-azure"` → `NotImplementedError`（T1–T5 门禁未过）

换真 backbone：新增 `backbone_<name>.py`（实现 `GameBackbone`）+ 改 `adapter.py` 一行，其余文件全不动。V3 已按 oss-list-v3 §4.3 预置 3 个占位 stub（`backbone_gamegen.py` / `backbone_oasis.py` / `backbone_mariogpt.py`），均 `raise NotImplementedError`，仅定死接口形态，过 T1–T5 门禁后再填真实实现。

## 运行

```
python -m examples.game_demo          # 5 场景端到端（level/worldmodel/重试/BLOCK/PASS）
python -m tests.test_game_branch      # 17 项分支测试（含 Critic 正确性）
python -m pytest tests/test_game_branch.py -v
```

## 文件

| 文件 | 接口 | 说明 |
|---|---|---|
| scene_objects.py | — | 游戏关键词词汇表（主题/实体/动作/元素，中英双语），WAM+Critic 共用 |
| backbone_interface.py | GameBackbone | 防腐层抽象接口（config/返回值必带 direction） |
| backbone_mock.py | GameBackbone | Mock 实现：level 布图（走廊可达/challenge 封墙）+ worldmodel 方块平移，均确定性 |
| backbone_gamegen.py | GameBackbone | 方向 B 主推（GameGen-O on Azure）占位 stub；未过 T1–T5 门禁前 `generate` 抛 `NotImplementedError` |
| backbone_oasis.py | GameBackbone | 方向 B 备选（OASIS）占位 stub；同上 |
| backbone_mariogpt.py | GameBackbone | 方向 A 主推（MarioGPT）占位 stub；同上 |
| wam.py | WorldModel | GameWAM，注入 backbone，从 goal.constraints 取 direction，转发 retry |
| critic.py | Critic | 按 direction 分派：level 可玩性（BFS/边界/悬空/尺寸）+ worldmodel 动作一致性 |
| primitives.py | PrimitiveLibrary | level 统计基元 / worldmodel frame_step+action_apply；game_spec 塞进 meta 透传 |
| mapper.py | Mapper | 基元 → 游戏 Executable；degrade 时钳制尺寸/帧数到安全下限 |
| executor.py | Executor | level 写 level_*.json + .txt(ASCII)；worldmodel 写 replay_*.json（纯 stdlib） |
| safety_gate.py | SafetyGate | 双模式（audit/passthrough） |
| adapter.py | — | 防腐层 + `register(registry, direction, backbone, safety_mode)`，backbone/方向唯一配置点 |
